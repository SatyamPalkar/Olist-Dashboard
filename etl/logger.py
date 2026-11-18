"""Structured logging for ETL pipeline execution."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for structured aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "run_id",
            "dataset",
            "source_file",
            "target_table",
            "rows_extracted",
            "rows_transformed",
            "rows_loaded",
            "rows_failed",
            "duration_seconds",
            "error_type",
            "reconciled",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logger(
    name: str = "olist_etl",
    log_dir: Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure console + rotating file JSON logging."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(console)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "etl.jsonl", encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)

    return logger


def log_extra(**kwargs: Any) -> dict[str, Any]:
    """Helper to attach structured fields to a log record."""
    return kwargs
