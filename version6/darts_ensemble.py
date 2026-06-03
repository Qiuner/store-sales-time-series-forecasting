import os
import warnings

import numpy as np
import pandas as pd
from darts import TimeSeries
from darts.dataprocessing import Pipeline
from darts.dataprocessing.transformers import InvertibleMapper, Scaler, StaticCovariatesTransformer
from darts.dataprocessing.transformers.missing_values_filler import MissingValuesFiller
from darts.metrics import rmsle
from darts.models import LightGBMModel, LinearRegressionModel, XGBModel
from darts.models.filtering.moving_average_filter import MovingAverageFilter
from sklearn.preprocessing import OneHotEncoder
from tqdm import tqdm

warnings.filterwarnings("ignore")
os.environ["LIGHTGBM_VERBOSITY"] = "-1"


# ==================== 参数与因子说明 ====================
# BASE_DIR:
#   数据文件所在根目录，默认使用仓库根目录。
# TRAIN_PATH / TEST_PATH / OIL_PATH / STORE_PATH / TRANSACTION_PATH / HOLIDAY_PATH:
#   各原始数据表路径。
# SUBMISSION_PATH:
#   version6 主线方案的提交文件输出路径。
# 这个版本使用的主要因子:
#   1. target series: 按 family 拆分后的多门店销量序列。
#   2. static covariates: city / state / type / cluster。
#   3. past covariates: transactions。
#   4. future covariates: oil、onpromotion、日期索引、work_day、筛选后的节假日。
#   5. future moving-average covariates: oil_ma7 / 28、onpromotion_ma7 / 28。
#   6. 多组 lags: 7、63、365、730，用于覆盖短中长期季节性。
# 这个版本的核心结构:
#   先分别训练 LightGBM 与 XGBoost 多分支集成，再做模型间平均融合。
BASE_DIR = "."
TRAIN_PATH = os.path.join(BASE_DIR, "train.csv")
TEST_PATH = os.path.join(BASE_DIR, "test.csv")
OIL_PATH = os.path.join(BASE_DIR, "oil.csv")
STORE_PATH = os.path.join(BASE_DIR, "stores.csv")
TRANSACTION_PATH = os.path.join(BASE_DIR, "transactions.csv")
HOLIDAY_PATH = os.path.join(BASE_DIR, "holidays_events.csv")
SUBMISSION_PATH = os.path.join(BASE_DIR, "version6", "submission_darts_ensemble.csv")


# ==================== 通用打印工具 ====================
def cprint(title: str, *args: object) -> None:
    print("=" * len(title))
    print(title)
    print("=" * len(title))
    for arg in args:
        print(arg)


# ==================== 数据读取 ====================
def load_data():
    train = pd.read_csv(TRAIN_PATH, parse_dates=["date"])
    test = pd.read_csv(TEST_PATH, parse_dates=["date"])
    oil = pd.read_csv(OIL_PATH, parse_dates=["date"]).rename(columns={"dcoilwtico": "oil"})
    store = pd.read_csv(STORE_PATH)
    transaction = pd.read_csv(TRANSACTION_PATH, parse_dates=["date"])
    holiday = pd.read_csv(HOLIDAY_PATH, parse_dates=["date"])
    return train, test, oil, store, transaction, holiday


# ==================== 原始数据预处理 ====================
# 补齐训练面板中的缺失日期与缺失组合，保证后续多序列建模输入规整。
def preprocess_train(train: pd.DataFrame) -> tuple[pd.DataFrame, list[str], pd.Timestamp, pd.Timestamp]:
    train_start = train.date.min()
    train_end = train.date.max()
    missing_dates = pd.date_range(train_start, train_end).difference(train.date.unique())
    missing_dates = missing_dates.strftime("%Y-%m-%d").tolist()

    multi_idx = pd.MultiIndex.from_product(
        [pd.date_range(train_start, train_end), train.store_nbr.unique(), train.family.unique()],
        names=["date", "store_nbr", "family"],
    )
    train = train.set_index(["date", "store_nbr", "family"]).reindex(multi_idx).reset_index()
    train[["sales", "onpromotion"]] = train[["sales", "onpromotion"]].fillna(0.0)
    train["id"] = train["id"].interpolate(method="linear", limit_direction="both")
    return train, missing_dates, train_start, train_end


