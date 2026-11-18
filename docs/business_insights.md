# Business Insights

**Analysis date:** 2026-11-18  
**Dataset:** Olist Brazilian E-Commerce Public Dataset (raw CSVs)  
**Scope:** Delivered orders only; purchase dates **2016-09-15 → 2018-08-29**  
**Orders in scope:** 96,478 delivered orders · **93,358** unique customers  

**Standards applied**

- Figures below are calculated from source extracts (see `scripts/ba_analysis.py` / `docs/_analysis_cache.json`).
- **Revenue = merchandise GMV**, not profit.
- Delivery–review relationships are **associations**, not proven causation.
- Early months (2016) and incomplete ramps are noted where they distort growth.

Currency amounts are **BRL** as stored in source fields.

---

## Executive snapshot (observations only)

| KPI | Value |
|---|---|
| Merchandise revenue | R$ 13,221,498 |
| Freight charges | R$ 2,202,966 |
| Total order value | R$ 15,424,464 |
| Average order value | R$ 159.88 |
| Unique customers | 93,358 |
| Repeat customer rate | 3.00% |
| Orders per customer | 1.03 |
| Average review score | 4.16 / 5 |
| Average delivery time | 12.56 days |
| Late delivery % | 8.11% |
| Avg actual − estimated delivery | −11.18 days (earlier than estimate on average) |

---

# A. Sales questions

## A1. Which categories generate the highest sales?

### 1) Required data
`order_items.price`, `orders.order_status`, `orders.order_purchase_timestamp`, `products.product_category_name`, `product_category_name_translation`.

### 2) Metric
Merchandise revenue by English category; category contribution %.

### 3) SQL calculation
See `kpi_definitions.md` §4.1 and §4.3.

### 4) Result (top 10 by merchandise revenue)

| Rank | Category | Merchandise revenue (BRL) | Share |
|---:|---|---:|---:|
| 1 | health_beauty | 1,233,132 | 9.3% |
| 2 | watches_gifts | 1,166,177 | 8.8% |
| 3 | bed_bath_table | 1,023,435 | 7.7% |
| 4 | sports_leisure | 954,853 | 7.2% |
| 5 | computers_accessories | 888,725 | 6.7% |
| 6 | furniture_decor | 711,928 | 5.4% |
| 7 | housewares | 615,629 | 4.7% |
| 8 | cool_stuff | 610,204 | 4.6% |
| 9 | auto | 578,967 | 4.4% |
| 10 | toys | 471,286 | 3.6% |

Top 5 categories = **~39.8%** of merchandise revenue.

### 5) Trends
Leaders are diversified across beauty, gifts, home, sports, and tech accessories rather than a single dominant category.

### 6) Commercial implications
Assortment and seller recruitment in these five categories disproportionately affect GMV. Promotional calendars should protect capacity and stock in these lines.

### 7) Recommended action
See `recommendations.md` — prioritise supply, visibility, and SLA monitoring for the top-5 GMV categories.

### 8) Limitations
- Category labels depend on seller taxonomy quality.  
- Revenue ≠ margin; high-sales categories may not be most profitable.  
- Multi-item baskets attribute revenue by item category, not “primary” basket category.

---

## A2. Which categories are declining?

### 1) Required data
Category merchandise revenue by purchase month.

### 2) Metric
% change in merchandise revenue between two multi-month windows with material platform volume:

- **Period 1:** 2017-03 → 2017-11  
- **Period 2:** 2017-12 → 2018-08  

Only categories with Period 1 revenue ≥ R$ 50,000.

### 3) SQL calculation (pattern)

```sql
-- Compare SUM(price) by category for period1 vs period2 purchase months
-- change_pct = (period2 - period1) / period1 * 100
```

### 4) Result — clearest decliners

| Category | Period 1 (BRL) | Period 2 (BRL) | Change |
|---|---:|---:|---:|
| computers | 133,791 | 79,144 | **−40.8%** |
| cool_stuff | 324,587 | 265,259 | **−18.3%** |
| toys | 230,071 | 223,188 | −3.0% |

**Fast growers in the same window (context):** stationery (+150%), housewares (+128%), baby (+126%), health_beauty (+116%), auto (+114%).

### 5) Trends
Decline is concentrated, not broad-based. Several large categories accelerated in Period 2 while `computers` and `cool_stuff` lost ground.

### 6) Commercial implications
Portfolio mix is shifting toward beauty, auto, housewares, and baby. Declining categories may reflect demand shift, assortment gaps, pricing, or seller exit — **not identifiable from sales totals alone**.

### 7) Recommended action
Category deep-dive on `computers` and `cool_stuff` (SKU count, active sellers, conversion proxies if available). Do not cut based on revenue trend alone without margin/availability context.

