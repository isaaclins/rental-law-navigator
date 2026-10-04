"""Tests for the rent-increase notice (#96): the math per city (highest lawful rent, start date after the last
increase, notice deadline), EN/ES, and that the numbers are exactly what /api/check returns for the same request.

Run: uv run --with pytest --with httpx pytest tests/test_notice.py -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web import check as C
from web.app import app

client = TestClient(app)
FACTS = {"year_built": 1960, "units": 10, "owner_occupied": False}


@pytest.fixture(autouse=True)
def fresh():
    C.CHECK_LIMIT.hits.clear()
    yield


def notice(**body) -> dict:
    r = client.post("/api/notice", json={"as_of": "2026-10-01", "lang": "en", **body})
    assert r.status_code == 200, r.text
    return r.json()


def same_as_check(d: dict) -> dict:
    """The rent verdict /api/check gives for the notice's own request."""
    r = client.post("/api/check", json=d["check_body"])
    assert r.status_code == 200, r.text
    v = next(x for x in r.json()["verdicts"] if x["id"] == "rent")
    if d["new_rent"]:
        assert v["values"] == d["verdict"]["values"]
        assert v["code"] == d["verdict"]["code"]
    return v


def by(d: dict, title_start: str) -> dict:
    return next(c for c in d["checks"] if c["t"].startswith(title_start))


def test_sf_fulton_matches_the_mockup():
    d = notice(address_id="A0027", current_rent=2400, last_increase="2026-01-01")
    assert (d["start"], d["deadline"], d["new_rent"]) == ("2027-01-01", "2026-12-02", 2438.4)
    assert d["verdict"]["code"] == "within" and not d["over"]
    same_as_check(d)
    text = d["letter"]["text"]
    assert text.startswith(
        "NOTICE OF RENT INCREASE\n\nTo: [Tenant name(s)] and all other occupants\n"
    )
    assert "3918 Fulton St, [Unit], San Francisco, CA 94118" in text
    assert (
        "Your monthly rent will increase from $2,400.00 to $2,438.40, an increase of $38.40 (1.6%), "
        "starting January 1, 2027." in text
    )
    assert "within the limit of the San Francisco Rent Ordinance (S.F. Admin. Code ch. 37)" in text
    assert (
        "annual allowable increase amount effective March 1, 2026 through February 28, 2027 is 1.6%"
        in text
    )
    assert "This notice is given at least 30 days before the new rent starts." in text
    assert "Date given: [on or before Dec 2, 2026]" in text
    assert [c["st"] for c in d["checks"]] == ["ok", "ok", "ok", "info"]
    assert by(d, "Within the 1.6% cap")["s"] == "Highest allowed: $2,438.40 · until Feb 28, 2027"
    assert by(d, "30 days' notice")["s"] == "Give it by Dec 2, 2026 for Jan 1, 2027"
    assert by(d, "30 days' notice")["quote"].startswith(
        "State law requires landlords to provide 30 days'"
    )
    assert by(d, "One increase a year")["s"] == "Last increase Jan 1, 2026"
    assert by(d, "Other required notices")["s"].startswith("None in our sources for this address.")
    assert "compliant" not in text.lower() and "complies" not in text.lower()


def test_sf_spanish():
    d = notice(address_id="A0027", current_rent=2400, last_increase="2026-01-01", lang="es")
    text = d["letter"]["text"]
    assert text.startswith(
        "AVISO DE AUMENTO DE RENTA\n\nPara: [Nombre(s) del inquilino] y todos los demás ocupantes"
    )
    assert (
        "Su renta mensual aumentará de $2,400.00 a $2,438.40, un aumento de $38.40 (1.6%), a partir del 1 de enero de 2027."
        in text
    )
    assert "Este aviso se entrega al menos 30 días antes de que empiece la nueva renta." in text
    assert "Fecha de entrega: [a más tardar el 2 dic 2026]" in text
    assert [c["t"] for c in d["checks"]][:3] == [
        "Dentro del límite del 1.6%",
        "30 días de aviso",
        "Un aumento al año",
    ]
    for w in ("Your monthly", "starting", "Date given"):
        assert w not in text


def test_over_the_cap_turns_red_with_the_check_amount():
    d = notice(address_id="A0027", current_rent=2400, last_increase="2026-01-01", new_rent=2500)
    assert d["over"] and d["verdict"]["code"] == "over"
    v = same_as_check(d)
    assert v["values"]["over_amount"] == 61.6
    assert by(d, "Over the 1.6% cap by $61.60")["st"] == "over"
    seg = next(s for b in d["letter"]["blocks"] for s in b["s"] if s.get("t") == "$2,500.00")
    assert seg.get("over") == 1