# 补齐油价日期并插值，避免未来协变量断裂。
def preprocess_oil(oil: pd.DataFrame, train_start: pd.Timestamp, test_end: pd.Timestamp) -> pd.DataFrame:
    oil = oil.merge(
        pd.DataFrame({"date": pd.date_range(train_start, test_end)}),
        on="date",
        how="outer",
    ).sort_values("date", ignore_index=True)
    oil["oil"] = oil["oil"].interpolate(method="linear", limit_direction="both")
    return oil


# 用门店销量信息辅助补齐 transaction，并在停业日强制置零。
def preprocess_transactions(train: pd.DataFrame, transaction: pd.DataFrame) -> pd.DataFrame:
    store_sales = train.groupby(["date", "store_nbr"]).sales.sum().reset_index()
    transaction = transaction.merge(store_sales, on=["date", "store_nbr"], how="outer").sort_values(
        ["date", "store_nbr"], ignore_index=True
    )
    transaction.loc[transaction.sales.eq(0), "transactions"] = 0.0
    transaction = transaction.drop(columns=["sales"])
    transaction["transactions"] = transaction.groupby("store_nbr", group_keys=False)["transactions"].apply(
        lambda x: x.interpolate(method="linear", limit_direction="both")
    )
    return transaction


# ==================== 节假日筛选与编码 ====================
# 只保留当前主线里验证效果较稳定的全国性节假日因子，并单独处理补班日。
def process_holidays(holiday: pd.DataFrame, store: pd.DataFrame):
    def process_holiday(s: str) -> str:
        if "futbol" in s:
            return "futbol"
        to_remove = list(set(store.city.str.lower()) | set(store.state.str.lower()))
        for w in to_remove:
            s = s.replace(w, "")
        return s

    holiday = holiday.copy()
    holiday["description"] = holiday.apply(
        lambda x: x.description.lower().replace(x.locale_name.lower(), ""),
        axis=1,
    ).apply(process_holiday)
    holiday["description"] = (
        holiday["description"]
        .replace(r"[+-]\d+|\b(de|del|traslado|recupero|puente|-)\b", "", regex=True)
        .replace(r"\s+|-", " ", regex=True)
        .str.strip()
    )
    holiday = holiday[holiday.transferred.eq(False)].copy()

    work_days = holiday[holiday.type.eq("Work Day")][["date", "type"]].rename(columns={"type": "work_day"}).reset_index(drop=True)
    work_days["work_day"] = work_days["work_day"].notna().astype(int)
    holiday = holiday[holiday.type != "Work Day"].reset_index(drop=True)

    national_holidays = holiday[holiday.locale.eq("National")][["date", "description"]].reset_index(drop=True)
    national_holidays = national_holidays[~national_holidays.duplicated()]
    national_holidays = pd.get_dummies(national_holidays, columns=["description"], prefix="nat")
    national_holidays = national_holidays.groupby("date").sum().reset_index()
    national_holidays = national_holidays.rename(columns={"nat_primer grito independencia": "nat_primer grito"})

    selected_holidays = [
        "nat_terremoto",
        "nat_navidad",
        "nat_dia la madre",
        "nat_dia trabajo",
        "nat_primer dia ano",
        "nat_futbol",
        "nat_dia difuntos",
    ]
    for col in selected_holidays:
        if col not in national_holidays.columns:
            national_holidays[col] = 0

    keep_national_holidays = national_holidays[["date", *selected_holidays]]
    return work_days, keep_national_holidays, selected_holidays


