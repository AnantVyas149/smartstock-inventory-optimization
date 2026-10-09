# SmartStock Data Dictionary & Supply Chain Assumptions

This document provides complete documentation for the relational data model, mathematical definitions, cost parameters, and operational assumptions used in SmartStock.

---

## 1. Relational Schema & Entity-Relationship Architecture

The analytical database consists of 4 Dimension tables and 6 Fact/Analytical tables.

### 1.1 `dim_suppliers` (Supplier / Vendor Dimension)
| Column Name | Data Type | Key Type | Description | Sample Values |
|---|---|---|---|---|
| `supplier_id` | VARCHAR(20) | Primary Key | Unique supplier identifier | `SUP-001`, `SUP-002` |
| `supplier_name` | VARCHAR(100) | - | Legal business name of vendor | `National Fresh Foods Co` |
| `country` | VARCHAR(50) | - | Country of manufacturing / origin | `USA`, `Canada`, `Taiwan` |
| `category_specialty` | VARCHAR(50) | - | Primary commodity handled | `FOODS`, `HOUSEHOLD`, `HOBBIES` |
| `contracted_lead_time_days` | INT | - | Nominal contractual lead time (Days) | `4`, `7`, `14`, `28` |
| `lead_time_std_days` | DECIMAL(5,2)| - | Standard deviation of delivery lead time ($\sigma_L$) | `0.80`, `1.40`, `5.20` |
| `target_on_time_rate` | DECIMAL(5,4)| - | SLA target on-time delivery rate | `0.9600` (96%) |
| `historical_on_time_rate`| DECIMAL(5,4)| - | Empirical historical OTD rate | `0.8200` to `0.9740` |
| `payment_terms` | VARCHAR(50) | - | Trade credit payment structure | `Net 15`, `Net 30`, `Net 60` |

---

### 1.2 `dim_warehouses` (Regional Distribution Centers / Stores)
| Column Name | Data Type | Key Type | Description | Sample Values |
|---|---|---|---|---|
| `warehouse_id` | VARCHAR(20) | Primary Key | Distribution center node code | `WH-CA1`, `WH-TX1`, `WH-WI1` |
| `store_id` | VARCHAR(20) | Unique Key | Corresponding Walmart store code from M5 | `CA_1`, `TX_1`, `WI_1` |
| `warehouse_name` | VARCHAR(100) | - | Descriptive node name | `Pacific Regional DC (Store CA_1)` |
| `city` | VARCHAR(50) | - | Facility location city | `Los Angeles`, `Dallas`, `Milwaukee` |
| `state` | VARCHAR(10) | - | State code | `CA`, `TX`, `WI` |
| `region` | VARCHAR(30) | - | Geographic sales territory | `West`, `South`, `Midwest` |
| `storage_capacity_units` | INT | - | Physical warehouse bin capacity | `180000`, `240000`, `150000` |
| `annual_holding_cost_rate`| DECIMAL(5,4)| - | Annual carrying cost fraction ($h$) | `0.2500` (25%), `0.2000` (20%) |
| `fixed_order_cost` | DECIMAL(10,2)| - | Fixed administrative PO placement cost ($S$) | `$85.00`, `$75.00`, `$80.00` |
| `handling_cost_per_unit` | DECIMAL(10,2)| - | Inbound touch & putaway cost per unit | `$0.40`, `$0.35`, `$0.38` |

---