### 8) Limitations
- Period lengths are equal in month count but include seasonality (e.g. Nov peak in Period 1).  
- Absolute Period 2 platform volume is higher overall, so “decline” is relative category performance, not proof of operational failure.  
- No traffic/conversion data in source.

---

## A3. What are the monthly trends?

### 1) Required data
Delivered order items + purchase timestamp.

### 2) Metric
Monthly merchandise revenue, order count, MoM %.

### 3) SQL calculation
See `kpi_definitions.md` §1.5.

### 4) Result — interpretation of the series

| Phase | Observation |
|---|---|
| 2016–early 2017 | Ramp-up; MoM % unstable (low volume) — **not usable as run-rate**. |
| 2017-02 → 2017-10 | Steady build from ~R$ 234k to ~R$ 648k merchandise / month. |
| **2017-11** | Peak month: **R$ 987,765** merchandise; **7,289** orders (~+52% MoM). Consistent with major promotional seasonality. |
| 2017-12 | Post-peak drop (−26% MoM) to R$ 726k. |
| 2018-01 → 2018-05 | High plateau (~R$ 826k–978k). |
| 2018-06 → 2018-08 | Softening: R$ 856k → 868k → **839k**; Aug −3.4% MoM. |

### 5) Trends
Long-term growth from 2017 into early 2018, then **flattening / mild decline** in mid-2018 versus the Mar–May 2018 peak.

### 6) Commercial implications
Management should not extrapolate 2017 hyper-growth into 2018 H2. Planning should use 2018 run-rate with explicit seasonality for November.

### 7) Recommended action
Set 2019 forecasts from 2018 monthly baseline + November uplift scenario; investigate June–August softness (mix, competition, logistics capacity) as a structured review.

### 8) Limitations
- August 2018 may be partially truncated relative to a full operational month depending on extract cut-off (last purchase 2018-08-29).  
- Delivered-only view lags purchase demand for late-period orders still in transit (less relevant at extract end for historical months).

---

## A4. Which regions generate the most revenue?

### 1) Required data
`customers.customer_state` joined via orders → items.

### 2) Metric
Merchandise revenue and order count by customer state; revenue share %.

### 3) SQL calculation

```sql
SELECT c.customer_state,
       SUM(oi.price) AS merchandise_revenue,
       COUNT(DISTINCT oi.order_id) AS orders
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY merchandise_revenue DESC;
```

### 4) Result — top states

| State | Merchandise revenue (BRL) | Share | Orders |
|---|---:|---:|---:|
| **SP** | 5,067,633 | **38.3%** | 40,501 |
| RJ | 1,759,651 | 13.3% | 12,350 |
| MG | 1,552,482 | 11.7% | 11,354 |
| RS | 728,897 | 5.5% | 5,345 |
| PR | 666,064 | 5.0% | 4,923 |
| SC | 507,012 | 3.8% | 3,546 |
| BA | 493,584 | 3.7% | 3,256 |

**SP + RJ + MG ≈ 63.4%** of merchandise revenue.

### 5) Trends
Revenue is heavily concentrated in the Southeast.

### 6) Commercial implications
National campaigns will still be dominated by SP/RJ/MG outcomes. Expansion into North/Northeast may grow orders but with different delivery economics (see Operations).

### 7) Recommended action
Dual strategy: defend Southeast experience/share; expand other regions only with logistics SLAs sized to observed delay risk.

### 8) Limitations
- Customer state ≠ delivery destination warehouse; cross-border shipping within Brazil still applies.  
- Population and internet penetration differences are external factors not in the dataset.

---

# B. Customer questions

## B1. How frequently do customers purchase?

### 1) Required data
`customer_unique_id`, delivered orders.

### 2) Metric
Orders per customer (mean).

### 3) SQL calculation
See `kpi_definitions.md` §2.3.

### 4) Result
**1.03** delivered orders per unique customer on average.

### 5) Trends
Marketplace behaviour is predominantly **one-and-done** within the observed window.

### 6) Commercial implications
Growth has been driven more by acquiring new customers than by deepening existing relationships. AOV and acquisition cost matter more than classical loyalty flywheels today.

### 7) Recommended action
Design retention tests (post-delivery offers, category cross-sell) aimed at converting first-order buyers — see recommendations.

### 8) Limitations
- Observation window ~2 years; some “one-time” buyers may repurchase after the extract end.  
- `customer_unique_id` quality depends on marketplace identity resolution.

---

## B2. What proportion of customers place repeat orders?

### 1–3) Data / metric / SQL
See `kpi_definitions.md` §2.2.

