-- Export grain-safe Tableau extracts from the analytics schema.
-- Scope: DELIVERED orders only (order_status = 'delivered'), purchase dates 2016-09-15 .. 2018-08-29.
-- Each file is a separate Tableau data source; they are never joined in Tableau, so no fan-out.
-- Run from the project root:  psql -v ON_ERROR_STOP=1 -f tableau/export_tableau_data.sql
-- (connection via standard PGHOST/PGPORT/PGDATABASE/PGUSER variables)

-- 1) orders.csv : one row per delivered order
COPY (
  with cust as (
    select dc.customer_unique_id, count(*) as delivered_orders
    from analytics.fact_orders f join analytics.dim_customers dc using (customer_key)
    where f.is_delivered group by 1),
  srank as (
    select coalesce(g.state, dc.state) as state,
           rank() over (order by sum(f.merchandise_sales) desc) as state_sales_rank
    from analytics.fact_orders f
    join analytics.dim_customers dc on dc.customer_key = f.customer_key
    left join analytics.dim_geography g on g.geography_key = f.customer_geography_key
    where f.is_delivered group by 1),
  lrank as (
    -- worst late-delivery states, only states with >= 300 delivered orders that have both dates
    select coalesce(g.state, dc.state) as state,
           rank() over (order by avg(f.is_late_delivery::int) desc) as state_late_rank
    from analytics.fact_orders f
    join analytics.dim_customers dc on dc.customer_key = f.customer_key
    left join analytics.dim_geography g on g.geography_key = f.customer_geography_key
    where f.is_delivered and f.is_late_delivery is not null
    group by 1 having count(*) >= 300)
  select f.order_id,
         pd.full_date                                   as purchase_date,
         date_trunc('month', pd.full_date)::date        as purchase_month,
         coalesce(g.state, dc.state)                    as customer_state,
         coalesce(g.region, s.region)                   as customer_region,
         coalesce(st.state_name, coalesce(g.state, dc.state)) || ' (' || coalesce(g.state, dc.state) || ')' as state_label,
         dc.customer_unique_id,
         case when cust.delivered_orders > 1 then 1 else 0 end as is_repeat_customer,
         f.merchandise_sales, f.freight_charges, f.order_value, f.item_count,
         f.delivery_days,
         case when f.is_late_delivery then 1 when f.is_late_delivery = false then 0 end as is_late,
         (dl.full_date - est.full_date)                 as days_vs_estimate,
         case when f.is_late_delivery is null then 'Unknown'
              when f.is_late_delivery and dl.full_date - est.full_date <= 7  then 'Late by up to 7 days'
              when f.is_late_delivery and dl.full_date - est.full_date <= 14 then 'Late by 8-14 days'
              when f.is_late_delivery                                        then 'Late by 15+ days'
              when dl.full_date - est.full_date <= -14 then '14+ days early'
              when dl.full_date - est.full_date <= -7  then '7-13 days early'
              else 'On time to 6 days early' end         as delivery_timing,
         case when f.is_late_delivery is null then 7
              when f.is_late_delivery and dl.full_date - est.full_date <= 7  then 4
              when f.is_late_delivery and dl.full_date - est.full_date <= 14 then 5
              when f.is_late_delivery                                        then 6
              when dl.full_date - est.full_date <= -14 then 1
              when dl.full_date - est.full_date <= -7  then 2
              else 3 end                                 as delivery_timing_order,
         f.review_score,
         sr.state_sales_rank,
         lr.state_late_rank
  from analytics.fact_orders f
  join analytics.dim_date pd on pd.date_key = f.purchase_date_key
  left join analytics.dim_date dl  on dl.date_key  = f.delivered_customer_date_key
  left join analytics.dim_date est on est.date_key = f.estimated_delivery_date_key
  join analytics.dim_customers dc on dc.customer_key = f.customer_key
  left join analytics.dim_geography g on g.geography_key = f.customer_geography_key
  left join analytics.seed_brazilian_states s on s.state_code = dc.state
  join cust on cust.customer_unique_id = dc.customer_unique_id
  join srank sr on sr.state = coalesce(g.state, dc.state)
  left join lrank lr on lr.state = coalesce(g.state, dc.state)
  left join analytics.seed_brazilian_states st on st.state_code = coalesce(g.state, dc.state)
  where f.is_delivered
  order by pd.full_date, f.order_id
) TO STDOUT WITH (format csv, header true) \g tableau/data/orders.csv

