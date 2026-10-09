# SmartStock: Enterprise Inventory Intelligence & Supply Chain Optimization Platform

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![Machine Learning](https://img.shields.io/badge/LightGBM-4.7-brightgreen.svg)](https://lightgbm.readthedocs.io/)
[![Business Intelligence](https://img.shields.io/badge/Power%20BI-Dashboard-yellow.svg)](https://powerbi.microsoft.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)
[![Dataset](https://img.shields.io/badge/Dataset-Walmart%20M5%20Retail-blueviolet.svg)](https://www.kaggle.com/c/m5-forecasting-accuracy)

---

## 1. Executive Summary & Business Context

In multi-warehouse retail and industrial manufacturing, supply chain executives face three constant conflicting pressures:
1. **The Availability Mandate:** Stockouts cause lost immediate sales, damage brand goodwill, and drive customers to competitors.
2. **The Working Capital Constraint:** Holding safety stock ties up expensive cash, incurs warehouse carrying costs (20–25% annual holding rate), and exposes goods to spoilage and obsolescence.
3. **The Uncertainty Challenge:** Customer demand is intermittent and seasonal, while supplier lead times are stochastic and prone to logistics bottlenecks.

**SmartStock** is an end-to-end inventory intelligence and replenishment decision-support system. It transforms raw retail point-of-sale scanner transactions into operational purchase orders, multi-echelon safety stock buffers, and out-of-sample demand forecasts.

### Core Business Questions Answered:
1. **Stockout Risk Identification:** Which SKU-warehouse nodes will stock out before the next purchase order arrives?
2. **Working Capital Visibility:** How much cash is trapped across categories and regional hubs?
3. **Demand Forecasting:** What are expected demand levels across 7, 14, and 28-day planning horizons?
4. **Model Selection:** Which statistical or machine learning algorithm yields the lowest out-of-sample error?
5. **Replenishment Parameters:** What should Safety Stock, Reorder Point (ROP), and Order Quantity (EOQ) be for each SKU?
6. **Supplier Reliability:** Which vendors pose lead-time and on-time delivery (OTD) risks?
7. **Scenario Sensitivity:** How do demand surges (+30%) and port delays (+50% lead time) impact carrying costs?
8. **Policy Superiority:** Can an optimized stochastic inventory policy reduce total operating cost while lifting service levels?

---

## 2. Key Results & Quantitative Impact

### 28-Day Dynamic Simulation Audit (Held-Out Test Period)
| Operational Metric | Baseline Legacy Rule | SmartStock Optimized | Business Variance / Lift |
|---|---|---|---|
| **Customer Fill Rate (Service Level)** | 83.76% | **91.54%** | **+7.78% Service Level Lift** |
| **Stockout Frequency** | 6.38% of node-days | **2.62% of node-days** | **-58.9% Reduction in Stockouts** |
| **Total Lost Sales** | 1,062 units | **553 units** | **-47.9% Lost Demand Avoided** |
| **Total Holding Cost** | \$254.34 | \$1,085.26 | +\$830.92 (Controlled Buffer Investment) |
| **Purchase Order Placement Admin Cost** | \$13,785.00 | \$13,200.00 | -\$585.00 (Optimized PO Cadence) |
| **Stockout Penalties & Lost Profit** | \$2,798.08 | \$1,415.56 | -\$1,382.52 (Penalties Averted) |
| **TOTAL MODELED INVENTORY COST** | **\$16,836.64** | **\$15,701.52** | **-\$1,135.12 Net Savings (-6.7%)** |

> **Financial Takeaway:** Investing in stochastic buffer stock increased inventory carrying costs by \$830, but averted \$1,382 in stockout penalties and saved \$585 in emergency order placement costs—yielding a **6.7% net cost reduction** while pushing customer fill rate past 91.5%.

---

## 3. Technology Stack

- **Data Processing & Analytics:** Python 3.14+, Pandas, NumPy, Scipy, Statsmodels
- **Machine Learning & Forecasting:** LightGBM Regressor, Holt-Winters Exponential Smoothing, Seasonal Naive, Naive Baselines
- **Relational Database & SQL:** MySQL 8.0 (DDL schema, CTEs, Window Functions, Partitions, Aggregations)
- **Interactive Decision Simulation:** Streamlit, Plotly Express & Graph Objects
- **Business Intelligence & Dashboards:** Power BI Desktop (Star-Schema Semantic Model, 20+ DAX Measures)
- **Exploratory Visualizations:** Matplotlib, Seaborn

---

## 4. Grounded Dataset Architecture

The demand engine is grounded directly in the **Walmart M5 Forecasting Dataset**:
- **Source Data:** `calendar.csv`, `sales_train_validation.csv` (120 MB), `sell_prices.csv` (203 MB).
- **Representative Portfolio Subset:** 50 diverse SKUs across 3 commodity categories (`FOODS`, `HOUSEHOLD`, `HOBBIES`) across 3 regional distribution hubs (`WH-CA1`, `WH-TX1`, `WH-WI1`).
- **Timeline:** 730 continuous calendar days (April 2014 to April 2016), comprising **109,500 daily demand records** and **\$482,966 in retail revenue**.
- **Demand Characteristics:** Authentic retail intermittent demand featuring **57.7% zero-sales days** and weekend/seasonal spikes.
- **Operational Layer:** Integrated 8 suppliers with empirical lead-time distributions (log-normal delays), contracted SLAs, MOQs (24 to 96 units), ordering multiples, annual holding rates (20–25%), and 6,220 historical purchase orders.

---

## 5. Operations Research & Replenishment Mathematics

### 5.1 Stochastic Lead-Time Convolution (King / Silver-Pyke-Peterson)
When customer demand $D \sim (\bar{D}, \sigma_D^2)$ and supplier lead time $L \sim (\bar{L}, \sigma_L^2)$ are stochastic random variables, the lead-time demand variance follows the **Law of Total Variance**:
$$\text{Var}(D_L) = \mathbb{E}[L]\text{Var}(D) + (\mathbb{E}[D])^2\text{Var}(L) = \bar{L}\sigma_D^2 + \bar{D}^2\sigma_L^2$$
$$\sigma_{LTD} = \sqrt{\bar{L}\sigma_D^2 + \bar{D}^2\sigma_L^2}$$

The dynamic Safety Stock is:
$$SS = \lceil Z \times \sigma_{LTD} \rceil = \lceil Z \times \sqrt{\bar{L}\sigma_D^2 + \bar{D}^2\sigma_L^2} \rceil$$
*Where:* $Z = \Phi^{-1}(\text{CSL})$. For 95% Cycle Service Level, $Z = 1.645$.

### 5.2 Reorder Point (ROP) & Constrained EOQ
$$ROP = \lceil (\bar{D} \times \bar{L}) + SS \rceil$$
$$EOQ = \sqrt{\frac{2 \cdot D_{\text{annual}} \cdot S}{H}}$$
$$Q^* = \lceil \frac{\max(EOQ, MOQ)}{\text{Batch Multiple}} \rceil \times \text{Batch Multiple}$$

---

## 6. Out-of-Sample Demand Forecasting Benchmark

Models were trained on 702 days and evaluated on a strictly chronologically held-out **28-day out-of-sample test window** across all 150 SKU-warehouse nodes:

| Model Name | Horizon | MAE (Units) | RMSE (Units) | WAPE (%) | Accuracy (%) | Bias |
|---|---|---|---|---|---|---|
| **Naive Baseline** | 28-Day | 1.458 | 3.005 | 93.64% | 6.36% | -0.137 |
| **Seasonal Naive (sNaive-7)**| 28-Day | 1.427 | 3.091 | 91.65% | 8.35% | -0.100 |
| **Exponential Smoothing** | 28-Day | 1.160 | 2.353 | 74.47% | 25.53% | -0.013 |
| **LightGBM Regressor** | **28-Day** | **1.030** | **2.408** | **66.12%** | **33.88%** | **-0.483** |

> **Why WAPE instead of MAPE?** In retail scanner datasets with 57.7% zero-sales days, Mean Absolute Percentage Error ($\text{MAPE} = \frac{|y - \hat{y}|}{y}$) incurs division-by-zero errors. Weighted Absolute Percentage Error ($\text{WAPE} = \frac{\sum |y - \hat{y}|}{\sum y}$) weights errors by sales volume, providing an unbiased metric for supply chain planning.

---

## 7. Enterprise SQL Analytics Suite (MySQL 8.0)

Located in `sql/schema.sql` and `sql/analytical_kpis.sql`:
1. **Query 1:** Daily & Monthly Demand Aggregations with MoM Growth & Rolling 3-Month Averages (`LAG()`, `AVG() OVER()`).
2. **Query 2:** Inventory Working Capital Tied Up & Days of Inventory Coverage (DOH/DOI).
3. **Query 3:** ABC-XYZ 9-Box Matrix Segmentation via Pareto Cumulative Share (`SUM() OVER()`) and Coefficient of Variation.
4. **Query 4:** Stockout Risk and Immediate Vulnerability Detection (flagging nodes exhausting inventory prior to PO arrival).
5. **Query 5:** Replenishment Orders Below ROP with Constrained EOQ/MOQ calculation.
6. **Query 6:** Supplier Lead-Time Scorecard, Delivery Delay Bias, and OTD Risk Tiering.
7. **Query 7:** High-Value Slow-Moving Inventory Identification (SLOB detection).
8. **Query 8:** Multi-Horizon Forecast Accuracy Benchmarking (WAPE, MAE, RMSE).
9. **Query 9:** Modeled Inventory Cost Structure across Warehouses and Categories.
10. **Query 10:** Operational Replenishment Dispatch Board ranked by urgency (`DENSE_RANK()`).

---

## 8. Power BI Executive Dashboard Architecture

The Power BI solution is organized into 5 dedicated analytical pages backed by a Star-Schema data model:
- **Page 1 — Executive Overview:** Total Inventory Value, Customer Fill Rate, Stockout Incident Rate, Modeled Policy Cost Savings, and DC Working Capital Distribution.
- **Page 2 — Demand Planning:** Out-of-sample actual vs forecast lines, WAPE benchmarking by model and category, and high-error SKU drilldowns.
- **Page 3 — Inventory Health:** ABC-XYZ 9-Box Matrix, Days of Coverage vs Capital Scatter, Stock on Hand vs ROP & Safety Stock, and Urgent Replenishment Action Board.
- **Page 4 — Supplier Performance:** Supplier Reliability Quadrant (OTD % vs Lead Time), Vendor Risk Tiering, Inbound PO Spend, and delayed shipment tracking.
- **Page 5 — Decision Simulator:** What-if service level comparisons (90% to 99%), lead-time shock evaluations, and policy trade-off curves.

*Refer to `powerbi/data_model_guide.md` and `powerbi/dashboard_specs.md` for visual-by-visual layout instructions, and `powerbi/DAX_measures.dax` for the full DAX measure library.*

---

## 9. Interactive Streamlit Decision Simulator

An interactive web application located in `app/streamlit_app.py` allows executives and operations research teams to test scenarios in real time:

To launch the application:
```bash
streamlit run app/streamlit_app.py
```

Features:
- **Live Parametric Sliders:** Demand Surges (-20% to +50%), Supplier Delays (0% to +100%), Service Level Targets (85% to 99%), and Holding Cost Rates.
- **Dynamic Recalculations:** Real-time re-computation of Safety Stock, Reorder Points, Working Capital, and High-Risk Node counts.
- **Visual Command Center:** Plotly interactive charts for cost breakdowns, supplier risk quadrants, and replenishment dispatch.

---

## 10. Repository File Structure

```
SmartStock/
├── data/
│   ├── raw/                  # Source Walmart M5 datasets (calendar, sales, prices)
│   ├── processed/            # Cleaned relational CSVs, model forecasts, and simulation logs
│   └── powerbi_exports/      # Star-schema CSV tables formatted for Power BI Desktop
├── sql/
│   ├── schema.sql            # MySQL 8.0 DDL relational schema with indexes & constraints
│   └── analytical_kpis.sql   # Production SQL queries with CTEs and Window Functions
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py      # M5 ingestion, operational dimension generator, and data hygiene audits
│   ├── eda_analytics.py      # ABC-XYZ segmentation, Pareto analysis, supplier profiling, and plots
│   ├── forecasting.py        # Naive, sNaive, Holt-Winters, and LightGBM out-of-sample benchmark
│   ├── inventory_engine.py   # Stochastic Safety Stock, ROP, Constrained EOQ, and Inventory Position
│   ├── simulation.py         # 28-day daily discrete-event inventory simulation engine
│   ├── scenario_analysis.py  # Parametric stress testing (+demand, +lead time, service level curves)
│   └── export_powerbi.py     # Power BI star-schema export utility
├── notebooks/
│   └── smartstock_walkthrough.ipynb # Comprehensive portfolio walkthrough notebook
├── app/
│   └── streamlit_app.py      # Streamlit Interactive Executive Command Center & Simulator
├── reports/
│   ├── figures/              # Generated high-resolution publication charts
│   ├── executive_summary.md  # Leadership memo with financial impacts and ROI
│   └── data_dictionary.md   # Complete schema, mathematical formulas, and cost assumptions
├── powerbi/
│   ├── DAX_measures.dax      # Complete DAX measures library categorized by dashboard page
│   ├── data_model_guide.md   # Star-schema relationships, cardinality, and setup guide
│   └── dashboard_specs.md    # Visual-by-visual layout specifications for all 5 pages
├── requirements.txt          # Python dependencies
└── README.md                 # Master project documentation
```

---

## 11. How to Run & Reproduce the Project

### Step 1: Clone Repository & Install Dependencies
```bash
git clone https://github.com/AnantVyas149/smartstock-inventory-optimization.git
cd smartstock-inventory-optimization
pip install -r requirements.txt
```

### Step 2: Run Master Pipeline (All 7 Steps in One Command)
```bash
python main.py
```

*Alternatively, execute the individual modules sequentially:*
```bash
# 1. Ingest M5 data and generate operational supply chain layers
python src/data_pipeline.py

# 2. Run data validation, ABC-XYZ segmentation, and profiling
python src/eda_analytics.py

# 3. Train and benchmark forecasting models on held-out test data
python src/forecasting.py

# 4. Calculate stochastic replenishment parameters (SS, ROP, EOQ)
python src/inventory_engine.py

# 5. Run 28-day daily discrete-event inventory simulation
python src/simulation.py

# 6. Execute parametric scenario stress tests
python src/scenario_analysis.py

# 7. Export star-schema tables for Power BI
python src/export_powerbi.py
```

### Step 3: Launch Streamlit App
```bash
streamlit run app/streamlit_app.py
```

### Step 4: Open in Power BI Desktop
1. Open Power BI Desktop.
2. Load CSV files from `data/powerbi_exports/`.
3. Follow `powerbi/data_model_guide.md` to link relationships and `powerbi/dashboard_specs.md` to construct visuals.
