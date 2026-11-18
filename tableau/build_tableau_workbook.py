"""Generate the Olist Tableau workbook (.twb and packaged .twbx) from code.

The workbook is written as XML instead of being built by clicking in Tableau, so it is
reproducible and reviewable. It reads the grain-safe CSV extracts in tableau/data/
produced by tableau/export_tableau_data.sql. Standard library only.

Four dashboards, dark theme (navy canvas, slate cards, white type; cyan = growth / on
time, pink = risk, amber = watch), story = status -> drivers -> action:
  1. Executive Overview   - KPI cards with sparklines and Jan-Aug YoY deltas, trends, ranked lists
  2. Delivery Diagnostics - where/when lateness concentrates: region x month heatmap,
                            state rate-vs-volume scatter, category late rate and review
  3. Seller & Fulfilment  - lead time split into seller dispatch vs carrier transit, shipping-limit misses,
                            late rate by route and seller state, seller exception list
  4. Action Queue         - state exception table (excess late orders vs network rate,
                            priority tiers) with a filter action to a monthly trend, and a playbook
Navigation buttons on each sidebar switch dashboards (sheet tabs also work).

Usage (from the project root):
    python3 tableau/build_tableau_workbook.py            # writes .twb and .twbx
    python3 tableau/build_tableau_workbook.py --qa DIR   # also writes QA copies (one per
                                                          # dashboard opened first) to DIR
"""
from __future__ import annotations

import csv
import sys
import uuid
import xml.dom.minidom
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
NAME = "Olist Executive Dashboard"
CSVS = ("orders.csv", "order_items.csv", "order_categories.csv", "order_fulfilment.csv", "order_sellers.csv",
        "customers.csv", "card_orders.csv", "payments.csv")

# ---------------------------------------------------------------- theme (lowercase hex: Tableau colour type)
BG = "#0e1621"        # dashboard canvas
SIDEBAR = "#0a1119"   # sidebar
CARD = "#18222f"      # card panels
TEXT = "#f2f5f8"      # primary type
LABEL = "#c3ccd6"     # header labels
MUTED = "#8a97a6"     # captions
BAR = "#c9d1da"       # neutral ranked bars
CYAN = "#3fc1e8"      # growth / on time / at or below network
GOOD = "#4cd6a4"      # favourable change
PINK = "#e8467c"      # risk / late / priority
AMBER = "#f2b84b"     # watch
TT_T, TT_L = "#16202b", "#5b6573"   # tooltip text (Tableau tooltips have a light background)
BRL = 'c"R$"#,##0;-"R$"#,##0'
BRL_M = 'c"R$"#,##0.00"M"'

TREND_MIN, TREND_MAX = "#2017-01-01#", "#2018-08-01#"
Y18 = "(YEAR([purchase_month]) = 2018 AND MONTH([purchase_month]) <= 8)"
Y17 = "(YEAR([purchase_month]) = 2017 AND MONTH([purchase_month]) <= 8)"

DASH_OVERVIEW, DASH_DIAG, DASH_ACTION = "Executive Overview", "Delivery Diagnostics", "Action Queue"
DASH_SELLER = "Seller & Fulfilment"
DASHBOARDS = (DASH_OVERVIEW, DASH_DIAG, DASH_SELLER, DASH_ACTION)
W, H = 1440, 840   # fits a 1920x1080 Tableau Desktop window without scrolling


def a(**kw) -> str:
    """Render XML attributes (keys with '_' become '-'), sorted like Tableau writes them."""
    return " ".join(f"{k.replace('_', '-')}={quoteattr(str(v))}" for k, v in sorted(kw.items()) if v is not None)


def sid(seed: str) -> str:
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "olist-tableau/" + seed)).upper() + "}"


def run(text, color=TEXT, size=9, bold=False) -> str:
    return f"<run {a(bold='true' if bold else None, fontcolor=color, fontsize=size)}>{escape(text)}</run>"


NL = "<run>Æ&#10;</run>"


def field(ref: str) -> str:
    return "<" + ref + ">"


# ---------------------------------------------------------------- data-driven axis headroom
def _read(name):
    with open(DATA_DIR / name, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def headroom():
    """Largest bar in each ranked list, so bars stop at ~half width and end labels never overlap."""
    cat, st_sales, st_late = defaultdict(float), defaultdict(float), defaultdict(lambda: [0, 0])
    for r in _read("order_items.csv"):
        cat[r["category"]] += float(r["price"])
    for r in _read("orders.csv"):
        st_sales[r["customer_state"]] += float(r["merchandise_sales"])
        if r["is_late"] != "":
            st_late[r["customer_state"]][0] += int(r["is_late"])
            st_late[r["customer_state"]][1] += 1
    big = {k: v for k, v in st_late.items() if v[1] >= 300}
    late = max(v[0] / v[1] for v in big.values())
    net = sum(v[0] for v in st_late.values()) / sum(v[1] for v in st_late.values())
    excess = max(abs(v[0] - v[1] * net) for v in big.values())
    sl = defaultdict(lambda: [0, 0])
    for r in _read("order_sellers.csv"):
        if r["is_late"] != "":
            sl[r["seller_id"]][0] += int(r["is_late"])
            sl[r["seller_id"]][1] += 1
    snet = sum(v[0] for v in sl.values()) / sum(v[1] for v in sl.values())
    seller_excess = max(v[0] - v[1] * snet for v in sl.values() if v[1] >= 100)
    return {"cat": max(cat.values()), "state": max(st_sales.values()), "late": late, "excess": excess,
            "seller_excess": seller_excess}


# ---------------------------------------------------------------- data sources
class DS:
    def __init__(self, key, caption, filename, cols, calcs=()):
        self.name = f"federated.olist{key}"
        self.conn = f"textscan.olist{key}"
        self.caption, self.filename = caption, filename
        self.cols = cols  # (name, datatype, role, type, caption, default_format)
        self.calcs = {c[0]: c for c in calcs}  # (name, caption, datatype, role, type, formula, fmt)

    def ref(self, inst: str) -> str:
        return f"[{self.name}].[{inst}]"

    def col_xml(self, name: str) -> str:
        if name in self.calcs:
            n, cap, dt, role, typ, formula, fmt = self.calcs[name]
            return (f"<column {a(caption=cap, datatype=dt, default_format=fmt, name=f'[{n}]', role=role, type=typ)}>"
                    f"<calculation {a(**{'class': 'tableau', 'formula': formula})} /></column>")
        n, dt, role, typ, cap, fmt = next(c for c in self.cols if c[0] == name)
        return f"<column {a(caption=cap, datatype=dt, default_format=fmt, name=f'[{n}]', role=role, type=typ)} />"

    def all_names(self):
        return [c[0] for c in self.cols] + list(self.calcs)

    def xml(self, directory: str) -> str:
        rel_cols = "".join(f"<column {a(datatype=c[1], name=c[0], ordinal=i)} />" for i, c in enumerate(self.cols))
        relation = (f"<relation {a(connection=self.conn, name=self.filename, table='[' + self.filename.replace('.', '#') + ']', type='table')}>"
                    f"<columns {a(character_set='UTF-8', header='yes', locale='en_US', separator=',')}>{rel_cols}</columns></relation>")
        # canonical 2026.3 object model (as Tableau re-saves it), so no legacy migration runs on open
        graph = ("<object-graph><objects><object caption=\"Migrated Data\" id=\"Migrated Data\">"
                 f"<properties context=\"\">{relation}</properties></object></objects></object-graph>")
        cols = "".join(self.col_xml(n) for n in self.all_names())
        return (
            f"<datasource {a(caption=self.caption, inline='true', name=self.name, version='18.1')}>"
            f"<connection class=\"federated\"><named-connections>"
            f"<named-connection {a(caption=self.filename, name=self.conn)}>"
            f"<connection {a(**{'class': 'textscan', 'directory': directory, 'filename': self.filename, 'password': '', 'server': ''})} />"
            f"</named-connection></named-connections>"
            f"{relation}</connection>"
            f"<aliases enabled=\"yes\" />{cols}"
            f"<layout {a(dim_ordering='alphabetic', measure_ordering='alphabetic', show_structure='true')} />"
            f"{graph}</datasource>"
        )


D, M, Q, N, O = "dimension", "measure", "quantitative", "nominal", "ordinal"
LATE_PCT = "100 * SUM([is_late]) / COUNT([is_late])"


def money_m(expr):
    return f'"R$" + STR(ROUND({expr} / 1000000, 2)) + "M"'


def arrow(new, old):
    return f'IIF({new} >= {old}, "▲ ", "▼ ")'



ORDERS = DS("orders", "Orders (delivered)", "orders.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_date", "date", D, O, "Purchase Date", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("customer_state", "string", D, N, "State Code", None),
    ("customer_region", "string", D, N, "Region", None),
    ("state_label", "string", D, N, "State", None),
    ("customer_unique_id", "string", D, N, "Customer Unique ID", None),
    ("is_repeat_customer", "integer", M, Q, "Is Repeat Customer", None),
    ("merchandise_sales", "real", M, Q, "Merchandise Sales", BRL),
    ("freight_charges", "real", M, Q, "Freight Charges", BRL),
    ("order_value", "real", M, Q, "Order Value", BRL),
    ("item_count", "integer", M, Q, "Item Count", None),
    ("delivery_days", "real", M, Q, "Delivery Days", None),
    ("is_late", "integer", M, Q, "Is Late", None),
    ("days_vs_estimate", "integer", M, Q, "Days vs Estimate", None),
    ("delivery_timing", "string", D, N, "Delivery Timing", None),
    ("delivery_timing_order", "integer", D, O, "Delivery Timing Order", None),
    ("review_score", "integer", M, Q, "Review Score", None),
    ("state_sales_rank", "integer", D, O, "#", "*00"),
    ("state_late_rank", "integer", D, O, "#", "*00"),
], calcs=[
    # KPI values (all delivered orders)
    ("Calc_KPI_Sales", "KPI Merchandise Sales", "string", M, N, money_m("SUM([merchandise_sales])"), None),
    ("Calc_KPI_Orders", "KPI Orders", "string", M, N, 'STR(ROUND(COUNTD([order_id]) / 1000, 1)) + "K"', None),
    ("Calc_KPI_Late", "KPI Late Delivery Rate", "string", M, N, f'STR(ROUND({LATE_PCT}, 1)) + "%"', None),
    ("Calc_KPI_Review", "KPI Avg Review", "string", M, N, 'STR(ROUND(AVG([review_score]), 2)) + " / 5"', None),
    ("Calc_KPI_AOV", "KPI Avg Order Value", "string", M, N,
     '"R$" + STR(ROUND(SUM([order_value]) / COUNTD([order_id]), 2))', None),
    ("Calc_KPI_Repeat", "KPI Repeat Customers", "string", M, N,
     'STR(ROUND(100 * COUNTD(IF [is_repeat_customer] = 1 THEN [customer_unique_id] END)'
     ' / COUNTD([customer_unique_id]), 1)) + "%"', None),
    ("Calc_KPI_Days", "KPI Avg Delivery Days", "string", M, N, 'STR(ROUND(AVG([delivery_days]), 1)) + " days"', None),
    ("Calc_KPI_Freight", "KPI Freight Share", "string", M, N,
     'STR(ROUND(100 * SUM([freight_charges]) / SUM([order_value]), 1)) + "%"', None),
    # Jan-Aug 2018 vs Jan-Aug 2017 comparisons
    ("Calc_D_Sales", "Delta Sales", "string", M, N,
     arrow(f"SUM(IF {Y18} THEN [merchandise_sales] END)", f"SUM(IF {Y17} THEN [merchandise_sales] END)")
     + f" + STR(INT(ROUND(100 * ABS(SUM(IF {Y18} THEN [merchandise_sales] END) / SUM(IF {Y17} THEN [merchandise_sales] END) - 1), 0)))"
     + ' + "% Jan-Aug 2018 vs 2017"', None),
    ("Calc_D_Orders", "Delta Orders", "string", M, N,
     arrow(f"COUNTD(IF {Y18} THEN [order_id] END)", f"COUNTD(IF {Y17} THEN [order_id] END)")
     + f" + STR(INT(ROUND(100 * ABS(COUNTD(IF {Y18} THEN [order_id] END) / COUNTD(IF {Y17} THEN [order_id] END) - 1), 0)))"
     + ' + "% Jan-Aug 2018 vs 2017"', None),
    ("Calc_D_Late", "Delta Late", "string", M, N,
     arrow(f"SUM(IF {Y18} THEN [is_late] END) / COUNT(IF {Y18} THEN [is_late] END)",
           f"SUM(IF {Y17} THEN [is_late] END) / COUNT(IF {Y17} THEN [is_late] END)")
     + f' + STR(ROUND(100 * SUM(IF {Y17} THEN [is_late] END) / COUNT(IF {Y17} THEN [is_late] END), 1))'
     + f' + "% to " + STR(ROUND(100 * SUM(IF {Y18} THEN [is_late] END) / COUNT(IF {Y18} THEN [is_late] END), 1))'
     + ' + "% (Jan-Aug 17 to 18)"', None),
    ("Calc_D_Review", "Delta Review", "string", M, N,
     arrow(f"AVG(IF {Y18} THEN [review_score] END)", f"AVG(IF {Y17} THEN [review_score] END)")
     + f' + STR(ROUND(AVG(IF {Y17} THEN [review_score] END), 2)) + " to "'
     + f' + STR(ROUND(AVG(IF {Y18} THEN [review_score] END), 2)) + " (Jan-Aug 17 to 18)"', None),
    # chart measures (numeric, formatted) - also used in tooltips
    ("Calc_Sales", "Sales (R$M)", "real", M, Q, "SUM([merchandise_sales]) / 1000000", BRL_M),
    ("Calc_Orders", "Orders", "integer", M, Q, "COUNTD([order_id])", "n#,##0"),
    ("Calc_Late_Orders", "Late Orders", "integer", M, Q, "SUM([is_late])", "n#,##0"),
    ("Calc_Late_Rate", "Late Rate", "real", M, Q, "SUM([is_late]) / COUNT([is_late])", "p0.0%"),
    ("Calc_Avg_Review", "Avg Review", "real", M, Q, "AVG([review_score])", "n0.00"),
    ("Calc_Avg_Days", "Avg Delivery Days", "real", M, Q, "AVG([delivery_days])", "n0.0"),
    ("Calc_Network_Late", "Network Late Rate", "real", M, Q, "{FIXED : SUM([is_late]) / COUNT([is_late])}", "p0.0%"),
    ("Calc_Gap_pp", "Gap (pp)", "real", M, Q,
     "100 * ([Calc_Late_Rate] - MIN([Calc_Network_Late]))", "n+0.0;-0.0"),
    ("Calc_Excess_Late", "Excess Late Orders", "real", M, Q,
     "SUM([is_late]) - COUNT([is_late]) * MIN([Calc_Network_Late])", "n+#,##0;-#,##0"),
    ("Calc_Late_Sales", "Late-order Sales", "real", M, Q,
     "SUM(IF [is_late] = 1 THEN [merchandise_sales] END)", BRL),
    ("Calc_Tier", "Tier", "string", M, N,
     'IF [Calc_Gap_pp] >= 3 AND [Calc_Excess_Late] >= 50 THEN "Priority" '
     'ELSEIF [Calc_Gap_pp] >= 1 THEN "Watch" ELSE "Monitor" END', None),
    ("Calc_Tier_Code", "Priority Tier Code", "integer", M, Q,
     'IF [Calc_Tier] = "Priority" THEN 3 ELSEIF [Calc_Tier] = "Watch" THEN 2 ELSE 1 END', None),
    ("Calc_Late_Code", "Late Share (colour)", "real", M, Q, "AVG([is_late])", "p0%"),
    ("Calc_Action_Label", "Action Label", "string", M, N,
     'IIF([Calc_Excess_Late] >= 0, "+", "") + STR(INT(ROUND([Calc_Excess_Late], 0)))', None),
    ("Calc_Month_Label", "Month", "string", D, N,
     "LEFT(DATENAME('month', [purchase_month]), 3) + \" \" + RIGHT(STR(YEAR([purchase_month])), 2)", None),
    ("Calc_Month_Index", "Month Index", "integer", M, Q, "YEAR([purchase_month]) * 100 + MONTH([purchase_month])", None),
    ("Calc_Outcome", "Delivery Outcome", "string", D, N,
     'IF ISNULL([is_late]) THEN "Unknown" ELSEIF [is_late] = 1 THEN "Late" ELSE "On time or early" END', None),
    ("Calc_Review_Label", "Review Label", "string", M, N, 'STR(ROUND(AVG([review_score]), 2)) + " ★"', None),
    ("Calc_State_Sales_Label", "State Sales Label", "string", M, N,
     money_m("SUM([merchandise_sales])") + f' + " · " + STR(ROUND({LATE_PCT}, 1)) + "% late"', None),
    ("Calc_State_Late_Label", "State Late Label", "string", M, N,
     f'STR(ROUND({LATE_PCT}, 1)) + "% · " + IIF(COUNT([is_late]) >= 1000, '
     'STR(ROUND(COUNT([is_late]) / 1000, 1)) + "K", STR(COUNT([is_late]))) + " orders"', None),
])