-- 2) order_items.csv : one row per order line of a delivered order
COPY (
  with crank as (
    select coalesce(initcap(nullif(replace(p.product_category_name_english, '_', ' '), '')), 'Uncategorised') as category,
           rank() over (order by sum(i.price) desc) as category_sales_rank
    from analytics.fact_order_items i
    join analytics.fact_orders f on f.order_key = i.order_key and f.is_delivered
    left join analytics.dim_products p on p.product_key = i.product_key
    group by 1)
  select i.order_id, date_trunc('month', pd.full_date)::date as purchase_month,
         coalesce(initcap(nullif(replace(p.product_category_name_english, '_', ' '), '')), 'Uncategorised') as category,
         sl.state as seller_state, i.price, i.freight_value,
         cr.category_sales_rank
  from analytics.fact_order_items i
  join analytics.fact_orders f on f.order_key = i.order_key and f.is_delivered
  join analytics.dim_date pd on pd.date_key = i.purchase_date_key
  left join analytics.dim_products p on p.product_key = i.product_key
  left join analytics.dim_sellers sl on sl.seller_key = i.seller_key
  join crank cr on cr.category = coalesce(initcap(nullif(replace(p.product_category_name_english, '_', ' '), '')), 'Uncategorised')
  order by 1, i.order_item_id
) TO STDOUT WITH (format csv, header true) \g tableau/data/order_items.csv

-- 3) payments.csv : one row per payment record of a delivered order
COPY (
  select pm.order_id, date_trunc('month', pd.full_date)::date as purchase_month,
         replace(pm.payment_type, '_', ' ') as payment_type, pm.payment_installments, pm.payment_value
  from analytics.fact_payments pm
  join analytics.fact_orders f on f.order_key = pm.order_key and f.is_delivered
  join analytics.dim_date pd on pd.date_key = pm.purchase_date_key
  order by 1, pm.payment_sequential
) TO STDOUT WITH (format csv, header true) \g tableau/data/payments.csv

-- 4) order_categories.csv : one row per delivered order x product category (added 2026-11-18)
--    Lets category late rate / review be computed per ORDER (not per item line), so an order with
--    3 items in one category is counted once. category_sales sums to total merchandise sales.
COPY (
  with crank as (
    select coalesce(initcap(nullif(replace(p.product_category_name_english, '_', ' '), '')), 'Uncategorised') as category,
           rank() over (order by sum(i.price) desc) as category_sales_rank
    from analytics.fact_order_items i
    join analytics.fact_orders f on f.order_key = i.order_key and f.is_delivered
    left join analytics.dim_products p on p.product_key = i.product_key
    group by 1),
  oc as (
    select i.order_key, i.order_id,
           coalesce(initcap(nullif(replace(p.product_category_name_english, '_', ' '), '')), 'Uncategorised') as category,
           sum(i.price) as category_sales, sum(i.freight_value) as category_freight, count(*) as item_lines
    from analytics.fact_order_items i
    join analytics.fact_orders f on f.order_key = i.order_key and f.is_delivered
    left join analytics.dim_products p on p.product_key = i.product_key
    group by 1, 2, 3)
  select oc.order_id, date_trunc('month', pd.full_date)::date as purchase_month,
         oc.category, oc.category_sales, oc.category_freight, oc.item_lines,
         case when f.is_late_delivery then 1 when f.is_late_delivery = false then 0 end as is_late,
         f.review_score, f.delivery_days, cr.category_sales_rank
  from oc
  join analytics.fact_orders f on f.order_key = oc.order_key
  join analytics.dim_date pd on pd.date_key = f.purchase_date_key
  join crank cr on cr.category = oc.category
  order by 1, 3
) TO STDOUT WITH (format csv, header true) \g tableau/data/order_categories.csv

-- ---------------------------------------------------------------------------------------------
-- Fulfilment extracts (added 2026-11-18). The carrier hand-off date is only in staging.stg_orders
-- (order_delivered_carrier_date); it is joined on order_id. Profile of the 96,478 delivered orders:
--   carrier date null 2 · customer date null 8 · carrier before purchase 165 · carrier after
--   customer delivery 23  ->  timing_valid = 1 for the 96,281 orders with a consistent sequence
--   purchase <= carrier hand-off <= customer delivery. Dispatch is measured from PURCHASE, not
--   approval (1,350 orders have a hand-off before approval, so approval is not a reliable start).
--   dispatch_days + transit_days = delivery_days for every valid order.
-- missed_ship_limit = carrier hand-off later than the seller's shipping_limit_date (latest limit
-- across that seller's items in the order; for the order-level flag, the latest across all items).
-- ---------------------------------------------------------------------------------------------

