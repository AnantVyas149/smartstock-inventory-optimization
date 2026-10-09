-- ==============================================================================
-- SMARTSTOCK DATABASE SCHEMA (MySQL 8.0 Compatible)
-- Enterprise Inventory Intelligence & Supply Chain Optimization Platform
-- ==============================================================================

DROP DATABASE IF EXISTS smartstock_db;
CREATE DATABASE smartstock_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartstock_db;

-- ------------------------------------------------------------------------------
-- 1. DIMENSION TABLES
-- ------------------------------------------------------------------------------

-- Dim Suppliers
CREATE TABLE dim_suppliers (
    supplier_id VARCHAR(20) NOT NULL,
    supplier_name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL,
    category_specialty VARCHAR(50) NOT NULL,
    contracted_lead_time_days INT NOT NULL,
    lead_time_std_days DECIMAL(5, 2) NOT NULL,
    target_on_time_rate DECIMAL(5, 4) NOT NULL,
    historical_on_time_rate DECIMAL(5, 4) NOT NULL,
    payment_terms VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dim_suppliers PRIMARY KEY (supplier_id)
) ENGINE=InnoDB COMMENT='Vendors and suppliers providing inbound inventory';

-- Dim Warehouses
CREATE TABLE dim_warehouses (
    warehouse_id VARCHAR(20) NOT NULL,
    store_id VARCHAR(20) NOT NULL,
    warehouse_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(10) NOT NULL,
    region VARCHAR(30) NOT NULL,
    storage_capacity_units INT NOT NULL,
    annual_holding_cost_rate DECIMAL(5, 4) NOT NULL COMMENT 'Annual inventory carrying cost as fraction of unit cost (e.g. 0.22)',
    fixed_order_cost DECIMAL(10, 2) NOT NULL COMMENT 'Administrative and logistics PO placement cost ($)',
    handling_cost_per_unit DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dim_warehouses PRIMARY KEY (warehouse_id),
    CONSTRAINT uq_dim_warehouses_store UNIQUE (store_id)
) ENGINE=InnoDB COMMENT='Distribution centers and store replenishment nodes';

-- Dim Products / SKUs
CREATE TABLE dim_products (
    sku_id VARCHAR(20) NOT NULL,
    m5_item_id VARCHAR(50) NOT NULL,
    sku_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    department VARCHAR(50) NOT NULL,
    base_sell_price DECIMAL(10, 2) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL COMMENT 'Procurement cost per unit ($)',
    gross_margin_rate DECIMAL(5, 4) NOT NULL,
    preferred_supplier_id VARCHAR(20) NOT NULL,
    moq INT NOT NULL COMMENT 'Minimum Order Quantity (units)',
    batch_order_multiple INT NOT NULL COMMENT 'Pack size ordering multiple',
    fixed_ordering_cost DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dim_products PRIMARY KEY (sku_id),
    CONSTRAINT fk_products_supplier FOREIGN KEY (preferred_supplier_id) REFERENCES dim_suppliers (supplier_id)
) ENGINE=InnoDB COMMENT='Product catalogue and operational procurement attributes';

CREATE INDEX idx_products_category ON dim_products (category);
CREATE INDEX idx_products_supplier ON dim_products (preferred_supplier_id);

-- Dim Calendar
CREATE TABLE dim_date (
    date_id DATE NOT NULL,
    d VARCHAR(10) NOT NULL,
    wm_yr_wk INT NOT NULL,
    wday INT NOT NULL COMMENT '1=Saturday, 7=Friday (M5 calendar)',
    month INT NOT NULL,
    year INT NOT NULL,
    event_name VARCHAR(100) DEFAULT 'None',
    is_event TINYINT NOT NULL DEFAULT 0,
    is_weekend TINYINT NOT NULL DEFAULT 0,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_id)
) ENGINE=InnoDB COMMENT='Continuous date dimension with event and holiday calendar markers';

CREATE INDEX idx_date_year_month ON dim_date (year, month);
CREATE INDEX idx_date_wday ON dim_date (wday);

-- ------------------------------------------------------------------------------
-- 2. TRANSACTION & FACT TABLES
-- ------------------------------------------------------------------------------

