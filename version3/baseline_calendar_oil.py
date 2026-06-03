import numpy as np
import pandas as pd


# ==================== 参数与因子说明 ====================
# TRAIN_PATH / TEST_PATH / STORES_PATH / HOLIDAYS_PATH / OIL_PATH:
#   原始数据表路径。
# VALIDATION_START:
#   线下验证起点日期。
# META_TRAIN_DAYS:
#   用于训练岭回归校准层的近端样本窗口长度。
# RIDGE_ALPHA:
#   岭回归正则强度，控制校准层复杂度。
# OUTPUT_PATH:
#   当前版本提交文件输出路径。
# 这个版本使用的主要因子:
#   1. version2 的分层移动平均统计量。
#   2. 节假日类型、作用范围和条目数。
#   3. 原油价格及 7/14 日平滑均值。
#   4. 月初/月末等补充时间因子。
#   5. onpromotion 的对数变换。
TRAIN_PATH = "train.csv"
TEST_PATH = "test.csv"
STORES_PATH = "stores.csv"
HOLIDAYS_PATH = "holidays_events.csv"
OIL_PATH = "oil.csv"
SAMPLE_SUBMISSION_PATH = "sample_submission.csv"

VALIDATION_START = "2017-08-01"
META_TRAIN_DAYS = 31
RIDGE_ALPHA = 3.0

OUTPUT_PATH = "version3/submission_calendar_oil.csv"