### 4) Result
**3.00%** repeat customers (2,801 / 93,358).

### 5) Trends
Repeat purchasing is rare relative to the large first-order base.

### 6) Commercial implications
Small improvements in repeat rate can move GMV meaningfully because the base of first-order customers is large — but only if offers are targeted (avoid blanket discounting that erodes merchandise value without measuring incrementality).

### 7) Recommended action
Prioritise CRM for Top-quartile spenders and on-time, high-review first orders (higher propensity proxies — test, don’t assume).

### 8) Limitations
Repeat rate is unweighted by revenue; a 3% repeater pool may still include high spenders.

---

## B3. Which customer segments are most valuable?

### 1) Required data
Lifetime merchandise spend per `customer_unique_id`.

### 2) Metric
Quartile segments by merchandise revenue.

### 3) Calculation
`pd.qcut` on lifetime merchandise revenue → Low / Medium / High / Top.

### 4) Result

| Segment | Customers | Merchandise revenue (BRL) | Avg spend | Revenue share | Avg orders |
|---|---:|---:|---:|---:|---:|
| Low | 23,341 | 679,248 | 29.10 | 5.1% | 1.00 |
| Medium | 23,338 | 1,527,015 | 65.43 | 11.5% | 1.02 |
| High | 23,339 | 2,747,817 | 117.74 | 20.8% | 1.03 |
| **Top** | 23,340 | **8,267,417** | **354.22** | **62.5%** | 1.08 |

### 5) Trends
Value is highly concentrated: the **Top quartile produces ~62.5% of merchandise revenue** despite equal headcount by construction.

### 6) Commercial implications
“Most valuable” customers are primarily **higher basket / higher lifetime merchandise spend**, not frequent repeaters (avg orders only 1.08 even in Top).

### 7) Recommended action
Protect Top-quartile experience (delivery promise accuracy, VIP support) and recruit sellers/SKUs that serve higher AOV baskets.

### 8) Limitations
- Quartiles are relative, not CRM tiers with business rules.  
- No gross margin — a high spender on low-margin freight-heavy goods may be less valuable economically.

---

# C. Operations questions

## C1. How often are orders delivered late?

### 1–3) Data / metric / SQL
See `kpi_definitions.md` §3.2–3.3.

### 4) Result
- Late delivery rate: **8.11%**  
- Average delivery time: **12.56 days**  
- Average actual − estimated: **−11.18 days** (estimates are generally conservative)

### 5) Trends
Most orders arrive before the promise date, but roughly **1 in 12** miss the estimate.

### 6) Commercial implications
Promise dates appear buffered on average; the business risk is the **late tail**, which correlates with much worse reviews (see C3).

### 7) Recommended action
Focus ops on reducing the late tail and regional hotspots rather than further extending already-padded ETAs nationally.

### 8) Limitations
- “Late” is vs marketplace estimate, not vs customer expectation or carrier SLA contract.  
- Excludes non-delivered statuses (canceled, shipped, etc.).

---

## C2. Which regions experience delivery delays?

### 1) Required data
Late flag + `customer_state`; minimum volume filter (≥ 200 delivered orders) for ranking.

### 2) Metric
Late % and average delivery days by state.

### 3) SQL calculation
Aggregate late flag by `customer_state` with a volume threshold.

### 4) Result — highest late % (≥ 200 orders)

| State | Orders | Late % | Avg delivery days | Avg review |
|---|---:|---:|---:|---:|
| AL | 397 | **23.9%** | 24.5 | 3.85 |
| MA | 717 | **19.7%** | 21.6 | 3.83 |
| PI | 476 | **16.0%** | 19.5 | 3.99 |
| CE | 1,279 | **15.3%** | 21.3 | 3.94 |
| SE | 335 | **15.2%** | 21.5 | 3.91 |
| BA | 3,256 | **14.0%** | 19.3 | 3.93 |
| **RJ** | 12,350 | **13.5%** | 15.3 | 3.97 |

Note: **RJ** combines material volume with elevated lateness — high business impact.

SP (largest volume) is comparatively better on average delivery days (~volume leader); still requires monitoring because absolute late counts scale with volume.

### 5) Trends
Northeast states show higher late rates and longer delivery times; RJ is a Southeast outlier by volume × lateness.

### 6) Commercial implications
Geographic expansion without logistics redesign risks CX damage. RJ lateness affects a large revenue share (13.3% of merchandise).

### 7) Recommended action
Carrier/SLA review for AL/MA/CE/BA and a dedicated RJ reliability workstream.

### 8) Limitations
- State-level averages hide city/carrier variance.  
- Seller location and shipping distance not fully modelled here (phase 2 with sellers/geolocation).

