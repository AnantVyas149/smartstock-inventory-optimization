"""
Export and format star-schema tables for Power BI ingestion.
"""

import os
import pandas as pd
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
POWERBI_DATA_DIR = os.path.join(BASE_DIR, "data", "powerbi_exports")
os.makedirs(POWERBI_DATA_DIR, exist_ok=True)

files = [
    ("dim_date.csv", "dim_calendar.csv"),
    ("dim_products.csv", "dim_products.csv"),
    ("dim_warehouses.csv", "dim_warehouses.csv"),
    ("dim_suppliers.csv", "dim_suppliers.csv"),
    ("fact_daily_demand.csv", "fact_daily_demand.csv"),
    ("fact_purchase_orders.csv", "fact_purchase_orders.csv"),
    ("fact_inventory_snapshot.csv", "fact_inventory_snapshot.csv"),
    ("fact_demand_forecasts.csv", "fact_demand_forecasts.csv"),
    ("fact_inventory_simulation.csv", "fact_inventory_simulation.csv"),
    ("scenario_analysis_results.csv", "fact_scenario_analysis.csv"),
]

for src_name, dst_name in files:
    src_path = os.path.join(PROCESSED_DATA_DIR, src_name)
    dst_path = os.path.join(POWERBI_DATA_DIR, dst_name)
    if os.path.exists(src_path):
        shutil.copyfile(src_path, dst_path)
        print(f"Copied {src_name} -> powerbi_exports/{dst_name}")

print("\nSuccessfully prepared all Power BI star-schema tables!")
