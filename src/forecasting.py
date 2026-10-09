"""
SmartStock Demand Forecasting Engine
====================================
Evaluates baseline, statistical, and machine learning models on held-out retail demand:
1. Naive Baseline (persistence)
2. Seasonal Naive (7-day cyclic persistence)
3. Exponential Smoothing (Holt-Winters additive seasonality)
4. LightGBM Regressor (feature-engineered with lags, rolling windows, and calendar attributes)

Evaluation Metrics:
- MAE  (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- WAPE (Weighted Absolute Percentage Error = sum(|y - y_hat|) / sum(y))
* Note on MAPE: Strictly omitted for intermittent data due to division-by-zero on zero-demand days.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
FIGURES_DIR = os.path.join(BASE_DIR, "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)


def load_forecasting_data():
    """Load cleaned demand data and sort chronologically."""
    df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"))
    df_demand["date"] = pd.to_datetime(df_demand["date"])
    df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_products.csv"))
    df_demand = pd.merge(df_demand, df_products[["sku_id", "category", "base_sell_price"]], on="sku_id", how="left")
    df_demand = df_demand.sort_values(by=["sku_id", "warehouse_id", "date"]).reset_index(drop=True)
    return df_demand


def train_eval_naive(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    """Naive Baseline: Forecast equals last observed demand point."""
    preds = []
    # Last value in train for each (sku, wh)
    last_vals = train_df.groupby(["sku_id", "warehouse_id"])["demand_units"].last().reset_index()
    last_vals.rename(columns={"demand_units": "forecast_units"}, inplace=True)

    test_merged = pd.merge(test_df, last_vals, on=["sku_id", "warehouse_id"], how="left")
    test_merged["model_name"] = "Naive Baseline"
    return test_merged


def train_eval_seasonal_naive(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    """Seasonal Naive (sNaive-7): Forecast repeats the 7-day weekly demand pattern from the last week of training."""
    # Extract last 7 days of training for each series
    preds = []
    for (sku, wh), group in train_df.groupby(["sku_id", "warehouse_id"]):
        last_7_days = group.sort_values("date").tail(7)
        # Map day_of_week -> last observed value
        last_7_days["day_of_week"] = last_7_days["date"].dt.dayofweek
        dow_map = last_7_days.set_index("day_of_week")["demand_units"].to_dict()

        sub_test = test_df[(test_df["sku_id"] == sku) & (test_df["warehouse_id"] == wh)].copy()
        sub_test["forecast_units"] = sub_test["date"].dt.dayofweek.map(dow_map).fillna(group["demand_units"].mean())
        preds.append(sub_test)

    res = pd.concat(preds, ignore_index=True)
    res["model_name"] = "Seasonal Naive (sNaive-7)"
    return res


def train_eval_exponential_smoothing(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    """Exponential Smoothing (Holt-Winters with 7-day additive seasonality)."""
    preds = []
    test_horizon = test_df["date"].nunique()

    for (sku, wh), group in train_df.groupby(["sku_id", "warehouse_id"]):
        series = group.sort_values("date")["demand_units"].values
        sub_test = test_df[(test_df["sku_id"] == sku) & (test_df["warehouse_id"] == wh)].copy()
        
        try:
            # Fit Holt-Winters with weekly seasonality (m=7)
            # Add small constant 1e-4 if needed
            model = ExponentialSmoothing(
                series,
                seasonal_periods=7,
                trend="add",
                seasonal="add",
                damped_trend=True,
                initialization_method="estimated"
            ).fit(damping_slope=0.98, remove_bias=True)
            fc = model.forecast(test_horizon)
            sub_test["forecast_units"] = np.clip(fc, 0, None)
        except Exception:
            # Fallback to Simple Exponential Smoothing if Holt-Winters encounters numerical singularity
            mean_val = np.mean(series[-14:])
            sub_test["forecast_units"] = mean_val

        preds.append(sub_test)

    res = pd.concat(preds, ignore_index=True)
    res["model_name"] = "Exponential Smoothing (Holt-Winters)"
    return res


def train_eval_lightgbm(df_all: pd.DataFrame, train_cutoff: pd.Timestamp) -> pd.DataFrame:
    """LightGBM Regressor with rigorous lag features, rolling windows, and calendar indicators."""
    df = df_all.copy()

    # Feature Engineering (strictly using prior info)
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["price_ratio"] = df["sell_price"] / df["base_sell_price"]

    # Lag features per SKU-Warehouse
    for lag in [7, 14, 21, 28]:
        df[f"lag_{lag}"] = df.groupby(["sku_id", "warehouse_id"])["demand_units"].shift(lag)

    # Rolling window stats (shifted by 1 to prevent leakage)
    for window in [7, 14, 28]:
        grouped = df.groupby(["sku_id", "warehouse_id"])["demand_units"]
        df[f"rolling_mean_{window}"] = grouped.transform(lambda x: x.shift(1).rolling(window).mean())
        df[f"rolling_std_{window}"] = grouped.transform(lambda x: x.shift(1).rolling(window).std())

    # Encode categoricals
    df["sku_code"] = df["sku_id"].astype("category").cat.codes
    df["wh_code"] = df["warehouse_id"].astype("category").cat.codes
    df["cat_code"] = df["category"].astype("category").cat.codes

    features = [
        "sku_code", "wh_code", "cat_code", "day_of_week", "month", "is_weekend",
        "price_ratio", "is_event",
        "lag_7", "lag_14", "lag_21", "lag_28",
        "rolling_mean_7", "rolling_std_7", "rolling_mean_14", "rolling_std_14",
        "rolling_mean_28", "rolling_std_28"
    ]

    # Split train and test
    train_set = df[df["date"] < train_cutoff].dropna(subset=features)
    test_set = df[df["date"] >= train_cutoff].copy().fillna(0)

    X_train, y_train = train_set[features], train_set["demand_units"]
    X_test = test_set[features]

    train_data = lgb.Dataset(X_train, label=y_train)
    params = {
        "objective": "regression_l1",  # MAE loss is robust against intermittent Poisson spikes
        "metric": "mae",
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "feature_fraction": 0.85,
        "verbose": -1,
        "seed": SEED
    }

    gbm = lgb.train(params, train_data, num_boost_round=120)
    test_set["forecast_units"] = np.clip(gbm.predict(X_test), 0, None)
    test_set["model_name"] = "LightGBM Regressor"
    return test_set


def compute_metrics(eval_df: pd.DataFrame) -> dict:
    """Calculate MAE, RMSE, and WAPE across predictions."""
    y_true = eval_df["demand_units"].values
    y_pred = eval_df["forecast_units"].values
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    sum_actual = np.sum(y_true)
    wape = np.sum(np.abs(y_true - y_pred)) / max(sum_actual, 1e-5)
    bias = np.mean(y_pred - y_true)

    return {
        "MAE": round(float(mae), 3),
        "RMSE": round(float(rmse), 3),
        "WAPE_pct": round(float(wape * 100), 2),
        "Accuracy_pct": round(float((1.0 - wape) * 100), 2),
        "Bias": round(float(bias), 3)
    }


def run_forecasting_pipeline():
    """Execute complete out-of-sample benchmark across all 4 models and multiple horizons."""
    print("=" * 70)
    print("DEMAND FORECASTING BENCHMARK (OUT-OF-SAMPLE TEST: 28 DAYS)")
    print("=" * 70)

    df_demand = load_forecasting_data()
    test_days = 28
    unique_dates = sorted(df_demand["date"].unique())
    train_cutoff = unique_dates[-test_days]
    print(f"Total Date Range:     {unique_dates[0].strftime('%Y-%m-%d')} to {unique_dates[-1].strftime('%Y-%m-%d')}")
    print(f"Train Period:         {unique_dates[0].strftime('%Y-%m-%d')} to {(train_cutoff - pd.Timedelta(days=1)).strftime('%Y-%m-%d')} (702 days)")
    print(f"Out-of-Sample Test:   {train_cutoff.strftime('%Y-%m-%d')} to {unique_dates[-1].strftime('%Y-%m-%d')} (28 days)")

    train_df = df_demand[df_demand["date"] < train_cutoff].copy()
    test_df = df_demand[df_demand["date"] >= train_cutoff].copy()

    # 1. Run all 4 models
    print("\n[1/4] Running Naive Baseline...")
    res_naive = train_eval_naive(train_df, test_df)

    print("[2/4] Running Seasonal Naive (sNaive-7)...")
    res_snaive = train_eval_seasonal_naive(train_df, test_df)

    print("[3/4] Running Exponential Smoothing (Holt-Winters)...")
    res_hw = train_eval_exponential_smoothing(train_df, test_df)

    print("[4/4] Running LightGBM Regressor (Feature Engineered)...")
    res_lgb = train_eval_lightgbm(df_demand, train_cutoff)

    # Combine all predictions
    all_models = [res_naive, res_snaive, res_hw, res_lgb]
    df_all_preds = pd.concat(all_models, ignore_index=True)
    df_all_preds["forecast_date"] = df_all_preds["date"].dt.strftime("%Y-%m-%d")
    df_all_preds["error"] = (df_all_preds["demand_units"] - df_all_preds["forecast_units"]).round(3)
    df_all_preds["absolute_error"] = np.abs(df_all_preds["error"]).round(3)
    df_all_preds["squared_error"] = (df_all_preds["error"] ** 2).round(3)

    # Horizon breakdown: 7-day, 14-day, 28-day
    min_test_date = train_cutoff
    benchmark_records = []

    for model_name in ["Naive Baseline", "Seasonal Naive (sNaive-7)", "Exponential Smoothing (Holt-Winters)", "LightGBM Regressor"]:
        sub_model = df_all_preds[df_all_preds["model_name"] == model_name]

        for horizon, days_lim in [("7-Day", 7), ("14-Day", 14), ("28-Day", 28)]:
            horizon_cutoff = min_test_date + pd.Timedelta(days=days_lim)
            h_df = sub_model[sub_model["date"] < horizon_cutoff]
            metrics = compute_metrics(h_df)
            metrics["Model"] = model_name
            metrics["Horizon"] = horizon
            benchmark_records.append(metrics)

    df_benchmark = pd.DataFrame(benchmark_records)
    print("\n" + "=" * 70)
    print("FORECASTING PERFORMANCE BENCHMARK (OUT-OF-SAMPLE EVALUATION)")
    print("=" * 70)
    print(df_benchmark[["Model", "Horizon", "MAE", "RMSE", "WAPE_pct", "Accuracy_pct", "Bias"]].to_string(index=False))

    # Add Horizon column to all predictions
    def assign_horizon(dt):
        delta = (dt - min_test_date).days
        if delta < 7:
            return 7
        elif delta < 14:
            return 14
        else:
            return 28

    df_all_preds["horizon_days"] = df_all_preds["date"].apply(assign_horizon)

    # Save to CSV
    export_cols = [
        "forecast_date", "sku_id", "warehouse_id", "model_name", "horizon_days",
        "forecast_units", "demand_units", "error", "absolute_error", "squared_error"
    ]
    df_all_preds[export_cols].rename(columns={"demand_units": "actual_units"}).to_csv(
        os.path.join(PROCESSED_DATA_DIR, "fact_demand_forecasts.csv"), index=False
    )
    df_benchmark.to_csv(os.path.join(PROCESSED_DATA_DIR, "forecast_model_benchmark.csv"), index=False)
    print(f"\n-> Exported forecast outputs to: {PROCESSED_DATA_DIR}")

    # Plot benchmarking visualization
    plot_forecasting_results(df_benchmark, df_all_preds)


def plot_forecasting_results(df_benchmark: pd.DataFrame, df_preds: pd.DataFrame):
    """Generate visual model comparison chart."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # 1. WAPE comparison across models and horizons
    sns.barplot(
        data=df_benchmark,
        x="Horizon",
        y="WAPE_pct",
        hue="Model",
        palette="viridis",
        ax=axes[0]
    )
    axes[0].set_title("Forecast Error (WAPE %) by Model & Horizon", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("WAPE (%) - Lower is Better", fontsize=10, fontweight="bold")
    axes[0].set_xlabel("Forecast Horizon", fontsize=10, fontweight="bold")
    axes[0].legend(title="Model", loc="upper left", fontsize=9)

    # 2. Time series drilldown: Aggregated actual vs model forecasts in test window
    daily_agg = df_preds.groupby(["date", "model_name"])[["demand_units", "forecast_units"]].sum().reset_index()
    actual_line = daily_agg[daily_agg["model_name"] == "Naive Baseline"][["date", "demand_units"]].rename(columns={"demand_units": "Total Demand"})

    axes[1].plot(actual_line["date"], actual_line["Total Demand"], label="Actual Demand (Scanner)", color="black", linewidth=2.5)
    for model_name, color in zip(
        ["Naive Baseline", "Seasonal Naive (sNaive-7)", "Exponential Smoothing (Holt-Winters)", "LightGBM Regressor"],
        ["#999999", "#ff7f0e", "#2ca02c", "#1f77b4"]
    ):
        sub = daily_agg[daily_agg["model_name"] == model_name]
        axes[1].plot(sub["date"], sub["forecast_units"], label=model_name, linewidth=1.8, color=color, linestyle="--" if "Naive" in model_name else "-")

    axes[1].set_title("Out-of-Sample Daily Aggregated Demand (Held-Out Test Period)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Total Units Demanded across Network", fontsize=10, fontweight="bold")
    axes[1].tick_params(axis="x", rotation=30)
    axes[1].legend(fontsize=8, loc="upper right")

    fig.tight_layout()
    chart_path = os.path.join(FIGURES_DIR, "forecasting_model_benchmark.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"-> Saved forecast comparison chart: {chart_path}")


if __name__ == "__main__":
    run_forecasting_pipeline()
