"""Sentence splitting for rule summaries (web/static/sentences.js, #163): never inside numbers, abbreviations or
parentheses. Runs the browser script in Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent.parent / "web" / "static" / "sentences.js"

CASES = [
    (
        "For rent-controlled units, the annual allowable increase is 1.6% of base rent for March 1, 2026 through "
        "February 28, 2027 (1.4% prior year). Units with a first CO after June 13, 1979 are exempt.",
        [
            "For rent-controlled units, the annual allowable increase is 1.6% of base rent for March 1, 2026 through "
            "February 28, 2027 (1.4% prior year).",
            "Units with a first CO after June 13, 1979 are exempt.",
        ],
    ),
    (
        "Landlords may not demand more than 1.5 times the monthly rent. Interest is paid yearly.",
        [
            "Landlords may not demand more than 1.5 times the monthly rent.",
            "Interest is paid yearly.",
        ],
    ),
    (
        "Fees are capped at $30 (the Berkeley Rent Board cites $68.96 for 2026). No fee if no unit is available.",
        [
            "Fees are capped at $30 (the Berkeley Rent Board cites $68.96 for 2026).",
            "No fee if no unit is available.",
        ],
    ),
    (
        "The U.S. Census decides. Sec. 5 applies (see Cal. Civ. Code § 1947.12. It is long). Done!",
        [
            "The U.S. Census decides.",
            "Sec. 5 applies (see Cal. Civ. Code § 1947.12. It is long).",
            "Done!",
        ],
    ),
    (
        "L.A. Mun. Code § 151.00 et seq. applies here.",
        ["L.A. Mun. Code § 151.00 et seq. applies here."],
    ),
    (
        "El aumento es de 1.6% (1.4% el año anterior). Las unidades están exentas.",
        ["El aumento es de 1.6% (1.4% el año anterior).", "Las unidades están exentas."],
    ),
]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("text,expected", CASES)
def test_split_sentences(text, expected):
    code = f"require({json.dumps(str(JS))}); process.stdout.write(JSON.stringify(globalThis.CE_TEXT.splitSentences({json.dumps(text)})))"
    got = json.loads(
        subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout
    )
    assert got == expected
    for sentence in got:
        assert not sentence[0].islower() and not sentence[0].isdigit()
