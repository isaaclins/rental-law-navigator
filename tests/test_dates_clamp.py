"""Month arithmetic never produces an impossible date (Isaac saw "31.02.2027"): Jan 31 + 1 month is the last day
of February, Feb 29 + 12 months is Feb 28. Server (web/check._add_months) and browser (app.js addMonths)."""

import datetime as dt
import shutil
import subprocess
from pathlib import Path

import pytest

from web.check import _add_months

D = dt.date
CASES = [
    (D(2027, 1, 31), 1, D(2027, 2, 28)),
    (D(2028, 1, 31), 1, D(2028, 2, 29)),
    (D(2028, 2, 29), 12, D(2029, 2, 28)),
    (D(2026, 3, 31), -1, D(2026, 2, 28)),
    (D(2026, 8, 31), 1, D(2026, 9, 30)),
    (D(2026, 12, 15), 1, D(2027, 1, 15)),
    (D(2026, 10, 1), 12, D(2027, 10, 1)),
]


@pytest.mark.parametrize("d,n,want", CASES)
def test_add_months_clamps(d, n, want):
    assert _add_months(d, n) == want


APP = Path(__file__).resolve().parent.parent / "web" / "static" / "app.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("d,n,want", CASES)
def test_js_add_months_clamps(d, n, want):
    src = APP.read_text()
    start = src.index("function addMonths(iso, n) {")
    end = src.index("\n}\n", start) + 3
    code = src[start:end] + f"process.stdout.write(addMonths({d.isoformat()!r}, {n}))"
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout
    assert out == want.isoformat()
