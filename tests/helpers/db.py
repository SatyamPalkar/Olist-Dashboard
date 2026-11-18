"""Optional PostgreSQL access for integration tests.

Connection uses POSTGRES_* env vars (ADR-002). Tests skip cleanly when
the warehouse is unavailable — never invent pass conditions.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore


def postgres_dsn() -> str | None:
    host = os.getenv("POSTGRES_HOST")
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    if not all([host, db, user, password]):
        return None
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"host={host} port={port} dbname={db} user={user} password={password}"


def database_available() -> bool:
    if psycopg is None:
        return False
    dsn = postgres_dsn()
    if not dsn:
        return False
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


@contextmanager
def db_connection() -> Iterator[Any]:
    dsn = postgres_dsn()
    if not dsn or psycopg is None:
        raise RuntimeError("PostgreSQL is not configured or psycopg is missing")
    with psycopg.connect(dsn) as conn:
        yield conn


def read_sql(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    with db_connection() as conn:
        return pd.read_sql(sql, conn, params=params)


def scalar(sql: str, params: tuple | dict | None = None) -> Any:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return None if row is None else row[0]


def table_exists(schema: str, table: str) -> bool:
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
    """
    return bool(scalar(sql, (schema, table)))


def warehouse_loaded() -> bool:
    """True when analytics.fact_orders exists and has rows."""
    if not database_available():
        return False
    try:
        if not table_exists("analytics", "fact_orders"):
            return False
        return int(scalar("SELECT COUNT(*) FROM analytics.fact_orders")) > 0
    except Exception:
        return False
