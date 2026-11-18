"""One-off data discovery for Olist CSVs. Prints schemas, nulls, dupes, keys."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
FILES = sorted(RAW.glob("*.csv"))


def profile(path: Path) -> dict:
    # Sample first for dtypes; full read for counts (geolocation is large but OK for discovery)
    df = pd.read_csv(path, low_memory=False)
    nulls = df.isna().sum()
    null_pct = (nulls / len(df) * 100).round(2)
    dups_full = int(df.duplicated().sum())
    result = {
        "file": path.name,
        "rows": int(len(df)),
        "cols": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "null_counts": {c: int(nulls[c]) for c in df.columns if nulls[c] > 0},
        "null_pct": {c: float(null_pct[c]) for c in df.columns if nulls[c] > 0},
        "duplicate_rows": dups_full,
        "sample": df.head(2).astype(str).to_dict(orient="records"),
    }
    # Candidate key uniqueness for common id columns
    id_like = [c for c in df.columns if c.endswith("_id") or c == "product_category_name"]
    uniqueness = {}
    for c in id_like:
        uniqueness[c] = {
            "nunique": int(df[c].nunique(dropna=True)),
            "nulls": int(df[c].isna().sum()),
            "is_unique": bool(df[c].is_unique),
        }
    # Composite uniqueness for known multi-key tables
    if path.name == "olist_order_items_dataset.csv":
        key = ["order_id", "order_item_id"]
        uniqueness["|".join(key)] = {
            "nunique": int(df.groupby(key).ngroups),
            "is_unique": bool(not df.duplicated(subset=key).any()),
        }
    if path.name == "olist_order_payments_dataset.csv":
        key = ["order_id", "payment_sequential"]
        uniqueness["|".join(key)] = {
            "nunique": int(df.groupby(key).ngroups),
            "is_unique": bool(not df.duplicated(subset=key).any()),
        }
    if path.name == "product_category_name_translation.csv":
        uniqueness["product_category_name"] = {
            "nunique": int(df["product_category_name"].nunique()),
            "is_unique": bool(df["product_category_name"].is_unique),
        }
    result["id_uniqueness"] = uniqueness
    return result


def main() -> None:
    reports = [profile(p) for p in FILES]
    out = Path("docs/data_discovery.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    for r in reports:
        print("=" * 72)
        print(r["file"], "| rows:", r["rows"])
        print("cols:", r["cols"])
        print("dtypes:", r["dtypes"])
        print("nulls:", r["null_counts"])
        print("dup_rows:", r["duplicate_rows"])
        print("ids:", r["id_uniqueness"])
    print("Wrote", out)


if __name__ == "__main__":
    main()
