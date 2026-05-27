import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from version6.darts_ensemble import (
    Trainer,
    get_covariates,
    get_target_series,
    load_data,
    merge_all_data,
    prepare_submission,
    preprocess_oil,
    preprocess_train,
    preprocess_transactions,
    process_holidays,
)


LGBM_WEIGHT = 0.45
XGB_WEIGHT = 0.55
OUTPUT_PATH = "version6_2/submission_darts_weighted_ensemble.csv"


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

    ens_models = ["lgbm", "lgbm", "lgbm", "lgbm"]
    ens_configs = [
        {**base_config},
        {**base_config, "lags": 7},
        {**base_config, "lags": 365},
        {**base_config, "lags": 730},
    ]

    xgb_base = {
        **base_config,
        "n_estimators": 100,
        "learning_rate": 0.1,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    }
    xgb_models = ["xgb", "xgb", "xgb", "xgb"]
    xgb_configs = [
        {**xgb_base},
        {**xgb_base, "lags": 7},
        {**xgb_base, "lags": 365},
        {**xgb_base, "lags": 730},
    ]

    predictions1 = trainer.ensemble_predict(model_names=ens_models, model_configs=ens_configs)
    predictions2 = trainer.ensemble_predict(model_names=ens_models, model_configs=ens_configs, drop_before="2015-01-01")
    lgbm_final = predictions1.merge(predictions2, on=["date", "store_nbr", "family"], how="left")
    lgbm_final["sales"] = lgbm_final[["sales_x", "sales_y"]].mean(axis=1)
    lgbm_final = lgbm_final.drop(columns=["sales_x", "sales_y"])

    xgb_predictions1 = trainer.ensemble_predict(model_names=xgb_models, model_configs=xgb_configs)
    xgb_predictions2 = trainer.ensemble_predict(model_names=xgb_models, model_configs=xgb_configs, drop_before="2015-01-01")
    xgb_final = xgb_predictions1.merge(xgb_predictions2, on=["date", "store_nbr", "family"], how="left")
    xgb_final["sales"] = xgb_final[["sales_x", "sales_y"]].mean(axis=1)
    xgb_final = xgb_final.drop(columns=["sales_x", "sales_y"])

    final_ensemble = lgbm_final.merge(
        xgb_final, on=["date", "store_nbr", "family"], suffixes=("_lgbm", "_xgb"), how="left"
    )
    final_ensemble["sales"] = (
        final_ensemble["sales_lgbm"] * LGBM_WEIGHT + final_ensemble["sales_xgb"] * XGB_WEIGHT
    )
    final_ensemble = final_ensemble.drop(columns=["sales_lgbm", "sales_xgb"])

    submission = prepare_submission(test, final_ensemble)
    submission.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved submission to {OUTPUT_PATH}")
    print(f"Blend weights -> lgbm: {LGBM_WEIGHT}, xgb: {XGB_WEIGHT}")
    print(submission.head())


if __name__ == "__main__":
    main()