---

## C3. Is delivery performance associated with review scores?

### 1) Required data
Late flag; order-level average `review_score`.

### 2) Metric
Mean review score for late vs on-time; Pearson correlation between late (0/1) and review score.

### 3) Calculation
Group means + correlation on delivered orders with reviews.

### 4) Result

| Group | Average review score |
|---|---:|
| On-time (or early) | **4.29** |
| Late | **2.57** |
| Correlation (late vs score) | **−0.37** |

### 5) Trends
Late deliveries coincide with sharply lower scores.

### 6) Commercial implications
Delivery punctuality is a leading **associated** driver of measured satisfaction. Reducing lateness is a high-leverage CX lever **if** further analysis confirms the relationship holds after controlling for category, price, and region.

### 7) Recommended action
Treat late reduction as a CX OKR; run controlled analysis (or A/B operational changes) before claiming causation in external reporting.

### 8) Limitations
**Correlation ≠ causation.** Late orders may also involve damaged goods, wrong items, difficult categories, or longer-distance hard-to-serve areas that independently affect scores.

---

# D. Product questions

## D1. Which categories have the highest sales?

Covered in **A1**. Same evidence: health_beauty, watches_gifts, bed_bath_table, sports_leisure, computers_accessories.

---

## D2. Which categories have low demand?

### 1–3) Data / metric / SQL
Merchandise revenue ranking ascending.

### 4) Result — lowest merchandise revenue categories

| Category | Merchandise revenue (BRL) |
|---|---:|
| security_and_services | 283 |
| fashion_childrens_clothes | 520 |
| cds_dvds_musicals | 730 |
| home_comfort_2 | 760 |
| flowers | 1,110 |
| pc_gamer | 1,307 |
| diapers_and_hygiene | 1,501 |
| arts_and_craftmanship | 1,814 |
| la_cuisine | 2,055 |
| fashion_sport | 2,095 |

### 5) Trends
Long tail of niche/low-volume categories contributes negligible GMV.

### 6) Commercial implications
Low demand ≠ automatic delist: some niches may be strategic or high margin. But catalogue complexity and freight burden should be reviewed.

### 7) Recommended action
Assortment rationalisation review for bottom-decile categories combining low revenue + high freight ratio (below).

### 8) Limitations
Low totals may reflect few listed SKUs, not weak sell-through rates (no impression/availability data).

---

## D3. How do freight charges vary by category?

### 1) Required data
`freight_value`, `price` by category.

### 2) Metric
Freight-to-merchandise ratio; average freight per item.

### 3) SQL pattern

```sql
SELECT category,
       SUM(freight_value) / NULLIF(SUM(price), 0) AS freight_to_price_ratio,
       AVG(freight_value) AS avg_freight_per_item
FROM ...
GROUP BY category;
```

### 4) Result — highest freight-to-price ratios

| Category | Freight / merchandise | Avg freight / item (BRL) |
|---|---:|---:|
| home_comfort_2 | 0.54 | 13.68 |
| flowers | 0.44 | 14.81 |
| furniture_mattress_and_upholstery | 0.37 | 42.74 |
| christmas_supplies | 0.37 | 21.27 |
| diapers_and_hygiene | 0.36 | 14.74 |
| cds_dvds_musicals | 0.31 | 16.07 |
| signaling_and_security | 0.30 | 32.88 |
| electronics | 0.30 | 16.74 |

Several **low-demand** categories also appear **freight-heavy**.

### 5) Trends
Bulky/home and some niche categories show freight that is a large fraction of merchandise value.

### 6) Commercial implications
High freight ratio increases customer price perception risk and may pressure seller economics even when GMV looks acceptable. Still **not** a profit measure without carrier cost.

### 7) Recommended action
Review shipping pricing rules and packaging for high-ratio categories; consider minimum order thresholds or freight subsidies policy with clear P&L ownership.

### 8) Limitations
Freight charged ≠ freight cost. Ratio can be high because price is low, not only because shipping is expensive.

---

## Cross-cutting observation: delivery vs reviews

The largest operational insight spanning CX and growth: **late deliveries average 2.57★ vs 4.29★ on-time**, with late rate 8.11% overall and much higher in several states. This is the strongest evidence-backed lever in the current data for protecting customer perception — while respecting that causality is not proven.

---

## Analysis artefacts

| Artefact | Role |
|---|---|
| `scripts/ba_analysis.py` | Reproducible KPI computation |
| `docs/_analysis_cache.json` | Machine-readable result cache used for this document |
| `docs/kpi_definitions.md` | Formal metric dictionary |
| `docs/recommendations.md` | Management actions |
