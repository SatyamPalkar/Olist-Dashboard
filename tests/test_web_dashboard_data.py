"""Web dashboard JSON equals an independent recomputation from the Tableau extracts (no database needed)."""
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "web_check_data", Path(__file__).resolve().parent.parent / "web" / "check_data.py")
check_data = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_data)


@pytest.mark.unit
def test_web_dashboard_headlines_match_extracts():
    assert check_data.check() == []