ITEMS = DS("items", "Order items (delivered)", "order_items.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("category", "string", D, N, "Category", None),
    ("seller_state", "string", D, N, "Seller State", None),
    ("price", "real", M, Q, "Item Price", BRL),
    ("freight_value", "real", M, Q, "Item Freight", BRL),
    ("category_sales_rank", "integer", D, O, "#", "*00"),
], calcs=[
    ("Calc_Item_Sales", "Sales", "real", M, Q, "SUM([price])", BRL),
    ("Calc_Item_Share", "Share of Sales", "real", M, Q, "SUM([price]) / MIN({FIXED : SUM([price])})", "p0.0%"),
    ("Calc_Item_Orders", "Orders", "integer", M, Q, "COUNTD([order_id])", "n#,##0"),
    ("Calc_Cat_Label", "Category Label", "string", M, N,
     money_m("SUM([price])") + ' + " · " + STR(ROUND(100 * SUM([price]) / MIN({FIXED : SUM([price])}), 1)) + "%"', None),
])

CATS = DS("categories", "Order x category (delivered)", "order_categories.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("category", "string", D, N, "Category", None),
    ("category_sales", "real", M, Q, "Category Sales", BRL),
    ("category_freight", "real", M, Q, "Category Freight", BRL),
    ("item_lines", "integer", M, Q, "Item Lines", None),
    ("is_late", "integer", M, Q, "Is Late", None),
    ("review_score", "integer", M, Q, "Review Score", None),
    ("delivery_days", "real", M, Q, "Delivery Days", None),
    ("category_sales_rank", "integer", D, O, "#", "*00"),
], calcs=[
    ("CC_Orders", "Orders", "integer", M, Q, "COUNT([order_id])", "n#,##0"),
    ("CC_Late_Rate", "Late Rate", "real", M, Q, "SUM([is_late]) / COUNT([is_late])", "p0.0%"),
    ("CC_Avg_Review", "Avg Review", "real", M, Q, "AVG([review_score])", "n0.00"),
    ("CC_Avg_Days", "Avg Delivery Days", "real", M, Q, "AVG([delivery_days])", "n0.0"),
    ("CC_Sales", "Sales", "real", M, Q, "SUM([category_sales])", BRL),
    ("CC_Size", "Category Order Count", "integer", D, Q, "{FIXED [category] : COUNT([order_id])}", "n#,##0"),
    ("CC_Network", "Network Late Rate", "real", M, Q, "{FIXED : SUM([is_late]) / COUNT([is_late])}", "p0.0%"),
    ("CC_Vs", "Vs Network", "string", M, N,
     'IF [CC_Late_Rate] > MIN([CC_Network]) THEN "Above network" ELSE "At or below network" END', None),
    ("CC_Vs_Code", "Vs Network Code", "integer", M, Q, "IIF([CC_Late_Rate] > MIN([CC_Network]), 1, 0)", None),
    ("CC_Label", "Category Diag Label", "string", M, N,
     'STR(ROUND(100 * [CC_Late_Rate], 1)) + "% · " + STR(ROUND([CC_Avg_Review], 2)) + " ★"', None),
])

PAYMENTS = DS("payments", "Payments (delivered)", "payments.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("payment_type", "string", D, N, "Payment Type", None),
    ("payment_installments", "integer", M, Q, "Installments", None),
    ("payment_value", "real", M, Q, "Payment Value", BRL),
])

