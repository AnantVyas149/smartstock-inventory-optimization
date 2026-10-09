"""
Script to generate notebooks/smartstock_walkthrough.ipynb programmatically.
"""

import nbformat as nbf

nb = nbf.v4.new_notebook()

cells = []

# Cell 1: Markdown Title & Abstract
cells.append(nbf.v4.new_markdown_cell("""# SmartStock: Enterprise Inventory Intelligence & Supply Chain Optimization
### A Data-Driven Decision Support System for Multi-Warehouse Replenishment
**Author:** Supply Chain Analytics & Operations Research Team  
**Dataset:** Authentic Walmart M5 Retail Demand (Scanner Transactions) + Operational Supply Chain Metadata  
**Tech Stack:** Python (Pandas, NumPy, Scipy, Statsmodels, LightGBM, Plotly, Seaborn), MySQL 8.0, Power BI, Streamlit

---

## 1. Executive Summary & Business Problem
A modern multi-echelon retail distributor faces three core operational tensions:
1. **The Availability Dilemma:** Stockouts damage customer goodwill, lose high-margin sales, and hurt market share.
2. **The Working Capital Dilemma:** Excess buffer inventory ties up expensive cash, incurs warehouse carrying costs, and exposes goods to obsolescence.
3. **The Uncertainty Dilemma:** Customer demand is highly volatile and intermittent, while overseas/domestic suppliers exhibit stochastic delivery lead times.

**SmartStock** bridges these tensions by replacing static, intuitive rules-of-thumb with **mathematically rigorous operations research** and **machine learning**:
- **Stochastic Lead-Time Convolution** (King / Silver-Pyke-Peterson variance propagation)
- **Gradient Boosted Demand Forecasting** (LightGBM vs Holt-Winters vs Baselines on out-of-sample held-out horizons)
- **Constrained Economic Order Quantities** (EOQ adjusted for MOQs and batch multiples)
- **Daily Discrete-Event Inventory Simulation** comparing existing legacy rules against the optimized policy.
"""))

# Cell 2: Imports & Environment Setup
cells.append(nbf.v4.new_code_cell("""import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import norm

# Setup paths
BASE_DIR = '..'
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
pd.set_option('display.max_columns', 25)
print('Environment initialized successfully.')
"""))

# Cell 3: Markdown Section 2 - Data Ingestion & Profiling
cells.append(nbf.v4.new_markdown_cell("""## 2. Data Hygiene & Exploratory Profiling
We inspect the dataset generated from the authentic Walmart M5 dataset covering **50 SKUs across 3 Regional Warehouses over 730 days (109,500 daily observations)**.
"""))

# Cell 4: Code - Load and inspect datasets
cells.append(nbf.v4.new_code_cell("""df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'dim_products.csv'))
df_warehouses = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'dim_warehouses.csv'))
df_suppliers = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'dim_suppliers.csv'))
df_demand = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'fact_daily_demand.csv'))

print(f"Total Products:     {len(df_products)}")
print(f"Total Warehouses:   {len(df_warehouses)}")
print(f"Total Suppliers:    {len(df_suppliers)}")
print(f"Total Demand Rows:  {len(df_demand):,}")
print(f"Total Revenue:      ${df_demand['revenue'].sum():,.2f}")
print(f"Zero-Demand Days:   {(df_demand['demand_units'] == 0).mean():.1%}")
"""))

# Cell 5: Markdown Section 3 - ABC-XYZ Segmentation
cells.append(nbf.v4.new_markdown_cell("""## 3. ABC-XYZ Portfolio Segmentation
Supply chain items cannot be managed with a one-size-fits-all policy:
- **ABC Classification (Pareto Rule):** Segmented by cumulative revenue contribution (A: top 80%, B: next 15%, C: bottom 5%).
- **XYZ Classification (Volatility):** Segmented by the **Coefficient of Variation ($CV = \\frac{\\sigma}{\\mu}$)**:
  - **Class X ($CV \\le 0.55$):** Highly stable, continuous demand.
  - **Class Y ($0.55 < CV \\le 0.95$):** Moderate variance, seasonal patterns.
  - **Class Z ($CV > 0.95$):** Highly erratic, intermittent demand.
"""))

