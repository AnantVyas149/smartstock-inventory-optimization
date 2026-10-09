# SmartStock: Executive Supply Chain & Inventory Optimization Memo

**TO:** Chief Supply Chain Officer (CSCO), Chief Financial Officer (CFO), VP of Operations  
**FROM:** Senior Supply Chain Analytics & Operations Research Team  
**DATE:** October 2026  
**SUBJECT:** Operational Replenishment Transformation & Dynamic Simulation Results  

---

## 1. Executive Summary & Core Financial Impact

In retail and industrial distribution, management is caught between two costly extremes: carrying excess inventory that ties up expensive working capital, or running lean and suffering stockouts that lose high-margin sales and erode customer loyalty.

To resolve this trade-off, we developed **SmartStock**, an end-to-end inventory intelligence and replenishment decision-support system grounded on **authentic Walmart retail scanner demand (M5 dataset)** across a 3-distribution-center network.

### Key Financial & Operational Results (28-Day Simulation Audit)
- **Net Cost Savings:** **6.7% reduction** in total modeled inventory operational costs ($1,135.12 net savings over the 28-day window across our 50-SKU test portfolio, scaling to **over \$148,000 in annualized savings** across the full regional catalog).
- **Service Level (Fill Rate) Lift:** Increased from **83.76% to 91.54%** (+7.78 percentage points improvement in unconstrained customer demand fulfillment).
- **Stockout Frequency Reduction:** Stockout incident rate fell from **6.38% to 2.62%** of node-days (a **58.9% reduction in stockout occurrences**).
- **Lost Sales Avoidance:** Cut lost sales units by nearly half (**from 1,062 lost units down to 553 units**).
- **Forecast Accuracy Breakthrough:** Gradient-boosted demand forecasting (LightGBM) achieved an out-of-sample **WAPE of 66.12%**, outperforming naive persistence benchmarks by **27.52 percentage points**.

---

## 2. Root Cause Analysis: Why the Legacy Policy Failed

Our audit of the legacy baseline rule (static 14-day reorder point with fixed monthly replenishment batches) revealed three critical operational flaws:

1. **Failure to Account for Lead-Time Variance:** Legacy rules treated supplier lead time as a constant deterministic scalar. However, supplier delays follow right-skewed distributions. When overseas or domestic shipments were delayed by 3 to 7 days, the static buffer was exhausted immediately, causing cascading stockouts.
2. **Intermittent Demand Blind Spots:** In retail store scanner data, 57.7% of daily observations are zero-sales days. Static moving averages over-ordered during random cluster spikes and under-ordered right before seasonal peaks.
3. **Suboptimal Order Sizing:** Ordering fixed batch quantities without balancing administrative PO placement costs ($75–$110/PO) against inventory holding rates (20–25%/year) resulted in excessive purchase order frequencies and administrative overhead.

---

## 3. The SmartStock Solution Architecture

SmartStock replaces heuristic rules with a multi-layered stochastic optimization engine:

```
[M5 Scanner Demand & Calendar] + [Supplier & Warehouse Dimensions]
                           │
                           ▼
          [Out-of-Sample Machine Learning Forecasting]
            - LightGBM Regressor (WAPE 66.1%, MAE 1.03)
                           │
                           ▼
        [Stochastic Inventory Optimization Engine]
  - King / Silver-Pyke-Peterson Variance Propagation:
      Var(LTD) = L * sigma_D^2 + D^2 * sigma_L^2
  - Stochastic Safety Stock: SS = Z * sqrt(Var(LTD))
  - Reorder Point: ROP = LTD + SS
  - Constrained EOQ: max(EOQ, MOQ) with batch multiples
                           │
                           ▼
          [Daily Discrete-Event Simulation Loop]
    - Inbound PO arrivals, Lost Sales, Holding/Ordering Costs
                           │
                           ▼
      [Executive Power BI Dashboard & Streamlit Simulator]
```

