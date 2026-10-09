# SmartStock Power BI Dashboard Specifications (5 Pages)

This document provides exact visual-by-visual instructions for constructing the 5-page SmartStock Executive Power BI report.

---

## Global Slicers & Formatting
Place a consistent **Global Filter Banner** across the top of Pages 1–4:
- **Warehouse / DC Slicer**: `dim_warehouses[warehouse_name]` (Dropdown)
- **Product Category Slicer**: `dim_products[category]` (Tile / Horizontal Pills)
- **Date Range Slicer**: `dim_calendar[date]` (Relative date or Between slider)

---

## Page 1: Executive Overview
*Audience: Chief Supply Chain Officer (CSCO), VP of Logistics, Finance Director*

### KPI Cards (Top Ribbon)
1. **Total Inventory Capital**: `[Total Inventory Value]` (Format: Currency `$#,##0`)
2. **Customer Fill Rate**: `[Simulated Fill Rate Optimized]` (Target: 95.0% | Status color: Green if >= 90%)
3. **Stockout Incident Rate**: `[Stockout Rate Optimized]` (Format: `0.0%` | Color: Red if > 5%)
4. **High-Risk SKU Count**: `[High Risk SKU Count]` (Card with alert indicator)
5. **Modeled Cost Savings**: `[Policy Net Savings]` (Format: `$#,##0` | Subtitle: `[Policy Savings Pct]`)

### Visual 1: Inventory Value by Category & Warehouse
- **Visual Type**: Clustered Column Chart
- **X-Axis**: `dim_products[category]`
- **Y-Axis**: `[Total Inventory Value]`
- **Legend**: `dim_warehouses[warehouse_name]`
- **Insight**: Highlights where working capital is concentrated across the distribution network.

### Visual 2: Policy Comparison — Baseline vs. SmartStock Optimized
- **Visual Type**: Clustered Bar Chart or 100% Stacked Bar
- **Y-Axis**: `fact_inventory_simulation[policy_name]`
- **X-Axis**: `[Total Modeled Inventory Cost]`, `[Simulated Fill Rate]`
- **Insight**: Directly demonstrates the ROI and service level lift delivered by stochastic inventory optimization.

### Visual 3: Inventory Health Quadrant (DOI vs. Working Capital)
- **Visual Type**: Scatter Plot
- **X-Axis**: `fact_inventory_snapshot[days_of_coverage]` (Days of Inventory)
- **Y-Axis**: `fact_inventory_snapshot[inventory_capital_tied]` (Capital Tied $)
- **Legend**: `fact_inventory_snapshot[abc_class]`
- **Size**: `fact_inventory_snapshot[mean_daily_demand]`
- **Play Axis / Tooltip**: `sku_id`, `sku_name`

---

## Page 2: Demand Planning & Forecast Evaluation
*Audience: Demand Planners, Supply Chain Data Scientists, Category Managers*

### KPI Cards (Top Ribbon)
1. **Forecast WAPE**: `[Forecast WAPE Pct]` (Format: `0.0%`)
2. **Forecast Accuracy**: `[Forecast Accuracy Pct]` (Format: `0.0%`)
3. **Mean Absolute Error (MAE)**: `[Forecast MAE]` (Units)
4. **Tracking Signal / Bias**: `[Forecast Bias]` (Color: Neutral)

### Slicers
- **Forecast Model Selector**: `fact_demand_forecasts[model_name]` (Single Select Pills: LightGBM Regressor, Holt-Winters, sNaive, Naive)
- **Forecast Horizon**: `fact_demand_forecasts[horizon_days]` (7, 14, 28 Days)

### Visual 1: Actual vs. Forecasted Daily Demand (Out-of-Sample Test Window)
- **Visual Type**: Line Chart
- **X-Axis**: `fact_demand_forecasts[forecast_date]`
- **Y-Axis**: `[Forecast Actual Units]`, `[Forecast Predicted Units]`
- **Legend**: Model / Series

### Visual 2: Model Performance Benchmarking Matrix
- **Visual Type**: Clustered Column Chart
- **X-Axis**: `fact_demand_forecasts[model_name]`
- **Y-Axis**: `[Forecast WAPE Pct]`
- **Legend / Small Multiples**: `dim_products[category]`
- **Insight**: Proves out-of-sample error reduction of LightGBM and Holt-Winters across categories.

### Visual 3: Top 10 High-Error SKUs (Attention Required)
- **Visual Type**: Table or Bar Chart
- **Rows**: `dim_products[sku_name]`, `dim_products[category]`
- **Values**: `[Forecast MAE]`, `[Forecast WAPE Pct]`, `[Forecast Actual Units]`
- **Sort**: `[Forecast WAPE Pct]` Descending

---

## Page 3: Inventory Health & Replenishment
*Audience: Inventory Analysts, Warehouse Operations, Purchasing Agents*

### KPI Cards (Top Ribbon)
1. **Total Stock on Hand**: `[Total On Hand Units]`
2. **Total On Order (Inbound)**: `[Total On Order Units]`
3. **SKUs Below ROP**: `[Nodes Below ROP Count]` (Count of immediate triggers)
4. **Recommended PO Spend**: `[Recommended PO Spend]` ($)
5. **Slow-Moving Capital (>45 Days)**: `[Slow Moving Capital Tied]` ($)

### Visual 1: ABC-XYZ 9-Box Matrix
- **Visual Type**: Matrix Visual
- **Rows**: `fact_inventory_snapshot[abc_class]` (A, B, C)
- **Columns**: `fact_inventory_snapshot[xyz_class]` (X, Y, Z)
- **Values**: Count of `sku_id`, Sum of `[Total Inventory Value]`
- **Conditional Formatting**: Background color gradient based on value concentration.