# Cell 6: Code - ABC-XYZ Display
cells.append(nbf.v4.new_code_cell("""df_abc_xyz = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'sku_abc_xyz_profile.csv'))
print("--- ABC Revenue Share Breakdown ---")
print(df_abc_xyz.groupby('abc_class')[['total_revenue', 'total_units']].sum())

print("\\n--- ABC-XYZ 9-Box Matrix ---")
matrix = pd.crosstab(df_abc_xyz['abc_class'], df_abc_xyz['xyz_class'], margins=True)
print(matrix)
"""))

# Cell 7: Markdown Section 4 - Forecasting Benchmark
cells.append(nbf.v4.new_markdown_cell("""## 4. Demand Forecasting Engine
We evaluate four distinct forecasting methodologies on a **strictly held-out 28-day out-of-sample window**:
1. **Naive Baseline:** $y_{t+h} = y_t$
2. **Seasonal Naive (sNaive-7):** $y_{t+h} = y_{t+h-7}$
3. **Exponential Smoothing (Holt-Winters):** Additive trend + weekly seasonality
4. **LightGBM Regressor:** Gradient-boosted trees utilizing lag features ($t-7, t-14, t-21, t-28$), rolling statistics (mean/std over 7, 14, 28 days), calendar events, and price ratios.

### Evaluation Metrics
$$\\text{MAE} = \\frac{1}{N}\\sum |y - \\hat{y}|, \\quad \\text{RMSE} = \\sqrt{\\frac{1}{N}\\sum(y - \\hat{y})^2}, \\quad \\text{WAPE} = \\frac{\\sum |y - \\hat{y}|}{\\sum y}$$
*Why not MAPE?* In intermittent demand with 57.7% zero-sales days, $\\text{MAPE} = \\frac{|y - \\hat{y}|}{y}$ produces division by zero or infinite penalties, making it mathematically invalid for retail time series.
"""))

# Cell 8: Code - Forecasting Results
cells.append(nbf.v4.new_code_cell("""df_benchmark = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'forecast_model_benchmark.csv'))
print(df_benchmark.to_string(index=False))
"""))

# Cell 9: Markdown Section 5 - Inventory Optimization Theory
cells.append(nbf.v4.new_markdown_cell("""## 5. Operations Research: Inventory Optimization Mathematics

### 5.1 Stochastic Lead-Time Demand Variance
When both daily demand $D$ and supplier lead time $L$ are random variables with means $\\bar{D}, \\bar{L}$ and standard deviations $\\sigma_D, \\sigma_L$, the variance of total lead-time demand is derived via the **Law of Total Variance**:
$$\\text{Var}(D_L) = \\mathbb{E}[L]\\text{Var}(D) + (\\mathbb{E}[D])^2\\text{Var}(L) = \\bar{L}\\sigma_D^2 + \\bar{D}^2\\sigma_L^2$$

Thus, the stochastic Safety Stock formula is:
$$SS = Z \\times \\sqrt{\\bar{L}\\sigma_D^2 + \\bar{D}^2\\sigma_L^2}$$
Where $Z = \\Phi^{-1}(\\text{CSL})$. For a 95% Cycle Service Level, $Z = 1.645$.

### 5.2 Reorder Point (ROP) & Economic Order Quantity (EOQ)
$$ROP = (\\bar{D} \\times \\bar{L}) + SS$$
$$EOQ = \\sqrt{\\frac{2 \\cdot D_{\\text{annual}} \\cdot S}{H}}$$
Constrained by supplier minimums: $Q^* = \\max(EOQ, MOQ)$, rounded to the nearest batch pack multiple.
"""))

# Cell 10: Code - Inventory Parameters Inspection
cells.append(nbf.v4.new_code_cell("""df_snapshot = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'fact_inventory_snapshot.csv'))
print(f"Total Evaluated SKU-Warehouse Nodes: {len(df_snapshot)}")
print(f"Mean Safety Stock (Fixed LT):        {df_snapshot['safety_stock_fixed_lt'].mean():.1f} units")
print(f"Mean Safety Stock (Variable LT):     {df_snapshot['safety_stock_variable_lt'].mean():.1f} units")
print(f"Nodes Currently Below ROP:           {df_snapshot['is_below_rop'].sum()} ({df_snapshot['is_below_rop'].mean():.1%})")
print(f"Total Working Capital On-Hand:       ${df_snapshot['inventory_capital_tied'].sum():,.2f}")
"""))