### Mathematical Innovation: Stochastic Lead-Time Convolution
SmartStock implements the King (2011) variance propagation equation, convolving stochastic customer demand ($D \sim \mu_D, \sigma_D$) with stochastic vendor lead time ($L \sim \mu_L, \sigma_L$):
$$\sigma_{LTD} = \sqrt{\bar{L}\sigma_D^2 + \bar{D}^2\sigma_L^2}$$
$$SS = Z \times \sigma_{LTD}$$

This dynamic buffer increases safety stock on long-lead-time, high-volatility items (such as overseas hobby goods) by **17.3%**, while freeing up capital on local, highly reliable fresh goods.

---

## 4. Supplier Performance & Risk Exposure

Our vendor scorecard evaluated 6,220 historical purchase orders across 8 suppliers:

| Supplier Name | Category Specialty | Contracted LT | Actual LT | Delay Bias | OTD Rate | Risk Tier |
|---|---|---|---|---|---|---|
| **Prairie Valley Dairy** | Foods | 4 days | 3.6 days | -0.4 days | 97.4% | Low Risk (Preferred) |
| **National Fresh Foods** | Foods | 5 days | 4.6 days | -0.4 days | 96.2% | Low Risk (Preferred) |
| **Apex CPG Cleaners** | Household | 10 days | 9.4 days | -0.6 days | 95.3% | Low Risk (Preferred) |
| **Harvest Prime Provisions** | Foods | 7 days | 6.8 days | -0.2 days | 94.1% | Moderate Risk (Watchlist) |
| **Keystone Merchandise** | Household | 12 days | 12.0 days | 0.0 days | 92.8% | Moderate Risk (Watchlist) |
| **CleanLiving Home** | Household | 14 days | 14.1 days | +0.1 days | 91.2% | Moderate Risk (Watchlist) |
| **Global Craft Importers** | Hobbies | 21 days | 22.1 days | +1.1 days | 88.4% | Moderate Risk (Watchlist) |
| **Pacific Leisure Goods** | Hobbies | 28 days | 30.2 days | +2.2 days | 82.1% | **High Risk (Critical)** |

**Strategic Action:** Pacific Leisure Goods accounts for significant stockout exposure due to an 82.1% OTD rate and +2.2 day delay bias. We recommend implementing contractual SLA delay penalties or dual-sourcing 30% of hobby volume with nearshore suppliers.

---

## 5. Scenario Stress Testing & Macroeconomic Sensitivity

Using our parametric scenario engine, we stress-tested the supply chain against market shocks:

1. **Demand Surge (+20%):** Increases average ROP from 32.9 to 38.3 units and raises required working capital by **9.1%** ($63.9K to $69.8K). Total annual policy cost rises by 9.6%.
2. **Lead Time Shock (+50% Port Delays):** Pushes network high-risk exposure from 65 nodes to **109 nodes (72.7% of network)**. Requires an immediate capital injection of buffer stock to prevent widespread stockouts.
3. **Compound Crisis (+20% Demand & +50% Lead Time):** Explodes high-risk nodes to **125 of 150 (83.3%)**, requiring average ROP to jump to 53.2 units.
4. **Service Level Sensitivity (90% vs 99%):** Moving from 95% CSL (Z=1.645) to 99% CSL (Z=2.326) increases average Safety Stock from **12.9 to 18.0 units (+39.5%)**. Management should target 98% on Class-A revenue drivers, but cap Class-C items at 90% to avoid locking up unnecessary cash.

---

## 6. Phased Implementation Roadmap

1. **Month 1: Automated Dispatch Integration:** Connect the SmartStock SQL Replenishment Query (Query 10) to procurement ERP systems to automate weekly purchase orders for nodes below ROP.
2. **Month 2: BI Dashboard Deployment:** Launch the 5-page Power BI dashboard for daily category manager reviews and inventory health monitoring.
3. **Month 3: Supplier SLA Renegotiation:** Utilize the vendor scorecard to establish supplier lead-time compliance agreements and volume allocation incentives.
4. **Month 4: Dynamic Re-tuning:** Re-train LightGBM forecasting weights and re-calculate seasonal ROPs quarterly.
