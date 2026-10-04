"""How this answer was made (web/howmade.py, features/howmade.js): who decided what, from the pipeline's records."""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web import howmade as HM
from web.app import STORE, app

client = TestClient(app)
ROOT = Path(__file__).resolve().parent.parent


def test_build_reads_the_extraction_entry_and_the_plain_record():
    audit = [
        {
            "ts": "2026-10-03T10:00:00",
            "stage": "extract",
            "doc_id": "D1",
            "model": "m-1",
            "prompt_version": "v9",
            "prompt_hash": "h1",
        },
        {"ts": "2026-10-03T11:00:00", "stage": "review", "jurisdiction": "X"},
        {
            "ts": "2026-10-03T12:00:00",
            "stage": "extract",
            "doc_id": "D1",
            "model": "m-1",
            "prompt_version": "v9",
            "prompt_hash": "h1",
            "cached": True,
        },
        {
            "ts": "2026-10-03T13:00:00",
            "stage": "extract",
            "doc_id": "D2",
            "model": "m-2",
            "prompt_hash": "h2",
        },
    ]
    rules = {"R-1": {"source_doc_id": "D1"}, "R-2": {"source_doc_id": "D9"}}
    plain = {
        "R-1": {
            "source": "generated",
            "method": "model",
            "needs_review": False,
            "validation": {"passed": True, "attempts": [{}, {}]},
        }
    }
    out = HM.build(audit, rules, plain)
    assert out["R-1"]["read"] == {
        "doc_id": "D1",
        "model": "m-1",
        "prompt_version": "v9",
        "at": "2026-10-03T10:00:00",
        "log": 2,
        "runs": 2,
    }
    assert out["R-1"]["worded"]["source"] == "generated" and out["R-1"]["worded"]["attempts"] == 2
    assert out["R-2"] == {
        "read": None,
        "worded": None,
    }  # no log entry, no plain record: nothing invented


def test_raw_rule_picks_the_model_output_for_this_rule():
    entry = {
        "raw_output": json.dumps(
            {
                "rules": [
                    {
                        "title": "Deposit cap",
                        "quoted_span": "shall not demand a deposit greater than one month",
                    },
                    {
                        "title": "Rent cap",
                        "quoted_span": "the annual allowable increase amount is 1.6%",
                    },
                ]
            }
        )
    }
    got = HM.raw_rule(
        entry, {"title": "x", "quoted_span": "The annual allowable increase amount is 1.6%."}
    )
    assert got["title"] == "Rent cap"
    assert HM.raw_rule({"raw_output": "not json"}, {"quoted_span": "a"}) is None


def test_api_every_rule_has_a_trail_and_the_log_is_the_audit_entry():
    rules = client.get("/api/howmade").json()["rules"]
    assert set(rules) == set(STORE.rules)
    s = rules["SF-RENT-01"]
    assert s["read"]["model"] and STORE.audit[s["read"]["log"]]["stage"] == "extract"
    assert STORE.audit[s["read"]["log"]]["doc_id"] == STORE.rules["SF-RENT-01"]["source_doc_id"]
    one = client.get("/api/howmade/SF-RENT-01").json()
    assert one["log_entry"]["model_output"]["quoted_span"].startswith("For rent-controlled units")
    assert "raw_output" not in one["log_entry"]
    assert client.get("/api/howmade/NOPE-01").status_code == 404
    # the short-answer source matches plain_language.json
    recs = json.loads((ROOT / "output/plain_language.json").read_text())["records"]
    for rid, rec in recs.items():
        if rid in rules:
            assert rules[rid]["worded"]["source"] == rec["source"]


node = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")


