"""Dates inside Spanish rule text read in Spanish (web.translate.es_dates)."""

import pytest

from web.translate import es_dates


@pytest.mark.parametrize(
    "text,expected",
    [
        ("el 1978-10-01 o antes", "el 1 oct 1978 o antes"),
        ("3% para 7/1/2025–6/30/2026", "3% para 1 jul 2025–30 jun 2026"),
        ("avisos 3/1/26–2/28/27", "avisos 1 mar 2026–28 feb 2027"),
        ("del March 1, 2026 al February 28, 2027", "del 1 mar 2026 al 28 feb 2027"),
        ("hasta el June 30", "hasta el 30 jun"),
        # citations, section ranges and fractions stay as they are
        (
            "L.A. Mun. Code § 151.00 et seq; §§ 98.0701-98.0710; 1/2 mes",
            "L.A. Mun. Code § 151.00 et seq; §§ 98.0701-98.0710; 1/2 mes",
        ),
        (None, None),
    ],
)
def test_es_dates(text, expected):
    assert es_dates(text) == expected


def test_spanish_address_has_no_english_dates():
    import re

    from web import app as A

    d = A.build_address("A0016", "2026-10-01", "es")
    texts = [
        s
        for c in d["categories"]
        for i in c["enacted"]
        for s in (
            i["explanation"],
            i["rule"]["requirement_display"],
            i["rule"]["key_value_display"],
        )
        if isinstance(s, str)
    ]
    for s in texts:
        assert not re.search(
            r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(March|February) \d", s
        ), s