### 1.3 `dim_products` (Catalogue & Procurement Constraints)
| Column Name | Data Type | Key Type | Description | Sample Values |
|---|---|---|---|---|
| `sku_id` | VARCHAR(20) | Primary Key | Internal inventory stock keeping unit | `SKU-001` to `SKU-050` |
| `m5_item_id` | VARCHAR(50) | - | Source Walmart M5 item identifier | `FOODS_1_032`, `HOBBIES_1_004` |
| `sku_name` | VARCHAR(100) | - | User-facing descriptive product label | `FOODS_1_032` |
| `category` | VARCHAR(50) | - | High-level commodity category | `FOODS`, `HOUSEHOLD`, `HOBBIES` |
| `department` | VARCHAR(50) | - | Department code | `FOODS_1`, `HOUSEHOLD_2`, `HOBBIES_1` |
| `base_sell_price` | DECIMAL(10,2)| - | Average retail selling price ($) | `$2.98`, `$9.58`, `$14.97` |
| `unit_cost` | DECIMAL(10,2)| - | Procurement unit purchase cost ($) | `$2.15`, `$5.36`, `$9.58` |
| `gross_margin_rate` | DECIMAL(5,4)| - | Benchmark gross profit margin | `0.2800` (Foods), `0.4400` (Hobbies) |
| `preferred_supplier_id` | VARCHAR(20) | Foreign Key | Foreign key to `dim_suppliers` | `SUP-001` |
| `moq` | INT | - | Minimum Order Quantity (Units) | `24`, `48`, `96` |
| `batch_order_multiple` | INT | - | Case pack multiple for ordering | `6`, `12`, `24` |
| `fixed_ordering_cost` | DECIMAL(10,2)| - | Administrative order placement cost ($S$) | `$75.00`, `$90.00`, `$110.00` |

---

### 1.4 `dim_date` (Calendar & Seasonal Events)
| Column Name | Data Type | Key Type | Description | Sample Values |
|---|---|---|---|---|
| `date_id` (or `date`) | DATE | Primary Key | Continuous daily date (`YYYY-MM-DD`) | `2014-04-26` to `2016-04-24` |
| `d` | VARCHAR(10) | - | M5 day index code | `d_1184` to `d_1913` |
| `wm_yr_wk` | INT | - | Walmart accounting year-week code | `11413` |
| `wday` | INT | - | Weekday index (1=Sat, 7=Fri) | `1` to `7` |
| `month` | INT | - | Calendar month (1–12) | `1` to `12` |
| `year` | INT | - | Calendar year | `2014`, `2015`, `2016` |
| `event_name` | VARCHAR(100) | - | Special holiday / cultural event | `SuperBowl`, `Thanksgiving`, `None` |
| `is_event` | TINYINT | - | Binary flag indicating promotional holiday | `0`, `1` |
| `is_weekend` | TINYINT | - | Binary flag for Saturday / Sunday | `0`, `1` |

---

### 1.5 `fact_daily_demand` (Daily Point-of-Sale Transactions)
- **Granularity:** 1 record per Date $\times$ SKU $\times$ Warehouse (109,500 rows).
- **Core Fields:** `date`, `sku_id`, `warehouse_id`, `demand_units` (unconstrained demand), `sell_price`, `unit_cost`, `revenue`, `cogs`, `gross_profit`.

---

### 1.6 `fact_purchase_orders` (Replenishment PO History)
- **Granularity:** 1 record per Purchase Order (6,220 rows).
- **Core Fields:** `po_id`, `sku_id`, `warehouse_id`, `supplier_id`, `order_date`, `expected_delivery_date`, `actual_delivery_date`, `order_quantity`, `actual_lead_time_days`, `lead_time_variance_days`, `is_on_time`, `total_po_cost`, `status`.

---

### 1.7 `fact_inventory_snapshot` (Replenishment Parameters)
- **Granularity:** 1 record per SKU $\times$ Warehouse (150 rows).
- **Core Fields:** `on_hand_inventory`, `on_order_inventory`, `backorders`, `inventory_position`, `mean_daily_demand`, `std_daily_demand`, `cv_demand`, `lead_time_days`, `lead_time_std_days`, `safety_stock_fixed_lt`, `safety_stock_variable_lt`, `reorder_point`, `eoq`, `days_of_coverage`, `inventory_capital_tied`, `is_below_rop`, `is_stockout_risk`, `abc_class`, `xyz_class`, `abc_xyz_segment`.

---

### 1.8 `fact_demand_forecasts` (Out-of-Sample Predictions)
- **Granularity:** 1 record per Forecast Date $\times$ SKU $\times$ Warehouse $\times$ Model $\times$ Horizon.
- **Core Fields:** `forecast_date`, `sku_id`, `warehouse_id`, `model_name`, `horizon_days`, `forecast_units`, `actual_units`, `error`, `absolute_error`, `squared_error`.