-- 5) order_fulfilment.csv : one row per delivered order
COPY (
  with lim as (select order_key, max(shipping_limit_date) as ship_limit, count(distinct seller_key) as seller_count
               from analytics.fact_order_items group by 1)
  select f.order_id,
         date_trunc('month', s.order_purchase_timestamp)::date as purchase_month,
         coalesce(g.state, dc.state)  as customer_state,
         coalesce(g.region, st.region) as customer_region,
         case when f.is_late_delivery then 1 when f.is_late_delivery = false then 0 end as is_late,
         f.review_score, f.delivery_days,
         case when v.ok then round((extract(epoch from s.order_delivered_carrier_date - s.order_purchase_timestamp) / 86400)::numeric, 2) end as dispatch_days,
         case when v.ok then round((extract(epoch from s.order_delivered_customer_date - s.order_delivered_carrier_date) / 86400)::numeric, 2) end as transit_days,
         case when v.ok then 1 else 0 end as timing_valid,
         case when s.order_delivered_carrier_date is null then null
              when s.order_delivered_carrier_date > lim.ship_limit then 1 else 0 end as missed_ship_limit,
         lim.seller_count
  from analytics.fact_orders f
  join staging.stg_orders s on s.order_id = f.order_id
  join lim on lim.order_key = f.order_key
  join analytics.dim_customers dc on dc.customer_key = f.customer_key
  left join analytics.dim_geography g on g.geography_key = f.customer_geography_key
  left join analytics.seed_brazilian_states st on st.state_code = dc.state
  cross join lateral (select coalesce(s.order_delivered_carrier_date >= s.order_purchase_timestamp
                                      and s.order_delivered_carrier_date <= s.order_delivered_customer_date, false) as ok) v
  where f.is_delivered
  order by 1
) TO STDOUT WITH (format csv, header true) \g tableau/data/order_fulfilment.csv

-- 6) order_sellers.csv : one row per delivered order x seller (+ seller_excess_rank, see below). An order with 2+ sellers (1,275 orders,
--    1.3%) appears once per seller; its order-level outcome (late flag, review, hand-off date) is
--    attributed to each seller in it, because Olist records one hand-off date per order.
COPY (
  with os as (
    select i.order_key, i.seller_key, sum(i.price) as seller_sales, count(*) as item_lines,
           max(i.shipping_limit_date) as ship_limit
    from analytics.fact_order_items i group by 1, 2),
  sc as (select order_key, count(*) as seller_count from os group by 1),
  base as (
  select f.order_id,
         date_trunc('month', s.order_purchase_timestamp)::date as purchase_month,
         sl.seller_id, left(sl.seller_id, 8) as seller_short,
         coalesce(sl.state, '?') as seller_state,
         coalesce(g.state, dc.state) as customer_state,
         coalesce(sl.state, '?') || ' → ' || coalesce(g.state, dc.state) as route,
         sc.seller_count, os.seller_sales, os.item_lines,
         case when f.is_late_delivery then 1 when f.is_late_delivery = false then 0 end as is_late,
         f.review_score,
         case when v.ok then round((extract(epoch from s.order_delivered_carrier_date - s.order_purchase_timestamp) / 86400)::numeric, 2) end as dispatch_days,
         case when v.ok then round((extract(epoch from s.order_delivered_customer_date - s.order_delivered_carrier_date) / 86400)::numeric, 2) end as transit_days,
         case when v.ok then 1 else 0 end as timing_valid,
         case when s.order_delivered_carrier_date is null then null
              when s.order_delivered_carrier_date > os.ship_limit then 1 else 0 end as missed_ship_limit
  from os
  join sc on sc.order_key = os.order_key
  join analytics.fact_orders f on f.order_key = os.order_key and f.is_delivered
  join staging.stg_orders s on s.order_id = f.order_id
  join analytics.dim_sellers sl on sl.seller_key = os.seller_key
  join analytics.dim_customers dc on dc.customer_key = f.customer_key
  left join analytics.dim_geography g on g.geography_key = f.customer_geography_key
  cross join lateral (select coalesce(s.order_delivered_carrier_date >= s.order_purchase_timestamp
                                      and s.order_delivered_carrier_date <= s.order_delivered_customer_date, false) as ok) v),
  -- seller exception rank: excess late orders vs the order x seller network late rate, sellers with 100+ rows
  net as (select sum(is_late)::numeric / count(is_late) as rate from base),
  sel as (select seller_id, count(is_late) as n, sum(is_late) as late from base group by 1),
  rk as (select seller_id, rank() over (order by late - n * (select rate from net) desc) as seller_excess_rank
         from sel where n >= 100)
  select b.*, rk.seller_excess_rank
  from base b left join rk using (seller_id)
  order by 1, 3
) TO STDOUT WITH (format csv, header true) \g tableau/data/order_sellers.csv

