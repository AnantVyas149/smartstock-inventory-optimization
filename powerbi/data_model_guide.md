# SmartStock Power BI Semantic Data Model & Architecture Guide

## 1. Architectural Architecture: Star Schema Design

The SmartStock Power BI data model follows a Kimball star-schema standard. Dimension tables filter downstream transactional and analytical fact tables with single-direction (1-to-many, `1:*`) relationships.

```
       +--------------------+       +---------------------+
       |    dim_calendar    |       |    dim_suppliers    |
       +---------+----------+       +----------+----------+
                 | 1                           | 1
                 |                             |
                 | *                           | *
+----------------v----------+       +----------v----------+
|     fact_daily_demand     |       | fact_purchase_orders|
+---------------------------+       +---------------------+
                 ^                             ^
                 | *                           | *
                 | 1                           | 1
       +---------+----------+                  |
       |    dim_products    +------------------+
       +---------+----------+
                 | 1
                 |
      +----------+--------------------------+
      | 1                                   | 1
      | *                                   | *
+-----v---------------------+        +------v--------------------+
| fact_inventory_snapshot   |        |   fact_demand_forecasts   |
+---------------------------+        +---------------------------+
      ^                                     ^
      | *                                   | *
      | 1                                   | 1
+-----+---------------------+---------------+
|        dim_warehouses     |
+---------------------------+
```

---

## 2. Table Relationships & Cardinality Configuration

Configure the relationships in Power BI Model View as follows:

| Upstream Dimension (1) | Primary Key (PK) | Downstream Fact (*) | Foreign Key (FK) | Cardinality | Cross Filter Direction | Active |
|---|---|---|---|---|---|---|
| `dim_calendar` | `date_id` (or `date`) | `fact_daily_demand` | `date` | One-to-Many (`1:*`) | Single | Yes |
| `dim_calendar` | `date_id` | `fact_demand_forecasts`| `forecast_date` | One-to-Many (`1:*`) | Single | Yes |
| `dim_calendar` | `date_id` | `fact_inventory_simulation` | `date` | One-to-Many (`1:*`) | Single | Yes |
| `dim_products` | `sku_id` | `fact_daily_demand` | `sku_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_products` | `sku_id` | `fact_inventory_snapshot`| `sku_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_products` | `sku_id` | `fact_purchase_orders` | `sku_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_products` | `sku_id` | `fact_demand_forecasts`| `sku_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_products` | `sku_id` | `fact_inventory_simulation`| `sku_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_warehouses` | `warehouse_id` | `fact_daily_demand` | `warehouse_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_warehouses` | `warehouse_id` | `fact_inventory_snapshot`| `warehouse_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_warehouses` | `warehouse_id` | `fact_purchase_orders` | `warehouse_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_warehouses` | `warehouse_id` | `fact_demand_forecasts`| `warehouse_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_warehouses` | `warehouse_id` | `fact_inventory_simulation`| `warehouse_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_suppliers` | `supplier_id` | `dim_products` | `preferred_supplier_id` | One-to-Many (`1:*`) | Single | Yes |
| `dim_suppliers` | `supplier_id` | `fact_purchase_orders` | `supplier_id` | One-to-Many (`1:*`) | Single | Yes |

*Note: `fact_scenario_analysis` is a disconnected parametric parameter table used on Page 5 for scenario slicing and benchmarking.*

---

## 3. Data Ingestion Steps into Power BI Desktop

1. Open Power BI Desktop.
2. Select **Get Data** -> **Folder** or **Text/CSV**.
3. Point to the exported directory:
   `d:\Python\Data Analytics\SmartStock\data\powerbi_exports\`
4. Load the 10 CSV files.
5. In **Power Query Editor**, confirm data types:
   - All `date` / `date_id` columns set to **Date**.
   - All ID columns (`sku_id`, `warehouse_id`, `supplier_id`, `po_id`) set to **Text**.
   - Numerical metrics (`demand_units`, `on_hand_inventory`, `reorder_point`, `eoq`) set to **Whole Number** or **Decimal Number**.
   - Currency and pricing metrics (`unit_cost`, `sell_price`, `revenue`, `total_cost`) set to **Fixed Decimal / Currency**.
6. Close & Apply.
7. Switch to **Model View** and verify the relationships match Section 2 above.
8. Create a blank calculation table named `_Measures` and paste the DAX definitions from `powerbi/DAX_measures.dax`.
