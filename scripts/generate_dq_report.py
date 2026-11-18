#!/usr/bin/env python3
"""Generate data quality JSON + Markdown reports from raw CSVs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.dq_report import build_raw_quality_report, write_report


def main() -> int:
    report = build_raw_quality_report()
    json_path = ROOT / "reports" / "data_quality_report.json"
    md_path = ROOT / "docs" / "data_quality_report.md"
    write_report(report, json_path=json_path, md_path=md_path)
    print(f"Status: {report['overall_data_quality_status']}")
    print(f"Records: {report['total_records_tested']:,}")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if report["overall_data_quality_status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
