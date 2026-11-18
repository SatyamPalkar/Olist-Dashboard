"""Transformation rules for Olist source data prior to raw-schema load."""

from __future__ import annotations

from typing import Any

import pandas as pd

from etl.config import DatasetConfig
from etl.logger import log_extra, setup_logger
from etl.validators import (
    ValidationReport,
    build_validation_report,
    detect_duplicates,
    validate_identifiers,
    validate_schema,
)

logger = setup_logger()

# Documented transformation rules applied by this module.
TRANSFORMATION_RULES: list[str] = [
    "Strip leading/trailing whitespace from all string cells.",
    "Standardise column names to snake_case (sources already mostly compliant).",
    "Rename known source typos: product_name_lenght→product_name_length, "
    "product_description_lenght→product_description_length.",
    "Cast zip-code prefixes to zero-padded 5-character text.",
    "Parse configured timestamp columns with pandas to_datetime (UTC-naive).",
    "Convert integer / float / numeric columns; unparseable values become null "
    "and are flagged via _quality_flags (rows are retained).",
    "Flag full-row and primary-key duplicates with _is_duplicate=True; never drop.",
    "Flag missing required identifiers; never drop those rows.",
    "Preserve _source_file and _row_number for lineage.",
    "Do not compute business KPIs in this layer.",
]


def standardise_column_names(df: pd.DataFrame, config: DatasetConfig) -> pd.DataFrame:
    """Lowercase/strip headers and apply configured renames."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    if config.column_renames:
        out = out.rename(columns=config.column_renames)
    return out


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].apply(
                lambda v: v.strip() if isinstance(v, str) else v
            )
    return out


def _pad_zip(series: pd.Series) -> pd.Series:
    """Normalise Brazilian zip prefixes to 5-char zero-padded text."""

    def _one(value: Any) -> Any:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return pd.NA
        text = str(value).strip()
        if text == "" or text.lower() in {"nan", "none", "<na>"}:
            return pd.NA
        # Source sometimes has fewer than 5 digits
        if text.isdigit():
            return text.zfill(5)
        return text

    return series.map(_one)


def convert_types(df: pd.DataFrame, config: DatasetConfig) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Apply type conversions; invalid values become null and are counted.

    Rows are never discarded for type issues.
    """
    out = df.copy()
    invalid_counts: dict[str, int] = {}

    zip_cols = [
        c
        for c in (
            "customer_zip_code_prefix",
            "seller_zip_code_prefix",
            "geolocation_zip_code_prefix",
        )
        if c in out.columns
    ]
    for col in zip_cols:
        out[col] = _pad_zip(out[col])

    for col in config.date_columns:
        if col not in out.columns:
            continue
        parsed = pd.to_datetime(out[col], errors="coerce")
        invalid = out[col].notna() & parsed.isna()
        invalid_counts[col] = int(invalid.sum())
        out[col] = parsed

    for col in config.int_columns:
        if col not in out.columns:
            continue
        numeric = pd.to_numeric(out[col], errors="coerce")
        invalid = out[col].notna() & numeric.isna()
        invalid_counts[col] = int(invalid.sum())
        # Use pandas nullable Int64
        out[col] = numeric.round().astype("Int64")

    for col in (*config.float_columns, *config.numeric_columns):
        if col not in out.columns:
            continue
        numeric = pd.to_numeric(out[col], errors="coerce")
        invalid = out[col].notna() & numeric.isna()
        invalid_counts[col] = int(invalid.sum())
        out[col] = numeric

    for col in config.text_columns:
        if col not in out.columns or col in zip_cols:
            continue
        out[col] = out[col].astype("string")

    return out, {k: v for k, v in invalid_counts.items() if v > 0}


def apply_quality_flags(
    df: pd.DataFrame,
    config: DatasetConfig,
    invalid_type_counts: dict[str, int],
) -> pd.DataFrame:
    """Attach _is_duplicate and _quality_flags without dropping rows."""
    out = df.copy()
    flags: list[list[str]] = [[] for _ in range(len(out))]

    is_dup, _, _ = detect_duplicates(out, config)
    out["_is_duplicate"] = is_dup.fillna(False).astype(bool)
    for idx in out.index[out["_is_duplicate"]]:
        flags[out.index.get_loc(idx)].append("duplicate_row")

    missing_mask, _ = validate_identifiers(out, config)
    for idx in out.index[missing_mask]:
        flags[out.index.get_loc(idx)].append("missing_required_id")

    # Flag rows where type coercion nullified a previously non-null value
    for col, count in invalid_type_counts.items():
        if count == 0 or col not in out.columns:
            continue
        # Re-detect: original non-empty string that became null is hard after conversion;
        # mark columns with known invalid counts via a column-level note on nulls that
        # are unexpected for non-nullable semantics — use a lighter approach:
        # attach flag when value is null and column had invalid conversions overall.
        # Safer: store type_invalid_<col> only on rows that are null after conversion
        # when the source had a value — we track via a side channel below.
        _ = count  # documented in report; per-row flags set in transform_dataset

    out["_quality_flags"] = flags
    return out


def _flag_type_invalids(
    original: pd.DataFrame,
    converted: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Add per-row type_invalid_* flags by comparing pre/post conversion nulls."""
    out = converted.copy()
    flags = list(out["_quality_flags"])
    for col in columns:
        if col not in original.columns or col not in out.columns:
            continue
        was_present = original[col].notna() & (original[col].astype(str).str.strip() != "")
        now_null = out[col].isna()
        bad = was_present & now_null
        for i, is_bad in enumerate(bad.tolist()):
            if is_bad:
                flags[i] = list(flags[i]) + [f"type_invalid:{col}"]
    out["_quality_flags"] = flags
    return out


def transform_dataset(
    df: pd.DataFrame,
    dataset_name: str,
    config: DatasetConfig,
) -> tuple[pd.DataFrame, ValidationReport]:
    """
    Run the full transformation suite for one dataset.

    Invalid records are flagged and retained — never silently discarded.
    """
    schema_issues = validate_schema(df, config)
    if schema_issues:
        logger.warning(
            "Schema issues for %s: %s",
            dataset_name,
            schema_issues,
            extra=log_extra(dataset=dataset_name, source_file=config.source_file),
        )

    # Preserve lineage columns through renames
    lineage_cols = [c for c in ("_row_number", "_source_file") if c in df.columns]
    lineage = df[lineage_cols].copy() if lineage_cols else pd.DataFrame(index=df.index)

    working = df.drop(columns=lineage_cols, errors="ignore")
    working = standardise_column_names(working, config)
    working = _strip_strings(working)
    pre_type = working.copy()
    working, invalid_types = convert_types(working, config)
    working = apply_quality_flags(working, config, invalid_types)
    working = _flag_type_invalids(
        pre_type,
        working,
        list(config.date_columns)
        + list(config.int_columns)
        + list(config.float_columns)
        + list(config.numeric_columns),
    )

    for col in lineage_cols:
        working[col] = lineage[col].values

    report = build_validation_report(working, dataset_name, config)
    report.invalid_type_counts = invalid_types
    report.issues.extend(schema_issues)

    logger.info(
        "Transformed %s rows for %s (dupes=%s, missing_ids=%s)",
        len(working),
        dataset_name,
        report.duplicate_row_count,
        report.missing_required_id_count,
        extra=log_extra(
            dataset=dataset_name,
            source_file=config.source_file,
            rows_transformed=len(working),
            rows_failed=report.missing_required_id_count,
        ),
    )
    return working, report


def transformation_rules() -> list[str]:
    """Return the documented transformation rule list."""
    return list(TRANSFORMATION_RULES)
