"""PostgreSQL load helpers: schema bootstrap, batch insert, reconciliation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from etl.config import DatasetConfig, Settings
from etl.extract import SourceFileMetadata
from etl.logger import log_extra, setup_logger
from etl.validators import ValidationReport

logger = setup_logger()


def create_db_engine(settings: Settings) -> Engine:
    """Create a pooled SQLAlchemy engine from settings."""
    return create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_size,
        pool_pre_ping=True,
        future=True,
    )


def apply_schema(engine: Engine, schema_sql_path: Path) -> None:
    """Execute the raw/etl schema DDL (idempotent CREATE IF NOT EXISTS)."""
    ddl = schema_sql_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(ddl))
    logger.info("Applied schema DDL from %s", schema_sql_path)


def start_ingestion_run(
    engine: Engine,
    settings: Settings,
    run_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Insert a running row into etl.ingestion_runs and return the run id."""
    rid = run_id or uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO etl.ingestion_runs
                    (run_id, pipeline_name, started_at, status, source_directory)
                VALUES
                    (:run_id, :pipeline_name, :started_at, 'running', :source_directory)
                """
            ),
            {
                "run_id": str(rid),
                "pipeline_name": "olist_raw_ingestion",
                "started_at": datetime.now(timezone.utc),
                "source_directory": str(settings.data_dir),
            },
        )
    return rid


def finish_ingestion_run(
    engine: Engine,
    run_id: uuid.UUID,
    status: str,
    notes: str | None = None,
) -> None:
    """Mark an ingestion run finished."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE etl.ingestion_runs
                SET finished_at = :finished_at,
                    status = :status,
                    notes = :notes
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": str(run_id),
                "finished_at": datetime.now(timezone.utc),
                "status": status,
                "notes": notes,
            },
        )


def _prepare_frame_for_load(
    df: pd.DataFrame,
    run_id: uuid.UUID,
    ingested_at: datetime,
) -> pd.DataFrame:
    """Add run metadata and normalise list/array columns for psycopg."""
    out = df.copy()
    out["_run_id"] = str(run_id)
    out["_ingested_at"] = ingested_at
    if "_quality_flags" in out.columns:
        out["_quality_flags"] = out["_quality_flags"].apply(
            lambda flags: list(flags) if isinstance(flags, (list, tuple)) else []
        )
    if "_is_duplicate" not in out.columns:
        out["_is_duplicate"] = False
    # Convert pandas NA to None for DB adapter
    return out.where(pd.notnull(out), None)


def _clean_value(value: Any) -> Any:
    """Normalise pandas/numpy values for psycopg binding."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()
    if isinstance(value, list):
        return json.dumps(value)
    if hasattr(value, "item") and not isinstance(value, (bytes, str)):
        try:
            item = value.item()
            if isinstance(item, float) and pd.isna(item):
                return None
            return item
        except (ValueError, AttributeError):
            return value
    return value


def _frame_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to plain dict records suitable for executemany."""
    records: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        cleaned = {key: _clean_value(value) for key, value in row.items()}
        # quality flags stored as JSONB — ensure JSON text when list already encoded
        if "_quality_flags" in cleaned and isinstance(cleaned["_quality_flags"], str):
            pass  # already JSON
        elif "_quality_flags" in cleaned and cleaned["_quality_flags"] is None:
            cleaned["_quality_flags"] = "[]"
        records.append(cleaned)
    return records


def truncate_raw_table(engine: Engine, settings: Settings, table: str) -> None:
    """Truncate a raw table (idempotent full-refresh semantics)."""
    qualified = f"{settings.raw_schema}.{table}"
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {qualified}"))


def batch_insert(
    engine: Engine,
    settings: Settings,
    table: str,
    df: pd.DataFrame,
    batch_size: int | None = None,
) -> int:
    """
    Insert rows in batches inside a single transaction.

    Returns the number of rows inserted.
    """
    if df.empty:
        return 0

    size = batch_size or settings.batch_size
    run_value = (
        uuid.UUID(str(df["_run_id"].iloc[0]))
        if "_run_id" in df.columns and pd.notna(df["_run_id"].iloc[0])
        else uuid.uuid4()
    )
    ingested = (
        df["_ingested_at"].iloc[0]
        if "_ingested_at" in df.columns
        else datetime.now(timezone.utc)
    )
    prepared = _prepare_frame_for_load(df, run_value, ingested)

    columns = list(prepared.columns)
    col_list = ", ".join(columns)
    placeholders = ", ".join(
        f"CAST(:{c} AS jsonb)" if c == "_quality_flags" else f":{c}" for c in columns
    )
    qualified = f"{settings.raw_schema}.{table}"
    sql = text(f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})")

    total = 0
    try:
        with engine.begin() as conn:
            for start in range(0, len(prepared), size):
                chunk = prepared.iloc[start : start + size]
                records = _frame_to_records(chunk)
                conn.execute(sql, records)
                total += len(records)
    except SQLAlchemyError:
        logger.exception(
            "Database error inserting into %s",
            qualified,
            extra=log_extra(target_table=table, error_type="database_error"),
        )
        raise

    return total


