"""
SmartStock Daily Discrete-Event Inventory Simulation Engine
===========================================================
Simulates multi-echelon SKU-Warehouse inventory replenishment over held-out M5 demand:
Compares:
1. Baseline Legacy Policy: Static ROP (14-day coverage) and fixed batch order quantity.
2. SmartStock Optimized Policy: Stochastic Safety Stock, Dynamic ROP, and EOQ with MOQ constraints.

Daily Simulation Sequence per SKU-Warehouse:
1. Inbound PO Arrivals: Receive orders delivered on date t.
2. Demand Fulfillment: Fulfill actual customer demand from on-hand stock.
3. Lost Sales / Stockout: Track unfulfilled demand (lost revenue + service penalty).
4. Continuous Review: Assess Inventory Position (IP = On_Hand + On_Order).
   If IP <= ROP, place replenishment order with supplier lead time.
5. Financial Costing: Compute daily holding cost, ordering cost, and stockout penalty.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
FIGURES_DIR = os.path.join(BASE_DIR, "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)


def run_inventory_simulation():
    """Execute dynamic discrete-event simulation over the 28-day test period."""
    print("=" * 70)
    print("DAILY INVENTORY SIMULATION: BASELINE VS. SMARTSTOCK OPTIMIZED")
    print("=" * 70)

    # Load data
    df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"))
    df_demand["date"] = pd.to_datetime(df_demand["date"])
    df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_products.csv"))
    df_suppliers = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_suppliers.csv"))
    df_warehouses = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_warehouses.csv"))
    df_params = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_inventory_snapshot.csv"))

    # Test window: last 28 days
    unique_dates = sorted(df_demand["date"].unique())
    test_dates = unique_dates[-28:]
    print(f"Simulation Window: {test_dates[0].strftime('%Y-%m-%d')} to {test_dates[-1].strftime('%Y-%m-%d')} (28 Days)")

    df_test_demand = df_demand[df_demand["date"].isin(test_dates)].copy()

    # Pre-build lookup dictionaries for speed
    prod_dict = df_products.set_index("sku_id").to_dict(orient="index")
    supp_dict = df_suppliers.set_index("supplier_id").to_dict(orient="index")
    wh_dict = df_warehouses.set_index("warehouse_id").to_dict(orient="index")
    param_dict = df_params.set_index(["sku_id", "warehouse_id"]).to_dict(orient="index")

    policies = ["Baseline Legacy Rule", "SmartStock Optimized"]
    all_sim_logs = []

    for policy in policies:
        print(f"\nSimulating Policy: [{policy}] across 150 nodes...")

        for (sku_id, wh_id), node_demand in df_test_demand.groupby(["sku_id", "warehouse_id"]):
            node_demand = node_demand.sort_values("date").reset_index(drop=True)
            p_info = prod_dict[sku_id]
            w_info = wh_dict[wh_id]
            s_info = supp_dict[p_info["preferred_supplier_id"]]
            node_param = param_dict[(sku_id, wh_id)]

            unit_cost = p_info["unit_cost"]
            sell_price = p_info["base_sell_price"]
            gross_margin = sell_price - unit_cost
            h_daily = (w_info["annual_holding_cost_rate"] * unit_cost) / 365.0
            order_cost_fixed = p_info["fixed_ordering_cost"]
            # Stockout penalty = Lost Gross Profit + $2.00 brand goodwill penalty
            stockout_penalty_per_unit = gross_margin + 2.00

            nominal_lt = s_info["contracted_lead_time_days"]
            lt_std = s_info["lead_time_std_days"]

            if policy == "Baseline Legacy Rule":
                rop = node_param["baseline_rop"]
                order_qty = node_param["baseline_order_qty"]
                # Baseline starts with arbitrary initial inventory (approx 10 days of demand)
                init_inv = int(np.round(node_param["mean_daily_demand"] * 10))
            else:
                rop = node_param["reorder_point"]
                order_qty = node_param["eoq"]
                # Optimized starts with healthy ROP buffer
                init_inv = int(np.round(node_param["safety_stock_variable_lt"] + node_param["mean_daily_demand"] * 7))

            on_hand = max(5, init_inv)
            on_order = 0
            pending_deliveries = []  # List of tuples: (arrival_day_index, qty)

            for day_idx, row in node_demand.iterrows():
                dt_str = row["date"].strftime("%Y-%m-%d")
                demand = int(row["demand_units"])

                # 1. Receive Inbound POs arriving today
                po_received = 0
                remaining_deliveries = []
                for arr_idx, qty in pending_deliveries:
                    if arr_idx <= day_idx:
                        po_received += qty
                    else:
                        remaining_deliveries.append((arr_idx, qty))
                pending_deliveries = remaining_deliveries
                
                on_hand += po_received
                on_order -= po_received

                # 2. Demand Fulfillment
                beginning_inv = on_hand
                fulfilled = min(on_hand, demand)
                lost_sales = demand - fulfilled
                on_hand -= fulfilled
                is_stockout = 1 if lost_sales > 0 else 0

                # 3. Continuous Review of Inventory Position
                inv_pos = on_hand + on_order
                po_placed = 0
                po_placed_units = 0

                if inv_pos <= rop:
                    # Place purchase order
                    po_placed = 1
                    po_placed_units = order_qty
                    on_order += order_qty

                    # Sample stochastic lead time
                    sampled_lt = max(1, int(np.round(np.random.normal(nominal_lt, lt_std))))
                    arrival_idx = day_idx + sampled_lt
                    pending_deliveries.append((arrival_idx, order_qty))

                # 4. Financial Cost Calculation
                holding_cost = round(on_hand * h_daily, 3)
                ordering_cost = round(order_cost_fixed if po_placed == 1 else 0.0, 2)
                stockout_cost = round(lost_sales * stockout_penalty_per_unit, 2)
                total_cost = round(holding_cost + ordering_cost + stockout_cost, 2)

                all_sim_logs.append({
                    "date": dt_str,
                    "sku_id": sku_id,
                    "warehouse_id": wh_id,
                    "policy_name": policy,
                    "beginning_inventory": beginning_inv,
                    "demand_units": demand,
                    "fulfilled_units": fulfilled,
                    "lost_sales_units": lost_sales,
                    "ending_inventory": on_hand,
                    "ending_on_order": on_order,
                    "po_placed_units": po_placed_units,
                    "po_received_units": po_received,
                    "holding_cost": holding_cost,
                    "ordering_cost": ordering_cost,
                    "stockout_cost": stockout_cost,
                    "total_cost": total_cost,
                    "is_stockout": is_stockout,
                    "unit_cost": unit_cost,
                })

    df_sim = pd.DataFrame(all_sim_logs)
    df_sim.to_csv(os.path.join(PROCESSED_DATA_DIR, "fact_inventory_simulation.csv"), index=False)

    # 5. Summarize and Compare Results
    summary = df_sim.groupby("policy_name").agg(
        total_demand=("demand_units", "sum"),
        total_fulfilled=("fulfilled_units", "sum"),
        total_lost_sales=("lost_sales_units", "sum"),
        stockout_occurrences=("is_stockout", "sum"),
        total_observations=("is_stockout", "count"),
        avg_inventory=("ending_inventory", "mean"),
        total_holding_cost=("holding_cost", "sum"),
        total_ordering_cost=("ordering_cost", "sum"),
        total_stockout_cost=("stockout_cost", "sum"),
        total_modeled_cost=("total_cost", "sum")
    ).reset_index()

    summary["fill_rate_pct"] = (summary["total_fulfilled"] / summary["total_demand"] * 100).round(2)
    summary["stockout_rate_pct"] = (summary["stockout_occurrences"] / summary["total_observations"] * 100).round(2)
    summary["avg_working_capital"] = (df_sim.groupby("policy_name").apply(
        lambda x: (x["ending_inventory"] * x["unit_cost"]).mean()
    ) * 150).round(2).values

    summary.to_csv(os.path.join(PROCESSED_DATA_DIR, "simulation_policy_comparison.csv"), index=False)

    print("\n" + "=" * 70)
    print("SIMULATION RESULTS: 28-DAY COMPARATIVE AUDIT")
    print("=" * 70)
    for _, row in summary.iterrows():
        print(f"Policy: {row['policy_name']}")
        print(f"  - Fill Rate (Service Level):     {row['fill_rate_pct']:.2f}%")
        print(f"  - Stockout Frequency:            {row['stockout_rate_pct']:.2f}% of node-days")
        print(f"  - Total Lost Sales Units:        {int(row['total_lost_sales']):,} units")
        print(f"  - Average Ending Inventory:      {row['avg_inventory']:.1f} units / node")
        print(f"  - Total Holding Cost:            ${row['total_holding_cost']:,.2f}")
        print(f"  - Total Ordering Cost:           ${row['total_ordering_cost']:,.2f}")
        print(f"  - Total Stockout Penalty:        ${row['total_stockout_cost']:,.2f}")
        print(f"  - TOTAL MODELED INVENTORY COST:  ${row['total_modeled_cost']:,.2f}")
        print(f"  - Est. Working Capital Tied:     ${row['avg_working_capital']:,.2f}")
        print("-" * 50)

    # Cost Difference Analysis
    base_cost = summary[summary["policy_name"] == "Baseline Legacy Rule"]["total_modeled_cost"].values[0]
    opt_cost = summary[summary["policy_name"] == "SmartStock Optimized"]["total_modeled_cost"].values[0]
    savings = base_cost - opt_cost
    savings_pct = (savings / base_cost) * 100

    print(f"FINANCIAL IMPACT: Net Modeled Savings: ${savings:,.2f} ({savings_pct:.1f}% reduction in total operational costs)")
    print("=" * 70)

    # Visual Simulation Plot
    plot_simulation_results(summary, df_sim)


def plot_simulation_results(summary: pd.DataFrame, df_sim: pd.DataFrame):
    """Plot simulation performance breakdown."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # 1. Cost breakdown stacked bar
    cost_cols = ["total_holding_cost", "total_ordering_cost", "total_stockout_cost"]
    cost_labels = ["Holding Cost", "Ordering Cost", "Stockout Penalty"]
    plot_df = summary.set_index("policy_name")[cost_cols]
    plot_df.columns = cost_labels

    plot_df.plot(kind="bar", stacked=True, ax=axes[0], color=["#2ca02c", "#1f77b4", "#d62728"], alpha=0.85)
    axes[0].set_title("Total Modeled Inventory Cost Breakdown ($)", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Total Cost ($ USD)", fontsize=10, fontweight="bold")
    axes[0].set_xlabel("Replenishment Policy", fontsize=10, fontweight="bold")
    axes[0].tick_params(axis="x", rotation=0)
    axes[0].legend(fontsize=9)

    # 2. Service Level (Fill Rate) vs Stockout Rate
    perf_metrics = summary[["policy_name", "fill_rate_pct", "stockout_rate_pct"]].set_index("policy_name")
    perf_metrics.columns = ["Fill Rate (%)", "Stockout Rate (%)"]
    perf_metrics.plot(kind="bar", ax=axes[1], color=["#1f77b4", "#ff7f0e"], alpha=0.85)
    axes[1].set_title("Customer Service Level vs Stockout Frequency", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Percentage (%)", fontsize=10, fontweight="bold")
    axes[1].set_xlabel("Replenishment Policy", fontsize=10, fontweight="bold")
    axes[1].tick_params(axis="x", rotation=0)
    axes[1].set_ylim(0, 105)
    axes[1].legend(fontsize=9)

    fig.tight_layout()
    chart_path = os.path.join(FIGURES_DIR, "simulation_policy_comparison.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"-> Saved simulation comparison chart: {chart_path}")


if __name__ == "__main__":
    run_inventory_simulation()
