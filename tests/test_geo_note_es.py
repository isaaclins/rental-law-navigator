"""#151: on Spanish address pages the resolver note ("How we found this address") is Spanish for every sample
address: app.js geoNoteEs knows every part geo/resolve.py writes into data/addresses_resolved.csv."""

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "web" / "static" / "app.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_every_sample_geocoder_note_has_spanish():
    notes = sorted(
        {
            r["resolution_note"]
            for r in csv.DictReader(open(ROOT / "data" / "addresses_resolved.csv"))
        }
    )
    src = APP.read_text()
    start = src.index("const GEO_ES = [")
    end = src.index("\n}\n", src.index("function geoNoteEs(note) {")) + 3
    code = (
        'const cap = (s) => String(s || "").replace(/^\\s*\\w/, (m) => m.toUpperCase());\n'
        + src[start:end]
        + f"\nprocess.stdout.write(JSON.stringify({json.dumps(notes)}.map(geoNoteEs)))"
    )
    out = json.loads(
        subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout
    )
    missing = [n for n, es in zip(notes, out, strict=True) if not es]
    assert not missing, missing[:5]
    for es in out:
        for en in ("geocoder", " match", "inside ", "was ignored", "neighborhood", "mailing name"):
            assert en not in es, es
