"""CSV extraction with metadata capture and optional chunked reading."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pandas as pd

from etl.config import DatasetConfig, Settings
from etl.logger import log_extra, setup_logger
from etl.validators import validate_file_available

logger = setup_logger()


@dataclass
class SourceFileMetadata:
    """Filesystem metadata recorded for lineage / audit."""

    path: Path
    source_file: str
    size_bytes: int
    mtime: datetime
    sha256: str
    encoding: str

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "source_file": self.source_file,
            "size_bytes": self.size_bytes,
            "mtime": self.mtime.isoformat(),
            "sha256": self.sha256,
            "encoding": self.encoding,
        }


def resolve_source_path(settings: Settings, config: DatasetConfig) -> Path:
    """Resolve absolute path to a configured source CSV."""
    return settings.data_dir / config.source_file


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Stream a file and return its SHA-256 hex digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def collect_file_metadata(path: Path, encoding: str) -> SourceFileMetadata:
    """Build metadata for an available source file."""
    validate_file_available(path)
    stat = path.stat()
    return SourceFileMetadata(
        path=path,
        source_file=path.name,
        size_bytes=stat.st_size,
        mtime=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        sha256=compute_sha256(path),
        encoding=encoding,
    )


def _read_csv(
    path: Path,
    encoding: str,
    chunksize: int | None = None,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """
    Read a CSV with encoding fallback.

    Tries the configured encoding first, then latin-1 / cp1252.
    """
    encodings = [encoding, "utf-8-sig", "latin-1", "cp1252"]
    seen: set[str] = set()
    last_error: Exception | None = None

    for enc in encodings:
        if enc in seen:
            continue
        seen.add(enc)
        try:
            return pd.read_csv(
                path,
                encoding=enc,
                dtype=str,  # preserve raw values; typing happens in transform
                keep_default_na=True,
                na_values=["", "NA", "N/A", "null", "None", "nan", "NaN"],
                low_memory=False,
                chunksize=chunksize,
            )
        except UnicodeDecodeError as exc:
            last_error = exc
            logger.warning("Encoding %s failed for %s; trying fallback", enc, path.name)
            continue

    raise ValueError(f"Unable to decode {path} with encodings {list(seen)}: {last_error}")


def extract_dataset(
    settings: Settings,
    dataset_name: str,
    config: DatasetConfig,
) -> tuple[pd.DataFrame, SourceFileMetadata]:
    """
    Extract an entire dataset into a DataFrame (chunk-concat for large files).

    Large files use chunked reads then concatenation so callers still receive
    one frame, while peak temporary memory stays bounded during parse.
    For true streaming load, use ``extract_dataset_chunks``.
    """
    path = resolve_source_path(settings, config)
    metadata = collect_file_metadata(path, settings.csv_encoding)
    logger.info(
        "Extracting %s (%s bytes)",
        config.source_file,
        metadata.size_bytes,
        extra=log_extra(dataset=dataset_name, source_file=config.source_file),
    )

    if config.chunk_size:
        frames = list(
            _read_csv(path, settings.csv_encoding, chunksize=config.chunk_size)
        )
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    else:
        result = _read_csv(path, settings.csv_encoding)
        assert isinstance(result, pd.DataFrame)
        df = result

    # Attach 1-based source row numbers for traceability (header excluded)
    df = df.copy()
    df["_row_number"] = range(1, len(df) + 1)
    df["_source_file"] = config.source_file

    logger.info(
        "Extracted %s rows from %s",
        len(df),
        config.source_file,
        extra=log_extra(
            dataset=dataset_name,
            source_file=config.source_file,
            rows_extracted=len(df),
        ),
    )
    return df, metadata


def extract_dataset_chunks(
    settings: Settings,
    dataset_name: str,
    config: DatasetConfig,
) -> tuple[Iterator[pd.DataFrame], SourceFileMetadata]:
    """Yield DataFrame chunks for very large sources (e.g. geolocation)."""
    path = resolve_source_path(settings, config)
    metadata = collect_file_metadata(path, settings.csv_encoding)
    chunk_size = config.chunk_size or settings.batch_size

    def _generator() -> Iterator[pd.DataFrame]:
        offset = 0
        chunks = _read_csv(path, settings.csv_encoding, chunksize=chunk_size)
        assert not isinstance(chunks, pd.DataFrame)
        for chunk in chunks:
            chunk = chunk.copy()
            chunk["_row_number"] = range(offset + 1, offset + len(chunk) + 1)
            chunk["_source_file"] = config.source_file
            offset += len(chunk)
            logger.info(
                "Extracted chunk rows=%s cumulative=%s file=%s",
                len(chunk),
                offset,
                config.source_file,
                extra=log_extra(
                    dataset=dataset_name,
                    source_file=config.source_file,
                    rows_extracted=offset,
                ),
            )
            yield chunk

    return _generator(), metadata


def list_available_sources(settings: Settings) -> dict[str, bool]:
    """Return availability map for every configured dataset."""
    return {
        name: resolve_source_path(settings, cfg).exists()
        for name, cfg in settings.datasets.items()
    }
