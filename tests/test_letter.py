"""Tests for the letter to the landlord (#122): the template fill per city, EN/ES, and that every number in the
letter is the one /api/check returns for the same body.

Run: uv run --with pytest --with httpx pytest tests/test_letter.py -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web import check as C
from web import letter as LT
from web.app import app

client = TestClient(app)
FACTS = {"year_built": 1960, "units": 10, "owner_occupied": False}


@pytest.fixture(autouse=True)
def fresh():
    C.CHECK_LIMIT.hits.clear()
    yield


def letter(**body) -> dict:
    r = client.post("/api/letter", json={"letter_date": "2026-10-04", **body})
    assert r.status_code == 200, r.text
    return r.json()


def rent_check(**body) -> dict:
    body.pop("address_text", None)
    r = client.post("/api/check", json=body)
    assert r.status_code == 200, r.text
    return next(v for v in r.json()["verdicts"] if v["id"] == "rent")


FULTON = dict(
    address_id="A0027",
    current_rent=2400,
    new_rent=2520,
    notice_date="2026-09-20",
    effective_date="2026-11-01",
)


def test_sf_fulton_en_matches_the_mockup():
    d = letter(**FULTON, lang="en")
    text = d["letter"]["text"]
    assert text.startswith(
        "October 4, 2026\n\n[Your name]\n3918 Fulton St, [Unit]\nSan Francisco, CA\n"
    )
    assert "Re: Rent increase notice dated September 20, 2026" in text
    assert "Dear [Landlord's name]," in text
    assert (
        "Your notice raises my rent from $2,400 to $2,520 a month from November 1, 2026. That is a 5% increase."
        in text
    )
    assert (
        "I believe my unit is covered by the San Francisco Rent Ordinance (S.F. Admin. Code ch. 37). "
        "The city's Rent Board states:" in text
    )
    assert (
        "“For rent-controlled units, the annual allowable increase amount effective March 1, 2026 through "
        "February 28, 2027 is 1.6%”" in text
    )
    assert "Source: https://www.sf.gov/news--annual-rent-increase-3126-22827-announced" in text
    assert (
        "At 1.6%, my rent can be at most $2,438.40 a month ($2,400 × 1.016). This does not count increases the"
        " Rent Board approves on a petition, such as for capital improvements, or other exceptions. Please send me"
        " a corrected notice." in text
    )
    assert text.rstrip().endswith("Thank you,\n[Your name]")
    assert [s["t"] for s in d["summary"]] == [
        "You got $2,400 → $2,520",
        "The limit is 1.6%",
        "You ask for a corrected notice",
    ]
    assert d["summary"][1]["s"] == "Until Feb 28, 2027 · S.F. Admin. Code ch. 37"
    assert d["summary"][2]["s"] == "At most $2,438.40 a month"
    assert d["help"]["url"] == "https://sf.gov/departments/rent-board"
    assert "San Francisco Rent Board or a tenant organization can help" in d["help"]["line"]
    assert d["title"] == "Letter to landlord - 3918 Fulton St"


def test_sf_fulton_es_is_spanish_with_the_same_numbers():
    d = letter(**FULTON, lang="es")
    text = d["letter"]["text"]
    assert text.startswith("4 de octubre de 2026\n\n[Su nombre]\n3918 Fulton St, [Unidad]\n")
    assert "Asunto: aviso de aumento de renta del 20 de septiembre de 2026" in text
    assert "Estimado/a [Nombre del arrendador]:" in text
    assert (
        "Su aviso aumenta mi renta de $2,400 a $2,520 al mes a partir del 1 de noviembre de 2026."
        in text
    )
    assert "Es un aumento del 5%." in text
    assert "la Ordenanza de Rentas de San Francisco" in text
    assert (
        "como máximo de $2,438.40 al mes ($2,400 × 1.016). Esto no cuenta los aumentos que la Junta de Rentas"
        " aprueba por petición, como por mejoras de capital, ni otras excepciones. Le pido que me envíe un aviso"
        " corregido." in text
    )
    assert "Fuente (texto original en inglés): https://www.sf.gov/" in text
    assert text.rstrip().endswith("Atentamente,\n[Su nombre]")
    # the quote stays the law's own words
    assert "For rent-controlled units, the annual allowable increase amount" in text
    assert d["help"]["name"] == "Junta de Rentas de San Francisco"
    assert d["help"]["line"].startswith("Lea la fuente citada. La Junta de Rentas de San Francisco")
    for w in ("Your notice", "Dear", "Thank you", "a month"):
        assert w not in text


CASES = [
    # LA RSO building, 3% cap period, notice too short
    (
        dict(
            address_id="A0001",
            current_rent=2000,
            new_rent=2100,
            notice_date="2026-02-20",
            effective_date="2026-03-15",
        ),
        "the Los Angeles Rent Stabilization Ordinance",
        "la Ordenanza de Estabilización de Rentas de Los Ángeles",
        "https://housing.lacity.gov/residents",
    ),
    # Berkeley (any address), 2026 AGA 1.0%
    (
        dict(
            place={"state": "CA", "jurisdiction": "Berkeley, CA"},
            facts=FACTS,
            current_rent=2000,
            increase_pct=5,
            effective_date="2026-03-15",
            address_text="2200 Blake St, Berkeley, CA",
        ),
        "the Berkeley Rent Stabilization Ordinance",
        "la Ordenanza de Estabilización de Rentas de Berkeley",
        "https://rentboard.berkeleyca.gov",
    ),
    # Santa Ana, 2.87% period
    (
        dict(
            place={"state": "CA", "jurisdiction": "Santa Ana, CA"},
            facts=FACTS,
            current_rent=3000,
            new_rent=3090,
            notice_date="2026-09-01",
            effective_date="2026-10-15",
        ),
        "the Santa Ana Rent Stabilization Ordinance",
        "la Ordenanza de Estabilización de Rentas de Santa Ana",
        "https://www.usa.gov/tenant-rights",
    ),
    # state cap, CPI unknown but over the 10% maximum
    (
        dict(
            address_id="A0023",
            current_rent=2000,
            increase_pct=12,
            notice_date="2026-09-01",
            effective_date="2026-10-15",
        ),
        "the California Tenant Protection Act",
        "la Ley de Protección al Inquilino de California",
        "https://housing.lacity.gov/residents",
    ),
    # state cap with a known CPI change: 5% + 3% = 8%
    (
        dict(
            address_id="A0023",
            current_rent=2000,
            increase_pct=9,
            notice_date="2026-09-01",
            effective_date="2026-10-15",
            cpi=3,
        ),
        "the California Tenant Protection Act",
        "la Ley de Protección al Inquilino de California",
        "https://housing.lacity.gov/residents",
    ),
    # San Diego (state law only), over the 10% maximum
    (
        dict(
            place={"state": "CA", "jurisdiction": "San Diego, CA"},
            facts=FACTS,
            current_rent=2500,
            increase_pct=15,
            effective_date="2026-10-15",
            address_text="1010 Market St, San Diego, CA",
        ),
        "the California Tenant Protection Act",
        "la Ley de Protección al Inquilino de California",
        "https://www.usa.gov/tenant-rights",
    ),
]


@pytest.mark.parametrize("body,law_en,law_es,help_url", CASES)
def test_every_city_fills_the_template_with_the_check_numbers(body, law_en, law_es, help_url):
    v = rent_check(**body, lang="en")
    assert v["code"] in ("over", "over_max")
    x = v["values"]
    limit = x["cap_max"] if v["code"] == "over_max" else x["cap_pct"]
    for lang, law in (("en", law_en), ("es", law_es)):
        d = letter(**body, lang=lang)
        assert d["verdict"]["values"] == x  # the letter's numbers are the check's numbers
        text = d["letter"]["text"]
        assert law in text
        for amount in (x["current_rent"], x["new_rent"], x["max_rent"]):
            assert LT.money(amount) in text
        assert LT.pct(x["increase_pct"]) in text
        assert LT.pct(limit) in text
        assert f"{LT.money(x['current_rent'])} × {LT.num(1 + limit / 100)}" in text
        assert v["rules"][0]["citation"] in text
        # the quoted sentence states the figure the letter uses (letter_quote: Berkeley's 1.0% is D008's, Santa
        # Ana's 2.87% D084's; legal review BER-RENT-01)
        r0 = v["rules"][0]
        assert (r0.get("letter_quote_url") or r0["url"]) in text
        if r0.get("letter_quote") and v["cap"].get("basis") == "period":
            assert (
                LT.quote_text(r0["letter_quote"]) in text
                and LT.pct(limit).rstrip("%") in r0["letter_quote"]
            )
        assert d["help"]["url"] == help_url
        assert d["summary"][2]["s"].endswith(
            f"{LT.money(x['max_rent'])} a month"
            if lang == "en"
            else f"{LT.money(x['max_rent'])} al mes"
        )
        if body.get("address_text"):
            assert body["address_text"].split(",")[0] in text
        # amounts in the letter are exactly the check's, recomputed independently
        assert round(x["current_rent"] * (1 + limit / 100), 2) == x["max_rent"]


def test_short_notice_adds_its_rule_and_date():
    d = letter(**CASES[0][0], lang="en")
    text = d["letter"]["text"]
    assert "The notice also came 23 days before the increase." in text
    assert "cannot take effect before March 22, 2026." in text
    assert "State law requires landlords to provide 30 days' written advance notice" in text
    assert text.index("Please send me a corrected notice.") > text.index("March 22, 2026")
    assert d["summary"][3] == {"t": "The notice was too short", "s": "30 days needed, 23 given"}
    es = letter(**CASES[0][0], lang="es")["letter"]["text"]
    assert "Además, el aviso llegó 23 días antes del aumento." in es
    assert "antes del 22 de marzo de 2026." in es


def test_cap_basis_wording():
    over_max = letter(**CASES[3][0], lang="en")["letter"]["text"]
    assert (
        "Even at the highest limit the law allows, 10%, my rent can be at most $2,200 a month ($2,000 × 1.1)."
        in over_max
    )
    cpi = letter(**CASES[4][0], lang="en")["letter"]["text"]
    assert (
        "With a cost-of-living (CPI) change of 3%, the limit is 8%, so my rent can be at most $2,160"
        in cpi
    )
    la = letter(**CASES[0][0], lang="en")["letter"]["text"]
    # the scraped link label "(click here to" is trimmed from the span itself (navigator.extract._trim_dangling_spans)
    assert "(click here to" not in la and "allowable rent increase percentage" in la


def test_not_over_is_refused_and_fields_never_reach_the_server():
    within = client.post(
        "/api/letter", json={**FULTON, "new_rent": 2430, "lang": "en"}
    )  # within the 1.6% cap
    assert within.status_code == 422 and within.json()["detail"] == "not_over"
    no_cap = client.post(
        "/api/letter",
        json={"address_id": "A0006", "current_rent": 3000, "new_rent": 4000, "lang": "en"},
    )  # Boston: state bar on rent control
    assert no_cap.status_code == 422
    bad = client.post("/api/letter", json={**FULTON, "your_name": "Maria"})
    assert bad.status_code == 422  # unknown fields are rejected: names stay in the browser
    d = letter(**FULTON, lang="en")
    fields = [s["f"] for b in d["letter"]["blocks"] for s in b["s"] if "f" in s]
    assert fields == ["name", "unit", "landlord", "name"]
    assert (
        LT.to_text(d["letter"]["blocks"], "en", {"name": "Maria Lopez"})
        .rstrip()
        .endswith("Maria Lopez")
    )


def test_exceptions_line_only_where_the_city_source_names_them():
    """The letter never claims a hard maximum where the city's source names more (#audit 2026-10-04): banked
    increases only for Berkeley (its source says so), pass-through/surcharge exceptions for SF and LA, nothing for
    the state cap or Santa Ana."""
    by_law = {}
    for body, law_en, _, _ in CASES:
        by_law[law_en] = letter(**body, lang="en")["letter"]["text"]
    assert "banked" in by_law["the Berkeley Rent Stabilization Ordinance"]
    assert "surcharges the city allows" in by_law["the Los Angeles Rent Stabilization Ordinance"]
    for law in (
        "the Santa Ana Rent Stabilization Ordinance",
        "the California Tenant Protection Act",
    ):
        assert "does not count" not in by_law[law]
    assert all(
        "banked" not in t
        for k, t in by_law.items()
        if k != "the Berkeley Rent Stabilization Ordinance"
    )


def test_article_before_a_number():
    for n, a in (
        ("8.33%", "an"),
        ("11%", "an"),
        ("18.5%", "an"),
        ("80%", "an"),
        ("1.5%", "a"),
        ("110%", "a"),
        ("5%", "a"),
        ("1.8%", "a"),
        ("11,000", "an"),
    ):
        assert LT.article(n) == a, n