-- Fact Daily Demand (Customer Outbound Sales & Demand)
CREATE TABLE fact_daily_demand (
    demand_id BIGINT AUTO_INCREMENT NOT NULL,
    date DATE NOT NULL,
    sku_id VARCHAR(20) NOT NULL,
    warehouse_id VARCHAR(20) NOT NULL,
    demand_units INT NOT NULL,
    sell_price DECIMAL(10, 2) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    revenue DECIMAL(12, 2) NOT NULL,
    cogs DECIMAL(12, 2) NOT NULL,
    gross_profit DECIMAL(12, 2) NOT NULL,
    event_name VARCHAR(100) DEFAULT 'None',
    is_event TINYINT NOT NULL DEFAULT 0,
    is_weekend TINYINT NOT NULL DEFAULT 0,
    CONSTRAINT pk_fact_daily_demand PRIMARY KEY (demand_id),
    CONSTRAINT fk_demand_date FOREIGN KEY (date) REFERENCES dim_date (date_id),
    CONSTRAINT fk_demand_sku FOREIGN KEY (sku_id) REFERENCES dim_products (sku_id),
    CONSTRAINT fk_demand_wh FOREIGN KEY (warehouse_id) REFERENCES dim_warehouses (warehouse_id)
) ENGINE=InnoDB COMMENT='Daily unconstrained customer demand and sales transactions';

CREATE INDEX idx_demand_date ON fact_daily_demand (date);
CREATE INDEX idx_demand_sku_wh ON fact_daily_demand (sku_id, warehouse_id);
CREATE INDEX idx_demand_sku_date ON fact_daily_demand (sku_id, date);

