"""
SmartStock Inventory Optimization Engine
========================================
Implements rigorous Operations Research and Stochastic Inventory Theory:
1. Inventory Position: IP = On_Hand + On_Order - Backorders
2. Lead-Time Demand: LTD = Mean_Daily_Demand * Mean_Lead_Time
3. Safety Stock (Fixed Lead Time): SS_fixed = Z * sigma_D * sqrt(L)
4. Safety Stock (Stochastic Lead Time): 
   SS_var = Z * sqrt( L * sigma_D^2 + D^2 * sigma_L^2 ) (King / Silver-Pyke-Peterson)
5. Reorder Point (ROP): ROP = LTD + SS
6. Economic Order Quantity (EOQ): EOQ = sqrt( (2 * D_annual * S) / H )
7. Order Constraints: Q_actual = max(EOQ, MOQ) rounded to batch_multiple
8. Working Capital & Days of Coverage (DOH / DOI)
"""

import os
import numpy as np
import pandas as pd
from scipy.stats import norm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

# Standard Cycle Service Level (CSL) targets and their corresponding Normal Z-scores
# 90% -> 1.282, 95% -> 1.645, 98% -> 2.054, 99% -> 2.326
SERVICE_LEVEL_Z = {
    0.90: 1.282,
    0.95: 1.645,
    0.98: 2.054,
    0.99: 2.326,
}


