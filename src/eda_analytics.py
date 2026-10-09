"""
SmartStock Exploratory Data Analysis & Supply Chain Profiling Engine
===================================================================
Performs rigorous data hygiene validation, statistical demand profiling,
ABC-XYZ segmentation (Pareto analysis & Coefficient of Variation),
and supplier lead-time risk evaluation.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

# Set clean styling for publication-grade portfolio plots
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = "Arial"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8


def validate_data_hygiene():
    """Audit data completeness, continuity, and consistency."""
    print("\n--- [AUDIT 1/3] DATA HYGIENE & CONTINUITY CHECK ---")
    df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"))
    df_date = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_date.csv"))
    
    # Fill event_name with 'None' if NA
    df_demand["event_name"] = df_demand["event_name"].fillna("None")
    
    # Check nulls in core numerical & key categorical columns
    core_cols = ["date", "sku_id", "warehouse_id", "demand_units", "sell_price", "unit_cost", "revenue", "cogs"]
    null_counts = df_demand[core_cols].isnull().sum()
    print("Null Counts in core fact_daily_demand fields:")
    for col, count in null_counts.items():
        print(f"  - {col}: {count}")
    assert null_counts.sum() == 0, "Data hygiene failed: Found unexpected null values in core fields!"

    # Check duplicates
    dups = df_demand.duplicated(subset=["date", "sku_id", "warehouse_id"]).sum()
    print(f"Duplicate (date, sku_id, warehouse_id) keys: {dups}")
    assert dups == 0, "Data hygiene failed: Duplicate records detected!"

    # Check date continuity per SKU-warehouse
    expected_days = len(df_date)
    grouped_counts = df_demand.groupby(["sku_id", "warehouse_id"])["date"].nunique()
    min_days, max_days = grouped_counts.min(), grouped_counts.max()
    print(f"Date continuity: Every SKU-Warehouse pair has exactly {min_days} to {max_days} days (Expected: {expected_days}).")
    assert min_days == expected_days and max_days == expected_days, "Gaps found in daily timeline!"
    print("-> DATA INTEGRITY AUDIT PASSED: 100% Complete & Gap-Free.")


def compute_abc_xyz_classification() -> pd.DataFrame:
    """
    Compute ABC-XYZ Matrix for all 50 SKUs across the network.
    ABC: Pareto Cumulative Revenue Analysis (80% / 15% / 5%)
    XYZ: Demand Volatility Analysis via Coefficient of Variation (CV = std / mean)
         X: CV <= 0.50 (Very predictable)
         Y: 0.50 < CV <= 1.00 (Moderate variability)
         Z: CV > 1.00 (Highly erratic / intermittent)
    """
    print("\n--- [AUDIT 2/3] COMPUTING ABC-XYZ MATRIX ---")
    df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"))
    df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_products.csv"))

    # Aggregate SKU level total revenue, total units, mean daily demand, std daily demand
    sku_stats = df_demand.groupby("sku_id").agg(
        total_revenue=("revenue", "sum"),
        total_cogs=("cogs", "sum"),
        total_units=("demand_units", "sum"),
        mean_daily_demand=("demand_units", "mean"),
        std_daily_demand=("demand_units", "std"),
        zero_demand_days=("demand_units", lambda x: (x == 0).sum()),
        total_days=("demand_units", "count"),
    ).reset_index()

    sku_stats["zero_demand_ratio"] = (sku_stats["zero_demand_days"] / sku_stats["total_days"]).round(4)
    sku_stats["cv"] = (sku_stats["std_daily_demand"] / sku_stats["mean_daily_demand"].replace(0, 1e-6)).round(4)

    # 1. ABC Classification (Pareto cumulative revenue share)
    sku_stats = sku_stats.sort_values(by="total_revenue", ascending=False).reset_index(drop=True)
    sku_stats["cum_revenue"] = sku_stats["total_revenue"].cumsum()
    sku_stats["cum_revenue_pct"] = (sku_stats["cum_revenue"] / sku_stats["total_revenue"].sum()).round(4)

    def assign_abc(cum_pct):
        if cum_pct <= 0.80:
            return "A"
        elif cum_pct <= 0.95:
            return "B"
        else:
            return "C"

    sku_stats["abc_class"] = sku_stats["cum_revenue_pct"].apply(assign_abc)

    # 2. XYZ Classification (Volatility via CV)
    def assign_xyz(cv):
        if cv <= 0.55:
            return "X"
        elif cv <= 0.95:
            return "Y"
        else:
            return "Z"

    sku_stats["xyz_class"] = sku_stats["cv"].apply(assign_xyz)
    sku_stats["abc_xyz_segment"] = sku_stats["abc_class"] + sku_stats["xyz_class"]

    # Merge product metadata
    sku_classified = pd.merge(df_products, sku_stats, on="sku_id", how="left")
    
    # Save processed segmentation
    sku_classified.to_csv(os.path.join(PROCESSED_DATA_DIR, "sku_abc_xyz_profile.csv"), index=False)
    
    # Print breakdown
    print("ABC Revenue Breakdown:")
    abc_summary = sku_classified.groupby("abc_class").agg(
        sku_count=("sku_id", "count"),
        total_revenue=("total_revenue", "sum"),
        revenue_share=("cum_revenue_pct", "max")
    )
    print(abc_summary)

    print("\nABC-XYZ 9-Box Distribution:")
    matrix = pd.crosstab(sku_classified["abc_class"], sku_classified["xyz_class"], margins=True)
    print(matrix)

    return sku_classified


def analyze_supplier_performance() -> pd.DataFrame:
    """Analyze supplier lead time distributions, variances, and on-time reliability."""
    print("\n--- [AUDIT 3/3] ANALYZING SUPPLIER LEAD TIME & RISK ---")
    df_pos = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_purchase_orders.csv"))
    df_suppliers = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_suppliers.csv"))

    supp_perf = df_pos.groupby("supplier_id").agg(
        total_orders=("po_id", "count"),
        avg_contracted_lt=("contracted_lead_time_days", "mean"),
        avg_actual_lt=("actual_lead_time_days", "mean"),
        std_actual_lt=("actual_lead_time_days", "std"),
        max_actual_lt=("actual_lead_time_days", "max"),
        otd_rate=("is_on_time", "mean"),
        total_spend=("total_po_cost", "sum")
    ).reset_index()

    supp_perf["lt_bias_days"] = (supp_perf["avg_actual_lt"] - supp_perf["avg_contracted_lt"]).round(2)
    supp_perf["otd_rate"] = supp_perf["otd_rate"].round(4)
    
    # Risk Score: combination of delay bias, variance, and non-compliance
    # Risk Score = (1 - OTD) * 50 + (lt_bias_days / avg_contracted_lt) * 30 + (std_actual_lt / avg_contracted_lt) * 20
    supp_perf["risk_score"] = (
        (1.0 - supp_perf["otd_rate"]) * 50 +
        (supp_perf["lt_bias_days"].clip(lower=0) / supp_perf["avg_contracted_lt"]) * 30 +
        (supp_perf["std_actual_lt"] / supp_perf["avg_contracted_lt"]) * 20
    ).round(2)

    def assign_supplier_tier(score):
        if score < 6.0:
            return "Low Risk (Preferred)"
        elif score < 12.0:
            return "Moderate Risk (Watchlist)"
        else:
            return "High Risk (Critical Review)"

    supp_perf["risk_tier"] = supp_perf["risk_score"].apply(assign_supplier_tier)
    supp_perf = pd.merge(df_suppliers[["supplier_id", "supplier_name", "country"]], supp_perf, on="supplier_id")
    supp_perf = supp_perf.sort_values(by="risk_score", ascending=False)
    
    supp_perf.to_csv(os.path.join(PROCESSED_DATA_DIR, "supplier_performance_summary.csv"), index=False)
    print("Supplier Risk Ranking:")
    print(supp_perf[["supplier_name", "avg_contracted_lt", "avg_actual_lt", "otd_rate", "risk_score", "risk_tier"]])
    return supp_perf


def generate_eda_visualizations(df_abc_xyz: pd.DataFrame, df_supp: pd.DataFrame):
    """Generate high-impact executive visual analytics charts."""
    df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"))
    
    # 1. ABC Pareto Chart
    fig, ax1 = plt.subplots(figsize=(10, 5))
    df_sorted = df_abc_xyz.sort_values(by="total_revenue", ascending=False).reset_index()
    x = range(len(df_sorted))
    ax1.bar(x, df_sorted["total_revenue"] / 1e6, color="#1f77b4", alpha=0.8, label="SKU Annual Revenue ($M)")
    ax1.set_xlabel("SKUs Ranked by Revenue", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Revenue ($ Millions)", color="#1f77b4", fontsize=11, fontweight="bold")
    
    ax2 = ax1.twinx()
    ax2.plot(x, df_sorted["cum_revenue_pct"] * 100, color="#d62728", linewidth=2.5, label="Cumulative Share (%)")
    ax2.axhline(80, color="#2ca02c", linestyle="--", alpha=0.8, label="80% Cutoff (Class A)")
    ax2.axhline(95, color="#ff7f0e", linestyle="--", alpha=0.8, label="95% Cutoff (Class B)")
    ax2.set_ylabel("Cumulative Revenue (%)", color="#d62728", fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 105)
    
    plt.title("ABC Pareto Analysis: 80/15/5 Revenue Concentration", fontsize=13, fontweight="bold", pad=15)
    fig.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "eda_abc_pareto.png"), dpi=300)
    plt.close()

    # 2. ABC-XYZ Heatmap Matrix
    ct = pd.crosstab(df_abc_xyz["abc_class"], df_abc_xyz["xyz_class"])
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(ct, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax, annot_kws={"size": 14, "weight": "bold"})
    ax.set_title("SmartStock ABC-XYZ SKU Distribution Matrix", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("XYZ Demand Volatility (X: Stable | Y: Variable | Z: Erratic)", fontsize=11, fontweight="bold")
    ax.set_ylabel("ABC Revenue Value (A: High | B: Medium | C: Low)", fontsize=11, fontweight="bold")
    fig.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "eda_abc_xyz_matrix.png"), dpi=300)
    plt.close()

    # 3. Monthly Demand Trend & Seasonality by Warehouse
    df_demand["date"] = pd.to_datetime(df_demand["date"])
    monthly = df_demand.set_index("date").groupby([pd.Grouper(freq="ME"), "warehouse_id"])["demand_units"].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(data=monthly, x="date", y="demand_units", hue="warehouse_id", marker="o", linewidth=2.2, ax=ax)
    ax.set_title("Monthly Total Demand Trend by Distribution Center (2024 - 2025)", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Timeline (Month)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Total Demand Units", fontsize=11, fontweight="bold")
    fig.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "eda_monthly_demand_trends.png"), dpi=300)
    plt.close()

    # 4. Supplier On-Time Delivery vs Lead Time Variance Scatter
    fig, ax = plt.subplots(figsize=(9, 5))
    scatter = ax.scatter(
        df_supp["avg_actual_lt"],
        df_supp["otd_rate"] * 100,
        s=df_supp["total_spend"] / 25000,
        c=df_supp["risk_score"],
        cmap="coolwarm",
        alpha=0.85,
        edgecolors="black"
    )
    for _, row in df_supp.iterrows():
        ax.annotate(row["supplier_id"], (row["avg_actual_lt"] + 0.3, row["otd_rate"] * 100 - 0.4), fontsize=9, fontweight="bold")
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Composite Risk Score (Higher = Riskier)", fontsize=10, fontweight="bold")
    ax.set_title("Supplier Reliability Landscape: Lead Time vs. On-Time Delivery", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Mean Actual Lead Time (Days)", fontsize=11, fontweight="bold")
    ax.set_ylabel("On-Time Delivery Rate (%)", fontsize=11, fontweight="bold")
    fig.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "eda_supplier_risk_quadrant.png"), dpi=300)
    plt.close()

    print(f"-> Successfully saved 4 publication-quality EDA figures to: {FIGURES_DIR}")


def run_full_eda():
    validate_data_hygiene()
    df_abc_xyz = compute_abc_xyz_classification()
    df_supp = analyze_supplier_performance()
    generate_eda_visualizations(df_abc_xyz, df_supp)
    print("\nEDA and Supply Chain Profiling Completed Successfully.")


if __name__ == "__main__":
    run_full_eda()
