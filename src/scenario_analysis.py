"""
SmartStock Scenario Sensitivity & Stress-Testing Engine
======================================================
Executes parametric sensitivity analysis across operational stressors:
1. Demand Surge: +10%, +20%, +30%
2. Supplier Lead-Time Shock: +20%, +50% delay
3. Executive Service Level Mandate: 90%, 95%, 98%, 99% Cycle Service Level (CSL)
4. Cost of Capital / Inflation Shock: Holding Cost Rate +25%, +50%
5. Compound Supply Chain Crisis: Demand +20% AND Lead Time +50%

Quantifies impacts on:
- Safety Stock (SS)
- Reorder Point (ROP)
- Inventory Working Capital ($)
- Total Modeled Annual Inventory Costs (Holding + Ordering + Stockout Risk)
- High-Risk Node Exposure Count
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import norm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
FIGURES_DIR = os.path.join(BASE_DIR, "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)


def evaluate_scenario(
    df_base: pd.DataFrame,
    df_products: pd.DataFrame,
    df_warehouses: pd.DataFrame,
    scenario_name: str,
    demand_multiplier: float = 1.0,
    lt_multiplier: float = 1.0,
    service_level: float = 0.95,
    holding_cost_multiplier: float = 1.0
) -> dict:
    """Evaluates inventory policy parameters under specific operational parameters."""
    z_val = norm.ppf(service_level)
    prod_dict = df_products.set_index("sku_id").to_dict(orient="index")
    wh_dict = df_warehouses.set_index("warehouse_id").to_dict(orient="index")

    total_ss = []
    total_rop = []
    total_capital = []
    total_annual_holding = []
    total_annual_ordering = []
    high_risk_count = 0

    for _, row in df_base.iterrows():
        sku_id = row["sku_id"]
        wh_id = row["warehouse_id"]
        p_info = prod_dict[sku_id]
        w_info = wh_dict[wh_id]

        d_bar = row["mean_daily_demand"] * demand_multiplier
        sigma_d = row["std_daily_demand"] * np.sqrt(demand_multiplier)
        l_bar = row["lead_time_days"] * lt_multiplier
        sigma_l = row["lead_time_std_days"] * np.sqrt(lt_multiplier)

        unit_cost = p_info["unit_cost"]
        s_order = p_info["fixed_ordering_cost"]
        h_rate = w_info["annual_holding_cost_rate"] * holding_cost_multiplier
        h_unit = h_rate * unit_cost

        # Stochastic Safety Stock
        var_ltd = (l_bar * (sigma_d ** 2)) + ((d_bar ** 2) * (sigma_l ** 2))
        sigma_ltd = np.sqrt(max(0.01, var_ltd))
        ss = int(np.ceil(z_val * sigma_ltd))
        rop = int(np.ceil((d_bar * l_bar) + ss))

        # EOQ
        d_annual = max(1.0, d_bar * 365.0)
        eoq_raw = np.sqrt((2.0 * d_annual * s_order) / max(0.01, h_unit))
        eoq = max(p_info["moq"], int(np.ceil(eoq_raw / p_info["batch_order_multiple"]) * p_info["batch_order_multiple"]))

        # Inventory Model Economics:
        # Average Cycle Stock = EOQ / 2
        # Average Total Inventory = Cycle Stock + Safety Stock
        avg_inventory = (eoq / 2.0) + ss
        capital_tied = avg_inventory * unit_cost
        annual_holding = capital_tied * h_rate
        orders_per_year = d_annual / eoq
        annual_ordering = orders_per_year * s_order

        # Stockout risk condition under scenario
        if row["on_hand_inventory"] < (d_bar * l_bar) or row["inventory_position"] <= rop:
            high_risk_count += 1

        total_ss.append(ss)
        total_rop.append(rop)
        total_capital.append(capital_tied)
        total_annual_holding.append(annual_holding)
        total_annual_ordering.append(annual_ordering)

    tot_capital = sum(total_capital)
    tot_holding = sum(total_annual_holding)
    tot_ordering = sum(total_annual_ordering)
    tot_modeled = tot_holding + tot_ordering

    return {
        "Scenario": scenario_name,
        "Demand_Multiplier": demand_multiplier,
        "Lead_Time_Multiplier": lt_multiplier,
        "Service_Level_Pct": round(service_level * 100, 1),
        "Z_Score": round(z_val, 2),
        "Avg_Safety_Stock_Units": round(np.mean(total_ss), 1),
        "Avg_Reorder_Point_Units": round(np.mean(total_rop), 1),
        "Total_Working_Capital_USD": round(tot_capital, 2),
        "Annual_Holding_Cost_USD": round(tot_holding, 2),
        "Annual_Ordering_Cost_USD": round(tot_ordering, 2),
        "Total_Annual_Policy_Cost_USD": round(tot_modeled, 2),
        "High_Risk_Node_Count": high_risk_count,
        "High_Risk_Node_Pct": round(high_risk_count / len(df_base) * 100, 1),
    }


def run_all_scenarios():
    """Run full matrix of scenario stress tests."""
    print("=" * 70)
    print("SMARTSTOCK SCENARIO SENSITIVITY & STRESS-TEST ENGINE")
    print("=" * 70)

    df_base = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_inventory_snapshot.csv"))
    df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_products.csv"))
    df_warehouses = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_warehouses.csv"))

    scenarios = [
        # Baseline
        ("Baseline (95% CSL, Nominal)", 1.0, 1.0, 0.95, 1.0),
        # Demand Surges
        ("Demand Surge +10%", 1.10, 1.0, 0.95, 1.0),
        ("Demand Surge +20%", 1.20, 1.0, 0.95, 1.0),
        ("Demand Surge +30%", 1.30, 1.0, 0.95, 1.0),
        # Lead Time Delays
        ("Lead Time Shock +20%", 1.0, 1.20, 0.95, 1.0),
        ("Lead Time Shock +50%", 1.0, 1.50, 0.95, 1.0),
        # Service Level Targets
        ("Service Level 90% (Lean)", 1.0, 1.0, 0.90, 1.0),
        ("Service Level 98% (High Availability)", 1.0, 1.0, 0.98, 1.0),
        ("Service Level 99% (Near Zero Stockout)", 1.0, 1.0, 0.99, 1.0),
        # Cost of Capital / Inflation
        ("Holding Cost Rate +25%", 1.0, 1.0, 0.95, 1.25),
        ("Holding Cost Rate +50%", 1.0, 1.0, 0.95, 1.50),
        # Compound Crisis
        ("Compound Crisis (Demand +20% & LT +50%)", 1.20, 1.50, 0.95, 1.0),
    ]

    results = []
    for sc_name, d_mult, lt_mult, sl_target, h_mult in scenarios:
        res = evaluate_scenario(df_base, df_products, df_warehouses, sc_name, d_mult, lt_mult, sl_target, h_mult)
        results.append(res)

    df_results = pd.DataFrame(results)
    
    # Calculate difference from baseline
    base_cost = df_results[df_results["Scenario"] == "Baseline (95% CSL, Nominal)"]["Total_Annual_Policy_Cost_USD"].values[0]
    base_cap = df_results[df_results["Scenario"] == "Baseline (95% CSL, Nominal)"]["Total_Working_Capital_USD"].values[0]
    df_results["Cost_Variance_vs_Base_USD"] = (df_results["Total_Annual_Policy_Cost_USD"] - base_cost).round(2)
    df_results["Cost_Variance_Pct"] = ((df_results["Cost_Variance_vs_Base_USD"] / base_cost) * 100).round(1)
    df_results["Capital_Variance_vs_Base_USD"] = (df_results["Total_Working_Capital_USD"] - base_cap).round(2)

    df_results.to_csv(os.path.join(PROCESSED_DATA_DIR, "scenario_analysis_results.csv"), index=False)

    print("\nScenario Matrix Results:")
    print(df_results[[
        "Scenario", "Avg_Safety_Stock_Units", "Avg_Reorder_Point_Units",
        "Total_Working_Capital_USD", "Total_Annual_Policy_Cost_USD",
        "Cost_Variance_Pct", "High_Risk_Node_Count"
    ]].to_string(index=False))

    plot_scenario_analysis(df_results)


def plot_scenario_analysis(df_results: pd.DataFrame):
    """Plot scenario sensitivity charts."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 1. Total Annual Cost by Scenario
    df_plot = df_results.sort_values("Total_Annual_Policy_Cost_USD", ascending=True)
    colors = ["#2ca02c" if "90%" in s else ("#d62728" if "Crisis" in s or "+50%" in s else "#1f77b4") for s in df_plot["Scenario"]]
    
    axes[0].barh(df_plot["Scenario"], df_plot["Total_Annual_Policy_Cost_USD"], color=colors, alpha=0.85)
    axes[0].set_title("Total Annual Modeled Cost by Operational Scenario ($)", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Annual Policy Cost ($ USD)", fontsize=10, fontweight="bold")

    # 2. Service Level Trade-off Curve (90% to 99%)
    sl_scenarios = df_results[df_results["Scenario"].str.contains("Service Level|Baseline")].sort_values("Service_Level_Pct")
    
    ax2 = axes[1]
    ax2_twin = ax2.twinx()

    line1 = ax2.plot(sl_scenarios["Service_Level_Pct"], sl_scenarios["Total_Working_Capital_USD"], marker="o", color="#1f77b4", linewidth=2.2, label="Working Capital ($)")
    line2 = ax2_twin.plot(sl_scenarios["Service_Level_Pct"], sl_scenarios["Avg_Safety_Stock_Units"], marker="s", color="#ff7f0e", linewidth=2.2, linestyle="--", label="Avg Safety Stock (Units)")

    ax2.set_title("Nonlinear Cost of High Availability: Service Level vs. Capital", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Target Cycle Service Level (%)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Working Capital Tied ($ USD)", color="#1f77b4", fontsize=10, fontweight="bold")
    ax2_twin.set_ylabel("Avg Safety Stock (Units)", color="#ff7f0e", fontsize=10, fontweight="bold")

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc="upper left", fontsize=9)

    fig.tight_layout()
    chart_path = os.path.join(FIGURES_DIR, "scenario_sensitivity_analysis.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"\n-> Saved scenario sensitivity chart: {chart_path}")


if __name__ == "__main__":
    run_all_scenarios()