FUL = DS("fulfilment", "Order fulfilment (delivered)", "order_fulfilment.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("customer_state", "string", D, N, "Customer State", None),
    ("customer_region", "string", D, N, "Region", None),
    ("is_late", "integer", M, Q, "Is Late", None),
    ("review_score", "integer", M, Q, "Review Score", None),
    ("delivery_days", "real", M, Q, "Delivery Days", "n0.0"),
    ("dispatch_days", "real", M, Q, "Seller Dispatch Days", "n0.0"),
    ("transit_days", "real", M, Q, "Carrier Transit Days", "n0.0"),
    ("timing_valid", "integer", D, Q, "Timing Valid", None),
    ("missed_ship_limit", "integer", M, Q, "Missed Shipping Limit", None),
    ("seller_count", "integer", M, Q, "Sellers in Order", None),
], calcs=[
    ("F_Outcome", "Delivery Outcome", "string", D, N,
     'IF [is_late] = 1 THEN "Late orders" ELSE "On-time orders" END', None),
    ("F_Valid", "Timing Usable", "integer", D, Q,
     "IF [timing_valid] = 1 AND NOT ISNULL([is_late]) THEN 1 ELSE 0 END", None),
    ("F_Ship_Label", "Seller Shipping", "string", D, N,
     'IF [missed_ship_limit] = 1 THEN "Shipped after limit" ELSE "Shipped within limit" END', None),
    ("F_Ship_Valid", "Shipping Flag Usable", "integer", D, Q,
     "IF NOT ISNULL([missed_ship_limit]) AND NOT ISNULL([is_late]) THEN 1 ELSE 0 END", None),
    ("F_Late_Code", "Late Share (colour)", "real", M, Q, "AVG([is_late])", "p0%"),
    ("F_Miss_Code", "Missed Limit Share (colour)", "real", M, Q, "AVG([missed_ship_limit])", "p0%"),
    ("F_Orders", "Orders", "integer", M, Q, "COUNT([order_id])", "n#,##0"),
    ("F_Late_Rate", "Late Rate", "real", M, Q, "SUM([is_late]) / COUNT([is_late])", "p0.0%"),
    ("F_Dispatch", "Avg Seller Dispatch (days)", "real", M, Q, "AVG([dispatch_days])", "n0.0"),
    ("F_Transit", "Avg Carrier Transit (days)", "real", M, Q, "AVG([transit_days])", "n0.0"),
    ("F_Review", "Avg Review", "real", M, Q, "AVG([review_score])", "n0.00"),
    ("F_Days_Label_D", "Dispatch Label", "string", M, N,
     'STR(ROUND(AVG([dispatch_days]), 1)) + " days"', None),
    ("F_Days_Label_T", "Transit Label", "string", M, N,
     'STR(ROUND(AVG([transit_days]), 1)) + " days"', None),
    ("F_Ship_Lbl", "Shipping Label", "string", M, N,
     'STR(ROUND(100 * SUM([is_late]) / COUNT([is_late]), 1)) + "% late · " + '
     'STR(ROUND(COUNT([is_late]) / 1000, 1)) + "K orders"', None),
])

SEL = DS("sellers", "Order x seller (delivered)", "order_sellers.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("seller_id", "string", D, N, "Seller ID", None),
    ("seller_short", "string", D, N, "Seller", None),
    ("seller_state", "string", D, N, "State", None),
    ("customer_state", "string", D, N, "Customer State", None),
    ("route", "string", D, N, "Route", None),
    ("seller_count", "integer", M, Q, "Sellers in Order", None),
    ("seller_sales", "real", M, Q, "Seller Sales", BRL),
    ("item_lines", "integer", M, Q, "Item Lines", None),
    ("is_late", "integer", M, Q, "Is Late", None),
    ("review_score", "integer", M, Q, "Review Score", None),
    ("dispatch_days", "real", M, Q, "Seller Dispatch Days", "n0.0"),
    ("transit_days", "real", M, Q, "Carrier Transit Days", "n0.0"),
    ("timing_valid", "integer", D, Q, "Timing Valid", None),
    ("missed_ship_limit", "integer", M, Q, "Missed Shipping Limit", None),
    ("seller_excess_rank", "integer", D, Q, "Seller Excess Rank", None),
], calcs=[
    ("S_Orders", "Orders", "integer", M, Q, "COUNT([is_late])", "n#,##0"),
    ("S_Late_Rate", "Late Rate", "real", M, Q, "SUM([is_late]) / COUNT([is_late])", "p0.0%"),
    ("S_Network", "Network Late Rate", "real", M, Q, "{FIXED : SUM([is_late]) / COUNT([is_late])}", "p0.0%"),
    ("S_Excess", "Excess Late Orders", "real", M, Q,
     "SUM([is_late]) - COUNT([is_late]) * MIN([S_Network])", "n+#,##0;-#,##0"),
    ("S_Vs_Code", "Vs Network Code", "integer", M, Q, "IIF([S_Late_Rate] > MIN([S_Network]), 1, 0)", None),
    ("S_Missed", "Missed Limit", "real", M, Q, "AVG([missed_ship_limit])", "p0%"),
    ("S_Dispatch", "Dispatch (d)", "real", M, Q, "AVG([dispatch_days])", "n0.0"),
    ("S_Transit", "Transit (d)", "real", M, Q, "AVG([transit_days])", "n0.0"),
    ("S_Review", "Avg Review", "real", M, Q, "AVG([review_score])", "n0.00"),
    ("S_Sales", "Seller Sales", "real", M, Q, "SUM([seller_sales])", BRL),
    ("S_Route_Size", "Route Volume", "integer", D, Q, "{FIXED [route] : COUNT([is_late])}", "n#,##0"),
    ("S_State_Size", "Seller State Volume", "integer", D, Q, "{FIXED [seller_state] : COUNT([is_late])}", "n#,##0"),
    ("S_Rate_Label", "Rate Label", "string", M, N,
     'STR(ROUND(100 * SUM([is_late]) / COUNT([is_late]), 1)) + "% · " + IIF(COUNT([is_late]) >= 1000, '
     'STR(ROUND(COUNT([is_late]) / 1000, 1)) + "K", STR(COUNT([is_late])))', None),
    ("S_Excess_Label", "Excess Label", "string", M, N,
     'IIF([S_Excess] >= 0, "+", "") + STR(INT(ROUND([S_Excess], 0)))', None),
])

CUST = DS("customers", "Customers (delivered)", "customers.csv", [
    ("customer_unique_id", "string", D, N, "Customer", None),
    ("first_purchase_date", "date", D, O, "First Purchase Date", None),
    ("first_purchase_month", "date", D, O, "First Purchase Month", None),
    ("customer_state", "string", D, N, "Customer State", None),
    ("first_order_late", "integer", M, Q, "First Order Late", None),
    ("delivered_orders", "integer", M, Q, "Delivered Orders", None),
    ("is_repeat", "integer", M, Q, "Is Repeat", None),
], calcs=[
    ("CU_First", "First Order", "string", D, N,
     'IF [first_order_late] = 1 THEN "Late" ELSE "On time" END', None),
    ("CU_Valid", "Retention Cohort", "integer", D, Q,
     "IF NOT ISNULL([first_order_late]) AND [first_purchase_date] < #2018-03-01# THEN 1 ELSE 0 END", None),
    ("CU_Repeat", "Repeat Rate", "real", M, Q, "AVG([is_repeat])", "p0.00%"),
    ("CU_Customers", "Customers", "integer", M, Q, "COUNT([customer_unique_id])", "n#,##0"),
    ("CU_Repeaters", "Repeat Customers", "integer", M, Q, "SUM([is_repeat])", "n#,##0"),
    ("CU_Code", "First Late (colour)", "real", M, Q, "AVG([first_order_late])", "p0%"),
    ("CU_Label", "Retention Label", "string", M, N,
     'STR(ROUND(100 * AVG([is_repeat]), 2)) + "% · " + STR(ROUND(COUNT([customer_unique_id]) / 1000, 1)) + "K"', None),
])

CARDO = DS("cards", "Credit-card orders (delivered)", "card_orders.csv", [
    ("order_id", "string", D, N, "Order ID", None),
    ("purchase_month", "date", D, O, "Purchase Month", None),
    ("card_installments", "integer", M, Q, "Card Instalments", None),
    ("installment_band", "string", D, N, "Term", None),
    ("band_order", "integer", D, O, "Band Order", None),
    ("card_rows", "integer", M, Q, "Card Payment Rows", None),
    ("uses_other_type", "integer", M, Q, "Also Other Payment Type", None),
    ("order_value", "real", M, Q, "Order Value", BRL),
    ("merchandise_sales", "real", M, Q, "Merchandise Sales", BRL),
    ("is_late", "integer", M, Q, "Is Late", None),
    ("review_score", "integer", M, Q, "Review Score", None),
], calcs=[
    ("K_Orders", "Orders", "integer", M, Q, "COUNT([order_id])", "n#,##0"),
    ("K_Share", "Share of Card Orders", "real", M, Q, "COUNT([order_id]) / MIN({FIXED : COUNT([order_id])})", "p0.0%"),
    ("K_AOV", "AOV", "real", M, Q, "AVG([order_value])", 'c"R$"#,##0'),
    ("K_Review", "Review", "real", M, Q, "AVG([review_score])", "n0.00"),
    ("K_Late", "Late", "real", M, Q, "SUM([is_late]) / COUNT([is_late])", "p0.0%"),
    ("K_Inst", "Avg Instalments", "real", M, Q, "AVG([card_installments])", "n0.0"),
    ("K_Label", "Share Label", "string", M, N, 'STR(ROUND(100 * COUNT([order_id]) / MIN({FIXED : COUNT([order_id])}), 1)) + "%"', None),
])

DERIV = {"attr": "Attribute", "none": "None", "sum": "Sum", "avg": "Avg", "min": "Min", "usr": "User", "ctd": "CountD"}


class Shelf:
    """Collects column-instances for one worksheet."""

    def __init__(self, ds: DS):
        self.ds, self.inst = ds, {}

    def __call__(self, fld, deriv="none", kind="nk") -> str:
        name = f"{deriv}:{fld}:{kind}"
        typ = {"nk": "nominal", "qk": "quantitative", "ok": "ordinal"}[kind]
        self.inst[name] = (f"<column-instance {a(column=f'[{fld}]', derivation=DERIV[deriv], name=f'[{name}]', pivot='key', type=typ)} />")
        return self.ds.ref(name)

    def deps(self) -> str:
        # calcs may reference other calcs and any base column, so declare every column of the source
        return "".join(self.ds.col_xml(n) for n in sorted(self.ds.all_names())) + "".join(self.inst[k] for k in sorted(self.inst))


# ---------------------------------------------------------------- worksheet builder
def dark_style(extra="", hide_field_labels=True) -> str:
    fl = ('<style-rule element="worksheet"><format attr="display-field-labels" scope="cols" value="false" />'
          '<format attr="display-field-labels" scope="rows" value="false" /></style-rule>') if hide_field_labels else ""
    return (
        f'<style-rule element="table"><format attr="background-color" value="{CARD}" /></style-rule>'
        f'<style-rule element="title"><format attr="background-color" value="{CARD}" /></style-rule>'
        f'<style-rule element="label"><format attr="color" value="{LABEL}" /><format attr="font-size" value="9" /></style-rule>'
        '<style-rule element="gridline"><format attr="line-visibility" scope="cols" value="off" />'
        '<format attr="line-visibility" scope="rows" value="off" /></style-rule>'
        '<style-rule element="zeroline"><format attr="line-visibility" value="off" /></style-rule>'
        '<style-rule element="table-div"><format attr="line-visibility" scope="cols" value="off" />'
        '<format attr="line-visibility" scope="rows" value="off" /></style-rule>'
        '<style-rule element="header-div"><format attr="line-visibility" scope="cols" value="off" />'
        '<format attr="line-visibility" scope="rows" value="off" /></style-rule>'
        + fl + extra
    )


def axis_hide(ref, scope) -> str:
    return f'<format attr="display" class="0" field={quoteattr(ref)} scope="{scope}" value="false" />'


def axis_title(ref, scope, text="") -> str:
    return f'<format attr="title" class="0" field={quoteattr(ref)} scope="{scope}" value={quoteattr(text)} />'


