"""Phase 1 profiling for Olist raw CSVs. Ground truth = files in data/raw/."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT_JSON = ROOT / "docs" / "data_profile_raw.json"
OUT_MD = ROOT / "docs" / "data_profile.md"

FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

# Columns that look categorical for value-count reporting
CATEGORICAL_HINTS = {
    "order_status",
    "payment_type",
    "customer_state",
    "seller_state",
    "geolocation_state",
    "product_category_name",
    "product_category_name_english",
    "review_score",
    "payment_sequential",
    "payment_installments",
}

TIMESTAMP_HINTS = re.compile(
    r"(timestamp|_at$|_date$|date$)", re.IGNORECASE
)

ID_HINTS = re.compile(r"(^|_)id$|_id$|zip_code_prefix", re.IGNORECASE)

# Exact shared-name coverage pairs and provisional zip-prefix links
ZIP_LINK = (
    ("customer_zip_code_prefix", "zip_code_prefix"),
    ("seller_zip_code_prefix", "zip_code_prefix"),
)


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size


def empty_as_null(s: pd.Series) -> pd.Series:
    """Treat NaN and blank/whitespace-only strings as null."""
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        stripped = s.astype("string").str.strip()
        return stripped.isna() | (stripped == "")
    return s.isna()


def infer_dtype_label(s: pd.Series, col: str) -> str:
    """Provisional dtype from pandas inference + timestamp parse attempts."""
    if TIMESTAMP_HINTS.search(col):
        parsed = pd.to_datetime(s, errors="coerce")
        non_null = (~empty_as_null(s)).sum()
        if non_null > 0 and parsed.notna().sum() / max(non_null, 1) > 0.5:
            return "datetime (provisional)"
    dt = s.dtype
    if pd.api.types.is_integer_dtype(dt):
        return "int"
    if pd.api.types.is_float_dtype(dt):
        # Nullable integer-like columns often load as float64 because of NaNs
        non_null = s.dropna()
        if len(non_null) and (non_null % 1 == 0).all():
            return "float (nullable int-like)"
        return "float"
    if pd.api.types.is_bool_dtype(dt):
        return "bool"
    if pd.api.types.is_datetime64_any_dtype(dt):
        return "datetime"
    return "object"


def sample_id_values(s: pd.Series, n: int = 3) -> list[str]:
    vals = []
    for v in s.dropna().astype(str).head(50):
        v = v.strip()
        if not v:
            continue
        if len(v) > 40:
            v = v[:37] + "..."
        vals.append(v)
        if len(vals) >= n:
            break
    return vals


def profile_file(path: Path) -> dict:
    size = file_size_bytes(path)
    # dtype inference from sample, then full load with low_memory=False
    sample = pd.read_csv(path, nrows=5000, low_memory=False)
    df = pd.read_csv(path, low_memory=False)

    rows = len(df)
    cols = list(df.columns)
    col_profiles = []
    for c in cols:
        null_mask = empty_as_null(df[c])
        null_count = int(null_mask.sum())
        null_rate = round(null_count / rows, 6) if rows else 0.0
        # Prefer full-frame dtype (sample can miss nulls that force float64)
        inferred = infer_dtype_label(df[c], c)

        entry: dict = {
            "name": c,
            "inferred_dtype": inferred,
            "pandas_dtype": str(df[c].dtype),
            "null_count": null_count,
            "null_rate": null_rate,
            "nunique": int(df[c].nunique(dropna=True)),
        }

        # Timestamp profiling
        if TIMESTAMP_HINTS.search(c):
            raw_non_null = int((~null_mask).sum())
            parsed = pd.to_datetime(df[c], errors="coerce")
            parseable = int(parsed.notna().sum())
            unparseable = raw_non_null - parseable
            entry["timestamp"] = {
                "min": str(parsed.min()) if parseable else None,
                "max": str(parsed.max()) if parseable else None,
                "parseable": parseable,
                "unparseable_non_null": unparseable,
                "raw_non_null": raw_non_null,
            }

        # Categorical-looking
        is_cat = (
            c in CATEGORICAL_HINTS
            or (
                inferred == "object"
                and entry["nunique"] <= 50
                and not c.endswith("_id")
                and "message" not in c
                and "comment" not in c
                and "title" not in c
            )
        )
        if is_cat and "message" not in c and "comment_title" not in c:
            vc = df[c].value_counts(dropna=False).head(20)
            entry["top_values"] = [
                {"value": (None if pd.isna(k) else str(k)), "count": int(v)}
                for k, v in vc.items()
            ]
            entry["distinct_count"] = entry["nunique"]

        # ID samples
        if (
            c.endswith("_id")
            or c.endswith("_prefix")
            or c in ("product_category_name", "product_category_name_english")
        ):
            entry["id_samples"] = sample_id_values(df[c], 3)

        col_profiles.append(entry)

    # Uniqueness for ID-like and known composites
    uniqueness = {}
    for c in cols:
        if c.endswith("_id") or c.endswith("_prefix") or c == "product_category_name":
            nunique = int(df[c].nunique(dropna=True))
            uniqueness[c] = {
                "unique_count": nunique,
                "row_count": rows,
                "is_unique": bool(df[c].is_unique and df[c].notna().all()),
                "duplicate_rows": int(rows - nunique) if df[c].notna().all() else None,
                "nulls": int(empty_as_null(df[c]).sum()),
            }

    composites = {
        "olist_order_items_dataset.csv": ["order_id", "order_item_id"],
        "olist_order_payments_dataset.csv": ["order_id", "payment_sequential"],
        "olist_order_reviews_dataset.csv": ["review_id"],  # check alone; also order_id
        "product_category_name_translation.csv": ["product_category_name"],
        "olist_geolocation_dataset.csv": [
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
        ],
    }
    if path.name in composites:
        key = composites[path.name]
        if all(k in df.columns for k in key):
            dup = int(df.duplicated(subset=key).sum())
            uniqueness["|".join(key)] = {
                "unique_count": int(df.drop_duplicates(subset=key).shape[0]),
                "row_count": rows,
                "is_unique": dup == 0,
                "duplicate_rows": dup,
            }

    # Extra: reviews may have duplicate review_id or multi reviews per order
    if path.name == "olist_order_reviews_dataset.csv":
        uniqueness["order_id_as_key"] = {
            "unique_count": int(df["order_id"].nunique()),
            "row_count": rows,
            "is_unique": bool(df["order_id"].is_unique),
            "orders_with_multiple_reviews": int(
                (df.groupby("order_id").size() > 1).sum()
            ),
        }
        review_id_dup_groups = int((df.groupby("review_id").size() > 1).sum())
        review_ids_multi_order = int(
            (df.groupby("review_id")["order_id"].nunique() > 1).sum()
        )
        uniqueness["review_id_duplicate_detail"] = {
            "unique_count": int(df["review_id"].nunique()),
            "row_count": rows,
            "is_unique": bool(df["review_id"].is_unique),
            "review_ids_with_multiple_rows": review_id_dup_groups,
            "review_ids_spanning_multiple_order_ids": review_ids_multi_order,
        }

    if path.name == "olist_order_payments_dataset.csv":
        uniqueness["order_id_as_key"] = {
            "unique_count": int(df["order_id"].nunique()),
            "row_count": rows,
            "is_unique": bool(df["order_id"].is_unique),
            "orders_with_multiple_payments": int(
                (df.groupby("order_id").size() > 1).sum()
            ),
        }

    if path.name == "olist_geolocation_dataset.csv":
        zip_col = "geolocation_zip_code_prefix"
        g = df.groupby(zip_col).size()
        uniqueness["geolocation_zip_code_prefix_multiplicity"] = {
            "unique_prefixes": int(g.shape[0]),
            "row_count": rows,
            "prefixes_with_multiple_rows": int((g > 1).sum()),
            "max_rows_per_prefix": int(g.max()),
            "mean_rows_per_prefix": round(float(g.mean()), 2),
        }

    if path.name == "olist_customers_dataset.csv":
        uniqueness["customer_unique_id"] = {
            "unique_count": int(df["customer_unique_id"].nunique()),
            "row_count": rows,
            "is_unique": bool(df["customer_unique_id"].is_unique),
            "nulls": int(empty_as_null(df["customer_unique_id"]).sum()),
        }

    return {
        "filename": path.name,
        "size_bytes": size,
        "row_count": rows,
        "column_count": len(cols),
        "columns": cols,
        "column_profiles": col_profiles,
        "uniqueness": uniqueness,
        "full_duplicate_rows": int(df.duplicated().sum()),
        "_df_columns": cols,  # helper stripped later
    }


def build_column_index(profiles: list[dict]) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = defaultdict(list)
    for p in profiles:
        for c in p["columns"]:
            idx[c].append(p["filename"])
    return dict(idx)


def coverage_check(
    child_vals: set, parent_vals: set
) -> dict:
    if not child_vals:
        return {
            "child_distinct": 0,
            "parent_distinct": len(parent_vals),
            "in_parent": 0,
            "orphans": 0,
            "coverage_pct": 100.0,
        }
    in_parent = child_vals & parent_vals
    orphans = child_vals - parent_vals
    return {
        "child_distinct": len(child_vals),
        "parent_distinct": len(parent_vals),
        "in_parent": len(in_parent),
        "orphans": len(orphans),
        "coverage_pct": round(100.0 * len(in_parent) / len(child_vals), 4),
        "orphan_samples": sorted(list(orphans))[:5],
    }


def load_series(filename: str, col: str) -> pd.Series:
    path = RAW / filename
    df = pd.read_csv(path, usecols=[col], low_memory=False)
    s = df[col]
    # Normalize for set comparison: strip strings, keep ints as int then str for zip
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        s = s.astype("string").str.strip()
        s = s[s.notna() & (s != "")]
    else:
        s = s.dropna()
    return s


# Column-specific dimension/parent file when the same name appears in 2+ files.
# Preference is evidence-oriented (lookup/master side), not invented FKs.
COLUMN_PARENT_FILE = {
    "order_id": "olist_orders_dataset.csv",
    "customer_id": "olist_customers_dataset.csv",
    "product_id": "olist_products_dataset.csv",
    "seller_id": "olist_sellers_dataset.csv",
    "product_category_name": "product_category_name_translation.csv",
}


def cross_file_coverage(profiles: list[dict]) -> list[dict]:
    col_idx = build_column_index(profiles)
    results = []

    # Exact shared column names in 2+ files
    for col, files in sorted(col_idx.items()):
        if len(files) < 2:
            continue
        sets = {}
        for f in files:
            sets[f] = set(load_series(f, col).astype(str))

        parent = COLUMN_PARENT_FILE.get(col)
        if parent is None or parent not in files:
            # Fallback: lexicographic only when no column-specific parent
            parent = sorted(files)[0]

        for child in files:
            if child == parent:
                continue
            cov = coverage_check(sets[child], sets[parent])
            results.append(
                {
                    "link_type": "exact_column_name",
                    "column": col,
                    "parent_file": parent,
                    "child_file": child,
                    "direction": "child_values_in_parent",
                    **cov,
                }
            )

        # Also report parent keys missing from each child (coverage gaps / anti-joins)
        for child in files:
            if child == parent:
                continue
            reverse = coverage_check(sets[parent], sets[child])
            results.append(
                {
                    "link_type": "exact_column_name_parent_not_in_child",
                    "column": col,
                    "parent_file": parent,
                    "child_file": child,
                    "direction": "parent_values_in_child",
                    **reverse,
                    "note": "Percent of distinct parent values found in child; "
                    "orphans here = parent keys with no matching child row.",
                }
            )

    # Provisional zip prefix links (name-based, not confirmed FK)
    geo_file = "olist_geolocation_dataset.csv"
    geo_col = "geolocation_zip_code_prefix"
    geo_vals = set(load_series(geo_file, geo_col).astype(str))

    for child_file, child_col, label in [
        (
            "olist_customers_dataset.csv",
            "customer_zip_code_prefix",
            "customer_zip_code_prefix → geolocation_zip_code_prefix",
        ),
        (
            "olist_sellers_dataset.csv",
            "seller_zip_code_prefix",
            "seller_zip_code_prefix → geolocation_zip_code_prefix",
        ),
    ]:
        child_vals = set(load_series(child_file, child_col).astype(str))
        cov = coverage_check(child_vals, geo_vals)
        results.append(
            {
                "link_type": "provisional_zip_prefix_name_link",
                "column_mapping": label,
                "parent_file": geo_file,
                "parent_column": geo_col,
                "child_file": child_file,
                "child_column": child_col,
                **cov,
                "note": "Provisional name-based link candidate only; not a confirmed FK. "
                "Geolocation has many rows per zip prefix.",
            }
        )

    return results


def quality_flags(profiles: list[dict], coverage: list[dict]) -> list[dict]:
    flags = []
    by_name = {p["filename"]: p for p in profiles}

    for p in profiles:
        for key, u in p["uniqueness"].items():
            if key.endswith("_id") or "|" in key or key == "product_category_name":
                if u.get("is_unique") is False and "as_key" not in key and "multiplicity" not in key:
                    # Expected non-unique FKs
                    if key in (
                        "order_id",
                        "customer_id",
                        "product_id",
                        "seller_id",
                        "customer_unique_id",
                    ):
                        # Only flag if this file claims grain of that key as PK
                        declared_pk = {
                            "olist_orders_dataset.csv": "order_id",
                            "olist_customers_dataset.csv": "customer_id",
                            "olist_products_dataset.csv": "product_id",
                            "olist_sellers_dataset.csv": "seller_id",
                            "olist_order_reviews_dataset.csv": "review_id",
                            "product_category_name_translation.csv": "product_category_name",
                        }
                        if declared_pk.get(p["filename"]) == key:
                            flags.append(
                                {
                                    "severity": "high",
                                    "file": p["filename"],
                                    "issue": f"Declared PK candidate `{key}` is NOT unique",
                                    "evidence": u,
                                }
                            )
                    elif "|" in key and not u.get("is_unique"):
                        flags.append(
                            {
                                "severity": "high",
                                "file": p["filename"],
                                "issue": f"Composite key candidate `{key}` is NOT unique",
                                "evidence": u,
                            }
                        )
                    elif key == "review_id" and not u.get("is_unique"):
                        # Detailed duplicate flag added below for reviews file
                        pass

        if p["full_duplicate_rows"] > 0:
            flags.append(
                {
                    "severity": "medium",
                    "file": p["filename"],
                    "issue": "Exact full-row duplicates present",
                    "evidence": {"full_duplicate_rows": p["full_duplicate_rows"]},
                }
            )

    # Geolocation multi-valued zip
    geo = by_name.get("olist_geolocation_dataset.csv")
    if geo:
        m = geo["uniqueness"].get("geolocation_zip_code_prefix_multiplicity")
        if m and m["prefixes_with_multiple_rows"] > 0:
            flags.append(
                {
                    "severity": "info",
                    "file": "olist_geolocation_dataset.csv",
                    "issue": "Multiple geolocation rows per zip_code_prefix (not 1:1)",
                    "evidence": m,
                }
            )

    # Multiple payments / reviews per order
    pay = by_name.get("olist_order_payments_dataset.csv")
    if pay:
        u = pay["uniqueness"].get("order_id_as_key", {})
        if u.get("orders_with_multiple_payments", 0) > 0:
            flags.append(
                {
                    "severity": "info",
                    "file": "olist_order_payments_dataset.csv",
                    "issue": "Multiple payment rows per order_id (expected grain)",
                    "evidence": u,
                }
            )

    rev = by_name.get("olist_order_reviews_dataset.csv")
    if rev:
        u = rev["uniqueness"].get("order_id_as_key", {})
        if not u.get("is_unique"):
            flags.append(
                {
                    "severity": "medium",
                    "file": "olist_order_reviews_dataset.csv",
                    "issue": "Multiple review rows per order_id",
                    "evidence": u,
                }
            )
        detail = rev["uniqueness"].get("review_id_duplicate_detail", {})
        if detail.get("review_ids_spanning_multiple_order_ids", 0) > 0:
            flags.append(
                {
                    "severity": "high",
                    "file": "olist_order_reviews_dataset.csv",
                    "issue": "Some duplicate review_id values span multiple distinct order_id values",
                    "evidence": detail,
                }
            )

    # Orphan-looking keys from coverage
    for c in coverage:
        if c.get("orphans", 0) <= 0:
            continue
        col = c.get("column") or c.get("column_mapping")
        if c["link_type"] == "exact_column_name":
            flags.append(
                {
                    "severity": "medium",
                    "file": c["child_file"],
                    "issue": (
                        f"Child values for `{col}` not found in parent "
                        f"`{c['parent_file']}` (coverage {c['coverage_pct']}%)"
                    ),
                    "evidence": {
                        "orphans": c["orphans"],
                        "child_distinct": c["child_distinct"],
                        "coverage_pct": c["coverage_pct"],
                        "orphan_samples": c.get("orphan_samples", []),
                        "link_type": c["link_type"],
                    },
                }
            )
        elif c["link_type"] == "exact_column_name_parent_not_in_child":
            flags.append(
                {
                    "severity": "info",
                    "file": c["parent_file"],
                    "issue": (
                        f"Parent `{col}` values in `{c['parent_file']}` have no match in "
                        f"`{c['child_file']}` ({c['orphans']} distinct; "
                        f"parent→child coverage {c['coverage_pct']}%)"
                    ),
                    "evidence": {
                        "parent_keys_missing_from_child": c["orphans"],
                        "parent_distinct": c["child_distinct"],
                        "coverage_pct": c["coverage_pct"],
                        "samples": c.get("orphan_samples", []),
                        "link_type": c["link_type"],
                    },
                }
            )
        elif c["link_type"] == "provisional_zip_prefix_name_link":
            flags.append(
                {
                    "severity": "info",
                    "file": c["child_file"],
                    "issue": (
                        f"Provisional zip-prefix values for `{col}` not found in "
                        f"`{c['parent_file']}` (coverage {c['coverage_pct']}%)"
                    ),
                    "evidence": {
                        "orphans": c["orphans"],
                        "child_distinct": c["child_distinct"],
                        "coverage_pct": c["coverage_pct"],
                        "orphan_samples": c.get("orphan_samples", []),
                        "link_type": c["link_type"],
                    },
                }
            )

    # Any nulls on timestamps / key-ish / category columns
    for p in profiles:
        for col in p["column_profiles"]:
            if col["null_count"] > 0 and (
                TIMESTAMP_HINTS.search(col["name"])
                or col["name"].endswith("_id")
                or "category" in col["name"]
            ):
                flags.append(
                    {
                        "severity": "info",
                        "file": p["filename"],
                        "issue": f"Nullable/empty values in `{col['name']}` "
                        f"({col['null_count']} / {p['row_count']}, "
                        f"{round(col['null_rate']*100, 2)}%)",
                        "evidence": {
                            "null_count": col["null_count"],
                            "null_rate": col["null_rate"],
                        },
                    }
                )

    # Extra review_id spanning multiple orders (if detectable from uniqueness notes)
    rev = by_name.get("olist_order_reviews_dataset.csv")
    if rev:
        # Reinforced in quality_flags via a lightweight re-check using stored uniqueness
        ru = rev["uniqueness"].get("review_id", {})
        if ru and not ru.get("is_unique"):
            # already flagged; add note that duplicates may span orders (checked in script notes)
            pass

    return flags


def fmt_pct(rate: float) -> str:
    return f"{rate * 100:.4f}%".rstrip("0").rstrip(".") + ("%" if False else "")


def to_markdown(profiles: list[dict], coverage: list[dict], flags: list[dict]) -> str:
    lines = []
    lines.append("# Olist raw data profile (Phase 1)")
    lines.append("")
    lines.append(
        "**Ground truth:** files in `data/raw/`. "
        "Dtypes are provisional pandas inferences from sampling/full read. "
        "No columns, joins, or metrics invented beyond shared column names "
        "(plus provisional zip-prefix name links)."
    )
    lines.append("")
    lines.append("## 1. Inventory")
    lines.append("")
    lines.append("| File | Size (bytes) | Rows (excl. header) | Columns |")
    lines.append("|------|-------------:|--------------------:|--------:|")
    for p in profiles:
        lines.append(
            f"| `{p['filename']}` | {p['size_bytes']:,} | {p['row_count']:,} | {p['column_count']} |"
        )
    lines.append("")

    lines.append("## 2. Per-file profiles")
    lines.append("")

    for p in profiles:
        lines.append(f"### `{p['filename']}`")
        lines.append("")
        lines.append(
            f"- Size: **{p['size_bytes']:,}** bytes | "
            f"Rows: **{p['row_count']:,}** | "
            f"Columns: **{p['column_count']}** | "
            f"Full-row duplicates: **{p['full_duplicate_rows']:,}**"
        )
        lines.append("")
        lines.append(
            "| # | Column | Inferred dtype (provisional) | pandas dtype | "
            "Null/empty | Null rate | Distinct |"
        )
        lines.append(
            "|---|--------|------------------------------|--------------|"
            "-----------:|----------:|---------:|"
        )
        for i, c in enumerate(p["column_profiles"], 1):
            lines.append(
                f"| {i} | `{c['name']}` | {c['inferred_dtype']} | `{c['pandas_dtype']}` | "
                f"{c['null_count']:,} | {c['null_rate']*100:.4f}% | {c['nunique']:,} |"
            )
        lines.append("")
        lines.append("**Column order (exact):** " + ", ".join(f"`{c}`" for c in p["columns"]))
        lines.append("")

        # Uniqueness
        lines.append("#### Primary-key candidacy / uniqueness")
        lines.append("")
        lines.append("| Key | Unique count | Row count | Is unique? | Notes |")
        lines.append("|-----|-------------:|----------:|:----------:|-------|")
        for key, u in p["uniqueness"].items():
            notes = []
            for k2, v2 in u.items():
                if k2 not in ("unique_count", "row_count", "is_unique", "nulls", "duplicate_rows"):
                    notes.append(f"{k2}={v2}")
            if u.get("nulls"):
                notes.append(f"nulls={u['nulls']}")
            if u.get("duplicate_rows") not in (None, 0):
                notes.append(f"dup_rows={u['duplicate_rows']}")
            lines.append(
                f"| `{key}` | {u.get('unique_count', u.get('unique_prefixes', '—'))} | "
                f"{u.get('row_count', '—')} | "
                f"{'yes' if u.get('is_unique') else ('n/a' if 'is_unique' not in u else 'no')} | "
                f"{'; '.join(notes) if notes else '—'} |"
            )
        lines.append("")

        # Timestamps
        ts_cols = [c for c in p["column_profiles"] if "timestamp" in c]
        if ts_cols:
            lines.append("#### Timestamp columns")
            lines.append("")
            lines.append(
                "| Column | Min (parsed) | Max (parsed) | Parseable | Unparseable (non-null) |"
            )
            lines.append(
                "|--------|--------------|--------------|----------:|-----------------------:|"
            )
            for c in ts_cols:
                t = c["timestamp"]
                lines.append(
                    f"| `{c['name']}` | {t['min']} | {t['max']} | "
                    f"{t['parseable']:,} | {t['unparseable_non_null']:,} |"
                )
            lines.append("")

        # Categoricals
        cat_cols = [c for c in p["column_profiles"] if "top_values" in c]
        if cat_cols:
            lines.append("#### Categorical-looking columns (top ≤20)")
            lines.append("")
            for c in cat_cols:
                lines.append(
                    f"**`{c['name']}`** — distinct: {c.get('distinct_count', c['nunique'])}"
                )
                lines.append("")
                lines.append("| Value | Count |")
                lines.append("|-------|------:|")
                for tv in c["top_values"]:
                    val = tv["value"] if tv["value"] is not None else "(null/empty)"
                    lines.append(f"| `{val}` | {tv['count']:,} |")
                lines.append("")

        # ID samples
        id_cols = [c for c in p["column_profiles"] if "id_samples" in c]
        if id_cols:
            lines.append("#### ID / key format samples (truncated, 2–3 values)")
            lines.append("")
            for c in id_cols:
                samples = ", ".join(f"`{s}`" for s in c["id_samples"])
                lines.append(f"- `{c['name']}`: {samples}")
            lines.append("")

    lines.append("## 3. Cross-file key coverage")
    lines.append("")
    lines.append(
        "Only exact shared column names, plus provisional zip-prefix name links "
        "(`customer_zip_code_prefix` / `seller_zip_code_prefix` ↔ "
        "`geolocation_zip_code_prefix`). "
        "`exact_column_name` coverage = % of distinct **child** values found in parent. "
        "`exact_column_name_parent_not_in_child` coverage = % of distinct **parent** "
        "values found in child (orphans = parent keys with no child match)."
    )
    lines.append("")
    lines.append(
        "| Link type | Mapping | Parent | Child | Distinct (from-side) | "
        "Matched | Unmatched | Coverage % |"
    )
    lines.append(
        "|-----------|---------|--------|-------|---------------------:|"
        "--------:|----------:|-----------:|"
    )
    for c in coverage:
        mapping = c.get("column") or c.get("column_mapping")
        lines.append(
            f"| {c['link_type']} | `{mapping}` | `{c['parent_file']}` | "
            f"`{c['child_file']}` | {c['child_distinct']:,} | {c['in_parent']:,} | "
            f"{c['orphans']:,} | {c['coverage_pct']} |"
        )
    lines.append("")

    # Detail orphan samples for non-100%
    orphans = [c for c in coverage if c.get("orphans", 0) > 0]
    if orphans:
        lines.append("### Unmatched key samples (up to 5)")
        lines.append("")
        for c in orphans:
            mapping = c.get("column") or c.get("column_mapping")
            lines.append(
                f"- [{c['link_type']}] `{c['child_file']}` ↔ `{c['parent_file']}` "
                f"(`{mapping}`): {c.get('orphan_samples', [])}"
            )
        lines.append("")

    lines.append("## 4. Data-quality flags")
    lines.append("")
    if not flags:
        lines.append("No flags raised.")
    else:
        lines.append("| Severity | File | Issue | Evidence (summary) |")
        lines.append("|----------|------|-------|--------------------|")
        for f in flags:
            ev = json.dumps(f["evidence"], ensure_ascii=False)
            if len(ev) > 180:
                ev = ev[:177] + "..."
            lines.append(
                f"| {f['severity']} | `{f['file']}` | {f['issue']} | `{ev}` |"
            )
    lines.append("")

    lines.append("## 5. Assumptions")
    lines.append("")
    lines.append(
        "- Null/empty = pandas NA **or** blank/whitespace-only string after strip."
    )
    lines.append(
        "- Inferred dtypes are provisional from pandas `read_csv` + timestamp parse attempts "
        "on name-hinted columns; not a warehouse type contract."
    )
    lines.append(
        "- Parent file for exact shared columns (when present): "
        "`order_id`→orders, `customer_id`→customers, `product_id`→products, "
        "`seller_id`→sellers, `product_category_name`→category translation; "
        "otherwise lexicographic. Reverse parent∉child gaps are also reported."
    )
    lines.append(
        "- Zip-prefix links are **provisional name-based** candidates only "
        "(not confirmed FKs); geolocation is multi-row per prefix."
    )
    lines.append(
        "- Categorical top-N capped at 20; review comment bodies not dumped."
    )
    lines.append(
        "- Secondary schema scrape used only for orientation; all numbers come from CSV files."
    )
    lines.append("")
    lines.append("## 6. Artifacts")
    lines.append("")
    lines.append(f"- Report: `{OUT_MD.relative_to(ROOT).as_posix()}`")
    lines.append(f"- Machine-readable: `{OUT_JSON.relative_to(ROOT).as_posix()}`")
    lines.append(f"- Script: `scripts/profile_olist_csvs.py`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    profiles = []
    for name in FILES:
        path = RAW / name
        if not path.exists():
            raise FileNotFoundError(path)
        print(f"Profiling {name} ...")
        profiles.append(profile_file(path))

    # Strip helper keys
    for p in profiles:
        p.pop("_df_columns", None)

    print("Cross-file coverage ...")
    coverage = cross_file_coverage(profiles)
    flags = quality_flags(profiles, coverage)

    payload = {
        "profiles": profiles,
        "coverage": coverage,
        "quality_flags": flags,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    OUT_MD.write_text(to_markdown(profiles, coverage, flags), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
