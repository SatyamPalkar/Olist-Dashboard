"""Aggregate the Tableau extracts (tableau/data/*.csv) into one small JSON file for the web dashboard.

Standard library only. No row-level customer or order identifiers are written: every output is an
aggregate at the grain its chart needs (month, region x month, state, route, category, seller, band).
Definitions match tableau/build_tableau_workbook.py and docs/tableau_build_spec.md.

Usage (from the project root):
    python3 web/build_data.py          # writes web/site/data/dashboard.json
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tableau" / "data"
OUT = Path(__file__).resolve().parent / "site" / "data" / "dashboard.json"
MONTHS = [f"{y}-{m:02d}" for y in (2017, 2018) for m in range(1, 13) if (y, m) <= (2018, 8)]


def rows(name):
    with open(SRC / name, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def num(v):
    return None if v in ("", None) else float(v)


class Acc:
    """Late / eligible / review / value accumulator."""

    __slots__ = ("n", "late", "elig", "rev_sum", "rev_n", "sales", "late_sales", "ids")

    def __init__(self):
        self.n = 0; self.late = 0; self.elig = 0; self.rev_sum = 0; self.rev_n = 0
        self.sales = 0.0; self.late_sales = 0.0

    def add(self, is_late, review, sales=0.0):
        self.n += 1
        self.sales += sales
        if is_late != "":
            self.elig += 1
            if is_late == "1":
                self.late += 1
                self.late_sales += sales
        if review != "":
            self.rev_sum += int(review); self.rev_n += 1

    @property
    def rate(self):
        return self.late / self.elig if self.elig else None

    @property
    def review(self):
        return self.rev_sum / self.rev_n if self.rev_n else None


def r(x, d=4):
    """Keep 10 significant decimals so the browser's own rounding matches Tableau's (no double rounding)."""
    return None if x is None else round(x, max(d, 10))


def tier(gap_pp, excess):
    if gap_pp >= 3 and excess >= 50:
        return "Priority"
    return "Watch" if gap_pp >= 1 else "Monitor"


def build():
    orders = list(rows("orders.csv"))
    tot = Acc()
    for o in orders:
        tot.add(o["is_late"], o["review_score"], float(o["merchandise_sales"]))
    net = tot.rate

    # ---------------- Executive Overview
    order_value = sum(float(o["order_value"]) for o in orders)
    freight = sum(float(o["freight_charges"]) for o in orders)
    days = [float(o["delivery_days"]) for o in orders if o["delivery_days"]]
    cust = {}
    for o in orders:
        cust[o["customer_unique_id"]] = o["is_repeat_customer"] == "1"
    period = {"2017": Acc(), "2018": Acc()}
    month = defaultdict(Acc)
    for o in orders:
        m = o["purchase_month"][:7]
        month[m].add(o["is_late"], o["review_score"], float(o["merchandise_sales"]))
        y, mm = m[:4], int(m[5:7])
        if y in period and mm <= 8:
            period[y].add(o["is_late"], o["review_score"], float(o["merchandise_sales"]))
    timing = defaultdict(Acc)
    order_of = {}
    for o in orders:
        if o["delivery_timing"] != "Unknown":
            timing[o["delivery_timing"]].add(o["is_late"], o["review_score"])
            order_of[o["delivery_timing"]] = int(o["delivery_timing_order"])
    by_state = defaultdict(Acc)
    meta_state = {}
    for o in orders:
        by_state[o["customer_state"]].add(o["is_late"], o["review_score"], float(o["merchandise_sales"]))
        meta_state[o["customer_state"]] = (o["state_label"], o["customer_region"], o["state_sales_rank"], o["state_late_rank"])
    cat = defaultdict(lambda: [0.0, set()])
    cat_rank = {}
    for i in rows("order_items.csv"):
        cat[i["category"]][0] += float(i["price"]); cat[i["category"]][1].add(i["order_id"])
        cat_rank[i["category"]] = int(i["category_sales_rank"])
    cat_total = sum(v[0] for v in cat.values())

    def state_row(s):
        a = by_state[s]; lab, reg, srk, lrk = meta_state[s]
        gap = 100 * (a.rate - net); exc = a.late - a.elig * net
        return {"code": s, "name": lab, "region": reg, "orders": a.n, "eligible": a.elig, "late": a.late,
                "rate": r(a.rate, 5), "review": r(a.review, 3), "sales": round(a.sales, 2),
                "late_sales": round(a.late_sales, 2), "gap_pp": r(gap, 3), "excess": r(exc, 2),
                "tier": tier(gap, exc) if lrk else None, "sales_rank": int(srk),
                "late_rank": int(lrk) if lrk else None}

    states = [state_row(s) for s in by_state]
    overview = {
        "kpi": {"sales": round(tot.sales, 2), "orders": tot.n, "late_rate": r(net, 6), "late": tot.late,
                "eligible": tot.elig, "review": r(tot.review, 4), "aov": round(order_value / tot.n, 2),
                "repeat_rate": r(sum(cust.values()) / len(cust), 5), "customers": len(cust),
                "delivery_days": r(sum(days) / len(days), 3), "freight_share": r(freight / order_value, 4)},
        "jan_aug": {y: {"sales": round(a.sales, 2), "orders": a.n, "late_rate": r(a.rate, 5),
                        "review": r(a.review, 4)} for y, a in period.items()},
        "monthly": [{"month": m, "sales": round(month[m].sales, 2), "orders": month[m].n, "late": month[m].late,
                     "eligible": month[m].elig, "rate": r(month[m].rate, 5), "review": r(month[m].review, 3)}
                    for m in MONTHS],
        "timing": [{"bucket": k, "order": order_of[k], "review": r(a.review, 3), "orders": a.n,
                    "late": 1 if order_of[k] >= 4 else 0} for k, a in sorted(timing.items(), key=lambda kv: order_of[kv[0]])],
        "top_categories": [{"rank": cat_rank[c], "category": c, "sales": round(v[0], 2), "share": r(v[0] / cat_total, 5),
                            "orders": len(v[1])} for c, v in sorted(cat.items(), key=lambda kv: cat_rank[kv[0]])
                           if cat_rank[c] <= 10],
        "top_states": sorted([s for s in states if s["sales_rank"] <= 10], key=lambda s: s["sales_rank"]),
        "worst_late": sorted([s for s in states if s["late_rank"] and s["late_rank"] <= 10], key=lambda s: s["late_rank"]),
        "category_top10_share": r(sum(v[0] for c, v in cat.items() if cat_rank[c] <= 10) / cat_total, 4),
    }

    # ---------------- Delivery Diagnostics
    heat = defaultdict(Acc)
    region = defaultdict(Acc)
    for o in orders:
        m = o["purchase_month"][:7]
        if m in MONTHS:
            heat[(o["customer_region"], m)].add(o["is_late"], o["review_score"])
            region[o["customer_region"]].add(o["is_late"], o["review_score"])
    regions = sorted(region, key=lambda k: -region[k].rate)
    cc = defaultdict(lambda: [Acc(), [], 0.0])
    cc_rows = cc_late = cc_elig = 0
    for c in rows("order_categories.csv"):
        a = cc[c["category"]]; a[0].add(c["is_late"], c["review_score"]); a[2] += float(c["category_sales"])
        if c["delivery_days"]:
            a[1].append(float(c["delivery_days"]))
        if c["is_late"] != "":
            cc_elig += 1; cc_late += int(c["is_late"])
    cc_net = cc_late / cc_elig
    cust_rows = [c for c in rows("customers.csv") if c["first_order_late"] != "" and c["first_purchase_date"] < "2018-03-01"]
    ret = {}
    for k, lab in (("0", "On time"), ("1", "Late")):
        g = [c for c in cust_rows if c["first_order_late"] == k]
        ret[lab] = {"customers": len(g), "repeaters": sum(int(c["is_repeat"]) for c in g),
                    "repeat_rate": r(sum(int(c["is_repeat"]) for c in g) / len(g), 5)}
    band = defaultdict(lambda: {"orders": 0, "value": 0.0, "inst": 0, "acc": Acc()})
    border = {}
    for k in rows("card_orders.csv"):
        b = band[k["installment_band"]]; b["orders"] += 1; b["value"] += float(k["order_value"])
        b["inst"] += int(k["card_installments"]); b["acc"].add(k["is_late"], k["review_score"])
        border[k["installment_band"]] = int(k["band_order"])
    card_total = sum(b["orders"] for b in band.values())
    diagnostics = {
        "regions": regions,
        "months": MONTHS,
        "heatmap": [{"region": g, "month": m, "late": heat[(g, m)].late, "eligible": heat[(g, m)].elig,
                     "rate": r(heat[(g, m)].rate, 5)} for g in regions for m in MONTHS],
        "region_rate": {g: r(region[g].rate, 5) for g in regions},
        "states": sorted([s for s in states if s["late_rank"]], key=lambda s: s["late_rank"]),
        "categories": sorted([{"category": k, "orders": v[0].n, "rate": r(v[0].rate, 5), "review": r(v[0].review, 3),
                               "days": r(sum(v[1]) / len(v[1]), 2), "sales": round(v[2], 2),
                               "above_network": v[0].rate > cc_net}
                              for k, v in cc.items() if v[0].n >= 1000], key=lambda x: -x["rate"]),
        "category_network": r(cc_net, 5),
        "retention": ret,
        "instalments": [{"band": k, "orders": b["orders"], "share": r(b["orders"] / card_total, 5),
                         "aov": round(b["value"] / b["orders"], 2), "avg_instalments": r(b["inst"] / b["orders"], 2),
                         "review": r(b["acc"].review, 3), "rate": r(b["acc"].rate, 5)}
                        for k, b in sorted(band.items(), key=lambda kv: border[kv[0]])],
        "card_orders": card_total,
    }

    # ---------------- Seller & Fulfilment
    split = {"Late orders": [0, 0.0, 0.0], "On-time orders": [0, 0.0, 0.0]}
    ship = {"Shipped after limit": Acc(), "Shipped within limit": Acc()}
    for f in rows("order_fulfilment.csv"):
        if f["timing_valid"] == "1" and f["is_late"] != "":
            s = split["Late orders" if f["is_late"] == "1" else "On-time orders"]
            s[0] += 1; s[1] += float(f["dispatch_days"]); s[2] += float(f["transit_days"])
        if f["missed_ship_limit"] != "" and f["is_late"] != "":
            ship["Shipped after limit" if f["missed_ship_limit"] == "1" else "Shipped within limit"].add(f["is_late"], "")
    os_rows = list(rows("order_sellers.csv"))
    os_net_l = sum(int(x["is_late"]) for x in os_rows if x["is_late"] != "")
    os_net_n = sum(1 for x in os_rows if x["is_late"] != "")
    os_net = os_net_l / os_net_n

    def group(key, thr):
        g = defaultdict(lambda: {"acc": Acc(), "disp": [], "tran": [], "miss": [], "sales": 0.0, "state": None, "rank": None})
        for x in os_rows:
            d = g[key(x)]; d["acc"].add(x["is_late"], x["review_score"]); d["sales"] += float(x["seller_sales"])
            d["state"] = x["seller_state"]; d["rank"] = x["seller_excess_rank"]
            if x["dispatch_days"]:
                d["disp"].append(float(x["dispatch_days"])); d["tran"].append(float(x["transit_days"]))
            if x["missed_ship_limit"] != "":
                d["miss"].append(int(x["missed_ship_limit"]))
        out = []
        for k, d in g.items():
            a = d["acc"]
            if a.elig < thr:
                continue
            out.append({"key": k, "orders": a.elig, "late": a.late, "rate": r(a.rate, 5),
                        "excess": r(a.late - a.elig * os_net, 2), "review": r(a.review, 3),
                        "dispatch": r(sum(d["disp"]) / len(d["disp"]), 2) if d["disp"] else None,
                        "transit": r(sum(d["tran"]) / len(d["tran"]), 2) if d["tran"] else None,
                        "missed": r(sum(d["miss"]) / len(d["miss"]), 4) if d["miss"] else None,
                        "sales": round(d["sales"], 2), "state": d["state"],
                        "rank": int(d["rank"]) if d["rank"] else None})
        return sorted(out, key=lambda x: -x["rate"])

    sellers = [dict(s, key=s["key"][:8]) for s in group(lambda x: x["seller_id"], 1)
               if s["rank"] and s["rank"] <= 15]
    seller = {
        "split": {k: {"orders": v[0], "dispatch": r(v[1] / v[0], 3), "transit": r(v[2] / v[0], 3)} for k, v in split.items()},
        "ship_limit": {k: {"orders": a.elig, "late": a.late, "rate": r(a.rate, 5)} for k, a in ship.items()},
        "routes": group(lambda x: x["route"], 500),
        "seller_states": group(lambda x: x["seller_state"], 300),
        "sellers": sorted(sellers, key=lambda s: s["rank"]),
        "network": r(os_net, 5),
        "seller_orders": os_net_n,
        "multi_seller_orders": len({x["order_id"] for x in os_rows if int(x["seller_count"]) > 1}),
        "ranked_sellers": len({x["seller_id"] for x in os_rows if x["seller_excess_rank"]}),
    }

    # ---------------- Action Queue
    sm = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for o in orders:
        m = o["purchase_month"][:7]
        if m in MONTHS and o["is_late"] != "":
            for k in (o["customer_state"], "ALL"):
                sm[k][m][0] += int(o["is_late"]); sm[k][m][1] += 1
    action = {
        "states": sorted([s for s in states if s["late_rank"]], key=lambda s: -s["excess"]),
        "state_monthly": {k: [v[m] for m in MONTHS] for k, v in sm.items()},
        "state_names": {s["code"]: s["name"] for s in states},
    }
    return {"meta": {"scope": "Delivered orders purchased 2016-09-15 to 2018-08-29 (BRL)",
                     "network_late_rate": r(net, 6), "source": "tableau/data/*.csv (warehouse extracts)"},
            "overview": overview, "diagnostics": diagnostics, "seller": seller, "action": action}


def main():
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