def load_dataset(
    engine: Engine,
    settings: Settings,
    dataset_name: str,
    config: DatasetConfig,
    df: pd.DataFrame,
    run_id: uuid.UUID,
    metadata: SourceFileMetadata,
    report: ValidationReport,
    duration_seconds: float,
    *,
    truncate: bool = True,
) -> int:
    """
    Idempotently load a transformed dataset into raw.<table>.

    Full-refresh: TRUNCATE then batch INSERT in one transaction when truncate=True.
    """
    ingested_at = datetime.now(timezone.utc)
    working = df.copy()
    working["_run_id"] = str(run_id)
    working["_ingested_at"] = ingested_at

    # Ensure column order matches expected business + metadata columns
    meta_cols = [
        "_source_file",
        "_row_number",
        "_is_duplicate",
        "_quality_flags",
        "_ingested_at",
        "_run_id",
    ]
    business_cols = [c for c in working.columns if c not in meta_cols]
    working = working[business_cols + [c for c in meta_cols if c in working.columns]]

    qualified = f"{settings.raw_schema}.{config.target_table}"
    columns = list(working.columns)
    col_list = ", ".join(columns)
    placeholders = ", ".join(
        f"CAST(:{c} AS jsonb)" if c == "_quality_flags" else f":{c}" for c in columns
    )
    insert_sql = text(f"INSERT INTO {qualified} ({col_list}) VALUES ({placeholders})")
    size = settings.batch_size
    loaded = 0

    try:
        with engine.begin() as conn:
            if truncate:
                conn.execute(text(f"TRUNCATE TABLE {qualified}"))
            for start in range(0, len(working), size):
                chunk = working.iloc[start : start + size]
                records = _frame_to_records(chunk)
                conn.execute(insert_sql, records)
                loaded += len(records)

            conn.execute(
                text(
                    """
                    INSERT INTO etl.ingestion_file_stats (
                        run_id, source_file, target_table,
                        rows_extracted, rows_transformed, rows_loaded, rows_failed,
                        duplicate_rows, null_profile_json,
                        file_size_bytes, file_mtime, file_sha256, duration_seconds
                    ) VALUES (
                        :run_id, :source_file, :target_table,
                        :rows_extracted, :rows_transformed, :rows_loaded, :rows_failed,
                        :duplicate_rows, CAST(:null_profile_json AS jsonb),
                        :file_size_bytes, :file_mtime, :file_sha256, :duration_seconds
                    )
                    """
                ),
                {
                    "run_id": str(run_id),
                    "source_file": config.source_file,
                    "target_table": config.target_table,
                    "rows_extracted": report.row_count,
                    "rows_transformed": report.row_count,
                    "rows_loaded": loaded,
                    "rows_failed": report.missing_required_id_count,
                    "duplicate_rows": report.duplicate_row_count,
                    "null_profile_json": json.dumps(report.null_counts),
                    "file_size_bytes": metadata.size_bytes,
                    "file_mtime": metadata.mtime,
                    "file_sha256": metadata.sha256,
                    "duration_seconds": duration_seconds,
                },
            )
    except SQLAlchemyError:
        logger.exception(
            "Failed loading %s into %s",
            dataset_name,
            qualified,
            extra=log_extra(
                dataset=dataset_name,
                target_table=config.target_table,
                error_type="database_error",
            ),
        )
        raise

    reconciled = loaded == report.row_count
    logger.info(
        "Loaded %s rows into %s (reconciled=%s)",
        loaded,
        qualified,
        reconciled,
        extra=log_extra(
            dataset=dataset_name,
            source_file=config.source_file,
            target_table=config.target_table,
            rows_loaded=loaded,
            rows_extracted=report.row_count,
            reconciled=reconciled,
            duration_seconds=duration_seconds,
        ),
    )
    return loaded


def record_failures(
    engine: Engine,
    run_id: uuid.UUID,
    source_file: str,
    target_table: str,
    failures: Iterable[dict[str, Any]],
) -> int:
    """Persist quarantine / failure rows (never silently discarded)."""
    rows = list(failures)
    if not rows:
        return 0
    sql = text(
        """
        INSERT INTO raw.ingestion_failures
            (run_id, source_file, target_table, row_number, error_type, error_message, raw_payload)
        VALUES
            (:run_id, :source_file, :target_table, :row_number, :error_type, :error_message,
             CAST(:raw_payload AS jsonb))
        """
    )
    payloads = []
    for item in rows:
        payloads.append(
            {
                "run_id": str(run_id),
                "source_file": source_file,
                "target_table": target_table,
                "row_number": item.get("row_number"),
                "error_type": item.get("error_type", "unknown"),
                "error_message": item.get("error_message"),
                "raw_payload": json.dumps(item.get("raw_payload", {}), default=str),
            }
        )
    with engine.begin() as conn:
        conn.execute(sql, payloads)
    return len(payloads)


def count_table_rows(engine: Engine, settings: Settings, table: str) -> int:
    """Return COUNT(*) for a raw table."""
    qualified = f"{settings.raw_schema}.{table}"
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {qualified}"))
        return int(result.scalar_one())


def reconcile_counts(
    engine: Engine,
    settings: Settings,
    expected: dict[str, int],
) -> dict[str, dict[str, Any]]:
    """Compare expected extracted counts to destination table counts."""
    results: dict[str, dict[str, Any]] = {}
    for table, expected_count in expected.items():
        actual = count_table_rows(engine, settings, table)
        results[table] = {
            "expected": expected_count,
            "actual": actual,
            "reconciled": expected_count == actual,
        }
    return results