def axis_range(ref, scope, lo=None, hi=None, scale=None) -> str:
    rt = "fixed" if lo is not None and hi is not None else None
    attrs = a(attr="space", **{"class": "0"}, field=ref, field_type="quantitative", max=hi, min=lo, range_type=rt,
              scale=scale, scope=scope, type="space")
    return f"<encoding {attrs} />"


DATE_LO, DATE_HI = "#2016-12-17#", "#2018-08-16#"   # half a month either side of Jan 2017 / Aug 2018


def date_axis(ref, show=True) -> str:
    """Month axis fixed to Jan 2017 - Aug 2018, quarterly ticks labelled 'Jan 17'."""
    attrs = a(attr="space", **{"class": "0"}, field=ref, field_type="quantitative", major_origin="#2017-01-01#",
              major_spacing="3.0", major_units="months", max=DATE_HI, min=DATE_LO, range_type="fixed", scope="cols",
              type="space")
    enc = f"<encoding {attrs} />"
    fmt = f'<format attr="text-format" field={quoteattr(ref)} value="*mmm yy" />'
    return enc + fmt + ("" if show else axis_hide(ref, "cols"))


def title_xml(title, subtitle=None) -> str:
    runs = run(title.upper(), TEXT, 10, bold=True)
    if subtitle:
        runs += NL + run(subtitle, MUTED, 8)
    return f"<layout-options><title><formatted-text>{runs}</formatted-text></title></layout-options>"


def tip(head, rows=(), note=None) -> str:
    """Tooltip runs: bold heading, then 'label: value' lines, then an optional muted note."""
    def seg(x):
        return field(x) if x.startswith("[federated.") else x
    out = run(seg(head), TT_T, 10, True)
    for lbl, val in rows:
        out += NL + run(lbl + ": ", TT_L, 9) + run(seg(val), TT_T, 9, True)
    if note:
        out += NL + run(note, TT_L, 8)
    return out


def worksheet(name, sh: Shelf, *, title=None, subtitle=None, mark="Bar", rows="", cols="", color=None, texts=(),
              label_runs=None, tooltip_runs=None, tooltip_cols=(), mark_color=CYAN, filters="", sorts="", slices=(),
              style="", show_labels=True, size=None, transparency=None, ws_palette="", hide_field_labels=True,
              label_color=None, cull_labels=False) -> str:
    ds = sh.ds
    enc = f"<color column={quoteattr(color)} />" if color else ""
    for t in texts:
        enc += f"<text column={quoteattr(t)} />"
    for t in tooltip_cols:
        enc += f"<tooltip column={quoteattr(t)} />"
    enc = f"<encodings>{enc}</encodings>" if enc else ""
    tt = f"<customized-tooltip><formatted-text>{tooltip_runs}</formatted-text></customized-tooltip>" if tooltip_runs else ""
    label = f"<customized-label><formatted-text>{label_runs}</formatted-text></customized-label>" if label_runs else ""
    fmt = f"<format attr=\"mark-labels-show\" value=\"{'true' if show_labels else 'false'}\" />"
    if not color:
        fmt += f"<format attr=\"mark-color\" value=\"{mark_color}\" />"
    if cull_labels:
        fmt += "<format attr=\"mark-labels-cull\" value=\"true\" />"
    if size:
        fmt += f"<format attr=\"size\" value=\"{size}\" />"
    if transparency is not None:
        fmt += f"<format attr=\"mark-transparency\" value=\"{transparency}\" />"
    slice_xml = ("<slices>" + "".join(f"<column>{s}</column>" for s in slices) + "</slices>") if slices else ""
    mark_rule = f'<style-rule element="mark">{ws_palette}</style-rule>' if ws_palette else ""
    return (
        f"<worksheet {a(name=name)}>{title_xml(title, subtitle) if title else ''}<table><view>"
        f"<datasources><datasource {a(caption=ds.caption, name=ds.name)} /></datasources>"
        f"<datasource-dependencies {a(datasource=ds.name)}>{sh.deps()}</datasource-dependencies>"
        f"{sorts}{filters}{slice_xml}<aggregation value=\"true\" /></view>"
        f"<style>{dark_style(style + mark_rule, hide_field_labels)}</style>"
        f"<panes><pane selection-relaxation-option=\"selection-relaxation-allow\">"
        f"<view><breakdown value=\"auto\" /></view><mark class=\"{mark}\" />{enc}{tt}{label}"
        f"<style><style-rule element=\"mark\">{fmt}</style-rule></style></pane></panes>"
        f"<rows>{rows}</rows><cols>{cols}</cols></table>"
        f"<simple-id uuid=\"{sid(name)}\" /></worksheet>"
    )


def range_filter(ref, lo, hi) -> str:
    return (f"<filter class=\"quantitative\" column={quoteattr(ref)} included-values=\"in-range\">"
            f"<min>{lo}</min><max>{hi}</max></filter>")


def sort(dim_ref, using_ref, direction="DESC") -> str:
    return f"<computed-sort column={quoteattr(dim_ref)} direction=\"{direction}\" using={quoteattr(using_ref)} />"


LEFT = '<style-rule element="cell"><format attr="text-align" value="left" /></style-rule>'

# ---------------------------------------------------------------- overview sheets
KPI_DEFS = {
    "KPI Sales": "Sum of item price excl. freight, all delivered orders (Sep 2016 - Aug 2018), BRL.",
    "KPI Orders": "Count of delivered orders, Sep 2016 - Aug 2018.",
    "KPI Late": "Orders delivered after the estimated date / delivered orders with both dates (8 excluded).",
    "KPI Review": "Average review score (1-5) of delivered orders that have a review.",
}


def kpi_card(name, caption, value_calc, delta_calc, delta_color):
    sh = Shelf(ORDERS)
    v, d = sh(value_calc, "usr"), sh(delta_calc, "usr")
    runs = (run(caption, MUTED, 9, True) + NL + run(field(v), TEXT, 24, True) + NL + run(field(d), delta_color, 8))
    return worksheet(name, sh, mark="Text", texts=[v, d], label_runs=runs, style=LEFT,
                     tooltip_runs=tip(caption, note=KPI_DEFS[name] + " Delta compares Jan-Aug 2018 with Jan-Aug 2017."))


def kpi_more():
    sh = Shelf(ORDERS)
    refs = {k: sh(k, "usr") for k in ("Calc_KPI_AOV", "Calc_KPI_Repeat", "Calc_KPI_Days", "Calc_KPI_Freight")}
    rows = [("AVG ORDER VALUE", "Calc_KPI_AOV"), ("REPEAT CUSTOMERS", "Calc_KPI_Repeat"),
            ("AVG DELIVERY TIME", "Calc_KPI_Days"), ("FREIGHT SHARE", "Calc_KPI_Freight")]
    runs = NL.join(run(lbl, MUTED, 8, True) + NL + run(field(refs[c]), TEXT, 12, True) for lbl, c in rows)
    return worksheet("KPI More", sh, mark="Text", texts=list(refs.values()), label_runs=runs, style=LEFT,
                     tooltip_runs=tip("SECONDARY METRICS", note=(
                         "AOV = (price + freight) / delivered orders. Repeat = unique customers with 2+ delivered "
                         "orders / all unique customers. Delivery time = purchase to customer delivery, days. "
                         "Freight share = freight / order value.")))


def spark(name, measure, deriv, kind, color, label, mark="Area"):
    sh = Shelf(ORDERS)
    mo = sh("purchase_month", "none", "qk")
    m = sh(measure, deriv, kind)
    style = f'<style-rule element="axis">{axis_hide(m, "rows")}{date_axis(mo, show=False)}</style-rule>'
    return worksheet(name, sh, mark=mark, rows=m, cols=mo, filters=range_filter(mo, TREND_MIN, TREND_MAX),
                     slices=[mo], style=style, show_labels=False, mark_color=color,
                     transparency=170 if mark == "Area" else None,
                     tooltip_runs=tip(mo, [(label, m)], "Purchase month"))


def trend_sales():
    sh = Shelf(ORDERS)
    mo, s = sh("purchase_month", "none", "qk"), sh("Calc_Sales", "usr", "qk")
    o = sh("Calc_Orders", "usr", "qk")
    style = (f'<style-rule element="axis">{axis_title(s, "rows")}{date_axis(mo, show=False)}'
             f'<format attr="width" field={quoteattr(s)} value="74" /></style-rule>')
    return worksheet("Trend Sales", sh, title="Monthly merchandise sales",
                     subtitle="Sales more than doubled in a year, peaking in Nov 2017 (Black Friday), then flattened in 2018",
                     mark="Area", rows=s, cols=mo, filters=range_filter(mo, TREND_MIN, TREND_MAX), slices=[mo],
                     style=style, show_labels=False, mark_color=CYAN, transparency=190,
                     tooltip_cols=[o], tooltip_runs=tip(mo, [("Merchandise sales", s), ("Delivered orders", o)],
                                                            "Item price excl. freight, by purchase month"))


def trend_late(name="Trend Late Rate", title="Late delivery rate by purchase month",
               subtitle="Logistics lagged demand: spikes in Nov 2017 (14%) and Feb-Mar 2018 (16-21%)"):
    sh = Shelf(ORDERS)
    mo, r = sh("purchase_month", "none", "qk"), sh("Calc_Late_Rate", "usr", "qk")
    lo, el = sh("Calc_Late_Orders", "usr", "qk"), sh("Calc_Orders", "usr", "qk")
    style = (f'<style-rule element="axis">{axis_title(r, "rows")}{axis_title(mo, "cols")}{date_axis(mo)}'
             f'<format attr="width" field={quoteattr(r)} value="56" /></style-rule>')
    return worksheet(name, sh, title=title, subtitle=subtitle,
                     mark="Bar", rows=r, cols=mo, filters=range_filter(mo, TREND_MIN, TREND_MAX), slices=[mo],
                     style=style, show_labels=False, mark_color=PINK, size="0.55",
                     tooltip_cols=[lo, el],
                     tooltip_runs=tip(mo, [("Late rate", r), ("Late orders", lo), ("Delivered orders", el)],
                                      "Late = delivered after the estimated date"))


def review_timing():
    sh = Shelf(ORDERS)
    t = sh("delivery_timing")
    r = sh("review_score", "avg", "qk")
    o_q = sh("delivery_timing_order", "none", "qk")
    o_min = sh("delivery_timing_order", "min", "qk")
    c = sh("Calc_Late_Code", "usr", "qk")
    oc = sh("Calc_Outcome", "attr")
    lbl = sh("Calc_Review_Label", "usr")
    n = sh("Calc_Orders", "usr", "qk")
    style = (f'<style-rule element="axis">{axis_hide(r, "cols")}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(t)} value="150" /></style-rule>')
    return worksheet("Review vs Delivery", sh, title="Late delivery vs review score",
                     subtitle="Avg review (1-5) by delivery date vs promise. Association, not proven cause.",
                     rows=t, cols=r, color=c, texts=[lbl], label_runs=run(field(lbl), TEXT, 9, True),
                     filters=range_filter(o_q, 1, 6), sorts=sort(t, o_min, "ASC"), slices=[o_q],
                     style=style, size="0.55", ws_palette=code_palette(c, (CYAN, PINK), 0, 1),
                     tooltip_cols=[n, oc], tooltip_runs=tip(t, [("Avg review", r), ("Delivered orders", n), ("Outcome", oc)],
                                                        "Delivered orders with a review, Sep 2016 - Aug 2018"))


