"""Load immutable Olist CSVs from data/raw without modifying them."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from tests.helpers.contracts import EXPECTED_COLUMNS, RAW_DIR, RAW_FILES


def raw_path(entity: str) -> Path:
    if entity not in RAW_FILES:
        raise KeyError(f"Unknown entity '{entity}'. Known: {sorted(RAW_FILES)}")
    return RAW_DIR / RAW_FILES[entity]


def assert_raw_available(entity: str) -> Path:
    path = raw_path(entity)
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing required raw file: {path}. See docs/data_acquisition.md."
        )
    if path.stat().st_size == 0:
        raise ValueError(f"Raw file is empty: {path}")
    return path


@lru_cache(maxsize=None)
def load_raw(entity: str) -> pd.DataFrame:
    """Read a full raw CSV. Cached for the process lifetime."""
    path = assert_raw_available(entity)
    df = pd.read_csv(path, low_memory=False)
    expected = EXPECTED_COLUMNS[entity]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")
    return df


def load_all_raw() -> dict[str, pd.DataFrame]:
    return {entity: load_raw(entity) for entity in RAW_FILES}


def null_report(df: pd.DataFrame) -> dict[str, int]:
    nulls = df.isna().sum()
    return {col: int(nulls[col]) for col in df.columns if nulls[col] > 0}


def duplicate_key_count(df: pd.DataFrame, keys: list[str]) -> int:
    return int(df.duplicated(subset=keys, keep=False).sum())
