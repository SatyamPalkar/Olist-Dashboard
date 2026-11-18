"""Build Tableau .hyper extracts from tableau/data/*.csv for the Tableau Public edition.

Tableau Public only accepts workbooks whose data sources are extracts. This script
converts each grain-safe CSV extract into a .hyper file (table "Extract"."Extract")
with exactly the column names and types declared in build_tableau_workbook.py, and
then checks the row count and a numeric checksum against the CSV.

Requires: pip install tableauhyperapi   (the only non-stdlib dependency, used only here)

Usage (from the project root):
    python3 tableau/build_hyper_extracts.py
    python3 tableau/build_tableau_workbook.py --public
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter, NOT_NULLABLE, NULLABLE, SqlType,
                             TableDefinition, TableName, Telemetry)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_tableau_workbook as wb  # noqa: E402  (column contract lives in the generator)

TYPES = {"string": SqlType.text(), "integer": SqlType.big_int(), "real": SqlType.double(), "date": SqlType.date()}
TABLE = TableName("Extract", "Extract")


def convert(value: str, datatype: str):
    if value == "":
        return None
    if datatype == "integer":
        return int(value)
    if datatype == "real":
        return float(value)
    if datatype == "date":
        return dt.date.fromisoformat(value[:10])
    return value


def build(ds, hyper: HyperProcess) -> None:
    src = wb.DATA_DIR / ds.filename
    out = wb.HYPER_DIR / (Path(ds.filename).stem + ".hyper")
    cols = [(c[0], c[1]) for c in ds.cols]
    with open(src, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c, _ in cols if c not in reader.fieldnames]
        if missing:
            raise SystemExit(f"{ds.filename}: columns declared in the workbook but missing in CSV: {missing}")
        rows = [[convert(r[c], t) for c, t in cols] for r in reader]
    table = TableDefinition(TABLE, [TableDefinition.Column(c, TYPES[t], NULLABLE) for c, t in cols])
    with Connection(hyper.endpoint, out, CreateMode.CREATE_AND_REPLACE) as con:
        con.catalog.create_schema("Extract")
        con.catalog.create_table(table)
        with Inserter(con, table) as ins:
            ins.add_rows(rows)
            ins.execute()
        # verify: row count and the sum of every numeric column match the CSV
        n = con.execute_scalar_query(f"SELECT COUNT(*) FROM {TABLE}")
        assert n == len(rows), (ds.filename, n, len(rows))
        for i, (c, t) in enumerate(cols):
            if t in ("integer", "real"):
                got = con.execute_scalar_query(f'SELECT SUM("{c}") FROM {TABLE}') or 0
                exp = sum(r[i] for r in rows if r[i] is not None)
                assert abs(got - exp) < 1e-6 * max(1, abs(exp)), (ds.filename, c, got, exp)
    print(f"{out.name:28s} {len(rows):>8,} rows  {out.stat().st_size / 1e6:6.1f} MB  verified")


def main() -> None:
    wb.HYPER_DIR.mkdir(exist_ok=True)
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        for ds in wb.DATASOURCES:
            build(ds, hyper)


if __name__ == "__main__":
    main()