def render(**arg) -> str:
    out = subprocess.run(
        ["node", str(ROOT / "tests/howmade_render.mjs"), json.dumps(arg)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


def text(h: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip())


@node
def test_render_sf_rent_four_steps_en_es():
    d = client.get("/api/address/A0027").json()
    h = render(
        kind="topic",
        d=d,
        cat="rent_increase_limits",
        lang="en",
        howmade=client.get("/api/howmade").json(),
    )
    t = text(h)
    assert h.count("<li") == 4  # read, checked, decided, worded; no flags
    assert (
        "AI read the official text on sf.gov (retrieved 2026-10-01) and pulled out this rule. 85% sure."
        in t
    )
    assert "Code found the quoted sentence word for word in that text." in t
    assert (
        "rules engine (no AI) decided it applies here: built 1923, on or before the 1979-06-13 cutoff (property records)."
        in t
    )
    assert "The state rule yields to this one." in t
    assert (
        "The short answer was written for this rule ahead of time and checked against its quote (not generated live)."
        in t
    )
    assert "person" not in h.lower()
    assert 'data-hm-log="SF-RENT-01"' in h and "is-ai" in h and "is-code" in h
    es = text(render(kind="topic", d=d, cat="rent_increase_limits", lang="es"))
    assert (
        "La IA leyó el texto oficial en sf.gov" in es
        and "El motor de reglas (sin IA) decidió que aplica aquí" in es
    )
    assert "se escribió para esta regla de antemano" in es


@node
def test_render_generated_low_confidence_unknown_and_answers():
    d = client.get("/api/address/A0027").json()
    c = next(x for x in d["categories"] if x["id"] == "security_deposits")
    sf = next(x for x in c["enacted"] if x["rule"]["team_rule_id"] == "SF-DEP-01")
    d1 = {**d, "categories": [{**c, "enacted": [sf]}]}
    t = text(render(kind="topic", d=d1, cat="security_deposits", lang="en"))
    assert "AI wrote the short answer; code checked its numbers, dates and length." in t
    assert "Needs a second look: our reading is 65% sure, under our 70% bar." in t
    # unknown: the engine names the missing fact
    d = client.get("/api/address/A0008").json()
    t = text(render(kind="topic", d=d, cat="rent_increase_limits", lang="en"))
    assert "The rules engine (no AI) couldn't decide: the year built isn't in public records." in t
    # any address: the facts are the reader's own answer
    v = client.post(
        "/api/evaluate",
        json={
            "address": {"state": "CA", "jurisdiction": "Los Angeles, CA"},
            "as_of": "2026-10-01",
            "facts": {"year_built": 1975, "units": 4},
        },
    ).json()
    t = text(render(kind="topic", d=v, cat="rent_increase_limits", lang="en"))
    assert "built 1975, on or before the 1978-10-01 cutoff; 4 units (your answer)" in t


@node
def test_render_secondary_source_and_conflict():
    d = client.get("/api/address/A0008").json()
    t = text(render(kind="topic", d=d, cat="algorithmic_rent_setting", lang="en"))
    assert "a summary rather than the official text" in t and "word for word in that summary" in t
    assert "May conflict with" in t and "NJ-ALG-01" not in t


@node
def test_ask_line():
    cite = {
        "id": "SF-RENT-01",
        "kind": "rule",
        "quoted_span": "x",
        "verbatim": True,
        "engine": {"result": "applies", "label": "Applies here"},
    }
    t = text(render(kind="ask", cite=cite, lang="en"))
    assert (
        t
        == "AI extracted it · quote checked word for word ✓ · engine: applies here · answer by AI, numbers checked by code"
    )
    t = text(render(kind="ask", cite={**cite, "verbatim": False, "engine": None}, lang="es"))
    assert "cita no encontrada palabra por palabra" in t and "motor" not in t


@node
def test_render_units_from_use_code_and_older_version():
    # #148: a lower bound from the land-use code, not the rule's "(<= 3 units)" threshold or "property records"
    d = client.get("/api/address/A0002").json()
    t = text(render(kind="topic", d=d, cat="application_screening_fees", lang="en"))
    assert "at least 20 units (the land-use code in property records)" in t
    t = text(render(kind="topic", d=d, cat="just_cause_eviction", lang="en"))
    assert "3 units" not in t
    # #158: an older version applied on this date; the missing fact is the version, not a building fact
    d = client.get("/api/address/A0001?as_of=2024-01-01").json()
    t = text(render(kind="topic", d=d, cat="rent_increase_limits", lang="en"))
    assert (
        "couldn't decide: on this date an older version of the law applied that our sources don't include"
        in t
    )
