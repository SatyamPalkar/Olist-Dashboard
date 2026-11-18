"""Check web/site/data/dashboard.json against an independent recomputation from tableau/data/*.csv.

The recomputation below deliberately does not import build_data.py. It asserts the headline figures
that appear on the dashboard and in README.md, and that no row-level identifiers are published.
Standard library only.  Usage:  python3 web/check_data.py      (exit code 1 on any failure)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tableau" / "data"
JSON_PATH = Path(__file__).resolve().parent / "site" / "data" / "dashboard.json"


def load(name):
    with open(DATA / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def recompute():
    o = load("orders.csv")
    dated = [x for x in o if x["is_late"] in ("0", "1")]
    late = sum(x["is_late"] == "1" for x in dated)
    net = late / len(dated)
    exp = {"orders": len(o), "sales": round(sum(float(x["merchandise_sales"]) for x in o), 2),
           "late_rate_pct": round(100 * net, 2)}
    st = {}
    for x in dated:
        s = st.setdefault(x["customer_state"], [0, 0, x["state_late_rank"]])
        s[0] += x["is_late"] == "1"; s[1] += 1
    excess = {k: v[0] - v[1] * net for k, v in st.items() if v[2]}
    gap = {k: 100 * (st[k][0] / st[k][1] - net) for k in excess}
    prio = [k for k in excess if gap[k] >= 3 and excess[k] >= 50]
    exp["priority_states"] = sorted(prio)
    exp["priority_excess"] = round(sum(excess[k] for k in prio))
    exp["rj_excess"] = round(excess["RJ"])
    f = [x for x in load("order_fulfilment.csv") if x["timing_valid"] == "1" and x["is_late"] in ("0", "1")]
    for lab, flag in (("late", "1"), ("ontime", "0")):
        g = [x for x in f if x["is_late"] == flag]
        exp[f"transit_{lab}"] = round(sum(float(x["transit_days"]) for x in g) / len(g), 1)
        exp[f"dispatch_{lab}"] = round(sum(float(x["dispatch_days"]) for x in g) / len(g), 1)
    s = [x for x in load("order_sellers.csv") if x["route"] == "SP → RJ" and x["is_late"] in ("0", "1")]
    exp["sp_rj_rate_pct"] = round(100 * sum(x["is_late"] == "1" for x in s) / len(s), 1)
    exp["sp_rj_orders"] = len(s)
    c = [x for x in load("customers.csv") if x["first_order_late"] in ("0", "1") and x["first_purchase_date"] < "2018-03-01"]
    for lab, flag in (("late", "1"), ("ontime", "0")):
        g = [x for x in c if x["first_order_late"] == flag]
        exp[f"repeat_{lab}_pct"] = round(100 * sum(x["is_repeat"] == "1" for x in g) / len(g), 2)
    k = load("card_orders.csv")
    exp["card_orders"] = len(k)
    exp["card_1x_share_pct"] = round(100 * sum(x["card_installments"] == "1" for x in k) / len(k), 1)
    return exp


def from_json(d):
    st = d["action"]["states"]; pr = [s for s in st if s["tier"] == "Priority"]
    sp = d["seller"]["split"]; rt = next(x for x in d["seller"]["routes"] if x["key"] == "SP → RJ")
    ret = d["diagnostics"]["retention"]
    return {"orders": d["overview"]["kpi"]["orders"], "sales": d["overview"]["kpi"]["sales"],
            "late_rate_pct": round(100 * d["overview"]["kpi"]["late_rate"], 2),
            "priority_states": sorted(s["code"] for s in pr), "priority_excess": round(sum(s["excess"] for s in pr)),
            "rj_excess": round(next(s["excess"] for s in st if s["code"] == "RJ")),
            "transit_late": round(sp["Late orders"]["transit"], 1), "transit_ontime": round(sp["On-time orders"]["transit"], 1),
            "dispatch_late": round(sp["Late orders"]["dispatch"], 1), "dispatch_ontime": round(sp["On-time orders"]["dispatch"], 1),
            "sp_rj_rate_pct": round(100 * rt["rate"], 1), "sp_rj_orders": rt["orders"],
            "repeat_late_pct": round(100 * ret["Late"]["repeat_rate"], 2),
            "repeat_ontime_pct": round(100 * ret["On time"]["repeat_rate"], 2),
            "card_orders": d["diagnostics"]["card_orders"],
            "card_1x_share_pct": round(100 * d["diagnostics"]["instalments"][0]["share"], 1)}


# Published figures (README.md / dashboard headlines) that both sides must equal
PUBLISHED = {"orders": 96478, "sales": 13221498.11, "late_rate_pct": 8.11,
             "priority_states": ["AL", "BA", "CE", "ES", "MA", "RJ"], "priority_excess": 1176, "rj_excess": 663,
             "transit_late": 25.7, "transit_ontime": 7.9, "dispatch_late": 5.8, "dispatch_ontime": 3.0,
             "sp_rj_rate_pct": 15.4, "sp_rj_orders": 8273, "repeat_late_pct": 3.19, "repeat_ontime_pct": 4.04,
             "card_orders": 74302, "card_1x_share_pct": 33.2}


def check() -> list[str]:
    raw = JSON_PATH.read_text(encoding="utf-8")
    d = json.loads(raw)
    exp, got, errors = recompute(), from_json(d), []
    for k, pub in PUBLISHED.items():
        if not (exp[k] == got[k] == pub):
            errors.append(f"{k}: published={pub} recomputed={exp[k]} json={got[k]}")
    if JSON_PATH.stat().st_size > 2_000_000:
        errors.append("dashboard.json exceeds 2 MB")
    for col in ("customer_unique_id", "order_id"):
        if col in raw:
            errors.append(f"row-level field name '{col}' found in JSON")
    ids = {x["customer_unique_id"] for x in load("customers.csv")[:500]}
    if any(i in raw for i in ids):
        errors.append("customer identifiers found in JSON")
    return errors


def test_dashboard_json_matches_independent_recomputation():
    assert check() == []


if __name__ == "__main__":
    errs = check()
    for e in errs:
        print("FAIL", e)
    print("OK: all headline figures match" if not errs else f"{len(errs)} failure(s)")
    sys.exit(1 if errs else 0)
