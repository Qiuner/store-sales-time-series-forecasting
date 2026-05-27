import numpy as np
import pandas as pd


TRAIN_PATH = "train.csv"
TEST_PATH = "test.csv"
SAMPLE_SUBMISSION_PATH = "sample_submission.csv"

VALIDATION_START = "2017-08-01"
SUBMISSION_OUTPUT = "version2/submission_baseline.csv"


def rmsle(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.clip(y_true, 0, None)
    y_pred = np.clip(y_pred, 0, None)
    return float(np.sqrt(np.mean((np.log1p(y_pred) - np.log1p(y_true)) ** 2)))


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["dayofweek"] = df["date"].dt.dayofweek
    return df


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


def predict_with_stats(target_df: pd.DataFrame, stats: dict[str, pd.DataFrame | float]) -> np.ndarray:
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

    # Promotions usually lift sales, but the relation is noisy.
    # Use a mild monotonic adjustment to avoid overreacting.
    promo_multiplier = 1.0 + 0.03 * np.log1p(pred_df["onpromotion"].to_numpy())
    pred = base_pred.to_numpy() * promo_multiplier
    return np.clip(pred, 0, None)


def validate(train_df: pd.DataFrame, validation_start: str) -> float:
    cutoff_date = pd.Timestamp(validation_start)
    valid_df = train_df[train_df["date"] >= cutoff_date].copy()

    stats = build_stats(train_df, cutoff_date)
    pred = predict_with_stats(valid_df, stats)
    score = rmsle(valid_df["sales"].to_numpy(), pred)
    return score


def fit_predict_submission(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    cutoff_date = test_df["date"].min()
    stats = build_stats(train_df, cutoff_date)
    pred = predict_with_stats(test_df, stats)

    submission = pd.read_csv(SAMPLE_SUBMISSION_PATH)
    submission["sales"] = pred
    return submission


def main() -> None:
    train = pd.read_csv(TRAIN_PATH, usecols=["date", "store_nbr", "family", "sales", "onpromotion"])
    test = pd.read_csv(TEST_PATH, usecols=["id", "date", "store_nbr", "family", "onpromotion"])

    train = add_time_features(train)
    test = add_time_features(test)

    score = validate(train, VALIDATION_START)
    print(f"Validation RMSLE from {VALIDATION_START} to 2017-08-15: {score:.6f}")

    submission = fit_predict_submission(train, test)
    submission.to_csv(SUBMISSION_OUTPUT, index=False)
    print(f"Saved submission to {SUBMISSION_OUTPUT}")
    print(submission.head())


if __name__ == "__main__":
    main()
