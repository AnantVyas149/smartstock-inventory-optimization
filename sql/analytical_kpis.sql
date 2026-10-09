-- ==============================================================================
-- SMARTSTOCK ENTERPRISE SQL ANALYTICS & BUSINESS KPI SUITE
-- Target Engine: MySQL 8.0+
-- Demonstrating CTEs, Window Functions, Partitions, and Supply Chain Logic
-- ==============================================================================

USE smartstock_db;

-- ==============================================================================
-- QUERY 1: Daily and Monthly Demand Aggregation with MoM Growth & Rolling Averages
-- Business Purpose: Track seasonal momentum, demand spikes, and warehouse-level run rates.
-- ==============================================================================
WITH MonthlyDemand AS (
    SELECT
        d.year,
        d.month,
        w.region,
        w.warehouse_name,
        p.category,
        SUM(f.demand_units) AS total_demand_units,
        SUM(f.revenue) AS total_revenue,
        COUNT(DISTINCT f.sku_id) AS active_skus
    FROM fact_daily_demand f
    JOIN dim_date d ON f.date = d.date_id
    JOIN dim_warehouses w ON f.warehouse_id = w.warehouse_id
    JOIN dim_products p ON f.sku_id = p.sku_id
    GROUP BY d.year, d.month, w.region, w.warehouse_name, p.category
),
MonthlyPaced AS (
    SELECT
        year,
        month,
        region,
        warehouse_name,
        category,
        total_demand_units,
        total_revenue,
        LAG(total_demand_units, 1) OVER (
            PARTITION BY warehouse_name, category 
            ORDER BY year, month
        ) AS prev_month_demand,
        AVG(total_demand_units) OVER (
            PARTITION BY warehouse_name, category 
            ORDER BY year, month 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3mo_avg_demand
    FROM MonthlyDemand
)
SELECT
    year,
    month,
    region,
    warehouse_name,
    category,
    total_demand_units,
    prev_month_demand,
    ROUND(
        (total_demand_units - prev_month_demand) / NULLIF(prev_month_demand, 0) * 100, 
        2
    ) AS mom_growth_pct,
    ROUND(rolling_3mo_avg_demand, 1) AS rolling_3mo_avg_demand,
    ROUND(total_revenue, 2) AS total_revenue
FROM MonthlyPaced
ORDER BY warehouse_name, category, year, month;


-- ==============================================================================
-- QUERY 2: Inventory Capital Tied Up & Days of Inventory Coverage (DOI / DOH)
-- Business Purpose: Measure working capital lockup and stock runway.
-- ==============================================================================
SELECT
    w.warehouse_id,
    w.warehouse_name,
    p.category,
    p.sku_id,
    p.sku_name,
    s.on_hand_inventory,
    s.inventory_position,
    p.unit_cost,
    ROUND(s.on_hand_inventory * p.unit_cost, 2) AS capital_tied_on_hand,
    ROUND(s.inventory_position * p.unit_cost, 2) AS capital_tied_position,
    s.mean_daily_demand,
    ROUND(
        s.on_hand_inventory / NULLIF(s.mean_daily_demand, 0), 
        1
    ) AS days_of_coverage_on_hand,
    CASE 
        WHEN s.mean_daily_demand = 0 THEN 'Dead Inventory'
        WHEN s.on_hand_inventory / s.mean_daily_demand < 7 THEN 'Critical Understock (<7d)'
        WHEN s.on_hand_inventory / s.mean_daily_demand BETWEEN 7 AND 30 THEN 'Healthy Buffer (7-30d)'
        ELSE 'Overstocked (>30d)'
    END AS coverage_health_status
FROM fact_inventory_snapshot s
JOIN dim_products p ON s.sku_id = p.sku_id
JOIN dim_warehouses w ON s.warehouse_id = w.warehouse_id
ORDER BY capital_tied_on_hand DESC;


-- ==============================================================================
-- QUERY 3: Enterprise ABC-XYZ Matrix Segmentation (Pareto + Coefficient of Variation)
-- Business Purpose: Categorize SKUs by revenue importance and demand predictability.
-- ==============================================================================
WITH SkuDemandStats AS (
    SELECT
        f.sku_id,
        p.sku_name,
        p.category,
        SUM(f.revenue) AS total_annual_revenue,
        SUM(f.demand_units) AS total_units_sold,
        AVG(f.demand_units) AS avg_daily_demand,
        STDDEV_SAMP(f.demand_units) AS std_daily_demand
    FROM fact_daily_demand f
    JOIN dim_products p ON f.sku_id = p.sku_id
    GROUP BY f.sku_id, p.sku_name, p.category
),
ParetoCalculations AS (
    SELECT
        sku_id,
        sku_name,
        category,
        total_annual_revenue,
        avg_daily_demand,
        std_daily_demand,
        ROUND(std_daily_demand / NULLIF(avg_daily_demand, 0), 4) AS cv_score,
        SUM(total_annual_revenue) OVER () AS global_revenue,
        SUM(total_annual_revenue) OVER (
            ORDER BY total_annual_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_cumulative_revenue
    FROM SkuDemandStats
),
SegmentedSKUs AS (
    SELECT
        sku_id,
        sku_name,
        category,
        total_annual_revenue,
        cv_score,
        running_cumulative_revenue / global_revenue AS cumulative_revenue_share,
        CASE
            WHEN running_cumulative_revenue / global_revenue <= 0.80 THEN 'A'
            WHEN running_cumulative_revenue / global_revenue <= 0.95 THEN 'B'
            ELSE 'C'
        END AS abc_class,
        CASE
            WHEN cv_score <= 0.55 THEN 'X'
            WHEN cv_score <= 0.95 THEN 'Y'
            ELSE 'Z'
        END AS xyz_class
    FROM ParetoCalculations
)
SELECT
    sku_id,
    sku_name,
    category,
    ROUND(total_annual_revenue, 2) AS total_annual_revenue,
    ROUND(cumulative_revenue_share * 100, 2) AS cum_rev_pct,
    cv_score,
    abc_class,
    xyz_class,
    CONCAT(abc_class, xyz_class) AS abc_xyz_segment,
    CASE CONCAT(abc_class, xyz_class)
        WHEN 'AX' THEN 'Automate & Lean JIT: High revenue, highly predictable'
        WHEN 'AY' THEN 'Close Monitoring: High revenue, seasonal variations'
        WHEN 'AZ' THEN 'Custom Buffers / VMI: High revenue, extreme volatility'
        WHEN 'BX' THEN 'Periodic Review: Medium value, steady consumption'
        WHEN 'BY' THEN 'Standard Safety Stock: Medium value and variance'
        WHEN 'BZ' THEN 'Consolidate Orders: Medium value, sporadic demand'
        WHEN 'CX' THEN 'Bulk / Two-Bin System: Low value, easy to automate'
        WHEN 'CY' THEN 'High MOQ / Low Priority: Low value, moderate swings'
        WHEN 'CZ' THEN 'Make-to-Order / Phase Out: Low value, erratic dead stock'
    END AS strategic_recommendation
FROM SegmentedSKUs
ORDER BY total_annual_revenue DESC;


-- ==============================================================================
-- QUERY 4: Stockout Risk and Immediate Vulnerability Detection
-- Business Purpose: Flag items where on-hand stock will not survive expected supplier lead time.
-- ==============================================================================
SELECT
    s.warehouse_id,
    w.warehouse_name,
    s.sku_id,
    p.sku_name,
    s.on_hand_inventory,
    s.on_order_inventory,
    s.backorders,
    s.lead_time_days,
    ROUND(s.mean_daily_demand * s.lead_time_days, 1) AS expected_lead_time_demand,
    s.safety_stock_variable_lt AS safety_stock,
    s.reorder_point,
    ROUND(s.on_hand_inventory / NULLIF(s.mean_daily_demand, 0), 1) AS days_until_stockout,
    CASE
        WHEN s.on_hand_inventory <= 0 THEN 'CRITICAL: Stocked Out'
        WHEN s.on_hand_inventory < (s.mean_daily_demand * s.lead_time_days) THEN 'HIGH RISK: Will Stockout Before PO Arrival'
        WHEN s.inventory_position <= s.reorder_point THEN 'MODERATE RISK: Below ROP'
        ELSE 'SAFE: Above ROP'
    END AS vulnerability_status
FROM fact_inventory_snapshot s
JOIN dim_products p ON s.sku_id = p.sku_id
JOIN dim_warehouses w ON s.warehouse_id = w.warehouse_id
WHERE s.is_stockout_risk = 1 OR s.is_below_rop = 1
ORDER BY days_until_stockout ASC;


-- ==============================================================================
-- QUERY 5: Products Below Reorder Point with Purchase Order Action
-- Business Purpose: Operational replenishment trigger list for procurement buyers.
-- ==============================================================================
SELECT
    s.warehouse_id,
    s.sku_id,
    p.sku_name,
    p.category,
    sup.supplier_name,
    s.on_hand_inventory,
    s.on_order_inventory,
    s.inventory_position,
    s.reorder_point,
    s.reorder_point - s.inventory_position AS inventory_deficit,
    s.eoq AS calculated_eoq,
    p.moq,
    -- Recommended Order = Greater of (Deficit, EOQ, MOQ) rounded up to batch multiple
    CEIL(
        GREATEST(s.reorder_point - s.inventory_position, s.eoq, p.moq) / p.batch_order_multiple
    ) * p.batch_order_multiple AS recommended_purchase_quantity,
    ROUND(
        (CEIL(GREATEST(s.reorder_point - s.inventory_position, s.eoq, p.moq) / p.batch_order_multiple) * p.batch_order_multiple) * p.unit_cost,
        2
    ) AS estimated_po_spend
FROM fact_inventory_snapshot s
JOIN dim_products p ON s.sku_id = p.sku_id
JOIN dim_suppliers sup ON p.preferred_supplier_id = sup.supplier_id
WHERE s.inventory_position <= s.reorder_point
ORDER BY inventory_deficit DESC;


-- ==============================================================================
-- QUERY 6: Supplier Lead-Time Performance, OTD Scorecard & Risk Classification
-- Business Purpose: Vendor management scorecard tracking contract compliance and delivery delays.
-- ==============================================================================
SELECT
    sup.supplier_id,
    sup.supplier_name,
    sup.country,
    COUNT(po.po_id) AS total_orders_placed,
    ROUND(AVG(po.contracted_lead_time_days), 1) AS avg_contracted_lt_days,
    ROUND(AVG(po.actual_lead_time_days), 1) AS avg_actual_lt_days,
    ROUND(STDDEV_SAMP(po.actual_lead_time_days), 2) AS std_actual_lt_days,
    ROUND(AVG(po.lead_time_variance_days), 2) AS avg_delivery_delay_days,
    ROUND(SUM(CASE WHEN po.is_on_time = 1 THEN 1 ELSE 0 END) / COUNT(po.po_id) * 100, 2) AS on_time_delivery_pct,
    ROUND(SUM(po.total_po_cost), 2) AS total_procurement_spend,
    CASE
        WHEN (SUM(CASE WHEN po.is_on_time = 1 THEN 1 ELSE 0 END) / COUNT(po.po_id)) >= 0.95 THEN 'Preferred Partner (OTD >= 95%)'
        WHEN (SUM(CASE WHEN po.is_on_time = 1 THEN 1 ELSE 0 END) / COUNT(po.po_id)) >= 0.90 THEN 'Standard Vendor (OTD 90-95%)'
        ELSE 'High Risk Vendor (OTD < 90%)'
    END AS vendor_risk_tier
FROM fact_purchase_orders po
JOIN dim_suppliers sup ON po.supplier_id = sup.supplier_id
GROUP BY sup.supplier_id, sup.supplier_name, sup.country
ORDER BY on_time_delivery_pct ASC;


-- ==============================================================================
-- QUERY 7: High-Value, Slow-Moving Inventory (SLOB / Excess Capital Identification)
-- Business Purpose: Surface capital trapped in sluggish products for liquidation or policy revision.
-- ==============================================================================
SELECT
    s.warehouse_id,
    p.category,
    s.sku_id,
    p.sku_name,
    s.abc_class,
    s.xyz_class,
    s.on_hand_inventory,
    p.unit_cost,
    ROUND(s.on_hand_inventory * p.unit_cost, 2) AS capital_locked_up,
    s.mean_daily_demand,
    ROUND(s.on_hand_inventory / NULLIF(s.mean_daily_demand, 0), 1) AS days_of_coverage
FROM fact_inventory_snapshot s
JOIN dim_products p ON s.sku_id = p.sku_id
WHERE s.abc_class IN ('A', 'B') 
  AND s.on_hand_inventory / NULLIF(s.mean_daily_demand, 0) > 45
ORDER BY capital_locked_up DESC;


-- ==============================================================================
-- QUERY 8: Forecast Accuracy Benchmarking (WAPE, MAE, RMSE) Across Models & Categories
-- Business Purpose: Determine best predictive algorithm for replenishment planning.
-- Formula Notes:
--   WAPE = SUM(|Actual - Forecast|) / SUM(Actual)
--   MAE  = AVG(|Actual - Forecast|)
--   RMSE = SQRT(AVG((Actual - Forecast)^2))
-- ==============================================================================
SELECT
    f.model_name,
    p.category,
    f.horizon_days,
    COUNT(f.forecast_id) AS evaluation_points,
    ROUND(SUM(f.actual_units), 1) AS total_actual_demand,
    ROUND(SUM(f.forecast_units), 1) AS total_forecasted_demand,
    ROUND(AVG(f.absolute_error), 3) AS mae,
    ROUND(SQRT(AVG(f.squared_error)), 3) AS rmse,
    ROUND(
        SUM(f.absolute_error) / NULLIF(SUM(f.actual_units), 0) * 100, 
        2
    ) AS wape_pct,
    ROUND(100.0 - (SUM(f.absolute_error) / NULLIF(SUM(f.actual_units), 0) * 100), 2) AS forecast_accuracy_pct
FROM fact_demand_forecasts f
JOIN dim_products p ON f.sku_id = p.sku_id
GROUP BY f.model_name, p.category, f.horizon_days
ORDER BY p.category, f.horizon_days, wape_pct ASC;


-- ==============================================================================
-- QUERY 9: Modeled Inventory Cost Structure by Warehouse and Category
-- Business Purpose: Compare total holding, ordering, and stockout costs across network nodes.
-- ==============================================================================
SELECT
    sim.policy_name,
    w.warehouse_name,
    p.category,
    SUM(sim.demand_units) AS total_simulated_demand,
    SUM(sim.fulfilled_units) AS total_fulfilled_units,
    SUM(sim.lost_sales_units) AS total_lost_sales_units,
    ROUND(SUM(sim.fulfilled_units) / NULLIF(SUM(sim.demand_units), 0) * 100, 2) AS fill_rate_pct,
    ROUND(SUM(sim.holding_cost), 2) AS total_holding_cost,
    ROUND(SUM(sim.ordering_cost), 2) AS total_ordering_cost,
    ROUND(SUM(sim.stockout_cost), 2) AS total_stockout_penalty_cost,
    ROUND(SUM(sim.total_cost), 2) AS total_inventory_cost
FROM fact_inventory_simulation sim
JOIN dim_warehouses w ON sim.warehouse_id = w.warehouse_id
JOIN dim_products p ON sim.sku_id = p.sku_id
GROUP BY sim.policy_name, w.warehouse_name, p.category
ORDER BY w.warehouse_name, p.category, sim.policy_name;


-- ==============================================================================
-- QUERY 10: Replenishment Recommendations Ranked by Operational Urgency
-- Business Purpose: Executive dispatch board prioritizing replenishment orders by risk & financial impact.
-- ==============================================================================
WITH UrgencyRanking AS (
    SELECT
        s.warehouse_id,
        w.warehouse_name,
        s.sku_id,
        p.sku_name,
        p.category,
        sup.supplier_name,
        s.on_hand_inventory,
        s.inventory_position,
        s.reorder_point,
        s.days_of_coverage,
        CEIL(GREATEST(s.reorder_point - s.inventory_position, s.eoq, p.moq) / p.batch_order_multiple) * p.batch_order_multiple AS recommended_qty,
        ROUND((CEIL(GREATEST(s.reorder_point - s.inventory_position, s.eoq, p.moq) / p.batch_order_multiple) * p.batch_order_multiple) * p.unit_cost, 2) AS order_value,
        CASE
            WHEN s.on_hand_inventory <= 0 THEN 1 -- Out of stock right now
            WHEN s.days_of_coverage < s.lead_time_days THEN 2 -- Stockout before delivery
            WHEN s.inventory_position <= s.reorder_point THEN 3 -- Below ROP
            ELSE 4
        END AS priority_code
    FROM fact_inventory_snapshot s
    JOIN dim_products p ON s.sku_id = p.sku_id
    JOIN dim_warehouses w ON s.warehouse_id = w.warehouse_id
    JOIN dim_suppliers sup ON p.preferred_supplier_id = sup.supplier_id
    WHERE s.inventory_position <= s.reorder_point
)
SELECT
    DENSE_RANK() OVER (ORDER BY priority_code ASC, order_value DESC) AS action_rank,
    CASE priority_code
        WHEN 1 THEN 'CRITICAL (Stockout Active)'
        WHEN 2 THEN 'HIGH (Stockout Impending)'
        WHEN 3 THEN 'MEDIUM (Standard ROP Trigger)'
    END AS urgency_level,
    warehouse_name,
    sku_id,
    sku_name,
    category,
    supplier_name,
    on_hand_inventory,
    inventory_position,
    reorder_point,
    days_of_coverage,
    recommended_qty,
    order_value
FROM UrgencyRanking
ORDER BY action_rank ASC;
