"""Check a rent increase, "New rent" field (web/static/sentences.js parseNewRent): "+300" is a $300 increase, never a
new rent of $300 (persona test, David). Runs the browser script in Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent.parent / "web" / "static" / "sentences.js"

CASES = [
    ("2300", 2000, {"new_rent": 2300}),
    ("$2,300", 2000, {"new_rent": 2300}),
    ("+300", 2000, {"new_rent": 2300, "delta": 300}),
    ("+$300", 2000, {"new_rent": 2300, "delta": 300}),
    ("300 more", 2000, {"new_rent": 2300, "delta": 300}),
    ("300 más", 2000, {"new_rent": 2300, "delta": 300}),
    ("-100", 2000, {"new_rent": 1900, "delta": -100}),
    ("5%", 2000, {"increase_pct": 5}),
    ("+5%", 2000, {"increase_pct": 5}),
    ("+300", None, None),
    ("", 2000, None),
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("text,current,expected", CASES)
def test_parse_new_rent(text, current, expected):
    code = (
        f"require({json.dumps(str(JS))}); process.stdout.write(JSON.stringify("
        f"globalThis.CE_RENT.parseNewRent({json.dumps(text)}, {json.dumps(current)})))"
    )
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == expected