def test_start_date_one_increase_a_year_and_notice_deadline():
    # LA RSO (once every 12 months, 3% for 7/1/2025-6/30/2026), drafted on Mar 1, 2026
    d = notice(
        address_id="A0001", current_rent=2000, last_increase="2025-03-15", as_of="2026-03-01"
    )
    assert (d["start"], d["deadline"], d["new_rent"]) == ("2026-04-01", "2026-03-02", 2060.0)
    assert d["earliest_by_year"] == "2026-03-15" and d["annual"]
    same_as_check(d)
    assert (
        "Your monthly rent will increase from $2,000.00 to $2,060.00, an increase of $60.00 (3%)"
        in d["letter"]["text"]
    )
    # Berkeley 2026 AGA 1%: Feb 1 would leave only 17 days' notice, so the start moves to Mar 1
    b = notice(
        place={"state": "CA", "jurisdiction": "Berkeley, CA"},
        facts=FACTS,
        current_rent=2000,
        last_increase="2025-02-01",
        as_of="2026-01-15",
        address_text="2200 Blake St, Berkeley, CA",
    )
    assert (b["start"], b["deadline"], b["new_rent"]) == ("2026-03-01", "2026-01-30", 2020.0)
    same_as_check(b)


def test_state_cap_with_cpi_and_santa_ana_other_notice():
    ca = notice(address_id="A0023", current_rent=2000, last_increase="2025-12-01", cpi=3)
    assert (ca["start"], ca["deadline"], ca["new_rent"]) == ("2026-12-01", "2026-11-01", 2160.0)
    same_as_check(ca)
    assert by(ca, "Within the 8% cap")["s"] == "Highest allowed: $2,160 · with a CPI change of 3%"
    sa = notice(
        place={"state": "CA", "jurisdiction": "Santa Ana, CA"},
        facts=FACTS,
        current_rent=3000,
        address_text="100 Main St, Santa Ana, CA",
    )
    assert (sa["start"], sa["deadline"], sa["new_rent"]) == ("2026-11-01", "2026-10-02", 3086.1)
    same_as_check(sa)
    other = by(sa, "Other required notices")
    assert "written notice of the ordinance" in other["s"] and other["url"]
    assert by(sa, "One increase a year")["st"] == "info"  # no last increase given: asks for it


def test_missing_figures_are_never_invented():
    la = notice(address_id="A0001", current_rent=2000, last_increase="2025-12-01")
    assert la["new_rent"] is None and la["verdict"]["code"] == "need_figure"
    assert "to [new rent], starting December 1, 2026." in la["letter"]["text"]
    assert by(la, "No figure for Dec 1, 2026")["st"] == "info"
    assert by(la, "Notice period")["s"].startswith("30 days for an increase under 10%")
    cpi = notice(address_id="A0023", current_rent=2000, last_increase="2025-12-01")
    assert cpi["new_rent"] is None
    assert (
        by(cpi, "The cap depends on the local CPI")["s"]
        == "5% + the CPI change, at most 10%. Enter the CPI."
    )
    boston = notice(address_id="A0006", current_rent=3000, new_rent=3200)
    assert boston["verdict"]["code"] == "state_bar" and boston["deadline"] is None
    assert by(boston, "No rent cap in our sources")["st"] == "info"
    assert "do not state the notice period" in by(boston, "Notice period")["s"]
    assert "This notice is given" not in boston["letter"]["text"]


def test_dates_that_break_the_rules_are_flagged():
    soon = notice(
        address_id="A0027", current_rent=2400, last_increase="2026-01-01", start="2026-12-01"
    )
    assert (
        soon["over"]
        and by(soon, "Less than 12 months after the last increase")["s"] == "Earliest: Jan 1, 2027"
    )
    late = notice(address_id="A0027", current_rent=2400, start="2026-10-15")
    assert late["over"] and by(late, "Too late for 30 days' notice")["st"] == "over"
    assert "[Date given]" in late["letter"]["text"]


def test_fields_stay_in_the_browser():
    bad = client.post(
        "/api/notice", json={"address_id": "A0027", "current_rent": 2400, "tenant": "Maria"}
    )
    assert bad.status_code == 422
    d = notice(address_id="A0027", current_rent=2400)
    fields = [s["f"] for b in d["letter"]["blocks"] for s in b["s"] if "f" in s]
    assert fields == ["tenant", "unit", "owner", "contact", "given"]


def test_notice_never_prints_a_negative_increase():
    """A new rent below the current one (a typo, or a fast clear + type) leaves the placeholder, never '$-237,574.00'."""
    from fastapi.testclient import TestClient

    from web.app import app

    c = TestClient(app)
    for lang in ("en", "es"):
        r = c.post(
            "/api/notice",
            json={"address_id": "A0016", "current_rent": 240000, "new_rent": 2450, "lang": lang},
        )
        if r.status_code != 200:
            continue
        text = str(r.json())
        assert "$-" not in text and "-$" not in text
