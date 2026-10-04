"""Tests for "Protections over time" (GET /api/stats/protections): city counts checked by hand against rules.json.

Run: uv run --with pytest --with httpx pytest tests/test_stats.py -q
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

from web import stats as S
from web.app import app

client = TestClient(app)
D = dt.date
CA = ["Los Angeles", "San Francisco", "San Diego", "Berkeley", "Santa Ana"]


def ids(pid: str) -> set[str]:
    return {r["team_rule_id"] for r in S.rules_for(pid)}


def covered(pid: str, d: dt.date) -> set[str]:
    return set(S.covered_on(S.rules_for(pid), d))


# ------------------------------------------------------------------ classification
def test_rent_cap_excludes_state_bar_on_rent_control():
    assert "CA-RENT-01" in ids("rent_cap")
    assert "MA-RENT-01" not in ids("rent_cap")  # Massachusetts bars local rent control: not a cap


def test_deposit_cap_excludes_interest_only_rules():
    assert {"CA-DEP-01", "MA-DEP-01", "NJ-DEP-01"} <= ids("deposit_cap")
    assert not {"BER-DEP-01", "LA-DEP-01", "SF-DEP-01"} & ids("deposit_cap")


def test_just_cause_excludes_notice_reprisal_and_relocation_rules():
    got = ids("just_cause")
    assert {"CA-EVIC-01", "NJ-EVIC-03", "SA-EVIC-01", "SD-EVIC-01"} <= got
    assert not {"BOS-EVIC-01", "CAM-EVIC-01", "MA-EVIC-01", "MA-EVIC-03", "NJ-EVIC-01"} & got
    assert not {"LA-EVIC-04", "SF-EVIC-02"} & got  # relocation payments


def test_fee_cap_excludes_broker_fees():
    assert {"CA-FEE-01", "MA-FEE-02", "NJ-FEE-01"} <= ids("fee_cap")
    assert "MA-FEE-01" not in ids("fee_cap")


def test_source_of_income_excludes_criminal_history_rules():
    got = ids("source_of_income")
    assert {"CA-SCR-01", "NJ-SCR-01", "MA-SCR-01", "BOS-SCR-01", "CAM-SCR-01"} <= got
    # San Diego's own ordinance is unverified (link-only): its answers are "unknown", so it counts apart
    assert "SD-SCR-01" in {
        r["team_rule_id"] for r in S.rules_for("source_of_income", unverified=True)
    }
    assert not {"CA-SCR-02", "NJ-SCR-02", "BER-SCR-01", "BOS-SCR-02", "SF-SCR-01"} & got


# ------------------------------------------------------------------ counts on dates
def test_state_law_covers_every_city_of_its_state():
    ca = next(r for r in S.rules_for("rent_cap") if r["team_rule_id"] == "CA-RENT-01")
    assert S.covers(ca) == CA


def test_ab1482_rent_cap_counts_for_all_ca_cities_from_2020():
    # AB 1482 (CA-RENT-01): in force from its in_force_since 2019-03-15 per the evaluator; certainly on 2020-01-01
    on = S.covered_on(S.rules_for("rent_cap"), D(2020, 1, 1))
    for c in CA:
        assert "CA-RENT-01" in on[c]
    # 5 CA + Jersey City; Hoboken and Newark are unverified (every answer there is "unknown"), not in force
    assert S.count_on("rent_cap", D(2020, 1, 1)) == 6
    assert not {"Boston", "Cambridge"} & covered("rent_cap", D(2026, 10, 1))


def test_nj_fair_act_in_force_2027_07_01():
    assert S.count_on("algorithmic_ban", D(2027, 6, 30)) == 7
    assert S.count_on("algorithmic_ban", D(2027, 7, 1)) == 8
    assert "Newark" in covered("algorithmic_ban", D(2027, 7, 1)) - covered(
        "algorithmic_ban", D(2027, 6, 30)
    )


def test_algorithmic_ban_steps():
    p = S.protection("algorithmic_ban")
    assert p["initial"]["count"] == 0
    assert [(s["date"], s["count"]) for s in p["steps"]] == [
        ("2024-10-14", 1),  # San Francisco
        ("2025-06-01", 3),  # San Diego, Jersey City
        ("2025-07-01", 4),  # Hoboken
        ("2026-01-01", 7),  # CA AB 325 adds Los Angeles, Berkeley, Santa Ana
        ("2027-07-01", 8),  # NJ FAIR Act adds Newark
    ]
    assert p["steps"][-1]["added"] == ["Newark"]
    assert [x["id"] for x in p["steps"][-1]["laws"]] == ["NJ-ALG-01"]
    assert {x["id"] for x in p["pending"]} == {"MA-ALG-P1", "MA-ALG-P2"}
    assert all(x["count_if_passed"] == 10 for x in p["pending"])


def test_nj_application_fee_cap_completes_coverage_2026_05_01():
    assert S.count_on("fee_cap", D(2026, 4, 30)) == 7
    assert S.count_on("fee_cap", D(2026, 5, 1)) == 10


def test_failed_measures_are_markers_not_coverage():
    p = S.protection("rent_cap")
    assert {x["id"]: x["count_if_passed"] for x in p["failed"]} == {
        "MA-RENT-P1": 8,
        "BOS-RENT-P1": 7,
    }
    assert p["final"]["count"] == 6


def test_unverified_rent_control_counts_as_unknown_like_the_address_answers():
    """Hoboken and Newark rent control: every lookup says unknown, so the chart must not call it in force."""
    import json
    from pathlib import Path

    p = S.protection("rent_cap")
    assert p["unknown"]["cities"] == ["Hoboken", "Newark"]
    assert {x["id"] for x in p["unknown"]["laws"]} == {"HOB-RENT-01", "NWK-RENT-01"}
    assert not {"Hoboken", "Newark"} & set(p["final"]["cities"])
    look = json.loads(Path("output/lookups.json").read_text())["lookups"]
    res = {
        e["result"]
        for v in look.values()
        for e in v
        if e["team_rule_id"] in ("HOB-RENT-01", "NWK-RENT-01")
    }
    assert res == {"unknown"}
    h = client.get("/api/stats/protections").json()
    rc = next(x for x in h["protections"] if x["id"] == "rent_cap")
    assert rc["unknown"]["count"] == 2


# ------------------------------------------------------------------ endpoint
def test_endpoint_headline_is_computed():
    d = client.get("/api/stats/protections").json()
    assert [p["id"] for p in d["protections"]] == [p[0] for p in S.PROTECTIONS]
    assert len(d["cities"]) == 10
    h = d["headline"]
    assert (h["protection"], h["from"], h["to"], h["from_year"], h["to_year"]) == (
        "algorithmic_ban",
        0,
        8,
        2024,
        2027,
    )
    assert h["without"] == ["Boston", "Cambridge"]


def test_endpoint_translates_titles():
    d = client.get("/api/stats/protections?lang=es").json()
    alg = next(p for p in d["protections"] if p["id"] == "algorithmic_ban")
    assert all(law["source_url"] for s in alg["steps"] for law in s["laws"])