def ranked(name, ds, rank_field, dim, measure, deriv, label_calc, title, subtitle, hi, tips, color=BAR,
           name_width=162):
    sh = Shelf(ds)
    rk_o = sh(rank_field, "none", "ok")
    rk_q = sh(rank_field, "none", "qk")
    d = sh(dim)
    m = sh(measure, deriv, "qk")
    lbl = sh(label_calc, "usr")
    tip_rows = [(lbl_, sh(f, "usr", "qk")) for lbl_, f in tips]
    style = (f'<style-rule element="axis">{axis_hide(m, "cols")}{axis_range(m, "cols", 0, hi)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(rk_o)} value="24" />'
             f'<format attr="width" field={quoteattr(d)} value="{name_width}" /></style-rule>')
    return worksheet(name, sh, title=title, subtitle=subtitle, rows=f"({rk_o} / {d})", cols=m, texts=[lbl],
                     label_runs=run(field(lbl), LABEL, 8), filters=range_filter(rk_q, 1, 10), slices=[rk_q],
                     style=style, mark_color=color, size="0.35",
                     tooltip_cols=[r for _, r in tip_rows], tooltip_runs=tip(d, tip_rows))


# ---------------------------------------------------------------- diagnostic sheets
def code_palette(ref, colors, lo, hi):
    """Colour a numeric code with fixed end points (categorical maps are ignored by 2026.3 on generated files)."""
    cols = "".join(f"<color>{c}</color>" for c in colors)
    return (f"<encoding {a(attr='color', field=ref, max=hi, min=lo, type='custom-interpolated')}>"
            f"<color-palette {a(custom='true', name='', type='ordered-sequential')}>{cols}</color-palette></encoding>")


TIER_PALETTE = (CYAN, AMBER, PINK)   # 1 Monitor, 2 Watch, 3 Priority


def heat_palette(ref):
    cols = "".join(f"<color>{c}</color>" for c in ("#1f2b3a", "#4a3050", "#8d3a63", "#c94272", PINK))
    return (f"<encoding {a(attr='color', field=ref, type='custom-interpolated')}>"
            f"<color-palette {a(custom='true', name='', type='ordered-sequential')}>{cols}</color-palette></encoding>")


def diag_heatmap():
    sh = Shelf(ORDERS)
    reg, ml = sh("customer_region"), sh("Calc_Month_Label")
    mo = sh("purchase_month", "none", "qk")
    idx = sh("Calc_Month_Index", "min", "qk")
    r = sh("Calc_Late_Rate", "usr", "qk")
    lo, n, net = sh("Calc_Late_Orders", "usr", "qk"), sh("Calc_Orders", "usr", "qk"), sh("Calc_Network_Late", "min", "qk")
    style = (f'<style-rule element="header"><format attr="width" field={quoteattr(reg)} value="96" />'
             f'<format attr="height" field={quoteattr(ml)} value="22" /></style-rule>'
             f'<style-rule element="label"><format attr="text-format" field={quoteattr(r)} value="p0%" /></style-rule>')
    return worksheet("Diag Heatmap", sh, title="Late rate by customer region and purchase month",
                     subtitle="Jan 2017 - Aug 2018. Regions sorted by late rate. Darker pink = later. "
                              "Mar 2018 hit every region; the Northeast and North were hit hardest.",
                     mark="Square", rows=reg, cols=ml, color=r, texts=[r], label_runs=run(field(r), TEXT, 8),
                     filters=range_filter(mo, TREND_MIN, TREND_MAX), sorts=sort(reg, r) + sort(ml, idx, "ASC"),
                     slices=[mo], style=style, ws_palette=heat_palette(r),
                     tooltip_cols=[lo, n, net],
                     tooltip_runs=tip(reg, [("Month", ml), ("Late rate", r), ("Late orders", lo),
                                            ("Delivered orders", n), ("Network late rate (all months)", net)],
                                      "Small cells (under 50 orders) are volatile: North Jan 2017 has 17."))


def diag_scatter():
    sh = Shelf(ORDERS)
    st, lab = sh("customer_state"), sh("state_label", "attr")
    rk_q = sh("state_late_rank", "none", "qk")
    n, r = sh("Calc_Orders", "usr", "qk"), sh("Calc_Late_Rate", "usr", "qk")
    tier, code = sh("Calc_Tier", "usr", "nk"), sh("Calc_Tier_Code", "usr", "qk")
    ex, gap, net = sh("Calc_Excess_Late", "usr", "qk"), sh("Calc_Gap_pp", "usr", "qk"), sh("Calc_Network_Late", "min", "qk")
    style = (f'<style-rule element="axis">{axis_title(n, "cols", "Delivered orders (log scale)")}'
             f'{axis_title(r, "rows", "Late rate")}{axis_range(n, "cols", 200, 60000, scale="log")}</style-rule>')
    return worksheet("Diag State Scatter", sh, title="Late rate vs order volume by state",
                     subtitle="States with 300+ delivered orders. Upper right = high rate at high volume (RJ). "
                              "Colour = action tier.",
                     mark="Circle", rows=r, cols=n, color=code, texts=[st], label_runs=run(field(st), TEXT, 8, True),
                     filters=range_filter(rk_q, 1, 99), slices=[rk_q], style=style, size="0.5", cull_labels=True,
                     ws_palette=code_palette(code, TIER_PALETTE, 1, 3),
                     tooltip_cols=[lab, tier, ex, gap, net],
                     tooltip_runs=tip(lab, [("Tier", tier), ("Late rate", r), ("Gap vs network (pp)", gap),
                                            ("Excess late orders", ex), ("Delivered orders", n)],
                                      "Network late rate = all delivered orders"))


def diag_categories(hi):
    sh = Shelf(CATS)
    c = sh("category")
    size = sh("CC_Size", "none", "qk")
    r = sh("CC_Late_Rate", "usr", "qk")
    vs, lbl, code = sh("CC_Vs", "usr", "nk"), sh("CC_Label", "usr"), sh("CC_Vs_Code", "usr", "qk")
    n, rv, dd = sh("CC_Orders", "usr", "qk"), sh("CC_Avg_Review", "usr", "qk"), sh("CC_Avg_Days", "usr", "qk")
    s = sh("CC_Sales", "usr", "qk")
    style = (f'<style-rule element="axis">{axis_hide(r, "cols")}{axis_range(r, "cols", 0, hi)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(c)} value="150" /></style-rule>')
    return worksheet("Diag Categories", sh, title="Late rate and review by category",
                     subtitle="22 categories with 1,000+ delivered orders: late rates only 5.5-9.8% "
                              "(states: 5.0-23.9%). Label: late rate · avg review.",
                     rows=c, cols=r, color=code, texts=[lbl], label_runs=run(field(lbl), LABEL, 8),
                     filters=range_filter(size, 1000, 10000000), sorts=sort(c, r), slices=[size],
                     style=style, size="0.4", ws_palette=code_palette(code, (CYAN, PINK), 0, 1),
                     tooltip_cols=[n, rv, dd, s, vs],
                     tooltip_runs=tip(c, [("Late rate", r), ("Vs network", vs), ("Avg review", rv), ("Avg delivery days", dd),
                                          ("Orders containing category", n), ("Category sales", s)],
                                      "Per order containing the category (order x category grain)"))


# ---------------------------------------------------------------- action sheets
def action_states(hi):
    sh = Shelf(ORDERS)
    lab = sh("state_label")
    rk_q = sh("state_late_rank", "none", "qk")
    tier_h = sh("Calc_Tier", "usr", "ok")
    hdr = [sh(f, "usr", "ok") for f in ("Calc_Orders", "Calc_Late_Rate", "Calc_Gap_pp", "Calc_Avg_Review",
                                         "Calc_Late_Sales")]
    ex, lbl = sh("Calc_Excess_Late", "usr", "qk"), sh("Calc_Action_Label", "usr")
    code = sh("Calc_Tier_Code", "usr", "qk")
    reg, lo, net = sh("customer_region", "attr"), sh("Calc_Late_Orders", "usr", "qk"), sh("Calc_Network_Late", "min", "qk")
    widths = "".join(f'<format attr="width" field={quoteattr(h)} value="{w}" />' for h, w in zip([tier_h] + hdr, (62, 54, 62, 58, 72, 100)))
    style = (f'<style-rule element="axis">{axis_title(ex, "cols", "Excess late orders")}'
             f'{axis_range(ex, "cols", -hi, hi)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(lab)} value="160" />{widths}</style-rule>'
             f'<style-rule element="zeroline"><format attr="line-visibility" value="on" />'
             f'<format attr="stroke-color" value="{MUTED}" /></style-rule>')
    return worksheet("Action States", sh, title="State exception queue",
                     subtitle="21 states with 300+ delivered orders, ranked by excess late orders. "
                              "Select a state to filter the trend.",
                     rows="(" + " / ".join([lab, tier_h] + hdr) + ")", cols=ex, color=code, texts=[lbl],
                     label_runs=run(field(lbl), LABEL, 8), filters=range_filter(rk_q, 1, 99), sorts=sort(lab, ex),
                     slices=[rk_q], style=style, size="0.45", hide_field_labels=False,
                     ws_palette=code_palette(code, TIER_PALETTE, 1, 3),
                     tooltip_cols=[reg, lo, net],
                     tooltip_runs=tip(lab, [("Tier", tier_h), ("Region", reg), ("Delivered orders", hdr[0]),
                                            ("Late orders", lo), ("Late rate", hdr[1]), ("Network late rate", net),
                                            ("Gap (pp)", hdr[2]), ("Excess late orders", ex), ("Avg review", hdr[3]),
                                            ("Sales on late orders", hdr[4])],
                                      "Excess = late orders - delivered orders x network late rate"))


# ---------------------------------------------------------------- seller & fulfilment sheets
FUL_NOTE = "96,281 delivered orders with purchase <= carrier hand-off <= customer delivery (197 excluded)"


