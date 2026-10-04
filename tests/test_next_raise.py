"""#152 "When can I raise the rent next?": date, amount and notice math, the engine's honest states, the API and the
calendar's notice-deadline events. No network: temporary database and secret (see tests/test_accounts.py)."""

from __future__ import annotations

import datetime as dt
import json

import pytest
from fastapi.testclient import TestClient

from web import accounts as A
from web.app import app

D = dt.date


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGATOR_SESSION_SECRET", str(tmp_path / "secret"))
    monkeypatch.setenv("NAVIGATOR_ACCOUNTS_DB", str(tmp_path / "private" / "accounts.db"))
    monkeypatch.setenv("NAVIGATOR_GOOGLE_OAUTH", str(tmp_path / "none.json"))
    monkeypatch.setattr(A, "LIMITS", {k: A.RateLimit(v.n, v.per) for k, v in A.LIMITS.items()})
    return tmp_path


# ------------------------------------------------------------------ pure math
def test_twelve_month_spacing_and_notice_deadline():
    r = A.raise_dates(D(2026, 1, 1), D(2026, 10, 1), 30)
    assert r["date"] == D(2027, 1, 1) and r["notice_by"] == D(2026, 12, 2) and not r["now"]
    # month ends and leap days: never an invalid date, never earlier than 12 months
    assert A.raise_dates(D(2026, 1, 31), D(2026, 2, 1), 30)["date"] == D(2027, 1, 31)
    assert A.raise_dates(D(2024, 2, 29), D(2024, 3, 1), 30)["date"] == D(2025, 2, 28)


def test_overdue_raise_starts_after_a_full_notice_from_today():
    r = A.raise_dates(D(2025, 3, 15), D(2026, 10, 1), 30)
    assert r["now"] and r["date"] == D(2026, 10, 31) and r["notice_by"] == D(2026, 10, 1)
    # 12 months end inside the notice window: the notice period wins
    r = A.raise_dates(D(2025, 10, 10), D(2026, 10, 1), 30)
    assert r["date"] == D(2026, 10, 31)


def test_no_notice_rule_means_no_deadline():
    r = A.raise_dates(D(2026, 2, 1), D(2026, 10, 1), None)
    assert r["date"] == D(2027, 2, 1) and r["notice_by"] is None


def test_max_rent_rounding():
    assert A.max_rent(2400, 1.6) == 2438.40
    assert A.max_rent(1850, 3.0) == 1905.50
    assert A.max_rent(3149.99, 1.6) == 3200.39


# ------------------------------------------------------------------ the engine on a future date
SF = json.dumps(
    {
        "year_built": 1923,
        "units": 6,
        "owner_occupied": False,
        "certificate_of_occupancy_date": None,
    },
    sort_keys=True,
)
NEW = json.dumps(
    {
        "year_built": 2005,
        "units": 6,
        "owner_occupied": False,
        "certificate_of_occupancy_date": None,
    },
    sort_keys=True,
)


def nr(state, jur, facts, last, rent, as_of="2026-10-01"):
    return A._next_raise(state, jur, facts, last, rent, as_of, "en", A._sig())


def test_sf_inside_the_published_period():
    r = nr("CA", "San Francisco, CA", SF, "2026-01-01", 2400.0)
    assert r["state"] == "ok" and r["date"] == "2027-01-01"
    assert r["cap_pct"] == 1.6 and r["max_rent"] == 2438.40 and r["cap_end"] == "2027-02-28"
    assert r["notice"]["days"] == 30 and r["notice"]["by"] == "2026-12-02" and r["notice"]["sure"]
    assert r["notice"]["rule"]["id"] == "CA-NOTICE-INC" and r["notice"]["rule"]["quote"]
    assert r["rules"][0]["id"] == "SF-RENT-01" and "1.6%" in r["rules"][0]["quote"]


def test_cap_not_out_yet_after_the_period():
    r = nr("CA", "San Francisco, CA", SF, "2026-04-01", 3100.0)
    assert r["state"] == "cap_not_out" and r["date"] == "2027-04-01"
    assert r["last_pct"] == 1.6 and r["cap_end"] == "2027-02-28" and "max_rent" not in r
    assert not r["notice"][
        "sure"
    ]  # the period applies to raises under 10%: unknown until the cap is out


def test_figure_out_but_not_in_our_sources():
    la = json.dumps({"year_built": 1964, "units": 39, "owner_occupied": False}, sort_keys=True)
    r = nr("CA", "Los Angeles, CA", la, "2025-12-01", 1850.0)
    assert r["state"] == "not_in_sources" and r["last_pct"] == 3.0 and r["cap_end"] == "2026-06-30"
    assert "max_rent" not in r