-- Fact Purchase Orders (Inbound Replenishment & Vendor Lead-Times)
CREATE TABLE fact_purchase_orders (
    po_id VARCHAR(20) NOT NULL,
    sku_id VARCHAR(20) NOT NULL,
    warehouse_id VARCHAR(20) NOT NULL,
    supplier_id VARCHAR(20) NOT NULL,
    order_date DATE NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date DATE NOT NULL,
    order_quantity INT NOT NULL,
    received_quantity INT NOT NULL,
    contracted_lead_time_days INT NOT NULL,
    actual_lead_time_days INT NOT NULL,
    lead_time_variance_days INT NOT NULL,
    is_on_time TINYINT NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    total_po_cost DECIMAL(14, 2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    CONSTRAINT pk_fact_pos PRIMARY KEY (po_id),
    CONSTRAINT fk_pos_sku FOREIGN KEY (sku_id) REFERENCES dim_products (sku_id),
    CONSTRAINT fk_pos_wh FOREIGN KEY (warehouse_id) REFERENCES dim_warehouses (warehouse_id),
    CONSTRAINT fk_pos_supplier FOREIGN KEY (supplier_id) REFERENCES dim_suppliers (supplier_id)
) ENGINE=InnoDB COMMENT='Historical purchase orders tracking supplier lead times and fill rates';

CREATE INDEX idx_po_dates ON fact_purchase_orders (order_date, actual_delivery_date);
CREATE INDEX idx_po_supplier ON fact_purchase_orders (supplier_id);
CREATE INDEX idx_po_sku_wh ON fact_purchase_orders (sku_id, warehouse_id);

-- Fact Inventory Snapshot & Replenishment Parameters
CREATE TABLE fact_inventory_snapshot (
    snapshot_date DATE NOT NULL,
    sku_id VARCHAR(20) NOT NULL,
    warehouse_id VARCHAR(20) NOT NULL,
    on_hand_inventory INT NOT NULL,
    on_order_inventory INT NOT NULL,
    backorders INT NOT NULL,
    inventory_position INT NOT NULL,
    mean_daily_demand DECIMAL(10, 3) NOT NULL,
    std_daily_demand DECIMAL(10, 3) NOT NULL,
    cv_demand DECIMAL(8, 4) NOT NULL,
    lead_time_days INT NOT NULL,
    lead_time_std_days DECIMAL(6, 2) NOT NULL,
    service_level_target DECIMAL(5, 4) NOT NULL,
    z_score DECIMAL(6, 3) NOT NULL,
    safety_stock_fixed_lt INT NOT NULL,
    safety_stock_variable_lt INT NOT NULL,
    reorder_point INT NOT NULL,
    eoq INT NOT NULL,
    days_of_coverage DECIMAL(8, 2) NOT NULL,
    inventory_capital_tied DECIMAL(14, 2) NOT NULL,
    is_below_rop TINYINT NOT NULL,
    is_stockout_risk TINYINT NOT NULL,
    abc_class CHAR(1) NOT NULL,
    xyz_class CHAR(1) NOT NULL,
    abc_xyz_segment VARCHAR(5) NOT NULL,
    CONSTRAINT pk_fact_inventory_snapshot PRIMARY KEY (snapshot_date, sku_id, warehouse_id),
    CONSTRAINT fk_snap_sku FOREIGN KEY (sku_id) REFERENCES dim_products (sku_id),
    CONSTRAINT fk_snap_wh FOREIGN KEY (warehouse_id) REFERENCES dim_warehouses (warehouse_id)
) ENGINE=InnoDB COMMENT='Periodic snapshot of inventory positions, safety stock, and reorder triggers';

CREATE INDEX idx_snap_sku_wh ON fact_inventory_snapshot (sku_id, warehouse_id);
CREATE INDEX idx_snap_risk ON fact_inventory_snapshot (is_stockout_risk, is_below_rop);

-- Fact Demand Forecasts (Model predictions and residuals)
CREATE TABLE fact_demand_forecasts (
    forecast_id BIGINT AUTO_INCREMENT NOT NULL,
    forecast_date DATE NOT NULL,
    sku_id VARCHAR(20) NOT NULL,
    warehouse_id VARCHAR(20) NOT NULL,
    horizon_days INT NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    forecast_units DECIMAL(10, 3) NOT NULL,
    actual_units DECIMAL(10, 3) NOT NULL,
    error DECIMAL(10, 3) NOT NULL,
    absolute_error DECIMAL(10, 3) NOT NULL,
    squared_error DECIMAL(12, 3) NOT NULL,
    CONSTRAINT pk_fact_forecasts PRIMARY KEY (forecast_id),
    CONSTRAINT fk_fc_sku FOREIGN KEY (sku_id) REFERENCES dim_products (sku_id),
    CONSTRAINT fk_fc_wh FOREIGN KEY (warehouse_id) REFERENCES dim_warehouses (warehouse_id)
) ENGINE=InnoDB COMMENT='Held-out forecast predictions across baseline and ML models';

CREATE INDEX idx_fc_model_horizon ON fact_demand_forecasts (model_name, horizon_days);
CREATE INDEX idx_fc_sku_wh_date ON fact_demand_forecasts (sku_id, warehouse_id, forecast_date);

-- Fact Inventory Simulation (Daily discrete-event simulation results)
CREATE TABLE fact_inventory_simulation (
    sim_id BIGINT AUTO_INCREMENT NOT NULL,
    date DATE NOT NULL,
    sku_id VARCHAR(20) NOT NULL,
    warehouse_id VARCHAR(20) NOT NULL,
    policy_name VARCHAR(50) NOT NULL COMMENT 'Baseline Static vs SmartStock Optimized',
    beginning_inventory INT NOT NULL,
    demand_units INT NOT NULL,
    fulfilled_units INT NOT NULL,
    lost_sales_units INT NOT NULL,
    ending_inventory INT NOT NULL,
    ending_on_order INT NOT NULL,
    po_placed_units INT NOT NULL,
    po_received_units INT NOT NULL,
    holding_cost DECIMAL(10, 2) NOT NULL,
    ordering_cost DECIMAL(10, 2) NOT NULL,
    stockout_cost DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(10, 2) NOT NULL,
    is_stockout TINYINT NOT NULL,
    CONSTRAINT pk_fact_simulation PRIMARY KEY (sim_id),
    CONSTRAINT fk_sim_sku FOREIGN KEY (sku_id) REFERENCES dim_products (sku_id),
    CONSTRAINT fk_sim_wh FOREIGN KEY (warehouse_id) REFERENCES dim_warehouses (warehouse_id)
) ENGINE=InnoDB COMMENT='Daily simulation logs comparing inventory control policies';

CREATE INDEX idx_sim_policy_date ON fact_inventory_simulation (policy_name, date);
CREATE INDEX idx_sim_sku_wh ON fact_inventory_simulation (sku_id, warehouse_id);