def ful_split(name, calc, label_calc, title, subtitle):
    sh = Shelf(FUL)
    o, v = sh("F_Outcome"), sh("F_Valid", "none", "qk")
    m, lbl, code = sh(calc, "usr", "qk"), sh(label_calc, "usr"), sh("F_Late_Code", "usr", "qk")
    d, t, n = sh("F_Dispatch", "usr", "qk"), sh("F_Transit", "usr", "qk"), sh("F_Orders", "usr", "qk")
    style = (f'<style-rule element="axis">{axis_hide(m, "cols")}{axis_range(m, "cols", 0, 38)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(o)} value="96" /></style-rule>')
    return worksheet(name, sh, title=title, subtitle=subtitle, rows=o, cols=m, color=code, texts=[lbl],
                     label_runs=run(field(lbl), TEXT, 9, True), filters=range_filter(v, 1, 1), slices=[v],
                     style=style, size="0.5", ws_palette=code_palette(code, (CYAN, PINK), 0, 1),
                     tooltip_cols=[d, t, n],
                     tooltip_runs=tip(o, [("Avg seller dispatch (purchase to hand-off)", d),
                                          ("Avg carrier transit (hand-off to customer)", t), ("Orders", n)], FUL_NOTE))


def ful_ship():
    sh = Shelf(FUL)
    lab, v = sh("F_Ship_Label"), sh("F_Ship_Valid", "none", "qk")
    r, lbl, code = sh("F_Late_Rate", "usr", "qk"), sh("F_Ship_Lbl", "usr"), sh("F_Miss_Code", "usr", "qk")
    n, d = sh("F_Orders", "usr", "qk"), sh("F_Dispatch", "usr", "qk")
    style = (f'<style-rule element="axis">{axis_hide(r, "cols")}{axis_range(r, "cols", 0, 0.66)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(lab)} value="124" /></style-rule>')
    return worksheet("Ful Ship Limit", sh, title="Late rate when the seller misses the shipping limit",
                     subtitle="Hand-off after the seller's shipping limit date. Association, not proven cause.",
                     rows=lab, cols=r, color=code, texts=[lbl], label_runs=run(field(lbl), TEXT, 9, True),
                     filters=range_filter(v, 1, 1), slices=[v], style=style, size="0.5",
                     ws_palette=code_palette(code, (CYAN, PINK), 0, 1), tooltip_cols=[n, d],
                     tooltip_runs=tip(lab, [("Late rate", r), ("Orders", n), ("Avg seller dispatch (days)", d)],
                                      "Shipping limit = latest shipping_limit_date of the order's items"))


def sel_bars(name, dim, size_field, thr, title, subtitle, dim_width):
    sh = Shelf(SEL)
    d, sz = sh(dim), sh(size_field, "none", "qk")
    r, lbl, code = sh("S_Late_Rate", "usr", "qk"), sh("S_Rate_Label", "usr"), sh("S_Vs_Code", "usr", "qk")
    n, ex, tr, ms = sh("S_Orders", "usr", "qk"), sh("S_Excess", "usr", "qk"), sh("S_Transit", "usr", "qk"), sh("S_Missed", "usr", "qk")
    net = sh("S_Network", "min", "qk")
    style = (f'<style-rule element="axis">{axis_hide(r, "cols")}{axis_range(r, "cols", 0, 0.42)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(d)} value="{dim_width}" /></style-rule>')
    return worksheet(name, sh, title=title, subtitle=subtitle, rows=d, cols=r, color=code, texts=[lbl],
                     label_runs=run(field(lbl), LABEL, 8), filters=range_filter(sz, thr, 10000000),
                     sorts=sort(d, r), slices=[sz], style=style, size="0.45",
                     ws_palette=code_palette(code, (CYAN, PINK), 0, 1), tooltip_cols=[n, ex, tr, ms, net],
                     tooltip_runs=tip(d, [("Late rate", r), ("Network late rate", net), ("Seller-orders", n),
                                          ("Excess late orders", ex), ("Avg carrier transit (days)", tr),
                                          ("Missed shipping limit", ms)],
                                      "Order x seller grain: an order with 2+ sellers counts once per seller"))


def sel_table(hi):
    sh = Shelf(SEL)
    s_, st = sh("seller_short"), sh("seller_state")
    rk = sh("seller_excess_rank", "none", "qk")
    hdr = [sh(f, "usr", "ok") for f in ("S_Orders", "S_Late_Rate", "S_Missed", "S_Dispatch", "S_Review")]
    ex, lbl = sh("S_Excess", "usr", "qk"), sh("S_Excess_Label", "usr")
    sid_, sales, tr = sh("seller_id", "attr"), sh("S_Sales", "usr", "qk"), sh("S_Transit", "usr", "qk")
    widths = "".join(f'<format attr="width" field={quoteattr(h)} value="{w}" />' for h, w in zip(hdr, (54, 66, 80, 78, 74)))
    style = (f'<style-rule element="axis">{axis_title(ex, "cols", "Excess late orders")}{axis_range(ex, "cols", 0, hi)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(s_)} value="70" />'
             f'<format attr="width" field={quoteattr(st)} value="44" />{widths}</style-rule>')
    return worksheet("Ful Sellers", sh, title="Seller exception list",
                     subtitle="Top 15 of 210 sellers with 100+ seller-orders, ranked by excess late orders "
                              "vs the 8.0% network rate (order x seller grain). Seller = first 8 characters of seller_id.",
                     rows="(" + " / ".join([s_, st] + hdr) + ")", cols=ex, texts=[lbl],
                     label_runs=run(field(lbl), LABEL, 8), filters=range_filter(rk, 1, 15), sorts=sort(s_, ex),
                     slices=[rk], style=style, size="0.45", mark_color=PINK, hide_field_labels=False,
                     tooltip_cols=[sid_, sales, tr],
                     tooltip_runs=tip(sid_, [("Seller-orders", hdr[0]), ("Late rate", hdr[1]), ("Excess late orders", ex),
                                             ("Missed shipping limit", hdr[2]), ("Avg dispatch (days)", hdr[3]),
                                             ("Avg transit (days)", tr), ("Avg review", hdr[4]), ("Seller sales", sales)],
                                      "Late flag and review are order-level; shared by every seller in the order"))


def diag_retention():
    sh = Shelf(CUST)
    f, v = sh("CU_First"), sh("CU_Valid", "none", "qk")
    r, lbl, code = sh("CU_Repeat", "usr", "qk"), sh("CU_Label", "usr"), sh("CU_Code", "usr", "qk")
    n, rp = sh("CU_Customers", "usr", "qk"), sh("CU_Repeaters", "usr", "qk")
    style = f'<style-rule element="axis">{axis_hide(r, "rows")}{axis_range(r, "rows", 0, 0.055)}</style-rule>'
    return worksheet("Diag Retention", sh, title="Repeat rate by first-order delivery",
                     subtitle="Customers whose first delivered order was before Mar 2018 (6+ months to reorder). "
                              "Association, not cause.",
                     rows=r, cols=f, color=code, texts=[lbl], label_runs=run(field(lbl), TEXT, 8, True),
                     filters=range_filter(v, 1, 1), slices=[v], style=style, size="0.6",
                     ws_palette=code_palette(code, (CYAN, PINK), 0, 1), tooltip_cols=[n, rp],
                     tooltip_runs=tip(f, [("Repeat rate (2+ delivered orders)", r), ("Repeat customers", rp),
                                          ("Customers", n)], "Unique customers (customer_unique_id)"))


def diag_instalments():
    sh = Shelf(CARDO)
    b, bo = sh("installment_band"), sh("band_order", "min", "qk")
    hdr = [sh(f, "usr", "ok") for f in ("K_Orders", "K_AOV", "K_Review", "K_Late")]
    sh_, lbl, inst = sh("K_Share", "usr", "qk"), sh("K_Label", "usr"), sh("K_Inst", "usr", "qk")
    widths = "".join(f'<format attr="width" field={quoteattr(h)} value="{w}" />' for h, w in zip(hdr, (52, 50, 50, 46)))
    style = (f'<style-rule element="axis">{axis_hide(sh_, "cols")}{axis_range(sh_, "cols", 0, 0.75)}</style-rule>'
             f'<style-rule element="header"><format attr="width" field={quoteattr(b)} value="40" />{widths}</style-rule>')
    return worksheet("Diag Instalments", sh, title="Credit-card instalments",
                     subtitle="74,302 delivered card orders; band = max instalments on the order's card payments. "
                              "Review and late rate: association only.",
                     rows="(" + " / ".join([b] + hdr) + ")", cols=sh_, texts=[lbl], label_runs=run(field(lbl), LABEL, 8),
                     sorts=sort(b, bo, "ASC"), style=style, size="0.5", mark_color=CYAN, hide_field_labels=False,
                     tooltip_cols=[inst],
                     tooltip_runs=tip(b, [("Share of card orders", sh_), ("Orders", hdr[0]), ("Avg order value", hdr[1]),
                                          ("Avg instalments", inst), ("Avg review", hdr[2]), ("Late rate", hdr[3])],
                                      "2 orders with 0 instalments excluded"))


def build_worksheets(hr):
    return [
        ("KPI Sales", kpi_card("KPI Sales", "MERCHANDISE SALES", "Calc_KPI_Sales", "Calc_D_Sales", GOOD)),
        ("KPI Orders", kpi_card("KPI Orders", "DELIVERED ORDERS", "Calc_KPI_Orders", "Calc_D_Orders", GOOD)),
        ("KPI Late", kpi_card("KPI Late", "LATE DELIVERY RATE", "Calc_KPI_Late", "Calc_D_Late", PINK)),
        ("KPI Review", kpi_card("KPI Review", "AVG REVIEW SCORE", "Calc_KPI_Review", "Calc_D_Review", PINK)),
        ("KPI More", kpi_more()),
        ("Spark Sales", spark("Spark Sales", "Calc_Sales", "usr", "qk", CYAN, "Merchandise sales")),
        ("Spark Orders", spark("Spark Orders", "Calc_Orders", "usr", "qk", CYAN, "Delivered orders")),
        ("Spark Late", spark("Spark Late", "Calc_Late_Rate", "usr", "qk", PINK, "Late rate")),
        ("Spark Review", spark("Spark Review", "Calc_Avg_Review", "usr", "qk", PINK, "Avg review", mark="Line")),
        ("Trend Sales", trend_sales()),
        ("Trend Late Rate", trend_late()),
        ("Review vs Delivery", review_timing()),
        ("Top Categories", ranked("Top Categories", ITEMS, "category_sales_rank", "category", "price", "sum",
                                  "Calc_Cat_Label", "Top categories by sales",
                                  "Top 10 = 62% of merchandise sales (label: sales · share)", hr["cat"] * 2.2,
                                  [("Sales", "Calc_Item_Sales"), ("Share of sales", "Calc_Item_Share"),
                                   ("Orders", "Calc_Item_Orders")])),
        ("Top States", ranked("Top States", ORDERS, "state_sales_rank", "state_label", "merchandise_sales", "sum",
                              "Calc_State_Sales_Label", "Top states by sales",
                              "SP = 38% of sales. RJ, the #2 market, is late on 13.5% of orders", hr["state"] * 2.6,
                              [("Sales", "Calc_Sales"), ("Orders", "Calc_Orders"), ("Late rate", "Calc_Late_Rate"),
                               ("Avg review", "Calc_Avg_Review")], color=CYAN)),
        ("Worst Late States", ranked("Worst Late States", ORDERS, "state_late_rank", "state_label", "Calc_Late_Rate",
                                     "usr", "Calc_State_Late_Label", "Highest late-delivery rates",
                                     "States with 300+ delivered orders. Network average: 8.1%", hr["late"] * 2.6,
                                     [("Late orders", "Calc_Late_Orders"), ("Orders", "Calc_Orders"),
                                      ("Avg review", "Calc_Avg_Review")], color=PINK)),
        ("Diag Heatmap", diag_heatmap()),
        ("Diag State Scatter", diag_scatter()),
        ("Diag Categories", diag_categories(0.16)),
        ("Diag Retention", diag_retention()),
        ("Diag Instalments", diag_instalments()),
        ("Ful Dispatch", ful_split("Ful Dispatch", "F_Dispatch", "F_Days_Label_D", "Seller dispatch",
                                   "Avg days from purchase to carrier hand-off")),
        ("Ful Transit", ful_split("Ful Transit", "F_Transit", "F_Days_Label_T", "Carrier transit",
                                  "Avg days from carrier hand-off to customer (same day scale)")),
        ("Ful Ship Limit", ful_ship()),
        ("Ful Routes", sel_bars("Ful Routes", "route", "S_Route_Size", 500, "Late rate by route",
                                "Seller state → customer state, routes with 500+ seller-orders. Label: rate · volume",
                                78)),
        ("Ful Seller States", sel_bars("Ful Seller States", "seller_state", "S_State_Size", 300,
                                       "Late rate by seller state", "Seller states with 300+ seller-orders", 40)),
        ("Ful Sellers", sel_table(round(hr["seller_excess"] * 1.9))),
        ("Action States", action_states(round(hr["excess"] * 1.8))),
        ("Action State Trend", trend_late("Action State Trend", "Monthly late rate: selected state",
                                          "All 27 states until a row is selected in the queue (click again to clear)")),
    ]