def test_state_formula_needs_inflation_and_states_without_a_notice_rule():
    r = nr("CA", "Los Angeles, CA", NEW, "2026-02-01", 2000.0)
    assert r["state"] == "need_cpi" and r["cap_max"] == 10.0 and r["max_rent"] == 2200.0
    r = nr("MA", "Boston, MA", NEW, "2026-02-01", 2000.0)
    assert r["state"] == "no_cap" and r["notice"] is None


def test_need_input_still_reports_todays_cap():
    r = nr("CA", "San Francisco, CA", SF, None, None)
    assert r["state"] == "need_input" and r["cap_now"] == {
        "code": "within",
        "pct": 1.6,
        "end": "2027-02-28",
    }


# ------------------------------------------------------------------ API + calendar
def signed_in(email="landlord@example.com", sub="nr1"):
    c = TestClient(app, base_url="http://testserver")
    uid = A.upsert_google_user(sub, email, "Lee")
    c.cookies.set(A.SESSION_COOKIE, A.sign("session", {"uid": uid, "sid": sub}, 3600))
    return c, {"X-CSRF-Token": c.get("/api/me").json()["csrf"]}


SF_PLACE = {"state": "CA", "jurisdiction": "San Francisco, CA", "place": "San Francisco"}


def test_rent_is_stored_once_and_drives_the_card():
    c, h = signed_in()
    body = {
        "label": "Fulton",
        "address": "3918 Fulton St, San Francisco, CA 94118",
        "place": SF_PLACE,
        "facts": {"year_built": 1923, "units": 6, "owner_occupied": False},
    }
    pid = c.post("/api/properties", json=body, headers=h).json()["id"]
    p = c.get("/api/properties?as_of=2026-10-01").json()["properties"][0]
    assert p["next_raise"]["state"] == "need_input" and p["brief"]["topics"]
    r = c.patch(
        f"/api/properties/{pid}",
        json={"rent": {"last_increase_date": "2026-01-01", "current_rent": 2400}},
        headers=h,
    )
    assert r.status_code == 200 and r.json()["rent"] == {
        "last_increase_date": "2026-01-01",
        "current_rent": 2400.0,
    }
    p = c.get("/api/properties?as_of=2026-10-01").json()["properties"][0]
    assert (
        p["next_raise"]["max_rent"] == 2438.40 and p["next_raise"]["notice"]["by"] == "2026-12-02"
    )
    assert (
        c.patch(
            f"/api/properties/{pid}", json={"rent": {"current_rent": -5}}, headers=h
        ).status_code
        == 422
    )
    assert (
        c.patch(
            f"/api/properties/{pid}",
            json={"rent": {"last_increase_date": None, "current_rent": None}},
            headers=h,
        ).json()["rent"]["current_rent"]
        is None
    )


def test_demo_portfolio_has_example_numbers_and_preview_saves_nothing():
    c = TestClient(app, base_url="http://testserver")
    c.post("/auth/demo")
    h = {"X-CSRF-Token": c.get("/api/me").json()["csrf"]}
    props = c.get("/api/properties?as_of=2026-10-01").json()["properties"]
    assert [p["next_raise"]["state"] for p in props] == ["ok", "not_in_sources", "not_in_sources"]
    hob = props[2]
    assert hob["brief"]["question"]["fact"] == "owner_occupied"
    r = c.post(
        f"/api/properties/{hob['id']}/preview",
        json={"facts": {**hob["facts"], "owner_occupied": True}},
        headers=h,
    )
    assert (
        r.status_code == 200
        and r.json()["summary"]["counts"].get("unknown", 0) < hob["summary"]["counts"]["unknown"]
    )
    again = c.get("/api/properties").json()["properties"][2]
    assert again["facts"]["owner_occupied"] is None  # nothing stored


def test_calendar_has_the_notice_deadline():
    c = TestClient(app, base_url="http://testserver")
    c.post("/auth/demo")
    with A.db() as con:
        user = con.execute("SELECT * FROM users WHERE google_sub = ?", (A.DEMO_SUB,)).fetchone()
    text = A.build_ics(user, "https://navigator.isaaclins.com", D(2026, 10, 4)).replace("\r\n ", "")
    assert (
        "SUMMARY:Send rent notice: Fulton Street flats" in text
        and "DTSTART;VALUE=DATE:20261202" in text
    )
    assert "up to $2\\,438.40 a month" in text
    # after the deadline passed, the next raise moves and so does the event
    later = A.build_ics(user, "https://navigator.isaaclins.com", D(2026, 12, 10)).replace(
        "\r\n ", ""
    )
    assert "DTSTART;VALUE=DATE:20261202" not in later
