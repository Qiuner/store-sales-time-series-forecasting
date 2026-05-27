import numpy as np
import pandas as pd
import lightgbm as lgb


TRAIN_PATH = "train.csv"
TEST_PATH = "test.csv"
SAMPLE_SUBMISSION_PATH = "sample_submission.csv"

TRAIN_START = "2017-01-01"
VALID_START = "2017-08-01"

OUTPUT_PATH = "version4/submission_lgbm.csv"


def rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.clip(y_true, 0, None)
    y_pred = np.clip(y_pred, 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dayofweek"] = df["date"].dt.dayofweek
    df["day"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["weekofyear"] = df["date"].dt.isocalendar().week.astype(np.int16)
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(np.int8)
    df["is_month_start"] = df["date"].dt.is_month_start.astype(np.int8)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(np.int8)
    return df


def build_panel(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    train = train.copy()
    test = test.copy()

    train["is_train"] = 1
    test["is_train"] = 0
    test["sales"] = np.nan

    full = pd.concat([train, test], ignore_index=True, sort=False)
    full["date"] = pd.to_datetime(full["date"])
    full = full.sort_values(["store_nbr", "family", "date"]).reset_index(drop=True)
    full = add_calendar_features(full)
    return full


def add_group_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    grp = df.groupby(["store_nbr", "family"], sort=False)

    for lag in [7, 14, 28]:
        df[f"lag_{lag}"] = grp["sales"].shift(lag)

    for window in [7, 14, 28]:
        df[f"rolling_mean_{window}"] = grp["sales"].transform(
            lambda s: s.shift(1).rolling(window, min_periods=1).mean()
        )
        df[f"rolling_std_{window}"] = grp["sales"].transform(
            lambda s: s.shift(1).rolling(window, min_periods=2).std()
        )

    df["promo_lag_7"] = grp["onpromotion"].shift(7)
    df["promo_mean_7"] = grp["onpromotion"].transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).mean()
    )
    return df


def fill_missing_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in feature_cols:
        if df[col].dtype.kind in "biufc":
            df[col] = df[col].fillna(-1.0)
        else:
            df[col] = df[col].fillna("missing")
    return df


def train_valid_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_mask = (df["is_train"] == 1) & (df["date"] >= pd.Timestamp(TRAIN_START)) & (df["date"] < pd.Timestamp(VALID_START))
    valid_mask = (df["is_train"] == 1) & (df["date"] >= pd.Timestamp(VALID_START))
    return df.loc[train_mask].copy(), df.loc[valid_mask].copy()


def make_feature_columns() -> tuple[list[str], list[str]]:
    feature_cols = [
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
    categorical_cols = ["store_nbr", "family", "dayofweek", "month", "weekofyear"]
    return feature_cols, categorical_cols


def fit_model(train_df: pd.DataFrame, valid_df: pd.DataFrame, feature_cols: list[str], categorical_cols: list[str]) -> tuple[lgb.LGBMRegressor, float]:
    X_train = train_df[feature_cols].copy()
    X_valid = valid_df[feature_cols].copy()

    for col in categorical_cols:
        X_train[col] = X_train[col].astype("category")
        X_valid[col] = X_valid[col].astype("category")

    y_train = np.log1p(train_df["sales"].to_numpy())
    y_valid = valid_df["sales"].to_numpy()

    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=1200,
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
        eval_set=[(X_valid, np.log1p(y_valid))],
        eval_metric="l2",
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)],
        categorical_feature=categorical_cols,
    )

    valid_pred = np.expm1(model.predict(X_valid, num_iteration=model.best_iteration_))
    score = rmsle(y_valid, valid_pred)
    return model, score


def refit_and_predict(full_df: pd.DataFrame, feature_cols: list[str], categorical_cols: list[str]) -> pd.DataFrame:
    train_mask = (full_df["is_train"] == 1) & (full_df["date"] >= pd.Timestamp(TRAIN_START))
    test_mask = full_df["is_train"] == 0

    train_df = full_df.loc[train_mask].copy()
    test_df = full_df.loc[test_mask].copy()

    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()

    for col in categorical_cols:
        X_train[col] = X_train[col].astype("category")
        X_test[col] = X_test[col].astype("category")

    y_train = np.log1p(train_df["sales"].to_numpy())

    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=400,
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
    model.fit(X_train, y_train, categorical_feature=categorical_cols)

    test_pred = np.clip(np.expm1(model.predict(X_test)), 0, None)

    submission = pd.read_csv(SAMPLE_SUBMISSION_PATH)
    submission["sales"] = test_pred
    return submission


def main() -> None:
    train = pd.read_csv(TRAIN_PATH, usecols=["date", "store_nbr", "family", "sales", "onpromotion"])
    test = pd.read_csv(TEST_PATH, usecols=["id", "date", "store_nbr", "family", "onpromotion"])

    train["date"] = pd.to_datetime(train["date"])
    test["date"] = pd.to_datetime(test["date"])

    train = train[train["date"] >= pd.Timestamp(TRAIN_START) - pd.Timedelta(days=35)].copy()

    full = build_panel(train, test)
    full = add_group_lag_features(full)

    feature_cols, categorical_cols = make_feature_columns()
    full = fill_missing_features(full, feature_cols)

    train_df, valid_df = train_valid_split(full)
    model, score = fit_model(train_df, valid_df, feature_cols, categorical_cols)
    print(f"Validation RMSLE: {score:.6f}")
    print(f"Best iteration: {model.best_iteration_}")

    submission = refit_and_predict(full, feature_cols, categorical_cols)
    submission.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved submission to {OUTPUT_PATH}")
    print(submission.head())


if __name__ == "__main__":
    main()