# ==================== 全量特征面板合并 ====================
def merge_all_data(
    train: pd.DataFrame,
    test: pd.DataFrame,
    oil: pd.DataFrame,
    store: pd.DataFrame,
    transaction: pd.DataFrame,
    work_days: pd.DataFrame,
    keep_national_holidays: pd.DataFrame,
    selected_holidays: list[str],
    missing_dates: list[str],
) -> pd.DataFrame:
    data = (
        pd.concat([train, test], axis=0, ignore_index=True)
        .merge(transaction, on=["date", "store_nbr"], how="left")
        .merge(oil, on="date", how="left")
        .merge(store, on="store_nbr", how="left")
        .merge(work_days, on="date", how="left")
        .merge(keep_national_holidays, on="date", how="left")
        .sort_values(["date", "store_nbr", "family"], ignore_index=True)
    )

    data[["work_day", *selected_holidays]] = data[["work_day", *selected_holidays]].fillna(0)
    data["day"] = data.date.dt.day
    data["month"] = data.date.dt.month
    data["year"] = data.date.dt.year
    data["day_of_week"] = data.date.dt.dayofweek
    data["day_of_year"] = data.date.dt.dayofyear
    data["week_of_year"] = data.date.dt.isocalendar().week.astype(int)
    data["date_index"] = data.date.factorize()[0]

    zero_sales_dates = missing_dates + [f"{j}-01-01" for j in range(2013, 2018)]
    data.loc[
        (data.date.isin(zero_sales_dates)) & (data.sales.eq(0)) & (data.onpromotion.eq(0)),
        ["sales", "onpromotion"],
    ] = np.nan

    data["store_nbr"] = data["store_nbr"].apply(lambda x: f"store_nbr_{x}")
    data["cluster"] = data["cluster"].apply(lambda x: f"cluster_{x}")
    data["type"] = data["type"].apply(lambda x: f"type_{x}")
    data["city"] = data["city"].apply(lambda x: f"city_{x.lower()}")
    data["state"] = data["state"].apply(lambda x: f"state_{x.lower()}")
    return data


# ==================== Darts 预处理流水线 ====================
# 统一负责缺失填补、静态协变量编码、对数变换和缩放。
def get_pipeline(static_covs_transform=False, log_transform=False):
    steps = [MissingValuesFiller(n_jobs=-1)]
    if static_covs_transform:
        steps.append(
            StaticCovariatesTransformer(
                transformer_cat=OneHotEncoder(),
                n_jobs=-1,
            )
        )
    if log_transform:
        steps.append(
            InvertibleMapper(
                fn=np.log1p,
                inverse_fn=np.expm1,
                n_jobs=-1,
            )
        )
    steps.append(Scaler())
    return Pipeline(steps)


# ==================== 目标序列构造 ====================
# 以 family 为外层分组，把每个门店的销量转换成 Darts TimeSeries。
def get_target_series(data: pd.DataFrame, train_end: pd.Timestamp, static_cols, log_transform=True):
    target_dict = {}
    pipe_dict = {}
    id_dict = {}

    for fam in tqdm(data.family.unique(), desc="Extract target"):
        df = data[(data.family.eq(fam)) & (data.date.le(train_end.strftime("%Y-%m-%d")))]
        pipe = get_pipeline(True, log_transform=log_transform)
        target = TimeSeries.from_group_dataframe(
            df=df,
            time_col="date",
            value_cols="sales",
            group_cols="store_nbr",
            static_cols=static_cols,
        )
        target_id = []
        for t in target:
            static_df = t.static_covariates
            store_nbr = static_df["store_nbr"].iloc[0]
            target_id.append({"store_nbr": store_nbr, "family": fam})
        id_dict[fam] = target_id
        target = pipe.fit_transform(target)
        target_dict[fam] = [t.astype(np.float32) for t in target]
        pipe_dict[fam] = pipe[2:]
    return target_dict, pipe_dict, id_dict