# ==================== 评估指标 ====================
def rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.clip(y_true, 0, None)
    y_pred = np.clip(y_pred, 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


# ==================== 基础时间特征 ====================
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["dayofweek"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["is_month_start"] = df["date"].dt.is_month_start.astype(np.int8)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(np.int8)
    return df


# ==================== 外部协变量准备 ====================
# 原油价格先补齐缺失，再构造平滑均值因子。
def prepare_oil() -> pd.DataFrame:
    oil = pd.read_csv(OIL_PATH)
    oil["date"] = pd.to_datetime(oil["date"])
    oil = oil.sort_values("date")
    oil["dcoilwtico"] = oil["dcoilwtico"].ffill().bfill()
    oil["oil_7d_mean"] = oil["dcoilwtico"].rolling(7, min_periods=1).mean()
    oil["oil_14d_mean"] = oil["dcoilwtico"].rolling(14, min_periods=1).mean()
    return oil


# ==================== 节假日特征工程 ====================
# 将不同作用范围的节假日统一映射到 store-date 粒度。
def _holiday_flags(df: pd.DataFrame, scope_col: str) -> pd.DataFrame:
    df = df.copy()
    df["is_holiday"] = (df["type"] == "Holiday").astype(np.int8)
    df["is_additional"] = (df["type"] == "Additional").astype(np.int8)
    df["is_bridge"] = (df["type"] == "Bridge").astype(np.int8)
    df["is_event"] = (df["type"] == "Event").astype(np.int8)
    df["is_transfer"] = (df["type"] == "Transfer").astype(np.int8)
    df["is_work_day"] = (df["type"] == "Work Day").astype(np.int8)
    df["is_transferred"] = df["transferred"].astype(np.int8)
    df["holiday_row_count"] = 1
    df["is_national"] = 0
    df["is_regional"] = 0
    df["is_local"] = 0
    df[scope_col] = 1
    return df[
        [
            "date",
            "store_nbr",
            "is_holiday",
            "is_additional",
            "is_bridge",
            "is_event",
            "is_transfer",
            "is_work_day",
            "is_transferred",
            "holiday_row_count",
            "is_national",
            "is_regional",
            "is_local",
        ]
    ]


def prepare_store_date_holidays(base_df: pd.DataFrame) -> pd.DataFrame:
    stores = pd.read_csv(STORES_PATH)
    holidays = pd.read_csv(HOLIDAYS_PATH)

    stores = stores[["store_nbr", "city", "state"]].copy()
    holidays["date"] = pd.to_datetime(holidays["date"])

    unique_store_dates = base_df[["date", "store_nbr"]].drop_duplicates().merge(stores, on="store_nbr", how="left")

    nat = unique_store_dates[["date", "store_nbr"]].merge(
        holidays[holidays["locale"] == "National"][["date", "type", "transferred"]],
        on="date",
        how="left",
    )
    nat = nat.dropna(subset=["type"])
    nat = _holiday_flags(nat, "is_national")

    reg = unique_store_dates[["date", "store_nbr", "state"]].merge(
        holidays[holidays["locale"] == "Regional"][["date", "locale_name", "type", "transferred"]],
        left_on=["date", "state"],
        right_on=["date", "locale_name"],
        how="left",
    )
    reg = reg.dropna(subset=["type"])
    reg = _holiday_flags(reg, "is_regional")

    loc = unique_store_dates[["date", "store_nbr", "city"]].merge(
        holidays[holidays["locale"] == "Local"][["date", "locale_name", "type", "transferred"]],
        left_on=["date", "city"],
        right_on=["date", "locale_name"],
        how="left",
    )
    loc = loc.dropna(subset=["type"])
    loc = _holiday_flags(loc, "is_local")

    all_holidays = pd.concat([nat, reg, loc], ignore_index=True)
    if all_holidays.empty:
        return unique_store_dates[["date", "store_nbr"]].assign(
            is_holiday=0,
            is_additional=0,
            is_bridge=0,
            is_event=0,
            is_transfer=0,
            is_work_day=0,
            is_transferred=0,
            holiday_row_count=0,
            is_national=0,
            is_regional=0,
            is_local=0,
        )

    agg = (
        all_holidays.groupby(["date", "store_nbr"], as_index=False)
        .agg(
            {
                "is_holiday": "max",
                "is_additional": "max",
                "is_bridge": "max",
                "is_event": "max",
                "is_transfer": "max",
                "is_work_day": "max",
                "is_transferred": "max",
                "holiday_row_count": "sum",
                "is_national": "max",
                "is_regional": "max",
                "is_local": "max",
            }
        )
    )
    return agg


# ==================== 特征合并 ====================
def enrich_features(df: pd.DataFrame, oil: pd.DataFrame, holidays_store_date: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(oil, on="date", how="left")
    df = df.merge(holidays_store_date, on=["date", "store_nbr"], how="left")

    holiday_cols = [
        "is_holiday",
        "is_additional",
        "is_bridge",
        "is_event",
        "is_transfer",
        "is_work_day",
        "is_transferred",
        "holiday_row_count",
        "is_national",
        "is_regional",
        "is_local",
    ]
    for col in holiday_cols:
        df[col] = df[col].fillna(0)

    df["dcoilwtico"] = df["dcoilwtico"].ffill().bfill()
    df["oil_7d_mean"] = df["oil_7d_mean"].ffill().bfill()
    df["oil_14d_mean"] = df["oil_14d_mean"].ffill().bfill()
    return df


# ==================== 基线统计与预测 ====================
def build_stats(train_df: pd.DataFrame, cutoff_date: pd.Timestamp) -> dict[str, pd.DataFrame | float]:
    history = train_df[train_df["date"] < cutoff_date].copy()

    recent_14 = history[history["date"] >= cutoff_date - pd.Timedelta(days=14)]
    recent_28 = history[history["date"] >= cutoff_date - pd.Timedelta(days=28)]
    recent_56 = history[history["date"] >= cutoff_date - pd.Timedelta(days=56)]

    stats = {
        "mean_14_sfd": recent_14.groupby(["store_nbr", "family", "dayofweek"], as_index=False)["sales"]
        .mean()
        .rename(columns={"sales": "pred_14_sfd"}),
        "mean_28_sfd": recent_28.groupby(["store_nbr", "family", "dayofweek"], as_index=False)["sales"]
        .mean()
        .rename(columns={"sales": "pred_28_sfd"}),
        "mean_56_sf": recent_56.groupby(["store_nbr", "family"], as_index=False)["sales"]
        .mean()
        .rename(columns={"sales": "pred_56_sf"}),
        "mean_56_fd": recent_56.groupby(["family", "dayofweek"], as_index=False)["sales"]
        .mean()
        .rename(columns={"sales": "pred_56_fd"}),
        "mean_family": history.groupby(["family"], as_index=False)["sales"]
        .mean()
        .rename(columns={"sales": "pred_family"}),
        "global_mean": float(history["sales"].mean()),
    }
    return stats


def predict_base(target_df: pd.DataFrame, stats: dict[str, pd.DataFrame | float]) -> np.ndarray:
    pred_df = target_df[["store_nbr", "family", "dayofweek", "onpromotion"]].copy()

    pred_df = pred_df.merge(stats["mean_14_sfd"], on=["store_nbr", "family", "dayofweek"], how="left")
    pred_df = pred_df.merge(stats["mean_28_sfd"], on=["store_nbr", "family", "dayofweek"], how="left")
    pred_df = pred_df.merge(stats["mean_56_sf"], on=["store_nbr", "family"], how="left")
    pred_df = pred_df.merge(stats["mean_56_fd"], on=["family", "dayofweek"], how="left")
    pred_df = pred_df.merge(stats["mean_family"], on=["family"], how="left")

    base_pred = (
        pred_df["pred_14_sfd"].fillna(0) * 0.45
        + pred_df["pred_28_sfd"].fillna(0) * 0.30
        + pred_df["pred_56_sf"].fillna(0) * 0.15
        + pred_df["pred_56_fd"].fillna(0) * 0.07
        + pred_df["pred_family"].fillna(stats["global_mean"]) * 0.03
    )
    promo_multiplier = 1.0 + 0.03 * np.log1p(pred_df["onpromotion"].to_numpy())
    return np.clip(base_pred.to_numpy() * promo_multiplier, 0, None)


# ==================== 校准层特征与模型 ====================
# 在移动平均基线之上，再用岭回归吸收节假日和油价等残差信息。
def make_meta_features(df: pd.DataFrame, base_pred: np.ndarray) -> pd.DataFrame:
    feat = pd.DataFrame(index=df.index)
    feat["log_base_pred"] = np.log1p(base_pred)
    feat["log_onpromotion"] = np.log1p(df["onpromotion"].to_numpy())
    feat["month"] = df["month"].to_numpy()
    feat["is_month_start"] = df["is_month_start"].to_numpy()
    feat["is_month_end"] = df["is_month_end"].to_numpy()
    feat["dcoilwtico"] = df["dcoilwtico"].to_numpy()
    feat["oil_7d_mean"] = df["oil_7d_mean"].to_numpy()
    feat["oil_14d_mean"] = df["oil_14d_mean"].to_numpy()
    feat["is_holiday"] = df["is_holiday"].to_numpy()
    feat["is_additional"] = df["is_additional"].to_numpy()
    feat["is_bridge"] = df["is_bridge"].to_numpy()
    feat["is_event"] = df["is_event"].to_numpy()
    feat["is_transfer"] = df["is_transfer"].to_numpy()
    feat["is_work_day"] = df["is_work_day"].to_numpy()
    feat["is_transferred"] = df["is_transferred"].to_numpy()
    feat["holiday_row_count"] = df["holiday_row_count"].to_numpy()
    feat["is_national"] = df["is_national"].to_numpy()
    feat["is_regional"] = df["is_regional"].to_numpy()
    feat["is_local"] = df["is_local"].to_numpy()
    return feat


def fit_ridge(X: pd.DataFrame, y: np.ndarray, alpha: float) -> dict[str, np.ndarray | list[str]]:
    columns = list(X.columns)
    x = X.to_numpy(dtype=np.float64)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0

    x_scaled = (x - mean) / std
    design = np.column_stack([np.ones(len(X)), x_scaled])

    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0

    beta = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return {"beta": beta, "mean": mean, "std": std, "columns": columns}


def predict_ridge(model: dict[str, np.ndarray | list[str]], X: pd.DataFrame) -> np.ndarray:
    x = X[model["columns"]].to_numpy(dtype=np.float64)
    x_scaled = (x - model["mean"]) / model["std"]
    design = np.column_stack([np.ones(len(X)), x_scaled])
    return design @ model["beta"]


# ==================== 验证与提交 ====================
def validate(train_df: pd.DataFrame) -> tuple[float, float]:
    valid_start = pd.Timestamp(VALIDATION_START)
    meta_start = valid_start - pd.Timedelta(days=META_TRAIN_DAYS)

    base_stats = build_stats(train_df, meta_start)

    meta_train = train_df[(train_df["date"] >= meta_start) & (train_df["date"] < valid_start)].copy()
    valid_df = train_df[train_df["date"] >= valid_start].copy()

    meta_train_base = predict_base(meta_train, base_stats)
    valid_base = predict_base(valid_df, base_stats)

    meta_x = make_meta_features(meta_train, meta_train_base)
    meta_y = np.log1p(meta_train["sales"].to_numpy())
    ridge_model = fit_ridge(meta_x, meta_y, RIDGE_ALPHA)

    valid_x = make_meta_features(valid_df, valid_base)
    valid_log_pred = predict_ridge(ridge_model, valid_x)
    valid_pred = np.expm1(valid_log_pred)

    base_score = rmsle(valid_df["sales"].to_numpy(), valid_base)
    calibrated_score = rmsle(valid_df["sales"].to_numpy(), valid_pred)
    return base_score, calibrated_score


def fit_submission(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    test_start = test_df["date"].min()
    meta_start = test_start - pd.Timedelta(days=META_TRAIN_DAYS)

    base_stats_for_meta = build_stats(train_df, meta_start)
    meta_train = train_df[(train_df["date"] >= meta_start) & (train_df["date"] < test_start)].copy()
    meta_train_base = predict_base(meta_train, base_stats_for_meta)

    meta_x = make_meta_features(meta_train, meta_train_base)
    meta_y = np.log1p(meta_train["sales"].to_numpy())
    ridge_model = fit_ridge(meta_x, meta_y, RIDGE_ALPHA)

    base_stats_for_test = build_stats(train_df, test_start)
    test_base = predict_base(test_df, base_stats_for_test)
    test_x = make_meta_features(test_df, test_base)
    test_log_pred = predict_ridge(ridge_model, test_x)
    test_pred = np.clip(np.expm1(test_log_pred), 0, None)

    submission = pd.read_csv(SAMPLE_SUBMISSION_PATH)
    submission["sales"] = test_pred
    return submission


# ==================== 主流程入口 ====================
def main() -> None:
    train = pd.read_csv(TRAIN_PATH, usecols=["date", "store_nbr", "family", "sales", "onpromotion"])
    test = pd.read_csv(TEST_PATH, usecols=["id", "date", "store_nbr", "family", "onpromotion"])

    train = add_time_features(train)
    test = add_time_features(test)

    combined_dates = pd.concat([train[["date", "store_nbr"]], test[["date", "store_nbr"]]], ignore_index=True)
    holidays_store_date = prepare_store_date_holidays(combined_dates)
    oil = prepare_oil()

    train = enrich_features(train, oil, holidays_store_date)
    test = enrich_features(test, oil, holidays_store_date)

    base_score, calibrated_score = validate(train)
    print(f"Validation base RMSLE: {base_score:.6f}")
    print(f"Validation calibrated RMSLE: {calibrated_score:.6f}")

    submission = fit_submission(train, test)
    submission.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved submission to {OUTPUT_PATH}")
    print(submission.head())


if __name__ == "__main__":
    main()
