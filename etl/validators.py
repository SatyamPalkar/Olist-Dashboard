"""Data quality validation helpers for Olist ETL."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from etl.config import DatasetConfig


@dataclass
class ValidationReport:
    """Outcome of validating a transformed frame before load."""

    dataset: str
    source_file: str
    row_count: int
    null_counts: dict[str, int] = field(default_factory=dict)
    duplicate_row_count: int = 0
    duplicate_key_count: int = 0
    missing_required_id_count: int = 0
    invalid_type_counts: dict[str, int] = field(default_factory=dict)
    quality_flag_counts: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "source_file": self.source_file,
            "row_count": self.row_count,
            "null_counts": self.null_counts,
            "duplicate_row_count": self.duplicate_row_count,
            "duplicate_key_count": self.duplicate_key_count,
            "missing_required_id_count": self.missing_required_id_count,
            "invalid_type_counts": self.invalid_type_counts,
            "quality_flag_counts": self.quality_flag_counts,
            "issues": self.issues,
        }


def validate_file_available(path: Path) -> None:
    """Raise FileNotFoundError if the CSV is missing or empty."""
    if not path.exists():
        raise FileNotFoundError(f"Source CSV not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Source path is not a file: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Source CSV is empty: {path}")


def validate_schema(df: pd.DataFrame, config: DatasetConfig) -> list[str]:
    """
    Ensure expected source columns are present (before rename).

    Returns a list of human-readable issues; does not raise for extras.
    """
    issues: list[str] = []
    source_required = set(config.required_columns)
    # Required columns may already use renamed names; map back to source names.
    reverse_renames = {v: k for k, v in config.column_renames.items()}
    expected_source_cols = {
        reverse_renames.get(col, col) for col in source_required
    } | set(config.column_renames.keys())

    # Also expect all configured logical columns (as source names)
    logical = (
        set(config.text_columns)
        | set(config.int_columns)
        | set(config.float_columns)
        | set(config.numeric_columns)
        | set(config.date_columns)
        | set(config.primary_keys)
        | set(config.required_columns)
    )
    for col in logical:
        source_name = reverse_renames.get(col, col)
        if source_name not in df.columns and col not in df.columns:
            # After rename check both
            if source_name not in expected_source_cols or source_name not in df.columns:
                if source_name not in df.columns and col not in df.columns:
                    issues.append(f"Missing expected column: {source_name}")

    # Simpler: check required source columns exist
    for col in config.required_columns:
        source_name = reverse_renames.get(col, col)
        if source_name not in df.columns and col not in df.columns:
            issues.append(f"Missing required column: {source_name}")

    for source_col in config.column_renames:
        if source_col not in df.columns:
            issues.append(f"Missing source column for rename: {source_col}")

    return issues


def validate_identifiers(
    df: pd.DataFrame, config: DatasetConfig
) -> tuple[pd.Series, int]:
    """
    Return a boolean mask of rows with missing required identifiers,
    and the count of such rows.
    """
    if not config.required_columns:
        return pd.Series(False, index=df.index), 0
    mask = pd.Series(False, index=df.index)
    for col in config.required_columns:
        if col in df.columns:
            mask = mask | df[col].isna() | (df[col].astype(str).str.strip() == "")
    return mask, int(mask.sum())


def detect_duplicates(
    df: pd.DataFrame, config: DatasetConfig
) -> tuple[pd.Series, int, int]:
    """
    Detect full-row duplicates and primary-key duplicates.

    Returns (is_duplicate_mask, full_dup_count, key_dup_count).
    Duplicate rows are flagged, not dropped.
    """
    business_cols = [
        c
        for c in df.columns
        if not c.startswith("_")
    ]
    full_dup = df.duplicated(subset=business_cols, keep="first")
    key_dup = pd.Series(False, index=df.index)
    if config.primary_keys and all(k in df.columns for k in config.primary_keys):
        key_dup = df.duplicated(subset=list(config.primary_keys), keep="first")
    is_dup = full_dup | key_dup
    return is_dup, int(full_dup.sum()), int(key_dup.sum())


def profile_nulls(df: pd.DataFrame) -> dict[str, int]:
    """Return non-zero null counts for business columns."""
    business = [c for c in df.columns if not c.startswith("_")]
    counts = df[business].isna().sum()
    return {col: int(counts[col]) for col in business if counts[col] > 0}


def build_validation_report(
    df: pd.DataFrame,
    dataset: str,
    config: DatasetConfig,
) -> ValidationReport:
    """Assemble a validation report without mutating the frame."""
    _, full_dups, key_dups = detect_duplicates(df, config)
    _, missing_ids = validate_identifiers(df, config)
    nulls = profile_nulls(df)

    flag_counts: dict[str, int] = {}
    if "_quality_flags" in df.columns:
        exploded = df["_quality_flags"].dropna().explode()
        if not exploded.empty:
            flag_counts = exploded.value_counts().astype(int).to_dict()

    issues: list[str] = []
    if full_dups:
        issues.append(f"{full_dups} full-row duplicate(s) flagged")
    if key_dups:
        issues.append(f"{key_dups} primary-key duplicate(s) flagged")
    if missing_ids:
        issues.append(f"{missing_ids} row(s) missing required identifiers")
    if nulls:
        issues.append(f"Nulls present in: {', '.join(nulls)}")

    return ValidationReport(
        dataset=dataset,
        source_file=config.source_file,
        row_count=len(df),
        null_counts=nulls,
        duplicate_row_count=full_dups,
        duplicate_key_count=key_dups,
        missing_required_id_count=missing_ids,
        quality_flag_counts=flag_counts,
        issues=issues,
    )