### Visual 2: Stock on Hand vs. Reorder Point & Safety Stock
- **Visual Type**: Bullet Chart or Clustered Bar
- **Y-Axis**: `dim_products[sku_name]` (Filtered to top 15 critical items)
- **Value**: `fact_inventory_snapshot[on_hand_inventory]`
- **Target Value 1**: `fact_inventory_snapshot[reorder_point]`
- **Target Value 2**: `fact_inventory_snapshot[safety_stock_variable_lt]`

### Visual 3: Urgent Replenishment Action Table (Dispatch Board)
- **Visual Type**: Table
- **Columns**:
  - `dim_warehouses[warehouse_name]`
  - `dim_products[sku_id]`
  - `dim_products[sku_name]`
  - `dim_suppliers[supplier_name]`
  - `fact_inventory_snapshot[on_hand_inventory]`
  - `fact_inventory_snapshot[inventory_position]`
  - `fact_inventory_snapshot[reorder_point]`
  - `fact_inventory_snapshot[days_of_coverage]`
  - `fact_inventory_snapshot[eoq]` (Recommended Order Qty)
  - `[Recommended PO Spend]`
- **Filter**: `fact_inventory_snapshot[is_below_rop] = 1`
- **Sort**: `days_of_coverage` Ascending (Most urgent stockout threat first)

---

## Page 4: Supplier Performance & Lead-Time Risk
*Audience: Procurement Managers, Vendor Sourcing, Supplier Relationship Directors*

### KPI Cards (Top Ribbon)
1. **Total Inbound Spend**: `[Total Inbound Spend]` ($)
2. **Overall Supplier OTD**: `[Supplier OTD Rate Pct]` (Target: 95.0%)
3. **Average Actual Lead Time**: `[Avg Actual Lead Time Days]` (Days)
4. **Average Delay per Shipment**: `[Avg Lead Time Delay Days]` (Days)
5. **Late PO Count**: `[Late Inbound PO Count]`

### Visual 1: Supplier Risk Quadrant (Lead Time vs. On-Time Delivery)
- **Visual Type**: Scatter Chart
- **X-Axis**: `[Avg Actual Lead Time Days]`
- **Y-Axis**: `[Supplier OTD Rate Pct]`
- **Size**: `[Total Inbound Spend]`
- **Legend / Tooltip**: `dim_suppliers[supplier_name]`, `dim_suppliers[country]`
- **Reference Lines**: Constant line at Y = 95% (OTD Target)

### Visual 2: Inbound Spend & Performance Scorecard by Vendor
- **Visual Type**: Table / Matrix
- **Columns**:
  - `dim_suppliers[supplier_name]`
  - `dim_suppliers[country]`
  - `[Total Inbound POs]`
  - `[Total Inbound Spend]`
  - `[Supplier OTD Rate Pct]` (Data bar formatting)
  - `[Avg Contracted Lead Time Days]`
  - `[Avg Actual Lead Time Days]`
  - `[Avg Lead Time Delay Days]`

### Visual 3: SKUs Exposed to High-Risk Vendors
- **Visual Type**: Treemap or Donut Chart
- **Category**: `dim_suppliers[supplier_name]`
- **Values**: `[Total Inventory Value]`
- **Filter**: Supplier OTD < 90%

---

## Page 5: Decision Simulator & Scenario Sensitivity
*Audience: Executive Committee, Operations Research Team, Strategic Planners*

### KPI Cards (Top Ribbon)
- Displays dynamic measures from `fact_scenario_analysis` based on selected scenario:
  1. **Selected Scenario**: `SELECTEDVALUE(fact_scenario_analysis[Scenario])`
  2. **Total Annual Modeled Cost**: `[Scenario Annual Cost]` ($)
  3. **Variance vs Baseline**: `[Scenario Cost Variance Pct]` (%)
  4. **Required Working Capital**: `[Scenario Working Capital]` ($)
  5. **High-Risk Node Exposure**: `[Scenario High Risk Count]`

### Slicer
- **Scenario Slicer**: `fact_scenario_analysis[Scenario]` (Single-select dropdown or vertical list)

### Visual 1: Annual Policy Cost Across Scenarios
- **Visual Type**: Horizontal Bar Chart
- **Y-Axis**: `fact_scenario_analysis[Scenario]`
- **X-Axis**: `fact_scenario_analysis[Total_Annual_Policy_Cost_USD]`
- **Data Labels**: On

### Visual 2: The Service Level Trade-Off Curve (Cost of Availability)
- **Visual Type**: Line and Clustered Column Chart
- **Shared X-Axis**: `fact_scenario_analysis[Service_Level_Pct]` (90%, 95%, 98%, 99%)
- **Column Y-Axis**: `fact_scenario_analysis[Total_Working_Capital_USD]` (Working Capital $)
- **Line Y-Axis**: `fact_scenario_analysis[Avg_Safety_Stock_Units]` (Safety Stock Units)
- **Insight**: Visually proves why aiming for 99.9% service level exponentially escalates working capital lockup.

### Visual 3: Scenario Sensitivity Summary Table
- **Visual Type**: Table
- **Columns**:
  - `Scenario`
  - `Service_Level_Pct`
  - `Avg_Safety_Stock_Units`
  - `Avg_Reorder_Point_Units`
  - `Total_Working_Capital_USD`
  - `Total_Annual_Policy_Cost_USD`
  - `Cost_Variance_Pct`
  - `High_Risk_Node_Count`
