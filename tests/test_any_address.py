"""API tests for the any-address lookup (#39): POST /api/resolve and /api/evaluate.

Run: uv run --with pytest --with httpx pytest tests/ -q
The Census geocoder is mocked except in test_live_census (skipped when the network is unavailable).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web import any_address as AA
from web.app import app

client = TestClient(app)


def census_match(state: str, place: str | None, county: str, fips: str = "06") -> dict:
    g = {
        "States": [{"STUSAB": state, "NAME": state, "GEOID": fips}],
        "Counties": [{"NAME": county}],
    }
    if place:
        g["Incorporated Places"] = [{"BASENAME": place, "NAME": f"{place} city"}]
    return {
        "matchedAddress": f"1 MAIN ST, {(place or 'SOMEWHERE').upper()}, {state}, 00000",
        "coordinates": {"x": -118.49, "y": 34.01},
        "geographies": g,
    }


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    AA.RESOLVE_LIMIT.hits.clear()
    AA.EVALUATE_LIMIT.hits.clear()
    AA._cache.clear()
    yield


def mock(monkeypatch, result):
    calls = []

    def fake(address):
        calls.append(address)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(AA, "census_lookup", fake)
    return calls


def test_resolve_covered_city_extension(monkeypatch):
    mock(monkeypatch, census_match("CA", "Santa Monica", "Los Angeles County"))
    d = client.post("/api/resolve", json={"address": "1685 Main St, Santa Monica, CA"}).json()
    assert d["match"] and d["scope"] == "city" and d["in_scope"]
    assert d["jurisdiction"] == "Santa Monica, CA" and d["extension"] == "santa-monica"
    assert [s["level"] for s in d["stack"]] == ["state", "county", "city"]
    assert d["stack"][-1]["covered"] is True


def test_resolve_main_city(monkeypatch):
    mock(monkeypatch, census_match("MA", "Boston", "Suffolk County", "25"))
    d = client.post("/api/resolve", json={"address": "1 City Hall Sq, Boston, MA"}).json()
    assert d["jurisdiction"] == "Boston, MA" and d["extension"] is None


def test_resolve_state_only_and_unincorporated(monkeypatch):
    mock(monkeypatch, census_match("CA", "Oakland", "Alameda County"))
    d = client.post("/api/resolve", json={"address": "1000 Broadway, Oakland, CA"}).json()
    assert d["scope"] == "state" and d["jurisdiction"] is None and d["in_scope"]
    assert "Oakland" in d["message"] and "not in our corpus" in d["message"]
    AA._cache.clear()
    mock(monkeypatch, census_match("CA", None, "Los Angeles County"))
    d = client.post("/api/resolve", json={"address": "1 Some Rd, Altadena, CA"}).json()
    assert d["scope"] == "state" and "unincorporated Los Angeles County" in d["message"]


def test_resolve_out_of_scope_lists_cities(monkeypatch):
    mock(monkeypatch, census_match("TX", "Austin", "Travis County", "48"))
    d = client.post("/api/resolve", json={"address": "100 Congress Ave, Austin, TX"}).json()
    assert d["scope"] == "none" and not d["in_scope"]
    assert "Cambridge, MA" in d["covered"]["MA"] and "Santa Monica, CA" in d["covered"]["CA"]


def test_resolve_no_match_and_upstream_down(monkeypatch):
    mock(monkeypatch, None)
    d = client.post("/api/resolve", json={"address": "nowhere street 99"}).json()
    assert d["match"] is False and d["covered"]
    AA._cache.clear()
    mock(monkeypatch, RuntimeError("timeout"))
    r = client.post("/api/resolve", json={"address": "1 Main St, Boston, MA"})
    assert r.status_code == 503


def test_resolve_cached_in_memory_by_hash(monkeypatch):
    calls = mock(monkeypatch, census_match("MA", "Cambridge", "Middlesex County", "25"))
    for _ in range(3):
        client.post("/api/resolve", json={"address": "795 Massachusetts Ave, Cambridge, MA"})
    assert len(calls) == 1
    assert all("Massachusetts" not in k for k in AA._cache)  # keys are hashes, not addresses


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"address": "abc"},
        {"address": "x" * 201},
        {"address": "12345 67890"},
        {"address": "1 Main St", "x": 1},
    ],
)
def test_resolve_validation(monkeypatch, body):
    mock(monkeypatch, None)
    assert client.post("/api/resolve", json=body).status_code == 422


def test_resolve_rate_limit(monkeypatch):
    mock(monkeypatch, None)
    codes = [
        client.post("/api/resolve", json={"address": f"{i} Main St, Boston, MA"}).status_code
        for i in range(22)
    ]
    assert codes[:20] == [200] * 20 and codes[-1] == 429


def test_forwarded_ip_only_behind_loopback():
    class R:
        def __init__(self, host, headers):
            self.client = type("C", (), {"host": host})()
            self.headers = headers

    assert AA.client_ip(R("127.0.0.1", {"cf-connecting-ip": "203.0.113.9"})) == "203.0.113.9"
    assert AA.client_ip(R("198.51.100.7", {"cf-connecting-ip": "203.0.113.9"})) == "198.51.100.7"


def ev(**kw):
    body = {
        "address": {"state": "CA", "jurisdiction": "Los Angeles, CA"},
        "as_of": "2026-10-01",
    } | kw
    return client.post("/api/evaluate", json=body)


def items(d):
    return [i for c in d["categories"] for i in c["enacted"] + c["pending"]]


def test_evaluate_unknowns_carry_needs_fact():
    d = ev().json()
    unk = [i for i in items(d) if i["result"] == "unknown"]
    assert unk and all(i["needs_fact"] for i in unk)
    assert all("year_built" in i["needs_fact"] for i in unk)
    assert d["fact_counts"]["year_built"] == len(unk) == d["unknowns"]
    assert {c["id"] for c in d["categories"]} >= {
        "rent_increase_limits",
        "algorithmic_rent_setting",
    }
    assert d["disclaimer"].startswith("Not legal advice")


def test_evaluate_facts_resolve_unknowns():
    d = ev(facts={"year_built": 1962, "units": 8, "owner_occupied": False}).json()
    assert d["unknowns"] == 0
    ids = {i["rule"]["team_rule_id"]: i["result"] for i in items(d)}
    assert ids["LA-RENT-01"] == "applies" and ids["CA-RENT-01"] == "superseded"
    assert d["fact_depends"]["year_built"] > 0


def test_evaluate_certificate_date_breaks_cutoff_year():
    base = {"address": {"state": "CA", "jurisdiction": "San Francisco, CA"}, "as_of": "2026-10-01"}
    d = client.post("/api/evaluate", json=base | {"facts": {"year_built": 1979, "units": 4}}).json()
    sf = next(i for i in items(d) if i["rule"]["team_rule_id"] == "SF-RENT-01")
    assert sf["result"] == "unknown" and sf["needs_fact"] == ["certificate_of_occupancy_date"]
    f = {"year_built": 1979, "units": 4, "certificate_of_occupancy_date": "1979-01-15"}
    d = client.post("/api/evaluate", json=base | {"facts": f}).json()
    sf = next(i for i in items(d) if i["rule"]["team_rule_id"] == "SF-RENT-01")
    assert sf["result"] == "applies"


def test_evaluate_owner_occupied_small_building_exempt():
    d = ev(facts={"year_built": 1962, "units": 2, "owner_occupied": True}).json()
    ids = {i["rule"]["team_rule_id"] for i in items(d)}
    assert "CA-RENT-01" not in ids  # exempt: owner-occupied duplex


def test_evaluate_extension_and_state_only():
    d = client.post(
        "/api/evaluate", json={"address": {"state": "CA", "jurisdiction": "Santa Monica, CA"}}
    ).json()
    assert any(i["rule"]["team_rule_id"].startswith("SMO-") for i in items(d))
    d = client.post("/api/evaluate", json={"address": {"state": "CA", "jurisdiction": None}}).json()
    assert d["scope"] == "state" and d["scope_note"]
    assert all(i["rule"]["level"] == "state" for i in items(d))


def test_evaluate_owner_exemption_needs_units_or_occupancy():
    """NJ owner-occupied small-building exemptions: units or owner occupancy settles them."""
    body = {"address": {"state": "NJ", "jurisdiction": "Newark, NJ"}}
    d = client.post("/api/evaluate", json=body).json()
    unk = {i["rule"]["team_rule_id"]: i["needs_fact"] for i in items(d) if i["result"] == "unknown"}
    assert unk["NJ-EVIC-01"] == ["units", "owner_occupied"]
    d = client.post(
        "/api/evaluate", json=body | {"facts": {"units": 12, "year_built": 1950}}
    ).json()
    left = [i for i in items(d) if i["result"] == "unknown"]
    # only the link-only Newark ordinance stays unknown: no fact settles it, needs_other says why
    assert [i["rule"]["team_rule_id"] for i in left] == ["NWK-RENT-01"]
    assert left[0]["needs_fact"] == [] and "only linked" in left[0]["needs_other"]


@pytest.mark.parametrize(
    "body",
    [
        {"address": {"state": "TX", "jurisdiction": None}},
        {"address": {"state": "CA", "jurisdiction": "Oakland, CA"}},
        {"address": {"state": "CA", "jurisdiction": "Boston, MA"}},
        {"address": {"state": "CA"}, "facts": {"units": 0}},
        {"address": {"state": "CA"}, "facts": {"year_built": 1500}},
        {"address": {"state": "CA"}, "facts": {"year_built": 2099}},
        {"address": {"state": "CA"}, "facts": {"name": "x"}},
        {"address": {"state": "CA"}, "as_of": "1990-01-01"},
        {"address": {"state": "CA"}, "as_of": "not-a-date"},
        {"address": {"state": "ca"}},
    ],
)
def test_evaluate_validation(body):
    assert client.post("/api/evaluate", json=body).status_code == 422


def test_evaluate_ignores_echoed_address_fields():
    r = client.post(
        "/api/evaluate",
        json={"address": {"state": "MA", "jurisdiction": "Boston, MA", "matched_address": "x"}},
    )
    assert r.status_code == 200


def test_live_census():
    """One real call to the US Census geocoder (skipped offline)."""
    try:
        m = AA.census_lookup("1685 Main St, Santa Monica, CA 90401")
    except RuntimeError as e:
        pytest.skip(f"Census geocoder unreachable: {e}")
    d = AA.interpret(m)
    assert d["state"] == "CA" and d["jurisdiction"] == "Santa Monica, CA"
    assert d["county"] == "Los Angeles County"


def test_evaluate_lists_exempt_rules():
    """A new building in San Diego is exempt from the state rent cap: listed under excluded, not shown as "no rule"."""
    body = {
        "address": {"state": "CA", "jurisdiction": "San Diego, CA"},
        "as_of": "2026-10-01",
        "facts": {"year_built": 2015, "units": 20},
    }
    d = client.post("/api/evaluate", json=body).json()
    rent = next(c for c in d["categories"] if c["id"] == "rent_increase_limits")
    assert not [i for i in rent["enacted"] if i["result"] == "applies"]
    ex = {e["id"]: e for e in rent["excluded"]}
    assert "CA-RENT-01" in ex and ex["CA-RENT-01"]["reasons"]
