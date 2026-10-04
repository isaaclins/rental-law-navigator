"""Tests for the rent-increase / deposit / fee / notice check (#40): the text parsers and the verdicts per address.

Run: uv run --with pytest --with httpx pytest tests/test_check.py -q
"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from web import check as C
from web.app import STORE, app

client = TestClient(app)
D = dt.date


@pytest.fixture(autouse=True)
def fresh():
    C.CHECK_LIMIT.hits.clear()
    yield


def post(**body) -> dict:
    r = client.post("/api/check", json=body)
    assert r.status_code == 200, r.text
    return {v["id"]: v for v in r.json()["verdicts"]}


# ------------------------------------------------------------------ parsers
def test_parse_period_slash_dates():
    p = C.parse_rent_cap(
        "Once per 12 months; annual percentage set by LAHD (3% for 7/1/2025–6/30/2026)"
    )
    assert p["periods"] == [(3.0, D(2025, 7, 1), D(2026, 6, 30))]
    assert C.cap_on(p, D(2026, 3, 1))["pct"] == 3.0
    assert C.cap_on(p, D(2026, 7, 1)) == {"pct": None, "need": "rate_figure"}


def test_parse_period_parenthesis_and_long_dates():
    p = C.parse_rent_cap(
        "1.6% (3/1/2026–2/28/2027)",
        "the annual allowable increase is 1.6% of base rent for March 1, 2026 through February 28, 2027 (1.4% prior year)",
    )
    assert p["periods"] == [(1.6, D(2026, 3, 1), D(2027, 2, 28))]


def test_parse_cpi_formula_ca():
    p = C.parse_rent_cap("5% + CPI, max 10%")
    assert p["formula"] == {"base": 5.0, "share": 1.0, "max": 10.0}
    assert C.cap_on(p, D(2026, 10, 1))["need"] == "cpi"
    assert C.cap_on(p, D(2026, 10, 1), cpi=3.0)["pct"] == 8.0
    assert C.cap_on(p, D(2026, 10, 1), cpi=7.0)["pct"] == 10.0


def test_parse_santa_ana_and_berkeley():
    sa = C.parse_rent_cap("Lesser of 3% or 80% of CPI change; 2.87% for 9/1/2026-8/31/2027")
    assert sa["periods"] == [(2.87, D(2026, 9, 1), D(2027, 8, 31))]
    assert sa["formula"] == {"base": 0.0, "share": 0.8, "max": 3.0}
    assert C.cap_on(sa, D(2026, 3, 1), cpi=2.5)["pct"] == 2.0
    ber = C.parse_rent_cap("AGA = 65% of CPI, max 5%; 2026 AGA 1.0%")
    assert ber["periods"] == [(1.0, D(2026, 1, 1), D(2026, 12, 31))]
    assert ber["formula"]["max"] == 5.0


def test_parse_state_bar_and_text_only():
    assert C.parse_rent_cap("state bar on local rent control")["bar"]
    p = C.parse_rent_cap("Rent control for buildings with 5+ units")
    assert C.cap_on(p, D(2026, 10, 1)) == {"pct": None, "need": "rate_figure"}


def test_rent_verdict_math():
    v = C.rent_verdict(2000, 2100, {"pct": 3.0})
    assert v["kind"] == "over"
    assert v["values"]["over_amount"] == 40.0 and v["values"]["over_pct"] == 2.0
    assert C.rent_verdict(2000, 2060, {"pct": 3.0})["kind"] == "ok"
    assert C.rent_verdict(2000, 1900, {"pct": None})["code"] == "no_increase"
    # unknown CPI: an increase above the maximum is over in any case, below it is "can't tell"
    f = {"pct": None, "need": "cpi", "base": 5.0, "share": 1.0, "max": 10.0}
    assert C.rent_verdict(2000, 2300, f)["code"] == "over_max"
    v = C.rent_verdict(2000, 2140, f)
    assert (
        v["kind"] == "unknown" and v["need"] == {"key": "cpi"} and v["values"]["cpi_needed"] == 2.0
    )


def test_parse_deposit_and_fee():
    assert C.parse_deposit_cap("1 month's rent (2 months for qualifying small landlords)") == {
        "months": 1.0,
        "alt_months": 2.0,
    }
    assert (
        C.parse_deposit_cap("1.5 months' rent; annual increase max 10%; return within 30 days")[
            "months"
        ]
        == 1.5
    )
    assert (
        C.parse_deposit_cap("Max = first month's rent; separate interest-bearing account")["months"]
        == 1.0
    )
    assert C.parse_deposit_cap("4.2% interest (3/1/2026–2/28/2027)") is None
    ca = C.parse_fee_cap(
        "$30 base per applicant, CPI-adjusted annually since 1998 ($68.96 for 2026 per Berkeley Rent Board)",
        "2026-01-01",
    )
    assert C.fee_cap_on(ca, D(2026, 5, 1))["amount"] == 68.96
    assert C.fee_cap_on(ca, D(2027, 5, 1)) == {"amount": None, "year": 2027}
    nj = C.parse_fee_cap("$50 per application, CPI-adjusted annually", "2026-05-01")
    assert C.fee_cap_on(nj, D(2026, 10, 1))["amount"] == 50.0
    assert C.fee_cap_on(nj, D(2027, 6, 1))["amount"] is None
    assert C.parse_fee_cap("First, last, security deposit, lock/key only", None) == {
        "amount": 0.0,
        "not_listed": True,
    }
    assert C.parse_fee_cap("Broker fee paid only by party who hired the broker", None) is None


def test_tenancy_minimum():
    assert C.tenancy_minimum({"key_value": "Just cause after 12 months; relocation"}) == (
        12,
        "month",
    )
    assert C.tenancy_minimum({"requirement": "After 30 days of tenancy, an owner cannot"}) == (
        30,
        "day",
    )
    assert C.tenancy_minimum({"key_value": "17 just causes"}) is None


# ------------------------------------------------------------------ verdicts per address
def test_la_rso_building_3_percent():
    # A0001: 6238 De Longpre Ave, Los Angeles, 32 units, built 1927 -> LA RSO, 3% for 7/1/2025-6/30/2026
    v = post(
        address_id="A0001",
        current_rent=2000,
        new_rent=2100,
        notice_date="2026-02-01",
        effective_date="2026-03-15",
    )
    assert v["rent"]["kind"] == "over"
    assert v["rent"]["values"]["cap_pct"] == 3.0
    assert v["rent"]["values"]["over_amount"] == 40.0
    assert v["rent"]["rules"][0]["id"] == "LA-RENT-01"
    assert v["rent"]["rules"][0]["quote"]
    assert v["notice"]["kind"] == "ok"
    ok = post(
        address_id="A0001",
        current_rent=2000,
        increase_pct=3,
        notice_date="2026-02-01",
        effective_date="2026-03-15",
    )
    assert ok["rent"]["kind"] == "ok" and ok["rent"]["values"]["max_rent"] == 2060.0


def test_la_rso_after_the_published_period_is_cant_tell():
    v = post(
        address_id="A0001",
        current_rent=2000,
        increase_pct=3,
        notice_date="2026-09-01",
        effective_date="2026-10-15",
    )
    assert v["rent"]["kind"] == "unknown"
    assert v["rent"]["need"]["key"] == "rate_figure"


def test_ab1482_building_needs_cpi():
    # A0023: Los Angeles, built 1987 -> not RSO, state cap 5% + CPI (max 10%)
    v = post(
        address_id="A0023",
        current_rent=2000,
        increase_pct=4,
        notice_date="2026-09-01",
        effective_date="2026-10-15",
    )
    assert v["rent"]["rules"][0]["id"] == "CA-RENT-01"
    assert v["rent"]["kind"] == "unknown" and v["rent"]["need"]["key"] == "cpi"
    over = post(
        address_id="A0023",
        current_rent=2000,
        increase_pct=12,
        notice_date="2026-09-01",
        effective_date="2026-10-15",
    )
    assert over["rent"]["code"] == "over_max" and over["rent"]["values"]["over_amount"] == 40.0
    known = post(
        address_id="A0023",
        current_rent=2000,
        increase_pct=9,
        effective_date="2026-10-15",
        notice_date="2026-09-01",
        cpi=3,
    )
    assert known["rent"]["kind"] == "over" and known["rent"]["values"]["cap_pct"] == 8.0


def test_sf_rent_ordinance():
    # A0016: 3515 Fillmore St, San Francisco, built 1926 -> 1.6% for 3/1/2026-2/28/2027
    v = post(
        address_id="A0016",
        current_rent=3000,
        new_rent=3048,
        notice_date="2026-09-01",
        effective_date="2026-10-15",
        deposit=3000,
    )
    assert v["rent"]["kind"] == "ok" and v["rent"]["rules"][0]["id"] == "SF-RENT-01"
    assert v["deposit"]["kind"] == "ok"
    over = post(
        address_id="A0016",
        current_rent=3000,
        new_rent=3100,
        notice_date="2026-09-20",
        effective_date="2026-10-15",
    )
    assert over["rent"]["kind"] == "over" and over["rent"]["values"]["over_amount"] == 52.0
    assert over["notice"]["kind"] == "short" and over["notice"]["values"]["days_needed"] == 30


def test_exempt_building_no_cap_applies():
    # A0022: Los Angeles, built 2012 -> new construction: neither the RSO nor the state cap covers it
    v = post(
        address_id="A0022",
        current_rent=3000,
        new_rent=3600,
        effective_date="2026-10-15",
        notice_date="2026-09-01",
    )
    assert v["rent"]["kind"] == "none" and v["rent"]["code"] == "no_cap"
    assert {x["id"] for x in v["rent"]["excluded"]} == {"CA-RENT-01", "LA-RENT-01"}


def test_missing_building_fact_is_named():
    # A0019: San Diego, year built not in the data
    v = post(
        address_id="A0019",
        current_rent=3000,
        new_rent=3100,
        effective_date="2026-10-15",
        notice_date="2026-09-01",
    )
    assert v["rent"]["kind"] == "unknown" and v["rent"]["need"]["key"] == "year_built"
    v = post(
        address_id="A0019",
        current_rent=3000,
        new_rent=3100,
        effective_date="2026-10-15",
        notice_date="2026-09-01",
        facts={"year_built": 1970},
    )
    assert v["rent"]["need"]["key"] == "cpi"


def test_deposit_fee_and_termination():
    v = post(
        address_id="A0001",
        effective_date="2026-03-15",
        current_rent=2000,
        deposit=3000,
        application_fee=80,
        termination="no_reason",
    )
    # A0001 has 32 units: the 2-month small-landlord exception can't apply, the cap is one month (legal review #1)
    dep = v["deposit"]
    assert (
        dep["kind"] == "over" and dep["values"]["small_excluded"] and dep["values"]["units"] == 32
    )
    assert dep["values"]["max"] == 2000 and dep["values"]["over_amount"] == 1000
    assert v["fee"]["kind"] == "over" and v["fee"]["values"]["over_amount"] == 11.04
    assert v["termination"]["kind"] == "over" and v["termination"]["code"] == "reason_required"
    ma = post(address_id="A0006", current_rent=3000, application_fee=40, deposit=3500)
    assert ma["fee"]["code"] == "not_listed" and ma["deposit"]["kind"] == "over"
    # state just-cause law (outside the cities in scope): protection starts after 12 months
    ca = {
        "place": {"state": "CA"},
        "facts": {"year_built": 1960, "units": 10},
        "effective_date": "2026-10-15",
        "termination": "no_reason",
    }
    assert post(**ca)["termination"]["need"]["key"] == "moved_in"
    assert post(**ca, moved_in="2026-03-01")["termination"]["code"] == "not_yet_protected"
    assert post(**ca, moved_in="2024-03-01")["termination"]["code"] == "reason_required"


def test_any_address_and_validation():
    v = post(
        place={"state": "CA", "jurisdiction": "Santa Ana, CA"},
        facts={"year_built": 1960, "units": 10},
        current_rent=3000,
        new_rent=3090,
        effective_date="2026-10-15",
        notice_date="2026-09-01",
    )
    assert v["rent"]["kind"] == "over" and v["rent"]["values"]["cap_pct"] == 2.87
    r = client.post(
        "/api/check",
        json={"address_id": "A0001", "notice_date": "2026-05-01", "effective_date": "2026-04-01"},
    )
    assert r.status_code == 422
    assert client.post("/api/check", json={"current_rent": 100}).status_code == 422


# ------------------------------------------------------------------ legal review 2026-10-04: small-landlord deposits
def test_deposit_small_landlord_exception_follows_the_unit_count():
    """One test (web/headlines.small_landlord_possible) for Check, Listen and the address page: a building with more
    than 4 units, or '5 or more' by use code, can't be a small landlord's; the cap is then one month."""
    big = post(address_id="A0016", current_rent=2000, deposit=4000)["deposit"]  # SF, 21 units
    assert (
        big["kind"] == "over"
        and big["values"]["over_amount"] == 2000
        and big["values"]["max"] == 2000
    )
    assert big["values"]["small_excluded"] and "alt_max" not in big["values"]
    six = post(address_id="A0007", current_rent=2000, deposit=4000)["deposit"]  # LA, 6 units
    assert six["kind"] == "over" and six["values"]["over_amount"] == 2000
    # a building whose count is unknown or small: the landlord type decides
    small = {
        "place": {"state": "CA", "jurisdiction": "Los Angeles, CA"},
        "current_rent": 2000,
        "deposit": 4000,
    }
    assert post(**small)["deposit"]["code"] == "need_landlord"
    assert post(**small, facts={"units": 3})["deposit"]["code"] == "need_landlord"
    assert post(**small, facts={"units": 6})["deposit"]["values"]["small_excluded"]
    # Santa Monica: the same test
    sm = post(
        place={"state": "CA", "jurisdiction": "Santa Monica, CA"},
        facts={"units": 12},
        current_rent=2000,
        deposit=4000,
    )["deposit"]
    assert sm["kind"] == "over" and sm["values"]["max"] == 2000


def test_nj_fee_cap_is_flat_in_2026_and_needs_the_cpi_figure_from_2027():
    """D066 § 1d: $50 flat until the first CPI adjustment on Jan 1, 2027 (legal review NJ-FEE-01)."""
    from web import check as C

    p = C.parse_fee_cap("$50 per application (CPI-adjusted yearly from 2027)", "2026-05-01")
    assert C.fee_cap_on(p, dt.date(2026, 12, 31)) == {"amount": 50.0, "until": "2026-12-31"}
    assert C.fee_cap_on(p, dt.date(2027, 3, 1)) == {"amount": None, "year": 2027}
    nj = next(i for i, a in STORE.addresses.items() if a.get("resolved_city") == "Newark")
    assert (
        post(address_id=nj, as_of="2026-10-01", application_fee=55)["fee"]["values"]["over_amount"]
        == 5
    )
    later = post(address_id=nj, as_of="2027-03-01", application_fee=55)["fee"]
    assert later["code"] == "need_figure" and later["need"] == {"key": "fee_figure", "year": 2027}
