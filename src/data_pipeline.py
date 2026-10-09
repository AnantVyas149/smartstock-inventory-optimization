"""
SmartStock Data Pipeline & Ingestion Engine (M5 Walmart Grounded)
================================================================
Ingests genuine Walmart sales, calendar, and price records from the M5 dataset,
subsets 50 representative SKUs across 3 geographic stores/warehouses over 730 days,
and constructs the synthetic operational supply chain layer (suppliers, lead times,
warehouses, procurement costs, MOQs, ordering costs, and purchase orders).

Dataset Sources:
- data/raw/sales_train_validation.csv: Unit sales for 30,490 items across 10 stores
- data/raw/calendar.csv: Dates, day of week, SNAP flags, calendar events
- data/raw/sell_prices.csv: Weekly store-level item retail prices
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Deterministic seed for reproducible operational generation
SEED = 42
np.random.seed(SEED)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
POWERBI_DATA_DIR = os.path.join(BASE_DIR, "data", "powerbi_exports")

os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(POWERBI_DATA_DIR, exist_ok=True)


def load_and_prepare_dimensions():
    """Build supplier and warehouse dimensions tailored for the M5 retail network."""
    # 1. Dim Suppliers (8 realistic CPG / Grocery / General Merchandise suppliers)
    suppliers = [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "National Fresh Foods Co",
            "country": "USA",
            "category_specialty": "FOODS",
            "contracted_lead_time_days": 5,
            "lead_time_std_days": 1.0,
            "target_on_time_rate": 0.96,
            "historical_on_time_rate": 0.96,
            "payment_terms": "Net 15",
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "Prairie Valley Dairy & Dry Goods",
            "country": "USA",
            "category_specialty": "FOODS",
            "contracted_lead_time_days": 4,
            "lead_time_std_days": 0.8,
            "target_on_time_rate": 0.98,
            "historical_on_time_rate": 0.97,
            "payment_terms": "Net 30",
        },
        {
            "supplier_id": "SUP-003",
            "supplier_name": "Harvest Prime Provisions",
            "country": "USA",
            "category_specialty": "FOODS",
            "contracted_lead_time_days": 7,
            "lead_time_std_days": 1.4,
            "target_on_time_rate": 0.94,
            "historical_on_time_rate": 0.94,
            "payment_terms": "Net 30",
        },
        {
            "supplier_id": "SUP-004",
            "supplier_name": "Apex CPG & Chemical Cleaners",
            "country": "USA",
            "category_specialty": "HOUSEHOLD",
            "contracted_lead_time_days": 10,
            "lead_time_std_days": 1.8,
            "target_on_time_rate": 0.95,
            "historical_on_time_rate": 0.95,
            "payment_terms": "Net 45",
        },
        {
            "supplier_id": "SUP-005",
            "supplier_name": "CleanLiving Home Products",
            "country": "USA",
            "category_specialty": "HOUSEHOLD",
            "contracted_lead_time_days": 14,
            "lead_time_std_days": 2.5,
            "target_on_time_rate": 0.92,
            "historical_on_time_rate": 0.91,
            "payment_terms": "Net 45",
        },
        {
            "supplier_id": "SUP-006",
            "supplier_name": "Global Craft & Hobby Importers",
            "country": "Canada",
            "category_specialty": "HOBBIES",
            "contracted_lead_time_days": 21,
            "lead_time_std_days": 3.8,
            "target_on_time_rate": 0.90,
            "historical_on_time_rate": 0.88,
            "payment_terms": "Net 60",
        },
        {
            "supplier_id": "SUP-007",
            "supplier_name": "Pacific Leisure Goods Ltd",
            "country": "Taiwan",
            "category_specialty": "HOBBIES",
            "contracted_lead_time_days": 28,
            "lead_time_std_days": 5.2,
            "target_on_time_rate": 0.86,
            "historical_on_time_rate": 0.82,
            "payment_terms": "Letter of Credit",
        },
        {
            "supplier_id": "SUP-008",
            "supplier_name": "Keystone General Merchandise",
            "country": "USA",
            "category_specialty": "HOUSEHOLD",
            "contracted_lead_time_days": 12,
            "lead_time_std_days": 2.1,
            "target_on_time_rate": 0.93,
            "historical_on_time_rate": 0.93,
            "payment_terms": "Net 30",
        },
    ]
    df_suppliers = pd.DataFrame(suppliers)

    # 2. Dim Warehouses / Distribution Centers (Mapping M5 Stores to Regional Warehouses)
    warehouses = [
        {
            "warehouse_id": "WH-CA1",
            "store_id": "CA_1",
            "warehouse_name": "Pacific Regional DC (Store CA_1)",
            "city": "Los Angeles",
            "state": "CA",
            "region": "West",
            "storage_capacity_units": 180000,
            "annual_holding_cost_rate": 0.25,  # 25% annual holding cost rate
            "fixed_order_cost": 85.0,  # $ per PO
            "handling_cost_per_unit": 0.40,
        },
        {
            "warehouse_id": "WH-TX1",
            "store_id": "TX_1",
            "warehouse_name": "South Central Hub (Store TX_1)",
            "city": "Dallas",
            "state": "TX",
            "region": "South",
            "storage_capacity_units": 240000,
            "annual_holding_cost_rate": 0.20,  # 20% annual holding cost rate
            "fixed_order_cost": 75.0,
            "handling_cost_per_unit": 0.35,
        },
        {
            "warehouse_id": "WH-WI1",
            "store_id": "WI_1",
            "warehouse_name": "Midwest Distribution Hub (Store WI_1)",
            "city": "Milwaukee",
            "state": "WI",
            "region": "Midwest",
            "storage_capacity_units": 150000,
            "annual_holding_cost_rate": 0.22,  # 22% annual holding cost rate
            "fixed_order_cost": 80.0,
            "handling_cost_per_unit": 0.38,
        },
    ]
    df_warehouses = pd.DataFrame(warehouses)

    return df_suppliers, df_warehouses


def process_m5_data():
    """
    Ingests M5 files, extracts 50 SKUs across 3 stores/warehouses over the last 730 days
    (d_1184 to d_1913, 2014-04-26 to 2016-04-24), merges prices, calendar, and operational layers.
    """
    print("=" * 70)
    print("INGESTING & STRUCTURING M5 WALMART SOURCE DATA")
    print("=" * 70)

    # 1. Load Calendar
    print("[1/6] Loading calendar.csv...")
    df_calendar_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "calendar.csv"))
    
    # Filter calendar for d_1184 to d_1913 (730 days)
    day_indices = [f"d_{i}" for i in range(1184, 1914)]
    df_calendar = df_calendar_raw[df_calendar_raw["d"].isin(day_indices)].copy()
    df_calendar["date_id"] = df_calendar["date"]
    df_calendar["event_name"] = df_calendar["event_name_1"].fillna("None")
    df_calendar["is_event"] = (df_calendar["event_name"] != "None").astype(int)
    df_calendar["is_weekend"] = df_calendar["wday"].isin([1, 2]).astype(int)  # in M5 wday 1=Sat, 2=Sun
    print(f"      -> Filtered 730 dates: {df_calendar['date'].min()} to {df_calendar['date'].max()}")

    # 2. Build Supplier & Warehouse Dimensions
    print("[2/6] Building operational dimension tables...")
    df_suppliers, df_warehouses = load_and_prepare_dimensions()
    target_stores = df_warehouses["store_id"].tolist()

    # 3. Load & Subset Sales Data
    print("[3/6] Reading sales_train_validation.csv and sampling 50 representative SKUs...")
    sales_cols = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"] + day_indices
    df_sales_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "sales_train_validation.csv"), usecols=sales_cols)
    df_sales_filtered = df_sales_raw[df_sales_raw["store_id"].isin(target_stores)].copy()

    # Calculate item velocity to sample a balanced portfolio of Fast, Medium, and Slow/Intermittent items
    df_sales_filtered["total_sales"] = df_sales_filtered[day_indices].sum(axis=1)
    item_stats = df_sales_filtered.groupby(["item_id", "cat_id", "dept_id"])["total_sales"].sum().reset_index()

    selected_item_ids = []
    sampling_specs = [
        ("FOODS", 20, 7, 7, 6),
        ("HOUSEHOLD", 15, 5, 5, 5),
        ("HOBBIES", 15, 5, 5, 5)
    ]
    for cat, total_n, fast_n, med_n, slow_n in sampling_specs:
        cat_items = item_stats[item_stats["cat_id"] == cat].sort_values("total_sales", ascending=False)
        n = len(cat_items)
        fast = cat_items.iloc[:int(n * 0.15)].sample(fast_n, random_state=SEED)
        med = cat_items.iloc[int(n * 0.15):int(n * 0.65)].sample(med_n, random_state=SEED)
        slow = cat_items.iloc[int(n * 0.65):].sample(slow_n, random_state=SEED)
        chosen = pd.concat([fast, med, slow])
        selected_item_ids.extend(chosen["item_id"].tolist())

    assert len(selected_item_ids) == 50, f"Expected 50 SKUs, got {len(selected_item_ids)}"
    df_sales_subset = df_sales_filtered[df_sales_filtered["item_id"].isin(selected_item_ids)].copy()
    print(f"      -> Sampled 50 SKUs across 3 stores: {len(df_sales_subset)} distinct time series.")

    # 4. Load Sell Prices for the selected items
    print("[4/6] Ingesting sell_prices.csv for selected items...")
    # Read prices with chunks or filtered by item_id for maximum speed & low memory footprint
    prices_iter = pd.read_csv(os.path.join(RAW_DATA_DIR, "sell_prices.csv"), chunksize=500000)
    prices_list = []
    for chunk in prices_iter:
        chunk_sub = chunk[(chunk["store_id"].isin(target_stores)) & (chunk["item_id"].isin(selected_item_ids))]
        if len(chunk_sub) > 0:
            prices_list.append(chunk_sub)
    df_prices = pd.concat(prices_list, ignore_index=True)
    print(f"      -> Loaded {len(df_prices):,} weekly price points.")

    # 5. Build dim_products with realistic operational parameters
    print("[5/6] Building dim_products and assigning operational costs & suppliers...")
    avg_prices = df_prices.groupby("item_id")["sell_price"].mean().to_dict()

    # Supplier assignment by category
    supp_food = ["SUP-001", "SUP-002", "SUP-003"]
    supp_house = ["SUP-004", "SUP-005", "SUP-008"]
    supp_hobby = ["SUP-006", "SUP-007"]

    # Category gross margin benchmarks (Retail/CPG benchmarks)
    # Foods: ~28% margin (Cost = 72% of sell price)
    # Household: ~36% margin (Cost = 64% of sell price)
    # Hobbies: ~44% margin (Cost = 56% of sell price)
    margin_map = {"FOODS": 0.28, "HOUSEHOLD": 0.36, "HOBBIES": 0.44}

    products = []
    for idx, item_id in enumerate(selected_item_ids, 1):
        sku_id = f"SKU-{idx:03d}"
        row_info = df_sales_subset[df_sales_subset["item_id"] == item_id].iloc[0]
        cat = row_info["cat_id"]
        dept = row_info["dept_id"]
        avg_price = round(avg_prices.get(item_id, 3.99), 2)
        margin = margin_map[cat]
        unit_cost = round(max(0.50, avg_price * (1.0 - margin)), 2)

        # Supplier mapping
        if cat == "FOODS":
            supp_id = supp_food[idx % len(supp_food)]
        elif cat == "HOUSEHOLD":
            supp_id = supp_house[idx % len(supp_house)]
        else:
            supp_id = supp_hobby[idx % len(supp_hobby)]

        # Operational constraints
        # MOQ depends on price: lower cost items have higher pack sizes
        if unit_cost < 3.0:
            moq = 96
            batch = 24
        elif unit_cost < 10.0:
            moq = 48
            batch = 12
        else:
            moq = 24
            batch = 6

        products.append({
            "sku_id": sku_id,
            "m5_item_id": item_id,
            "sku_name": f"{dept}_{item_id[-3:]}",
            "category": cat,
            "department": dept,
            "base_sell_price": avg_price,
            "unit_cost": unit_cost,
            "gross_margin_rate": margin,
            "preferred_supplier_id": supp_id,
            "moq": moq,
            "batch_order_multiple": batch,
            "fixed_ordering_cost": 75.0 if cat == "FOODS" else (90.0 if cat == "HOUSEHOLD" else 110.0),
        })

    df_products = pd.DataFrame(products)
    sku_mapping = df_products.set_index("m5_item_id")["sku_id"].to_dict()
    unit_cost_map = df_products.set_index("sku_id")["unit_cost"].to_dict()

    # 6. Melt and Assemble fact_daily_demand
    print("[6/6] Reshaping sales time-series into normalized fact_daily_demand...")
    id_vars = ["item_id", "store_id"]
    df_melted = pd.melt(
        df_sales_subset,
        id_vars=id_vars,
        value_vars=day_indices,
        var_name="d",
        value_name="demand_units"
    )

    # Store to Warehouse ID mapping
    store_to_wh = df_warehouses.set_index("store_id")["warehouse_id"].to_dict()
    df_melted["warehouse_id"] = df_melted["store_id"].map(store_to_wh)
    df_melted["sku_id"] = df_melted["item_id"].map(sku_mapping)

    # Merge calendar
    df_melted = pd.merge(
        df_melted,
        df_calendar[["d", "date", "wm_yr_wk", "wday", "month", "year", "event_name", "is_event", "is_weekend"]],
        on="d",
        how="left"
    )

    # Merge weekly sell prices
    df_melted = pd.merge(
        df_melted,
        df_prices[["store_id", "item_id", "wm_yr_wk", "sell_price"]],
        on=["store_id", "item_id", "wm_yr_wk"],
        how="left"
    )

    # If sell_price is missing in certain weeks (e.g. out of catalog), fill with SKU base price
    base_price_map = df_products.set_index("sku_id")["base_sell_price"].to_dict()
    df_melted["sell_price"] = df_melted["sell_price"].fillna(df_melted["sku_id"].map(base_price_map))
    df_melted["unit_cost"] = df_melted["sku_id"].map(unit_cost_map)

    # Calculate financial metrics
    df_melted["revenue"] = (df_melted["demand_units"] * df_melted["sell_price"]).round(2)
    df_melted["cogs"] = (df_melted["demand_units"] * df_melted["unit_cost"]).round(2)
    df_melted["gross_profit"] = (df_melted["revenue"] - df_melted["cogs"]).round(2)

    # Clean demand columns
    fact_daily_demand = df_melted[[
        "date", "sku_id", "warehouse_id", "demand_units", "sell_price", "unit_cost",
        "revenue", "cogs", "gross_profit", "event_name", "is_event", "is_weekend"
    ]].sort_values(by=["date", "sku_id", "warehouse_id"]).reset_index(drop=True)

    # 7. Generate fact_purchase_orders for the 2-year period
    print("Generating authentic historical purchase orders with lead-time distributions...")
    df_pos = generate_purchase_orders(df_products, df_suppliers, df_warehouses, fact_daily_demand)

    # Save all datasets to data/processed
    print("\nSaving finalized tables to data/processed/...")
    df_suppliers.to_csv(os.path.join(PROCESSED_DATA_DIR, "dim_suppliers.csv"), index=False)
    df_warehouses.to_csv(os.path.join(PROCESSED_DATA_DIR, "dim_warehouses.csv"), index=False)
    df_products.to_csv(os.path.join(PROCESSED_DATA_DIR, "dim_products.csv"), index=False)
    df_calendar.to_csv(os.path.join(PROCESSED_DATA_DIR, "dim_date.csv"), index=False)
    fact_daily_demand.to_csv(os.path.join(PROCESSED_DATA_DIR, "fact_daily_demand.csv"), index=False)
    df_pos.to_csv(os.path.join(PROCESSED_DATA_DIR, "fact_purchase_orders.csv"), index=False)

    print("\n" + "=" * 70)
    print("M5 INGESTION & OPERATIONAL PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Total Unique SKUs:               {len(df_products)}")
    print(f"Total Distribution Hubs:         {len(df_warehouses)}")
    print(f"Total Calendar Days:             {len(df_calendar)} ({df_calendar['date'].min()} to {df_calendar['date'].max()})")
    print(f"Total Daily Demand Records:      {len(fact_daily_demand):,}")
    print(f"Total Customer Demand (Units):   {fact_daily_demand['demand_units'].sum():,}")
    print(f"Total Demand Revenue:            ${fact_daily_demand['revenue'].sum():,.2f}")
    print(f"Zero Demand Days Proportion:     {(fact_daily_demand['demand_units'] == 0).mean():.1%}")
    print(f"Total Inbound POs Generated:     {len(df_pos):,}")
    print(f"Total Inbound Spend:             ${df_pos['total_po_cost'].sum():,.2f}")
    print(f"Supplier Inbound OTD:            {df_pos['is_on_time'].mean():.1%}")
    print("=" * 70)


def generate_purchase_orders(df_products, df_suppliers, df_warehouses, df_demand):
    """
    Generates realistic inbound purchase orders across 2014-2016 matching actual SKU consumption rates.
    """
    pos = []
    po_counter = 10001
    supp_dict = df_suppliers.set_index("supplier_id").to_dict(orient="index")
    
    # Calculate average daily demand per SKU-warehouse to pace orders realistically
    mean_demand = df_demand.groupby(["sku_id", "warehouse_id"])["demand_units"].mean().to_dict()

    start_date = datetime(2014, 4, 26)
    end_date = datetime(2016, 4, 10)

    for _, prod in df_products.iterrows():
        sku_id = prod["sku_id"]
        supp_id = prod["preferred_supplier_id"]
        supp_info = supp_dict[supp_id]
        nominal_lt = supp_info["contracted_lead_time_days"]
        lt_std = supp_info["lead_time_std_days"]
        otd_prob = supp_info["historical_on_time_rate"]
        moq = prod["moq"]
        unit_cost = prod["unit_cost"]

        for _, wh in df_warehouses.iterrows():
            wh_id = wh["warehouse_id"]
            d_mean = mean_demand.get((sku_id, wh_id), 2.0)
            
            # Replenishment cycle length (days): order enough to cover 10-25 days of demand, bounded by MOQ
            cycle_days = max(7, int(np.random.uniform(12, 24)))
            order_size = max(moq, int(np.ceil(d_mean * cycle_days / prod["batch_order_multiple"])) * prod["batch_order_multiple"])

            curr_date = start_date + timedelta(days=int(np.random.uniform(1, 10)))

            while curr_date <= end_date:
                expected_arrival = curr_date + timedelta(days=nominal_lt)
                is_on_time = 1 if np.random.rand() < otd_prob else 0

                if is_on_time:
                    actual_lt = max(1, int(np.round(np.random.normal(nominal_lt, lt_std * 0.7))))
                    actual_lt = min(actual_lt, nominal_lt)
                else:
                    delay_days = int(np.random.exponential(scale=max(3, nominal_lt * 0.35)) + 1)
                    actual_lt = nominal_lt + delay_days

                actual_arrival = curr_date + timedelta(days=actual_lt)

                pos.append({
                    "po_id": f"PO-{po_counter}",
                    "sku_id": sku_id,
                    "warehouse_id": wh_id,
                    "supplier_id": supp_id,
                    "order_date": curr_date.strftime("%Y-%m-%d"),
                    "expected_delivery_date": expected_arrival.strftime("%Y-%m-%d"),
                    "actual_delivery_date": actual_arrival.strftime("%Y-%m-%d"),
                    "order_quantity": order_size,
                    "received_quantity": order_size if actual_arrival <= datetime(2016, 4, 24) else 0,
                    "contracted_lead_time_days": nominal_lt,
                    "actual_lead_time_days": actual_lt,
                    "lead_time_variance_days": actual_lt - nominal_lt,
                    "is_on_time": is_on_time,
                    "unit_cost": unit_cost,
                    "total_po_cost": round(order_size * unit_cost, 2),
                    "status": "Delivered" if actual_arrival <= datetime(2016, 4, 24) else "In-Transit",
                })
                po_counter += 1
                curr_date += timedelta(days=cycle_days + int(np.random.uniform(-2, 3)))

    return pd.DataFrame(pos)


if __name__ == "__main__":
    process_m5_data()