-- 7) customers.csv : one row per unique customer (customer_unique_id) with 1+ delivered order.
--    first order = earliest purchase timestamp (tie-break: order_id).
COPY (
  with o as (
    select dc.customer_unique_id, f.order_id, s.order_purchase_timestamp, f.is_late_delivery,
           coalesce(g.state, dc.state) as customer_state,
           row_number() over (partition by dc.customer_unique_id order by s.order_purchase_timestamp, f.order_id) as rn,
           count(*) over (partition by dc.customer_unique_id) as delivered_orders
    from analytics.fact_orders f
    join staging.stg_orders s on s.order_id = f.order_id
    join analytics.dim_customers dc on dc.customer_key = f.customer_key
    left join analytics.dim_geography g on g.geography_key = f.customer_geography_key
    where f.is_delivered)
  select customer_unique_id,
         order_purchase_timestamp::date as first_purchase_date,
         date_trunc('month', order_purchase_timestamp)::date as first_purchase_month,
         customer_state,
         case when is_late_delivery then 1 when is_late_delivery = false then 0 end as first_order_late,
         delivered_orders,
         case when delivered_orders > 1 then 1 else 0 end as is_repeat
  from o where rn = 1
  order by 1
) TO STDOUT WITH (format csv, header true) \g tableau/data/customers.csv

-- 8) card_orders.csv : one row per delivered order paid at least partly by credit card (added 2026-11-18).
--    Grain: order. card_installments = MAX(payment_installments) over the order's credit-card payment rows
--    (282 orders have 2+ card rows). Profile of delivered-order payments: 74,304 orders with a card row;
--    2 have 0 instalments (invalid) and are EXCLUDED; 2,182 card orders also use another payment type
--    (order_value is the whole order). Non-card types always have 1 instalment except 2 boleto rows (10),
--    which are out of scope. 11+ band keeps the 12-24 instalment tail (rare but valid card terms).
COPY (
  with cc as (
    select pm.order_key, max(pm.payment_installments) as card_installments, count(*) as card_rows
    from analytics.fact_payments pm where pm.payment_type = 'credit_card' group by 1),
  oth as (select order_key, max(case when payment_type <> 'credit_card' then 1 else 0 end) as uses_other_type
          from analytics.fact_payments group by 1)
  select f.order_id, date_trunc('month', pd.full_date)::date as purchase_month,
         cc.card_installments,
         case when cc.card_installments = 1 then '1'
              when cc.card_installments <= 3 then '2-3'
              when cc.card_installments <= 6 then '4-6'
              when cc.card_installments <= 10 then '7-10'
              else '11+' end as installment_band,
         case when cc.card_installments = 1 then 1 when cc.card_installments <= 3 then 2
              when cc.card_installments <= 6 then 3 when cc.card_installments <= 10 then 4 else 5 end as band_order,
         cc.card_rows, oth.uses_other_type, f.order_value, f.merchandise_sales,
         case when f.is_late_delivery then 1 when f.is_late_delivery = false then 0 end as is_late,
         f.review_score
  from cc
  join analytics.fact_orders f on f.order_key = cc.order_key and f.is_delivered
  join oth on oth.order_key = cc.order_key
  join analytics.dim_date pd on pd.date_key = f.purchase_date_key
  where cc.card_installments >= 1
  order by 1
) TO STDOUT WITH (format csv, header true) \g tableau/data/card_orders.csv