# ==================== 协变量序列构造 ====================
# past covariates 只保留历史可见信息，future covariates 则覆盖训练和预测区间。
def get_covariates(
    data: pd.DataFrame,
    train_end: pd.Timestamp,
    past_cols,
    future_cols,
    past_ma_cols=None,
    future_ma_cols=None,
    past_window_sizes=[7, 28],
    future_window_sizes=[7, 28],
):
    past_dict = {}
    future_dict = {}
    covs_pipe = get_pipeline()

    for fam in tqdm(data.family.unique(), desc="Extract covariates"):
        df = data[data.family.eq(fam)]

        past_covs = TimeSeries.from_group_dataframe(
            df=df[df.date.le(train_end.strftime("%Y-%m-%d"))],
            time_col="date",
            value_cols=past_cols,
            group_cols="store_nbr",
        )
        past_covs = [p.with_static_covariates(None) for p in past_covs]
        past_covs = covs_pipe.fit_transform(past_covs)
        if past_ma_cols is not None:
            for size in past_window_sizes:
                ma_filter = MovingAverageFilter(window=size)
                old_names = [f"rolling_mean_{size}_{col}" for col in past_ma_cols]
                new_names = [f"{col}_ma{size}" for col in past_ma_cols]
                past_ma_covs = [
                    ma_filter.filter(p[past_ma_cols]).with_columns_renamed(old_names, new_names) for p in past_covs
                ]
                past_covs = [p.stack(p_ma) for p, p_ma in zip(past_covs, past_ma_covs)]
        past_dict[fam] = [p.astype(np.float32) for p in past_covs]

        future_covs = TimeSeries.from_group_dataframe(
            df=df,
            time_col="date",
            value_cols=future_cols,
            group_cols="store_nbr",
        )
        future_covs = [f.with_static_covariates(None) for f in future_covs]
        future_covs = covs_pipe.fit_transform(future_covs)
        if future_ma_cols is not None:
            for size in future_window_sizes:
                ma_filter = MovingAverageFilter(window=size)
                old_names = [f"rolling_mean_{size}_{col}" for col in future_ma_cols]
                new_names = [f"{col}_ma{size}" for col in future_ma_cols]
                future_ma_covs = [
                    ma_filter.filter(f[future_ma_cols]).with_columns_renamed(old_names, new_names) for f in future_covs
                ]
                future_covs = [f.stack(f_ma) for f, f_ma in zip(future_covs, future_ma_covs)]
        future_dict[fam] = [f.astype(np.float32) for f in future_covs]

    return past_dict, future_dict


