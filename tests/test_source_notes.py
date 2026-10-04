"""Rules whose quote doesn't back their citation get an amber 'Source unclear' note, never 'word for word' (audit item 17)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from web import source_notes as SN
from web.app import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_every_note_is_for_a_real_rule_in_both_languages():
    ids = {r["team_rule_id"] for r in json.loads((ROOT / "output/rules.json").read_text())["rules"]}
    assert set(SN.NOTES) == {"HOB-RENT-01", "NWK-RENT-01", "SD-SCR-01", "LA-DEP-01"}
    assert set(SN.NOTES) <= ids
    for n in SN.NOTES.values():
        assert n["en"] and n["es"] and n["en"] != n["es"]
    assert SN.note("SF-RENT-01") is None


def _notes(o):
    if isinstance(o, dict):
        if o.get("source_note"):
            yield (o.get("team_rule_id") or o.get("id")), o["source_note"]
        for v in o.values():
            yield from _notes(v)
    elif isinstance(o, list):
        for v in o:
            yield from _notes(v)


def test_address_api_carries_the_note_en_and_es():
    # Hoboken A0002: the exempt rent ordinance; Newark A0003: the unread ordinance
    for aid, rid in (("A0002", "HOB-RENT-01"), ("A0003", "NWK-RENT-01"), ("A0001", "LA-DEP-01")):
        en = dict(_notes(client.get(f"/api/address/{aid}").json()))
        es = dict(_notes(client.get(f"/api/address/{aid}?lang=es").json()))
        assert en[rid]["lead"] == "Source unclear."
        assert es[rid]["lead"] == "Fuente poco clara."


def test_share_page_shows_the_note_not_word_for_word():
    html = client.get("/s/A0003/rent/2026-10-01").text
    assert "Source unclear." in html and 'class="sh-ok"' not in html