---

### 1.9 `fact_inventory_simulation` (Daily Simulation Logs)
- **Granularity:** 1 record per Day $\times$ SKU $\times$ Warehouse $\times$ Policy (8,400 rows).
- **Core Fields:** `date`, `sku_id`, `warehouse_id`, `policy_name`, `beginning_inventory`, `demand_units`, `fulfilled_units`, `lost_sales_units`, `ending_inventory`, `ending_on_order`, `po_placed_units`, `po_received_units`, `holding_cost`, `ordering_cost`, `stockout_cost`, `total_cost`, `is_stockout`.

---

## 2. Mathematical Formulas & Engineering Operations Research

### 2.1 Inventory Position
$$\text{Inventory Position (IP)} = \text{On-Hand Inventory} + \text{On-Order Inventory} - \text{Backorders}$$
*Unit:* Units.

### 2.2 Stochastic Lead-Time Demand Variance (Law of Total Variance)
$$\text{Var}(D_L) = \bar{L}\sigma_D^2 + \bar{D}^2\sigma_L^2$$
$$\sigma_{LTD} = \sqrt{\bar{L}\sigma_D^2 + \bar{D}^2\sigma_L^2}$$
*Where:*
- $\bar{D}$: Mean daily demand (Units/day).
- $\sigma_D$: Standard deviation of daily demand (Units/day).
- $\bar{L}$: Mean supplier lead time (Days).
- $\sigma_L$: Standard deviation of lead time (Days).

### 2.3 Stochastic Safety Stock
$$\text{Safety Stock (SS)} = \lceil Z \times \sigma_{LTD} \rceil$$
*Where:* $Z = \Phi^{-1}(\text{CSL})$. For CSL = 95%, $Z = 1.645$.

### 2.4 Reorder Point (ROP)
$$\text{ROP} = \lceil (\bar{D} \times \bar{L}) + SS \rceil$$

### 2.5 Economic Order Quantity (EOQ) with Operational Bounds
$$\text{EOQ}_{\text{unconstrained}} = \sqrt{\frac{2 \times D_{\text{annual}} \times S}{H}}$$
$$\text{EOQ}_{\text{constrained}} = \lceil \frac{\max(\text{EOQ}_{\text{unconstrained}}, \text{MOQ})}{\text{Batch Pack Multiple}} \rceil \times \text{Batch Pack Multiple}$$
*Where:*
- $D_{\text{annual}} = \bar{D} \times 365$ (Annual demand in units).
- $S$: Fixed administrative PO ordering cost ($/PO).
- $H = h \times C_{\text{unit}}$: Annual unit holding cost ($/unit/year).

### 2.6 Forecast Error Metrics
$$\text{MAE} = \frac{1}{N}\sum_{i=1}^N |y_i - \hat{y}_i|$$
$$\text{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^N (y_i - \hat{y}_i)^2}$$
$$\text{WAPE} = \frac{\sum_{i=1}^N |y_i - \hat{y}_i|}{\sum_{i=1}^N y_i} \times 100\%$$
*Note on MAPE:* Omitted due to division-by-zero during zero-demand days ($y_i = 0$).

---

## 3. Financial & Costing Assumptions

1. **Holding Cost Rate ($h$):** Assumed between 20% and 25% annually across distribution centers, reflecting capital opportunity cost (10–12%), physical storage and utilities (4–5%), insurance and taxes (2%), and shrinkage/breakage (2–4%).
2. **Fixed Order Placement Cost ($S$):** Assumed at \$75 to \$110 per purchase order, representing buyer time, PO generation, EDI transaction fees, and receiving documentation.
3. **Stockout Penalty:** Modeled as Lost Gross Margin ($P_{\text{sell}} - C_{\text{unit}}$) plus a \$2.00 brand goodwill / customer churn penalty per unfulfilled unit.
4. **Demand Unconstrained Assumption:** Historical scanner sales from M5 are treated as true customer demand (lost sales in baseline simulations occur when on-hand inventory is insufficient).
