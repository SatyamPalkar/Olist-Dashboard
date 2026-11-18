"""Orchestrate extract → transform → load for the Olist raw ingestion pipeline."""

from __future__ import annotations

import argparse
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.engine import Engine

from etl.config import Settings, get_settings
from etl.extract import extract_dataset, list_available_sources
from etl.load import (
    apply_schema,
    create_db_engine,
    finish_ingestion_run,
    load_dataset,
    reconcile_counts,
    record_failures,
    start_ingestion_run,
)
from etl.logger import log_extra, setup_logger
from etl.transform import transform_dataset, transformation_rules
from etl.validators import validate_file_available

logger = setup_logger()


@dataclass
class DatasetResult:
    """Per-dataset pipeline outcome."""

    dataset: str
    source_file: str
    target_table: str
    rows_extracted: int = 0
    rows_transformed: int = 0
    rows_loaded: int = 0
    rows_failed: int = 0
    duration_seconds: float = 0.0
    reconciled: bool = False
    issues: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Full pipeline execution summary."""

    run_id: str
    status: str
    datasets: list[DatasetResult] = field(default_factory=list)
    reconciliation: dict[str, dict[str, Any]] = field(default_factory=dict)
    duration_seconds: float = 0.0

    @property
    def all_reconciled(self) -> bool:
        return bool(self.reconciliation) and all(
            item["reconciled"] for item in self.reconciliation.values()
        )


def run_dataset(
    engine: Engine,
    settings: Settings,
    dataset_name: str,
    run_id: uuid.UUID,
) -> DatasetResult:
    """Run ETL for a single configured dataset."""
    config = settings.datasets[dataset_name]
    started = time.perf_counter()
    result = DatasetResult(
        dataset=dataset_name,
        source_file=config.source_file,
        target_table=config.target_table,
    )

    df, metadata = extract_dataset(settings, dataset_name, config)
    result.rows_extracted = len(df)

    transformed, report = transform_dataset(df, dataset_name, config)
    result.rows_transformed = len(transformed)
    result.rows_failed = report.missing_required_id_count
    result.issues = list(report.issues)

    # Quarantine missing-id rows for audit while still loading them into raw
    if report.missing_required_id_count:
        missing = transformed[
            transformed["_quality_flags"].apply(
                lambda flags: isinstance(flags, list) and "missing_required_id" in flags
            )
        ]
        failures = []
        for _, row in missing.iterrows():
            payload = {
                c: row[c]
                for c in transformed.columns
                if not str(c).startswith("_")
            }
            failures.append(
                {
                    "row_number": int(row["_row_number"]) if "_row_number" in row else None,
                    "error_type": "missing_required_id",
                    "error_message": "Required identifier missing; row retained in raw load",
                    "raw_payload": payload,
                }
            )
        record_failures(
            engine,
            run_id,
            config.source_file,
            config.target_table,
            failures,
        )

    duration = time.perf_counter() - started
    loaded = load_dataset(
        engine,
        settings,
        dataset_name,
        config,
        transformed,
        run_id,
        metadata,
        report,
        duration,
        truncate=True,
    )
    result.rows_loaded = loaded
    result.duration_seconds = duration
    result.reconciled = loaded == result.rows_extracted
    return result


def run_pipeline(
    settings: Settings | None = None,
    dataset_names: list[str] | None = None,
    *,
    apply_ddl: bool = True,
) -> PipelineResult:
    """
    Execute the full (or selected) Olist raw ingestion pipeline.

    Idempotent: each dataset TRUNCATEs its raw table then reloads, so repeated
    execution converges to the same destination counts.
    """
    settings = settings or get_settings()
    setup_logger(log_dir=settings.log_dir)
    pipeline_started = time.perf_counter()
    run_id = uuid.uuid4()

    logger.info(
        "Starting Olist ETL run_id=%s config=%s",
        run_id,
        settings.as_safe_dict(),
        extra=log_extra(run_id=str(run_id)),
    )
    logger.info("Transformation rules: %s", transformation_rules())

    availability = list_available_sources(settings)
    selected = dataset_names or list(settings.datasets.keys())
    for name in selected:
        if name not in settings.datasets:
            raise KeyError(f"Unknown dataset: {name}")
        path = settings.data_dir / settings.datasets[name].source_file
        validate_file_available(path)
        if not availability.get(name, False):
            raise FileNotFoundError(f"Dataset unavailable: {name} -> {path}")

    engine = create_db_engine(settings)
    status = "success"
    results: list[DatasetResult] = []
    expected_counts: dict[str, int] = {}
    reconciliation: dict[str, dict[str, Any]] = {}

    try:
        if apply_ddl:
            apply_schema(engine, settings.schema_sql)
        start_ingestion_run(engine, settings, run_id)

        for name in selected:
            logger.info("Processing dataset=%s", name, extra=log_extra(run_id=str(run_id), dataset=name))
            ds_result = run_dataset(engine, settings, name, run_id)
            results.append(ds_result)
            expected_counts[ds_result.target_table] = ds_result.rows_extracted
            if not ds_result.reconciled:
                status = "success_with_warnings"

        reconciliation = reconcile_counts(engine, settings, expected_counts)
        if not all(item["reconciled"] for item in reconciliation.values()):
            status = "failed"
            finish_ingestion_run(
                engine,
                run_id,
                status,
                notes="Source/destination counts did not reconcile",
            )
        else:
            finish_ingestion_run(engine, run_id, status, notes="All datasets reconciled")

    except Exception as exc:
        status = "failed"
        logger.exception(
            "Pipeline failed: %s",
            exc,
            extra=log_extra(run_id=str(run_id), error_type=type(exc).__name__),
        )
        try:
            finish_ingestion_run(engine, run_id, status, notes=str(exc))
        except Exception:
            logger.exception("Unable to finalise ingestion run status")
        raise
    finally:
        engine.dispose()

    duration = time.perf_counter() - pipeline_started
    pipeline_result = PipelineResult(
        run_id=str(run_id),
        status=status,
        datasets=results,
        reconciliation=reconciliation if status != "failed" or expected_counts else {},
        duration_seconds=duration,
    )

    # Ensure reconciliation is set even on partial success
    if not pipeline_result.reconciliation and expected_counts:
        # engine already disposed; reconciliation already computed above on success path
        pass

    logger.info(
        "Pipeline finished status=%s duration=%.2fs reconciled=%s",
        pipeline_result.status,
        pipeline_result.duration_seconds,
        pipeline_result.all_reconciled,
        extra=log_extra(
            run_id=pipeline_result.run_id,
            duration_seconds=pipeline_result.duration_seconds,
            reconciled=pipeline_result.all_reconciled,
        ),
    )
    for ds in results:
        logger.info(
            "Summary dataset=%s extracted=%s transformed=%s loaded=%s failed=%s reconciled=%s",
            ds.dataset,
            ds.rows_extracted,
            ds.rows_transformed,
            ds.rows_loaded,
            ds.rows_failed,
            ds.reconciled,
            extra=log_extra(
                run_id=pipeline_result.run_id,
                dataset=ds.dataset,
                source_file=ds.source_file,
                target_table=ds.target_table,
                rows_extracted=ds.rows_extracted,
                rows_transformed=ds.rows_transformed,
                rows_loaded=ds.rows_loaded,
                rows_failed=ds.rows_failed,
                duration_seconds=ds.duration_seconds,
                reconciled=ds.reconciled,
            ),
        )
    return pipeline_result


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Olist retail BI raw ETL pipeline")
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=None,
        help="Optional subset of dataset keys (default: all)",
    )
    parser.add_argument(
        "--skip-ddl",
        action="store_true",
        help="Do not apply sql/01_raw_schema.sql before loading",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Override OLIST_DATA_DIR",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.data_dir:
        settings.data_dir = __import__("pathlib").Path(args.data_dir)

    result = run_pipeline(
        settings=settings,
        dataset_names=args.datasets,
        apply_ddl=not args.skip_ddl,
    )
    print("\nReconciliation:")
    for table, info in result.reconciliation.items():
        flag = "OK" if info["reconciled"] else "MISMATCH"
        print(f"  [{flag}] {table}: expected={info['expected']} actual={info['actual']}")
    return 0 if result.status.startswith("success") and result.all_reconciled else 1


if __name__ == "__main__":
    raise SystemExit(main())
