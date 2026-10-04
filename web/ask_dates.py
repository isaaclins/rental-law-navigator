"""Dates in an Ask question (EN + ES): "as of Aug 12, 2023", "on 8/12/2023", "in 2023", "back in March 2025",
"next July", "el 1 de enero de 2027", "en agosto de 2023", "next year", "hace 2 años" ...

find_date(q, base) -> {"iso", "span", "grain", "out_of_range"} or None. Relative dates count from `base` (the page's
as-of date). A month without a day is its 1st, a year alone is January 1: the answer card says which day it used.
Pure functions, no I/O (tested in tests/test_ask.py)."""

from __future__ import annotations

import datetime as dt
import re
import unicodedata

MIN_DATE, MAX_DATE = (
    "1970-01-01",
    "2100-12-31",
)  # beyond the data's own horizon Ask answers with a note

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
    "enero": 1,
    "ene": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    "dic": 12,
}
_MON = "|".join(sorted(MONTHS, key=len, reverse=True))
_NUMW = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "a": 1,
}
_N = r"(\d{1,2}|one|two|three|four|five|a|un|uno|una|dos|tres|cuatro|cinco)"
_N2 = r"([2-9]|1\d|two|three|four|five|dos|tres|cuatro|cinco)"  # "in a year" is a span of time, not a date
# words that make a bare year a date ("in 2023"), not a law number ("P.L.2026")
_PREP = r"(?:as of|as at|on|in|during|for|by|from|since|until|before|after|back in|around|about|asking about|regarding|at the end of|en|el|del|desde|hasta|para|durante|antes de|despu[eé]s de|a partir de|al)"