class Trainer:
    # ==================== 训练器模块 ====================
    # 集中封装协变量裁剪、模型构建、单 family 预测和集成逻辑。
    def __init__(
        self,
        target_dict,
        pipe_dict,
        id_dict,
        past_dict,
        future_dict,
        forecast_horizon,
        folds,
        zero_fc_window,
        static_covs=None,
        past_covs=None,
        future_covs=None,
    ):
        self.target_dict = target_dict.copy()
        self.pipe_dict = pipe_dict.copy()
        self.id_dict = id_dict.copy()
        self.past_dict = past_dict.copy()
        self.future_dict = future_dict.copy()
        self.forecast_horizon = forecast_horizon
        self.folds = folds
        self.zero_fc_window = zero_fc_window
        self.static_covs = static_covs
        self.past_covs = past_covs
        self.future_covs = future_covs
        self.setup()

    def setup(self):
        # 根据实验设置裁剪静态协变量、过去协变量和未来协变量。
        for fam in tqdm(self.target_dict.keys(), desc="Setup"):
            if self.static_covs != "keep_all":
                if self.static_covs is not None:
                    target = self.target_dict[fam]
                    keep_static = [col for col in target[0].static_covariates.columns if col.startswith(tuple(self.static_covs))]
                    static_covs_df = [t.static_covariates[keep_static] for t in target]
                    self.target_dict[fam] = [t.with_static_covariates(d) for t, d in zip(target, static_covs_df)]
                else:
                    self.target_dict[fam] = [t.with_static_covariates(None) for t in self.target_dict[fam]]

            if self.past_covs != "keep_all":
                if self.past_covs is not None:
                    self.past_dict[fam] = [p[self.past_covs] for p in self.past_dict[fam]]
                else:
                    self.past_dict[fam] = None

            if self.future_covs != "keep_all":
                if self.future_covs is not None:
                    self.future_dict[fam] = [p[self.future_covs] for p in self.future_dict[fam]]
                else:
                    self.future_dict[fam] = None

    @staticmethod
    def clip(array):
        return np.clip(array, a_min=0.0, a_max=None)

    def train_valid_split(self, target, length):
        # 预留给线下切分使用，当前主线主要直接做全量预测。
        train = [t[:-length] for t in target]
        valid_end_idx = -length + self.forecast_horizon
        if valid_end_idx >= 0:
            valid_end_idx = None
        valid = [t[-length:valid_end_idx] for t in target]
        return train, valid

    def get_models(self, model_names, model_configs):
        # 按配置动态构建 lr / lgbm / xgb 多分支模型。
        models = {
            "lr": LinearRegressionModel,
            "lgbm": LightGBMModel,
            "xgb": XGBModel,
        }
        configs = [cfg.copy() for cfg in model_configs]
        if "xgb" in model_names:
            xgb_idx = np.where(np.array(model_names) == "xgb")[0]
            for idx in xgb_idx:
                configs[idx] = {"tree_method": "hist", **configs[idx]}
        built = []
        for j, name in enumerate(model_names):
            cfg = configs[j]
            if name == "lgbm":
                cfg = {"verbosity": -1, **cfg}
            elif name == "xgb":
                cfg = {"verbosity": 0, **cfg}
            built.append(models[name](**cfg))
        return built

    def generate_forecasts(self, models, train, pipe, past_covs, future_covs, drop_before):
        # 对单个 family 的所有门店序列做多模型预测，并在门店近期全零时强制输出零预测。
        if drop_before is not None:
            date = pd.Timestamp(drop_before) - pd.Timedelta(days=1)
            train = [t.drop_before(date) for t in train]

        inputs = {"series": train, "past_covariates": past_covs, "future_covariates": future_covs}
        zero_pred = pd.DataFrame(
            {"date": pd.date_range(train[0].end_time(), periods=self.forecast_horizon + 1)[1:], "sales": np.zeros(self.forecast_horizon)}
        )
        zero_pred = TimeSeries.from_dataframe(df=zero_pred, time_col="date", value_cols="sales")

        pred_list = []
        ens_pred = [0 for _ in range(len(train))]

        for m in models:
            m.fit(**inputs)
            pred = m.predict(n=self.forecast_horizon, **inputs)
            pred = pipe.inverse_transform(pred)

            for j in range(len(train)):
                if train[j][-self.zero_fc_window :].values().sum() == 0:
                    pred[j] = zero_pred

            pred = [p.map(self.clip) for p in pred]
            pred_list.append(pred)
            for j in range(len(ens_pred)):
                ens_pred[j] += pred[j] / len(models)

        return pred_list, ens_pred

    def metric(self, valid, pred):
        return rmsle(valid, pred, inter_reduction=np.mean)

    def ensemble_predict(self, model_names, model_configs, drop_before=None):
        # 对所有 family 执行预测，并把 TimeSeries 结果还原回表格形式。
        forecasts = []
        for fam in tqdm(self.target_dict.keys(), desc="Forecast"):
            target = self.target_dict[fam]
            pipe = self.pipe_dict[fam]
            target_id = self.id_dict[fam]
            past_covs = self.past_dict[fam]
            future_covs = self.future_dict[fam]
            models = self.get_models(model_names, model_configs)
            _, ens_pred = self.generate_forecasts(models, target, pipe, past_covs, future_covs, drop_before)

            ens_pred_dataframes = []
            for p, i in zip(ens_pred, target_id):
                df = p.to_dataframe().reset_index()
                df = df.assign(**i)
                ens_pred_dataframes.append(df)
            ens_pred_df = pd.concat(ens_pred_dataframes, axis=0)
            forecasts.append(ens_pred_df)

        forecasts = pd.concat(forecasts, axis=0)
        forecasts = forecasts.rename_axis(None, axis=1).reset_index(drop=True)
        return forecasts


