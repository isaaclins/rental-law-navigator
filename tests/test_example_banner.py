"""Home search: "Example address in {q}" names a searched city or ZIP, never the typed fragment of a street (#Isaac 08:32:
"Example address in hf." for 53-55 Ashford St, "in z." for 3654 Arizona St)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "web" / "static"
APP = (STATIC / "app.js").read_text()
ES = json.loads((STATIC / "i18n" / "es.json").read_text())

BOSTON = {
    "id": "A0065",
    "street": "53-55 ASHFORD ST",
    "postal_city": "Allston",
    "city": "Boston",
    "state": "MA",
    "zip": "02134",
}
SAN_DIEGO = {
    "id": "A0099",
    "street": "3654 ARIZONA ST",
    "postal_city": "San Diego",
    "city": "San Diego",
    "state": "CA",
    "zip": "92104",
}


def _src() -> str:
    m = re.search(r"function examplePlace\(q, a\) \{.*?\n\}", APP, re.S)
    assert m, "examplePlace() missing from app.js"
    return m.group(0)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize(
    "q,addr,place",
    [
        ("hf", BOSTON, ""),
        ("z", SAN_DIEGO, ""),
        ("Ashford", BOSTON, ""),
        ("53-55 Ashford St", BOSTON, ""),
        ("boston", BOSTON, "Boston"),
        ("Boston, MA", BOSTON, "Boston"),
        ("allston", BOSTON, "Allston"),
        ("02134", BOSTON, "02134"),
        ("92104", BOSTON, ""),
        ("san diego", SAN_DIEGO, "San Diego"),
        ("", BOSTON, ""),
        ("boston", None, ""),
    ],
)
def test_example_place(q, addr, place):
    js = (
        f"{_src()}\nconsole.log(JSON.stringify(examplePlace({json.dumps(q)}, {json.dumps(addr)})));"
    )
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == place


def test_pick_uses_example_place_and_both_languages_have_the_placeholder():
    assert 'sessionStorage.setItem("ce.example", q)' not in APP
    assert "examplePlace(q, ADDR.find((x) => x.id === id))" in APP
    assert 'ex_banner: "Example address in {q}. Your building may differ."' in APP
    assert "{q}" in ES["ex_banner"]
