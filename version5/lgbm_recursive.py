import numpy as np
import pandas as pd
import lightgbm as lgb


TRAIN_PATH = "train.csv"
TEST_PATH = "test.csv"
SAMPLE_SUBMISSION_PATH = "sample_submission.csv"

TRAIN_START = "2017-01-01"
VALID_START = "2017-08-01"
HISTORY_DAYS = 28

OUTPUT_PATH = "version5/submission_lgbm_recursive.csv"


def rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.clip(y_true, 0, None)
    y_pred = np.clip(y_pred, 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["dayofweek"] = df["date"].dt.dayofweek
    df["day"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["weekofyear"] = df["date"].dt.isocalendar().week.astype(np.int16)
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(np.int8)
    df["is_month_start"] = df["date"].dt.is_month_start.astype(np.int8)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(np.int8)
    return df


def prepare_base_frame(train: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
    train = train.copy()
    future = future.copy()

    train["is_train"] = 1
    future["is_train"] = 0
    future["sales"] = np.nan

    full = pd.concat([train, future], ignore_index=True, sort=False)
    full = add_calendar_columns(full)
    full = full.sort_values(["store_nbr", "family", "date"]).reset_index(drop=True)
    return full


def add_static_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sf_key"] = df["store_nbr"].astype(str) + "__" + df["family"].astype(str)
    return df


def build_history_dict(history_df: pd.DataFrame) -> dict[str, list[float]]:
    history_df = history_df.sort_values(["sf_key", "date"])
    out: dict[str, list[float]] = {}
    for key, grp in history_df.groupby("sf_key", sort=False):
        out[key] = grp["sales"].astype(float).tolist()
    return out


def build_promo_history_dict(history_df: pd.DataFrame) -> dict[str, list[float]]:
    history_df = history_df.sort_values(["sf_key", "date"])
    out: dict[str, list[float]] = {}
    for key, grp in history_df.groupby("sf_key", sort=False):
        out[key] = grp["onpromotion"].astype(float).tolist()
    return out


def safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(values))


def safe_std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return float(np.std(values, ddof=1))


def make_temporal_features(
    df_slice: pd.DataFrame,
    sales_history: dict[str, list[float]],
    promo_history: dict[str, list[float]],
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []

    for row in df_slice.itertuples(index=False):
        history = sales_history.get(row.sf_key, [])
        promo_hist = promo_history.get(row.sf_key, [])

        lag_7 = history[-7] if len(history) >= 7 else np.nan
        lag_14 = history[-14] if len(history) >= 14 else np.nan
        lag_28 = history[-28] if len(history) >= 28 else np.nan

        last_7 = history[-7:]
        last_14 = history[-14:]
        last_28 = history[-28:]

        promo_lag_7 = promo_hist[-7] if len(promo_hist) >= 7 else np.nan
        promo_mean_7 = safe_mean(promo_hist[-7:])

        rows.append(
            {
                "row_id": row.row_id,
                "store_nbr": row.store_nbr,
                "family": row.family,
                "onpromotion": row.onpromotion,
                "dayofweek": row.dayofweek,
                "day": row.day,
                "month": row.month,
                "weekofyear": row.weekofyear,
                "is_weekend": row.is_weekend,
                "is_month_start": row.is_month_start,
                "is_month_end": row.is_month_end,
                "lag_7": lag_7,
                "lag_14": lag_14,
                "lag_28": lag_28,
                "rolling_mean_7": safe_mean(last_7),
                "rolling_mean_14": safe_mean(last_14),
                "rolling_mean_28": safe_mean(last_28),
                "rolling_std_7": safe_std(last_7),
                "rolling_std_14": safe_std(last_14),
                "rolling_std_28": safe_std(last_28),
                "promo_lag_7": promo_lag_7,
                "promo_mean_7": promo_mean_7,
            }
        )

    feat = pd.DataFrame(rows).sort_values("row_id").reset_index(drop=True)
    return feat


def feature_columns() -> tuple[list[str], list[str]]:
    cols = [
        "store_nbr",
        "family",
        "onpromotion",
        "dayofweek",
        "day",
        "month",
        "weekofyear",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        "lag_7",
        "lag_14",
        "lag_28",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_28",
        "rolling_std_7",
        "rolling_std_14",
        "rolling_std_28",
        "promo_lag_7",
        "promo_mean_7",
    ]
    categorical = ["store_nbr", "family", "dayofweek", "month", "weekofyear"]
    return cols, categorical


def fill_missing(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        if df[col].dtype.kind in "biufc":
            df[col] = df[col].fillna(-1.0)
    return df


def fit_lgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_valid: pd.DataFrame,
    y_valid_log: np.ndarray,
    categorical_cols: list[str],
) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=1500,
        learning_rate=0.03,
        num_leaves=127,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid_log)],
        eval_metric="l2",
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)],
        categorical_feature=categorical_cols,
    )
    return model