# ==================== 提交文件整理 ====================
def prepare_submission(test: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    predictions = predictions.copy()
    predictions["store_nbr"] = predictions["store_nbr"].replace("store_nbr_", "", regex=True).astype(int)
    submission = test.merge(predictions, on=["date", "store_nbr", "family"], how="left")[["id", "sales"]]
    submission["sales"] = submission["sales"].clip(lower=0)
    return submission


# ==================== 主流程入口 ====================
# version6 先做 LGBM 多分支平均，再做 XGB 多分支平均，最后两者 1:1 融合。
def main():
    train, test, oil, store, transaction, holiday = load_data()
    test_end = test.date.max()

    train, missing_dates, train_start, train_end = preprocess_train(train)
    oil = preprocess_oil(oil, train_start, test_end)
    transaction = preprocess_transactions(train, transaction)
    work_days, keep_national_holidays, selected_holidays = process_holidays(holiday, store)
    data = merge_all_data(
        train,
        test,
        oil,
        store,
        transaction,
        work_days,
        keep_national_holidays,
        selected_holidays,
        missing_dates,
    )

    static_cols = ["city", "state", "type", "cluster"]
    target_dict, pipe_dict, id_dict = get_target_series(data, train_end, static_cols)

    past_cols = ["transactions"]
    future_cols = [
        "oil",
        "onpromotion",
        "day",
        "month",
        "year",
        "day_of_week",
        "day_of_year",
        "week_of_year",
        "date_index",
        "work_day",
        *selected_holidays,
    ]
    future_ma_cols = ["oil", "onpromotion"]
    past_dict, future_dict = get_covariates(
        data,
        train_end,
        past_cols=past_cols,
        future_cols=future_cols,
        future_ma_cols=future_ma_cols,
    )

    trainer = Trainer(
        target_dict=target_dict,
        pipe_dict=pipe_dict,
        id_dict=id_dict,
        past_dict=past_dict,
        future_dict=future_dict,
        forecast_horizon=16,
        folds=1,
        zero_fc_window=21,
        static_covs="keep_all",
        past_covs="keep_all",
        future_covs="keep_all",
    )

    base_config = {
        "random_state": 0,
        "lags": 63,
        "lags_past_covariates": list(range(-16, -23, -1)),
        "lags_future_covariates": (14, 1),
        "output_chunk_length": 1,
    }

    gbdt_config1 = {**base_config}
    gbdt_config2 = {**base_config, "lags": 7}
    gbdt_config3 = {**base_config, "lags": 365}
    gbdt_config4 = {**base_config, "lags": 730}
    ens_models = ["lgbm", "lgbm", "lgbm", "lgbm"]
    ens_configs = [gbdt_config1, gbdt_config2, gbdt_config3, gbdt_config4]

    xgb_config1 = {
        **base_config,
        "n_estimators": 100,
        "learning_rate": 0.1,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    }
    xgb_config2 = {**xgb_config1, "lags": 7}
    xgb_config3 = {**xgb_config1, "lags": 365}
    xgb_config4 = {**xgb_config1, "lags": 730}
    xgb_models = ["xgb", "xgb", "xgb", "xgb"]
    xgb_configs = [xgb_config1, xgb_config2, xgb_config3, xgb_config4]

    predictions1 = trainer.ensemble_predict(model_names=ens_models, model_configs=ens_configs)
    predictions2 = trainer.ensemble_predict(model_names=ens_models, model_configs=ens_configs, drop_before="2015-01-01")
    final_predictions = predictions1.merge(predictions2, on=["date", "store_nbr", "family"], how="left")
    final_predictions["sales"] = final_predictions[["sales_x", "sales_y"]].mean(axis=1)
    final_predictions = final_predictions.drop(columns=["sales_x", "sales_y"])

    xgb_predictions1 = trainer.ensemble_predict(model_names=xgb_models, model_configs=xgb_configs)
    xgb_predictions2 = trainer.ensemble_predict(model_names=xgb_models, model_configs=xgb_configs, drop_before="2015-01-01")
    xgb_final = xgb_predictions1.merge(xgb_predictions2, on=["date", "store_nbr", "family"], how="left")
    xgb_final["sales"] = xgb_final[["sales_x", "sales_y"]].mean(axis=1)
    xgb_final = xgb_final.drop(columns=["sales_x", "sales_y"])

    final_ensemble = final_predictions.merge(
        xgb_final, on=["date", "store_nbr", "family"], suffixes=("_lgbm", "_xgb"), how="left"
    )
    final_ensemble["sales"] = final_ensemble[["sales_lgbm", "sales_xgb"]].mean(axis=1)
    final_ensemble = final_ensemble.drop(columns=["sales_lgbm", "sales_xgb"])

    submission = prepare_submission(test, final_ensemble)
    submission.to_csv(SUBMISSION_PATH, index=False)
    print(f"Saved submission to {SUBMISSION_PATH}")
    print(submission.head())


if __name__ == "__main__":
    main()