BUILT = re.compile(
    r"\b(?:built|constructed|erected|completed|construid[oa]s?|edificad[oa]s?|terminad[oa]s?|year built|ano de construccion)"
    r"(?:\s+(?:back|around|about|alrededor de|hacia))?\s*$"
)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _date(y: int, m: int, d: int) -> dt.date | None:
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def _add_months(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def _num(w: str) -> int:
    return int(w) if w.isdigit() else _NUMW[w]


def _res(d: dt.date | None, span: str, grain: str) -> dict | None:
    if d is None:
        return None
    iso = d.isoformat()
    return {
        "iso": iso,
        "span": span.strip(" ,.;?¿!¡"),
        "grain": grain,
        "out_of_range": not (MIN_DATE <= iso <= MAX_DATE),
    }


def find_date(q: str, base: str) -> dict | None:
    """The first date the question names, or None."""
    t = _fold(q)
    b = dt.date.fromisoformat(base)
    pats = [
        # ISO 2023-08-12
        (
            r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b",
            lambda m: (_date(int(m[1]), int(m[2]), int(m[3])), "day"),
        ),
        # 8/12/2023, 8/12/23 (US order)
        (
            r"\b(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b",
            lambda m: (
                _date(int(m[3]) + (2000 if len(m[3]) == 2 else 0), int(m[1]), int(m[2])),
                "day",
            ),
        ),
        # Aug 12, 2023 / August 12th 2023
        (
            rf"\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b",
            lambda m: (_date(int(m[3]), MONTHS[m[1]], int(m[2])), "day"),
        ),
        # 12 August 2023 / 1 de enero de 2027 / el 1 de enero del 2027
        (
            rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:de\s+)?({_MON})\.?,?\s+(?:de[l]?\s+)?(\d{{4}})\b",
            lambda m: (_date(int(m[3]), MONTHS[m[2]], int(m[1])), "day"),
        ),
        # March 2025 / agosto de 2023
        (
            rf"\b({_MON})\.?,?\s+(?:de[l]?\s+)?(\d{{4}})\b",
            lambda m: (_date(int(m[2]), MONTHS[m[1]], 1), "month"),
        ),
        # next / last / this year
        (
            r"\b(next year|el proximo ano|el ano que viene|el ano proximo)\b",
            lambda m: (dt.date(b.year + 1, 1, 1), "year"),
        ),
        (r"\b(last year|el ano pasado)\b", lambda m: (dt.date(b.year - 1, 1, 1), "year")),
        (
            r"\b(next month(?!'s|\s+(?:of\s+)?rent)|el proximo mes|el mes que viene)\b",
            lambda m: (_add_months(b, 1), "month"),
        ),
        (
            r"\b(last month(?!'s|\s+(?:of\s+)?rent|\s*,|\s+(?:and|or|plus|deposit))|el mes pasado)\b",
            lambda m: (_add_months(b, -1), "month"),
        ),
        # next July / el próximo julio / julio próximo / last March / this July
        (
            rf"\b(?:next|el proximo|este proximo)\s+({_MON})\b|\b({_MON})\s+(?:proximo|que viene)\b",
            lambda m: (_next_month(b, MONTHS[m[1] or m[2]], future=True), "month"),
        ),
        (
            rf"\b(?:last|el pasado)\s+({_MON})\b|\b({_MON})\s+pasado\b",
            lambda m: (_next_month(b, MONTHS[m[1] or m[2]], future=False), "month"),
        ),
        (rf"\bthis\s+({_MON})\b", lambda m: (dt.date(b.year, MONTHS[m[1]], 1), "month")),
        # in 2 years / 2 years ago / hace 2 años / en 2 años / dentro de 2 años
        (
            rf"\b(?:in|en|dentro de)\s+{_N2}\s+(?:years?|anos?)\b",
            lambda m: (_years(b, _num(m[1])), "year"),
        ),
        (
            rf"\b{_N}\s+years?\s+ago\b|\bhace\s+{_N}\s+anos?\b",
            lambda m: (_years(b, -_num(m[1] or m[2])), "year"),
        ),
        # in 2023 / as of 2023 / en 2023 (a preposition makes it a date)
        (
            rf"\b{_PREP}\s+(?:the\s+(?:year\s+)?|el\s+ano\s+|ano\s+)?((?:19|20)\d{{2}})\b(?!\s*-|\s*,\s*c\.)",
            lambda m: (dt.date(int(m[1]), 1, 1), "year"),
        ),
    ]
    money = re.search(
        r"\bfirst (?:month|and last)\b|\b(?:primer|ultimo) mes\b", t
    )  # move-in money, not dates
    best = None
    for rx, fn in pats:
        if money and "month" in rx and "last" in rx:
            continue
        m = next(  # "built in 1962", "construido en 1962": a fact about the building, not the as-of date
            (x for x in re.finditer(rx, t) if not BUILT.search(t[: x.start()])), None
        )
        if not m:
            continue
        d, grain = fn(m)
        if d is None:
            continue
        if best is None or m.start() < best[0]:
            best = (m.start(), m.end(), d, grain)
    if not best:
        return None
    s0, s1, d, grain = best
    # the span in the original text (folding keeps lengths for Latin text; guard anyway)
    span = q[s0:s1] if len(q) == len(t) else t[s0:s1]
    return _res(d, span, grain)


def _next_month(b: dt.date, month: int, future: bool) -> dt.date:
    if future:
        y = b.year if month > b.month else b.year + 1
    else:
        y = b.year if month < b.month else b.year - 1
    return dt.date(y, month, 1)


def _years(b: dt.date, n: int) -> dt.date:
    return (
        dt.date(b.year + n, 1, 1)
        if n > 0
        else (_date(b.year + n, b.month, b.day) or dt.date(b.year + n, b.month, 28))
    )


def strip_date(q: str, found: dict | None) -> str:
    """The question without its date words (for place, address and topic detection)."""
    if not found or not found.get("span"):
        return q
    i = _fold(q).find(_fold(found["span"]))
    if i < 0:
        return q
    head = re.sub(
        r"(?:\b(?:back in|as of|as at|on|in|during|for|by|around|since|until|from|en|el|del|desde|hasta|para|durante|a partir de)\s+)+$",
        "",
        q[:i],
        flags=re.I,
    )
    out = head + q[i + len(found["span"]) :]
    return re.sub(r"\s{2,}", " ", re.sub(r"^\W*,\s*", "", out)).strip(" ,")


def fmt(iso: str, lang: str) -> str:
    d = dt.date.fromisoformat(iso)
    if lang == "es":
        names = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        return f"{d.day} de {names[d.month - 1]} de {d.year}"
    return d.strftime("%b ") + f"{d.day}, {d.year}"