# ---------------------------------------------------------------- dashboard layout engine
class Z:
    """Layout node. kind: sheet | text | button | flow. size = fixed px along parent's direction."""

    def __init__(self, kind, name=None, size=None, weight=1.0, children=(), direction="vert", bg=None, margin=0,
                 padding=0, runs=None, title=True, target=None, active=False):
        self.__dict__.update(locals())
        del self.__dict__["self"]


def Sheet(name, size=None, weight=1.0, title=True, margin=5, padding=8):
    return Z("sheet", name, size, weight, title=title, bg=CARD, margin=margin, padding=padding)


def Text(runs, size=None, weight=1.0, bg=SIDEBAR, margin=0, padding=16):
    return Z("text", size=size, weight=weight, runs=runs, bg=bg, margin=margin, padding=padding)


def Button(target, active, size=34):
    return Z("button", size=size, target=target, active=active, margin=4, padding=0)


def Flow(direction, children, size=None, weight=1.0, bg=None, margin=0, padding=0):
    return Z("flow", size=size, weight=weight, children=children, direction=direction, bg=bg, margin=margin,
             padding=padding)


class Emitter:
    def __init__(self):
        self.ids = iter(range(3, 100000))

    @staticmethod
    def box(x, y, w, h):
        return dict(x=round(x * 100000 / W), y=round(y * 100000 / H), w=round(w * 100000 / W), h=round(h * 100000 / H))

    @staticmethod
    def zstyle(bg=None, margin=0, padding=0):
        f = '<format attr="border-style" value="none" /><format attr="border-width" value="0" />'
        f += f'<format attr="margin" value="{margin}" /><format attr="padding" value="{padding}" />'
        if bg:
            f += f'<format attr="background-color" value="{bg}" />'
        return f"<zone-style>{f}</zone-style>"

    def emit(self, z: Z, x, y, w, h, fixed=None) -> str:
        fx = dict(is_fixed="true", fixed_size=fixed) if fixed is not None else {}
        box = self.box(x, y, w, h)
        zid = next(self.ids)
        if z.kind == "sheet":
            return (f"<zone {a(id=zid, name=z.name, show_title=None if z.title else 'false', **box, **fx)}>"
                    f"{self.zstyle(z.bg, z.margin, z.padding)}</zone>")
        if z.kind == "text":
            return (f"<zone {a(id=zid, type_v2='text', **box, **fx)}><formatted-text>{z.runs}</formatted-text>"
                    f"{self.zstyle(z.bg, z.margin, z.padding)}</zone>")
        if z.kind == "button":
            bg, fg = (CYAN, BG) if z.active else (CARD, TEXT)
            act = f'tabdoc:goto-sheet window-id="{sid("win-" + z.target)}"'
            return (f"<zone {a(id=zid, type_v2='dashboard-object', **box, **fx)}>"
                    f"<button {a(action=act, button_type='text')}><button-visual-state>"
                    f"<caption>{escape(z.target.upper())}</caption>"
                    f"<tooltip-text>Go to {escape(z.target)}</tooltip-text>"
                    f"<button-caption-font-style {a(bold='true', fontcolor=fg, fontname='Tableau Medium', fontsize=9)} />"
                    f"<format attr=\"background-color\" value=\"{bg}\" /><format attr=\"border-style\" value=\"none\" />"
                    f"</button-visual-state></button>{self.zstyle(SIDEBAR, z.margin, 0)}</zone>")
        # flow: split along the direction; sized children keep their px, others share the remainder by weight
        inset = z.margin + z.padding
        ix, iy, iw, ih = x + inset, y + inset, w - 2 * inset, h - 2 * inset
        length = ih if z.direction == "vert" else iw
        flex = [c for c in z.children if c.size is None]
        rest = length - sum(c.size for c in z.children if c.size is not None)
        tot = sum(c.weight for c in flex) or 1
        kids, pos = [], (iy if z.direction == "vert" else ix)
        for i, c in enumerate(z.children):
            ln = c.size if c.size is not None else round(rest * c.weight / tot)
            if i == len(z.children) - 1:
                ln = (iy + ih if z.direction == "vert" else ix + iw) - pos
            fixed_px = ln   # Tableau only honours child sizes in flow containers when they are fixed
            if z.direction == "vert":
                kids.append(self.emit(c, ix, pos, iw, ln, fixed_px))
            else:
                kids.append(self.emit(c, pos, iy, ln, ih, fixed_px))
            pos += ln
        return (f"<zone {a(id=zid, param='vert' if z.direction == 'vert' else 'horz', type_v2='layout-flow', **box, **fx)}>"
                f"{''.join(kids)}{self.zstyle(z.bg, z.margin, z.padding)}</zone>")


def brand_runs(subtitle):
    return (run("OLIST", TEXT, 24, True) + NL + run("RETAIL PERFORMANCE", TEXT, 11, True) + NL
            + run(subtitle, CYAN, 9, True) + NL + run("Delivered orders · Sep 2016-Aug 2018", MUTED, 8))


def notes_runs(heading, items, footer):
    runs = run(heading, CYAN, 9, True) + NL
    for head, body in items:
        runs += NL + run(head, TEXT, 8, True) + NL + run(body, LABEL, 8) + NL
    return runs + NL + run(footer, MUTED, 7)


SOURCE_NOTE = ("Source: Olist public data → PostgreSQL warehouse → CSV extracts (one grain per chart). "
               "Figures verified 2026-11-18.")


def sidebar(active, items, heading="KEY TAKEAWAYS"):
    return Flow("vert", [Text(brand_runs(active.upper()), size=140, padding=16)]
                + [Button(d, d == active) for d in DASHBOARDS]
                + [Text(notes_runs(heading, items, SOURCE_NOTE), padding=16)], size=260, bg=SIDEBAR)


def page(active, items, main):
    return Flow("horz", [sidebar(active, items), main], bg=BG)


def header_band(title, sub):
    return Text(run(title, TEXT, 13, True) + NL + run(sub, MUTED, 8), size=62, bg=CARD, margin=5, padding=12)


OVERVIEW_ITEMS = [
    ("1  GROWTH", "Jan-Aug 2018 sales +141% vs 2017; flat at R$0.84-0.98M a month since Mar 2018."),
    ("2  LOGISTICS STRAIN", "Late rate more than doubled (4.2% to 9.4%), peaking in Feb-Mar 2018."),
    ("3  LATENESS HURTS RATINGS", "4.3 stars when early vs ~1.7 when 8+ days late."),
    ("4  CONCENTRATION", "SP = 38% of sales; top 10 categories = 62%."),
    ("5  REGIONAL RISK", "Northeast 14.3% late vs ~7% South/Southeast; RJ 13.5% at scale."),
    ("6  RETENTION GAP", "Only 3.0% of customers ordered twice."),
    ("7  PAYMENTS", "Credit card 78.5% of payment value, boleto 18.0%."),
]
DIAG_ITEMS = [
    ("WHEN", "Mar 2018: 19%+ late in every region (South 19.4%, Southeast 19.2%)."),
    ("WHERE", "Geography amplifies it: NE 36.3%, North 39.2% in Mar 2018; NE 14.4% vs South 7.1% overall."),
    ("NOT THE DRIVER", "Category: 22 large categories sit at 5.5-9.8% late; states span 5.0-23.9%."),
    ("CATEGORY EXCEPTION", "Office Furniture: slowest (20.6 days) and lowest-rated (3.64) large category."),
    ("RETENTION", "First order late: 3.19% repeat vs 4.04% on time (cohort before Mar 2018). Association."),
    ("INSTALMENTS", "37% of card orders use 4+ instalments. Order value rises with term: R$101 (1x) to R$333 "
                    "(7-10x)."),
]
SELLER_ITEMS = [
    ("DISPATCH VS TRANSIT", "Late orders: 5.8 days seller dispatch + 25.7 days carrier transit. On-time orders: "
                            "3.0 + 7.9. About 86% of the extra 20.6 days is transit."),
    ("SHIPPING LIMIT", "Sellers handed over after the shipping limit on 9.0% of orders; those were late 24.4% "
                       "vs 6.5%. 27% of late orders had a missed limit."),
    ("ROUTES", "SP → RJ is late 15.4% on 8,273 seller-orders, the largest excess of any route; SP → CE 15.2%, "
               "SP → BA 14.7%."),
    ("SELLER STATES", "71% of seller-orders ship from SP (69,395 of 97,811), so route says more than seller state."),
    ("GRAIN AND EXCLUSIONS", "Order x seller: 1,275 multi-seller orders (1.3%) count once per seller. 197 orders "
                             "with missing or out-of-sequence hand-off dates are excluded from timing."),
]
ACTION_ITEMS = [
    ("HOW TIERS WORK", "Priority: late rate 3+ pp above the network (8.11%) and 50+ excess late orders. Watch: 1+ pp "
                       "above. Monitor: otherwise."),
    ("PRIORITY STATES (6)", "RJ, BA, CE, MA, ES, AL: 1,176 excess late orders and R$426.7K of sales on late orders "
                            "(3.2% of all sales)."),
    ("BIGGEST LEVER", "Rio de Janeiro alone accounts for 663 excess late orders (56% of the Priority total), on 12,351 "
                      "orders."),
    ("WATCH (8)", "PA, SC, PE, RN, SE, PI, PB, MS: 255 excess late orders combined."),
    ("FIXED POPULATION", "Tiers and headline use all delivered orders in the 21 states with 300+ orders. Selecting "
                         "a state filters only the monthly trend."),
]