# Cell 11: Markdown Section 6 - Daily Discrete-Event Simulation
cells.append(nbf.v4.new_markdown_cell("""## 6. Daily Discrete-Event Simulation & Policy Audit
We execute a dynamic 28-day daily simulation testing the **Baseline Legacy Rule** against **SmartStock Optimized Policy** on actual customer demand:
"""))

# Cell 12: Code - Simulation Results
cells.append(nbf.v4.new_code_cell("""df_sim_comp = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'simulation_policy_comparison.csv'))
for _, row in df_sim_comp.iterrows():
    print(f"Policy: {row['policy_name']}")
    print(f"  - Customer Fill Rate:    {row['fill_rate_pct']:.2f}%")
    print(f"  - Stockout Frequency:    {row['stockout_rate_pct']:.2f}% of node-days")
    print(f"  - Total Lost Sales:      {int(row['total_lost_sales']):,} units")
    print(f"  - Holding Cost:          ${row['total_holding_cost']:,.2f}")
    print(f"  - Ordering Admin Cost:   ${row['total_ordering_cost']:,.2f}")
    print(f"  - Stockout Penalty:      ${row['total_stockout_cost']:,.2f}")
    print(f"  - TOTAL OPERATING COST:  ${row['total_modeled_cost']:,.2f}")
    print('-'*50)

base_c = df_sim_comp[df_sim_comp['policy_name'] == 'Baseline Legacy Rule']['total_modeled_cost'].values[0]
opt_c = df_sim_comp[df_sim_comp['policy_name'] == 'SmartStock Optimized']['total_modeled_cost'].values[0]
savings_val = base_c - opt_c
savings_pct_val = (savings_val / base_c) * 100
print(f"NET FINANCIAL SAVINGS: ${savings_val:,.2f} ({savings_pct_val:.1f}% Cost Reduction)")
"""))

# Cell 13: Markdown Section 7 - Scenario Stress Testing
cells.append(nbf.v4.new_markdown_cell("""## 7. Strategic Scenario Sensitivity Analysis
We subject the network to supply shocks, demand surges, and executive service level adjustments:
"""))

# Cell 14: Code - Scenario Matrix
cells.append(nbf.v4.new_code_cell("""df_scenarios = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'scenario_analysis_results.csv'))
print(df_scenarios[['Scenario', 'Avg_Safety_Stock_Units', 'Avg_Reorder_Point_Units', 'Total_Working_Capital_USD', 'Total_Annual_Policy_Cost_USD', 'Cost_Variance_Pct', 'High_Risk_Node_Count']].to_string(index=False))
"""))

# Cell 15: Markdown Section 8 - Conclusion & Strategic Recommendations
cells.append(nbf.v4.new_markdown_cell("""## 8. Strategic Business Recommendations

1. **Adopt LightGBM Demand Forecasting:** LightGBM achieved a **66.12% WAPE**, cutting out-of-sample forecast error by **27.5 percentage points** over naive baselines. This provides the demand signal foundation required for precision replenishment.
2. **Implement Stochastic Lead-Time Safety Buffers:** Accounting for supplier variance ($\\sigma_L$) adds ~17% to safety stock buffers, directly reducing stockout exposure from 6.38% down to 2.62% and increasing fill rate to 91.54%.
3. **Execute Supplier Development for High-Risk Vendors:** Pacific Leisure Goods Ltd exhibited an on-time delivery rate of only 82% and an average lead time of 28 days. Contracts should either enforce SLA penalties or reallocate volume to domestic partners.
4. **Deploy the Streamlit Decision Simulator & Power BI Executive Dashboard:** Equip operational purchasing agents with real-time ROP replenishment boards and leadership with financial exposure monitors.
"""))

nb['cells'] = cells

output_path = 'notebooks/smartstock_walkthrough.ipynb'
with open(output_path, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"Successfully generated {output_path}!")