def cast_categories(df: pd.DataFrame, categorical_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in categorical_cols:
        df[col] = df[col].astype("category")
    return df


def recursive_predict(
    history_df: pd.DataFrame,
    future_df: pd.DataFrame,
    model: lgb.LGBMRegressor,
    feat_cols: list[str],
    categorical_cols: list[str],
) -> pd.DataFrame:
    history_df = history_df.copy()
    future_df = future_df.copy()

    history_df = add_static_keys(history_df)
    future_df = add_static_keys(future_df)

    sales_history = build_history_dict(history_df)
    promo_history = build_promo_history_dict(history_df)

    future_df = future_df.sort_values(["date", "store_nbr", "family"]).reset_index(drop=True)
    future_df["row_id"] = np.arange(len(future_df))

    pred_frames = []
    for current_date in sorted(future_df["date"].unique()):
        day_slice = future_df[future_df["date"] == current_date].copy()
        feat = make_temporal_features(day_slice, sales_history, promo_history)
        feat = fill_missing(feat, feat_cols)
        feat = cast_categories(feat, categorical_cols)

        pred = np.clip(np.expm1(model.predict(feat[feat_cols], num_iteration=model.best_iteration_)), 0, None)
        day_slice["sales_pred"] = pred
        pred_frames.append(day_slice[["row_id", "sales_pred"]])

        for row in day_slice.itertuples(index=False):
            sales_history.setdefault(row.sf_key, []).append(float(row.sales_pred))
            promo_history.setdefault(row.sf_key, []).append(float(row.onpromotion))

    pred_df = pd.concat(pred_frames, ignore_index=True).sort_values("row_id").reset_index(drop=True)
    future_df = future_df.sort_values("row_id").reset_index(drop=True)
    future_df["sales_pred"] = pred_df["sales_pred"].to_numpy()
    return future_df


def build_training_features(train_hist: pd.DataFrame, train_target: pd.DataFrame) -> pd.DataFrame:
    history = add_static_keys(train_hist.copy())
    target = add_static_keys(train_target.copy())
    target = target.sort_values(["date", "store_nbr", "family"]).reset_index(drop=True)
    target["row_id"] = np.arange(len(target))

    sales_history = build_history_dict(history)
    promo_history = build_promo_history_dict(history)

    feat_frames = []
    for current_date in sorted(target["date"].unique()):
        day_slice = target[target["date"] == current_date].copy()
        feat = make_temporal_features(day_slice, sales_history, promo_history)
        feat_frames.append(feat)

        # Training features for date t may use values before t,
        # then we can append the true t sales for subsequent dates.
        for row in day_slice.itertuples(index=False):
            sales_history.setdefault(row.sf_key, []).append(float(row.sales))
            promo_history.setdefault(row.sf_key, []).append(float(row.onpromotion))

    features = pd.concat(feat_frames, ignore_index=True).sort_values("row_id").reset_index(drop=True)
    target = target.sort_values("row_id").reset_index(drop=True)
    feature_only = features.drop(
        columns=[
            "row_id",
            "store_nbr",
            "family",
            "onpromotion",
            "dayofweek",
            "day",
            "month",
            "weekofyear",
            "is_weekend",
            "is_month_start",
            "is_month_end",
        ]
    )
    out = pd.concat([target.reset_index(drop=True), feature_only], axis=1)
    return out


def main() -> None:
    train = pd.read_csv(TRAIN_PATH, usecols=["date", "store_nbr", "family", "sales", "onpromotion"])
    test = pd.read_csv(TEST_PATH, usecols=["id", "date", "store_nbr", "family", "onpromotion"])

    train = add_calendar_columns(train)
    test = add_calendar_columns(test)

    train = train[train["date"] >= pd.Timestamp(TRAIN_START) - pd.Timedelta(days=HISTORY_DAYS)].copy()

    hist_train = train[train["date"] < pd.Timestamp(TRAIN_START)].copy()
    model_train = train[(train["date"] >= pd.Timestamp(TRAIN_START)) & (train["date"] < pd.Timestamp(VALID_START))].copy()
    valid = train[train["date"] >= pd.Timestamp(VALID_START)].copy()

    train_feat = build_training_features(hist_train, model_train)
    valid_history = train[train["date"] < pd.Timestamp(VALID_START)].copy()

    feat_cols, categorical_cols = feature_columns()
    train_feat = fill_missing(train_feat, feat_cols)
    train_feat = cast_categories(train_feat, categorical_cols)

    valid_feat_for_es = build_training_features(hist_train, train[(train["date"] >= pd.Timestamp(TRAIN_START)) & (train["date"] < pd.Timestamp(VALID_START) + pd.Timedelta(days=1))].copy())
    valid_feat_for_es = valid_feat_for_es[valid_feat_for_es["date"] == pd.Timestamp(VALID_START)].copy()
    valid_feat_for_es = fill_missing(valid_feat_for_es, feat_cols)
    valid_feat_for_es = cast_categories(valid_feat_for_es, categorical_cols)

    model = fit_lgbm(
        train_feat[feat_cols],
        np.log1p(train_feat["sales"].to_numpy()),
        valid_feat_for_es[feat_cols],
        np.log1p(valid_feat_for_es["sales"].to_numpy()),
        categorical_cols,
    )

    valid_pred_df = recursive_predict(valid_history, valid, model, feat_cols, categorical_cols)
    valid_score = rmsle(valid["sales"].to_numpy(), valid_pred_df["sales_pred"].to_numpy())
    print(f"Leakage-free validation RMSLE: {valid_score:.6f}")
    print(f"Best iteration: {model.best_iteration_}")

    full_history = train[train["date"] < test["date"].min()].copy()
    full_train_target = train[train["date"] >= pd.Timestamp(TRAIN_START)].copy()
    full_train_feat = build_training_features(
        train[train["date"] < pd.Timestamp(TRAIN_START)].copy(),
        full_train_target,
    )
    full_train_feat = fill_missing(full_train_feat, feat_cols)
    full_train_feat = cast_categories(full_train_feat, categorical_cols)

    final_model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=max(model.best_iteration_ or 600, 300),
        learning_rate=0.03,
        num_leaves=127,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    final_model.fit(
        full_train_feat[feat_cols],
        np.log1p(full_train_feat["sales"].to_numpy()),
        categorical_feature=categorical_cols,
    )

    test_pred_df = recursive_predict(full_history, test, final_model, feat_cols, categorical_cols)

    submission = pd.read_csv(SAMPLE_SUBMISSION_PATH)
    submission["sales"] = test_pred_df.sort_values("id")["sales_pred"].to_numpy()
    submission.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved submission to {OUTPUT_PATH}")
    print(submission.head())


if __name__ == "__main__":
    main()