def compute_inventory_parameters(target_service_level: float = 0.95) -> pd.DataFrame:
    """
    Computes statistical and operational replenishment parameters for all SKU-Warehouse pairs.
    """
    z_score = SERVICE_LEVEL_Z.get(target_service_level, norm.ppf(target_service_level))

    df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"))
    df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_products.csv"))
    df_suppliers = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_suppliers.csv"))
    df_warehouses = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "dim_warehouses.csv"))
    df_abc_xyz = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "sku_abc_xyz_profile.csv"))

    # Map supplier parameters
    supp_dict = df_suppliers.set_index("supplier_id").to_dict(orient="index")
    prod_dict = df_products.set_index("sku_id").to_dict(orient="index")
    wh_dict = df_warehouses.set_index("warehouse_id").to_dict(orient="index")
    abc_dict = df_abc_xyz.set_index("sku_id")[["abc_class", "xyz_class", "abc_xyz_segment"]].to_dict(orient="index")

    # Demand statistics per SKU-Warehouse
    demand_stats = df_demand.groupby(["sku_id", "warehouse_id"]).agg(
        mean_daily_demand=("demand_units", "mean"),
        std_daily_demand=("demand_units", "std"),
        total_units_sold=("demand_units", "sum"),
        total_days=("demand_units", "count")
    ).reset_index()

    records = []
    snapshot_date = "2016-04-24"  # End of historical M5 window

    for _, row in demand_stats.iterrows():
        sku_id = row["sku_id"]
        wh_id = row["warehouse_id"]
        d_bar = row["mean_daily_demand"]
        sigma_d = row["std_daily_demand"] if not np.isnan(row["std_daily_demand"]) else 0.5

        prod_info = prod_dict[sku_id]
        wh_info = wh_dict[wh_id]
        supp_info = supp_dict[prod_info["preferred_supplier_id"]]
        abc_info = abc_dict.get(sku_id, {"abc_class": "B", "xyz_class": "Y", "abc_xyz_segment": "BY"})

        l_bar = supp_info["contracted_lead_time_days"]
        sigma_l = supp_info["lead_time_std_days"]
        unit_cost = prod_info["unit_cost"]
        moq = prod_info["moq"]
        batch_mult = prod_info["batch_order_multiple"]
        s_order_cost = prod_info["fixed_ordering_cost"]
        h_rate = wh_info["annual_holding_cost_rate"]
        h_unit = h_rate * unit_cost  # Annual holding cost per unit ($/unit/year)

        # 1. Lead-Time Demand (LTD)
        ltd = d_bar * l_bar

        # 2. Safety Stock - Fixed Lead Time
        # SS = Z * sigma_D * sqrt(L)
        ss_fixed = int(np.ceil(z_score * sigma_d * np.sqrt(l_bar)))

        # 3. Safety Stock - Stochastic / Variable Lead Time
        # Var(LTD) = L * sigma_D^2 + D^2 * sigma_L^2
        var_ltd = (l_bar * (sigma_d ** 2)) + ((d_bar ** 2) * (sigma_l ** 2))
        sigma_ltd = np.sqrt(var_ltd)
        ss_variable = int(np.ceil(z_score * sigma_ltd))

        # 4. Reorder Point (ROP) using stochastic safety stock
        rop = int(np.ceil(ltd + ss_variable))

        # 5. Economic Order Quantity (EOQ)
        # Annual Demand D_annual = d_bar * 365
        d_annual = max(1.0, d_bar * 365.0)
        eoq_raw = np.sqrt((2.0 * d_annual * s_order_cost) / max(0.01, h_unit))
        # Practical constrained order quantity: max(EOQ, MOQ) rounded up to batch multiple
        eoq = max(moq, int(np.ceil(eoq_raw / batch_mult) * batch_mult))

        # 6. Baseline Policy Parameters (Standard existing rule: static 14-day coverage ROP and fixed 30-day order)
        baseline_rop = int(np.ceil(d_bar * 14.0))
        baseline_order_qty = max(moq, int(np.ceil((d_bar * 21.0) / batch_mult) * batch_mult))

        # 7. Simulated current on-hand & on-order inventory state at snapshot
        # Healthy distribution centered around ROP + SS with realistic random variation
        on_hand = max(0, int(np.round(np.random.normal(ss_variable * 1.4 + d_bar * 5, max(1.0, ss_variable * 0.3)))))
        on_order = int(np.random.choice([0, eoq], p=[0.7, 0.3]))
        backorders = max(0, int(np.random.poisson(0.2) if on_hand == 0 else 0))
        inv_position = on_hand + on_order - backorders

        # 8. Stockout risk & Coverage metrics
        days_of_coverage = round(on_hand / max(d_bar, 0.05), 1)
        capital_tied = round(on_hand * unit_cost, 2)
        is_below_rop = 1 if inv_position <= rop else 0
        is_stockout_risk = 1 if on_hand < ltd or inv_position <= rop else 0

        records.append({
            "snapshot_date": snapshot_date,
            "sku_id": sku_id,
            "warehouse_id": wh_id,
            "on_hand_inventory": on_hand,
            "on_order_inventory": on_order,
            "backorders": backorders,
            "inventory_position": inv_position,
            "mean_daily_demand": round(d_bar, 3),
            "std_daily_demand": round(sigma_d, 3),
            "cv_demand": round(sigma_d / max(d_bar, 0.001), 4),
            "lead_time_days": l_bar,
            "lead_time_std_days": sigma_l,
            "service_level_target": target_service_level,
            "z_score": round(z_score, 3),
            "safety_stock_fixed_lt": ss_fixed,
            "safety_stock_variable_lt": ss_variable,
            "reorder_point": rop,
            "eoq": eoq,
            "baseline_rop": baseline_rop,
            "baseline_order_qty": baseline_order_qty,
            "days_of_coverage": days_of_coverage,
            "inventory_capital_tied": capital_tied,
            "is_below_rop": is_below_rop,
            "is_stockout_risk": is_stockout_risk,
            "abc_class": abc_info["abc_class"],
            "xyz_class": abc_info["xyz_class"],
            "abc_xyz_segment": abc_info["abc_xyz_segment"],
        })

    df_snapshot = pd.DataFrame(records)
    df_snapshot.to_csv(os.path.join(PROCESSED_DATA_DIR, "fact_inventory_snapshot.csv"), index=False)
    
    print("=" * 70)
    print(f"INVENTORY OPTIMIZATION ENGINE (Target Service Level: {target_service_level:.0%})")
    print("=" * 70)
    print(f"Total Evaluated SKU-Warehouse Nodes: {len(df_snapshot)}")
    print(f"Total On-Hand Inventory (Units):     {df_snapshot['on_hand_inventory'].sum():,}")
    print(f"Total Capital Tied Up (On-Hand):     ${df_snapshot['inventory_capital_tied'].sum():,.2f}")
    print(f"Nodes Below ROP (Trigger Order):     {df_snapshot['is_below_rop'].sum()} ({df_snapshot['is_below_rop'].mean():.1%})")
    print(f"Nodes at High Stockout Risk:         {df_snapshot['is_stockout_risk'].sum()} ({df_snapshot['is_stockout_risk'].mean():.1%})")
    print(f"Average Days of Inventory Coverage:  {df_snapshot['days_of_coverage'].mean():.1f} days")
    print(f"Mean Safety Stock (Fixed LT):        {df_snapshot['safety_stock_fixed_lt'].mean():.1f} units")
    print(f"Mean Safety Stock (Variable LT):     {df_snapshot['safety_stock_variable_lt'].mean():.1f} units")
    print("=" * 70)

    return df_snapshot


if __name__ == "__main__":
    compute_inventory_parameters()