def playbook_runs():
    T, L, Mu = TEXT, LABEL, MUTED
    steps = [
        ("1  OWNER", "Logistics / carrier management lead (owner to be confirmed by the business)."),
        ("2  ACTION", "For Priority states: review carrier performance and the estimated-date setting per state; "
                      "consider longer promised dates where carriers cannot meet them."),
        ("3  TRIGGER", "A state's monthly late rate is 3+ pp above the network rate for 2 consecutive months."),
        ("4  SUCCESS MEASURE", "Excess late orders and late rate per state, monthly; guardrail: avg review and "
                               "delivered-order volume."),
        ("5  NEXT INVESTIGATION", "Seller & Fulfilment shows most extra delay is carrier transit. Next: carrier-level "
                                  "performance on the worst routes (e.g. SP → RJ)."),
    ]
    runs = run("PLAYBOOK", CYAN, 9, True) + NL
    for h_, b in steps:
        runs += NL + run(h_, T, 8, True) + NL + run(b, L, 8)
    return runs + NL + NL + run("Recommendations are hypotheses from measured data, not proven causes.", Mu, 7)


def layouts():
    pad = 8
    # --- Executive Overview
    cards = [Flow("vert", [Sheet(k, size=96, title=False, margin=0, padding=6),
                           Sheet(s, title=False, margin=0, padding=4)], bg=CARD, margin=5, padding=6)
             for k, s in (("KPI Sales", "Spark Sales"), ("KPI Orders", "Spark Orders"),
                          ("KPI Late", "Spark Late"), ("KPI Review", "Spark Review"))]
    kpi_row = Flow("horz", cards + [Sheet("KPI More", title=False, padding=12, weight=0.95)], size=186)
    trend = Flow("vert", [Sheet("Trend Sales", size=164, margin=0, padding=6),
                          Sheet("Trend Late Rate", margin=0, padding=6)], bg=CARD, margin=5, padding=4, weight=62)
    mid_row = Flow("horz", [trend, Sheet("Review vs Delivery", weight=38)], size=300)
    low_row = Flow("horz", [Sheet("Top Categories"), Sheet("Top States", weight=1.1), Sheet("Worst Late States")])
    overview = page(DASH_OVERVIEW, OVERVIEW_ITEMS,
                    Flow("vert", [kpi_row, mid_row, low_row], padding=pad // 2, bg=BG))
    # --- Delivery Diagnostics
    diag = page(DASH_DIAG, DIAG_ITEMS, Flow("vert", [
        header_band("Late delivery is a network-wide timing shock, amplified by geography, not by product category",
                    "Mar 2018: every region was 19%+ late (Northeast 36%, North 39%). States span 5.0-23.9% late; "
                    "large categories only 5.5-9.8%. Measured on delivered orders; associations, not proven causes."),
        Sheet("Diag Heatmap", size=238),
        Flow("horz", [Sheet("Diag State Scatter", weight=35), Sheet("Diag Categories", weight=34),
                      Flow("vert", [Sheet("Diag Retention", size=218), Sheet("Diag Instalments")], weight=31)]),
    ], padding=pad // 2, bg=BG), )
    # --- Action Queue
    action = page(DASH_ACTION, ACTION_ITEMS, Flow("vert", [
        header_band("Six priority states hold 1,176 excess late orders. Rio de Janeiro alone has 663 (56%)",
                    "Excess late orders = late orders - delivered orders x network late rate (8.11%). Fixed population: "
                    "21 states with 300+ delivered orders, Sep 2016 - Aug 2018. Selection does not change the headline."),
        Flow("horz", [Sheet("Action States", weight=66),
                      Flow("vert", [Sheet("Action State Trend", size=300),
                                    Text(playbook_runs(), bg=CARD, margin=5, padding=14)], weight=34)]),
    ], padding=pad // 2, bg=BG))
    # --- Seller & Fulfilment
    seller = page(DASH_SELLER, SELLER_ITEMS, Flow("vert", [
        header_band("Late orders lose most of their time in carrier transit, not seller dispatch",
                    "Late orders: 25.7 transit vs 5.8 dispatch days (on time: 7.9 vs 3.0): ~86% of the extra 20.6 days is "
                    "transit. Missed shipping limits (9.0% of orders): 24.4% late vs 6.5%. Associations."),
        Flow("horz", [Sheet("Ful Dispatch"), Sheet("Ful Transit"), Sheet("Ful Ship Limit", weight=1.15)], size=196),
        Flow("horz", [Sheet("Ful Routes", weight=27), Sheet("Ful Seller States", weight=19),
                      Sheet("Ful Sellers", weight=54)]),
    ], padding=pad // 2, bg=BG))
    return {DASH_OVERVIEW: overview, DASH_DIAG: diag, DASH_SELLER: seller, DASH_ACTION: action}


SHEETS_ON = {
    DASH_OVERVIEW: ["KPI Sales", "KPI Orders", "KPI Late", "KPI Review", "KPI More", "Spark Sales", "Spark Orders",
                    "Spark Late", "Spark Review", "Trend Sales", "Trend Late Rate", "Review vs Delivery",
                    "Top Categories", "Top States", "Worst Late States"],
    DASH_DIAG: ["Diag Heatmap", "Diag State Scatter", "Diag Categories", "Diag Retention", "Diag Instalments"],
    DASH_SELLER: ["Ful Dispatch", "Ful Transit", "Ful Ship Limit", "Ful Routes", "Ful Seller States", "Ful Sellers"],
    DASH_ACTION: ["Action States", "Action State Trend"],
}


def dashboards_xml(first=DASH_OVERVIEW, fixed_size=True) -> str:
    out = ""
    lay = layouts()
    for name in [first] + [d for d in DASHBOARDS if d != first]:
        root = lay[name]
        em = Emitter()
        body = em.emit(root, 0, 0, W, H)
        zones = (f"<zones><zone {a(id=2, type_v2='layout-basic', h=100000, w=100000, x=0, y=0)}>{body}"
                 f"{Emitter.zstyle(BG)}</zone></zones>")
        size = f"<size {a(maxheight=H, maxwidth=W, minheight=H, minwidth=W)} />" if fixed_size else ""
        out += (f"<dashboard {a(name=name)}>"
                f"<style><style-rule element=\"table\"><format attr=\"background-color\" value=\"{BG}\" /></style-rule></style>"
                f"{size}{zones}<simple-id uuid=\"{sid('dashboard-' + name)}\" /></dashboard>")
    return f"<dashboards>{out}</dashboards>"


def actions_xml() -> str:
    return (
        "<actions>"
        f"<action {a(caption='Queue: filter trend by state', name='[ActionOlistQueueFilter]')}>"
        "<activation auto-clear=\"true\" type=\"on-select\" />"
        f"<source {a(dashboard=DASH_ACTION, type='sheet', worksheet='Action States')} />"
        "<command command=\"tsc:tsl-filter\">"
        "<param name=\"exclude\" value=\"Action States\" />"
        "<param name=\"special-fields\" value=\"all\" />"
        f"<param name=\"target\" value={quoteattr(DASH_ACTION)} />"
        "</command></action></actions>"
    )


def windows_xml(first) -> str:
    order = [first] + [d for d in DASHBOARDS if d != first]
    out = ""
    for d in order:
        vps = "".join(f"<viewpoint {a(name=n)}><zoom type=\"entire-view\" /></viewpoint>" for n in SHEETS_ON[d])
        out += (f"<window {a(**{'class': 'dashboard'}, maximized='true' if d == first else None, name=d)}>"
                f"<viewpoints>{vps}</viewpoints><active id=\"-1\" />"
                f"<device-preview><device is-portrait=\"true\" name=\"Generic Phone\" type=\"Phone\" /></device-preview>"
                f"<simple-id uuid=\"{sid('win-' + d)}\" /></window>")
    return f"<windows source-height=\"30\">{out}</windows>"


def workbook_xml(directory: str, first=DASH_OVERVIEW, fixed_size=True) -> str:
    sheets = build_worksheets(headroom())
    return (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        "<workbook original-version=\"18.1\" source-build=\"2026.3.1 (20263.26.1110.1931)\" source-platform=\"mac\" "
        "version=\"18.1\" xmlns:user=\"http://www.tableausoftware.com/xml/user\">"
        "<document-format-change-manifest><BasicButtonObject /><BasicButtonObjectTextSupport /><ObjectModelEncapsulateLegacy />"
        "<ObjectModelTableType /><SchemaViewerObjectModel /><SetMembershipControl /><SheetIdentifierTracking />"
        "<SortTagCleanup /><WindowsPersistSimpleIdentifiers /></document-format-change-manifest>"
        "<preferences><preference name=\"ui.encoding.shelf.height\" value=\"24\" /><preference name=\"ui.shelf.height\" value=\"26\" /></preferences>"
        "<style><style-rule element=\"all\"><format attr=\"font-family\" value=\"Tableau Book\" /></style-rule>"
        "<style-rule element=\"worksheet\"><format attr=\"font-size\" value=\"9\" /></style-rule></style>"
        f"<datasources>{''.join(d.xml(directory) for d in (ORDERS, ITEMS, CATS, FUL, SEL, CUST, CARDO, PAYMENTS))}</datasources>"
        f"{actions_xml()}"
        f"<worksheets>{''.join(x for _, x in sheets)}</worksheets>"
        f"{dashboards_xml(first, fixed_size)}{windows_xml(first)}</workbook>\n"
    )


def pretty(xml_text: str) -> str:
    return xml.dom.minidom.parseString(xml_text.encode()).toprettyxml(indent="  ", encoding="utf-8").decode()


def write_twbx(path: Path, first=DASH_OVERVIEW, fixed_size=True) -> None:
    packaged = pretty(workbook_xml("Data/olist", first, fixed_size))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{NAME}.twb", packaged)
        for f in CSVS:
            z.write(DATA_DIR / f, f"Data/olist/{f}")


def main() -> None:
    twb = HERE / f"{NAME}.twb"
    twb.write_text(pretty(workbook_xml(str(DATA_DIR))), encoding="utf-8")
    write_twbx(HERE / f"{NAME}.twbx")
    print(f"wrote {twb}\nwrote {HERE / (NAME + '.twbx')}")
    if "--qa" in sys.argv:   # screenshot copies: identical workbook, but each opens on a different dashboard
        out = Path(sys.argv[sys.argv.index("--qa") + 1])
        out.mkdir(parents=True, exist_ok=True)
        for i, d in enumerate(DASHBOARDS, 1):
            p = out / f"QA{i} {d}.twbx"
            write_twbx(p, d)   # same fixed 1440 x 840 canvas as the production workbook
            print(f"wrote {p}")


if __name__ == "__main__":
    main()
