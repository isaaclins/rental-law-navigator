"""Deterministic normalisation of LLM output: jurisdictions, categories, dates, citations."""

from __future__ import annotations

import datetime as dt
import re

from .config import CATEGORIES, CITIES, STATES

_STATE_NAMES = {
    "california": "CA",
    "ca": "CA",
    "new jersey": "NJ",
    "nj": "NJ",
    "massachusetts": "MA",
    "ma": "MA",
    "commonwealth of massachusetts": "MA",
    "state of california": "CA",
    "state of new jersey": "NJ",
}
_CITY_ALIASES = {
    "los angeles": "Los Angeles, CA",
    "city of los angeles": "Los Angeles, CA",
    "la": "Los Angeles, CA",
    "san francisco": "San Francisco, CA",
    "city and county of san francisco": "San Francisco, CA",
    "sf": "San Francisco, CA",
    "san diego": "San Diego, CA",
    "city of san diego": "San Diego, CA",
    "berkeley": "Berkeley, CA",
    "city of berkeley": "Berkeley, CA",
    "santa ana": "Santa Ana, CA",
    "city of santa ana": "Santa Ana, CA",
    "jersey city": "Jersey City, NJ",
    "city of jersey city": "Jersey City, NJ",
    "hoboken": "Hoboken, NJ",
    "city of hoboken": "Hoboken, NJ",
    "newark": "Newark, NJ",
    "city of newark": "Newark, NJ",
    "boston": "Boston, MA",
    "city of boston": "Boston, MA",
    "cambridge": "Cambridge, MA",
    "city of cambridge": "Cambridge, MA",
}


def jurisdiction(j: str | None) -> str | None:
    if not j:
        return None
    s = j.strip()
    if s in STATES or s in CITIES:
        return s
    low = re.sub(r"\s+", " ", s.lower().replace(".", "")).strip()
    if low in _STATE_NAMES:
        return _STATE_NAMES[low]
    city = low.split(",")[0].strip()
    if city in _CITY_ALIASES:
        cand = _CITY_ALIASES[city]
        st = low.split(",")[1].strip().upper() if "," in low else cand[-2:]
        st = _STATE_NAMES.get(st.lower(), st)
        return cand if cand.endswith(st) else None
    return None


def level_for(j: str) -> str:
    return "state" if j in STATES else "city"


def state_of(j: str) -> str:
    return j if j in STATES else CITIES[j][0]


def category(c: str | None) -> str | None:
    if not c:
        return None
    c = c.strip().lower().replace(" ", "_").replace("-", "_")
    return c if c in CATEGORIES else None


_MONTHS = {
    m[:3]: i
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        1,
    )
}


def date(s: str | None) -> str | None:
    """ISO date or partial date (YYYY-MM / YYYY) or None."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            dt.date.fromisoformat(s)
            return s
        except ValueError:
            return None
    if re.fullmatch(r"\d{4}-\d{2}", s) or re.fullmatch(r"\d{4}", s):
        return s
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"([A-Za-z]+)\.? (\d{1,2}),? (\d{4})", s)
    if m and m.group(1).lower()[:3] in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(1).lower()[:3]]:02d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"([A-Za-z]+)\.? (\d{4})", s)
    if m and m.group(1).lower()[:3] in _MONTHS:
        return f"{m.group(2)}-{_MONTHS[m.group(1).lower()[:3]]:02d}"
    return None


def date_floor(s: str | None) -> dt.date | None:
    """Earliest calendar date a (partial) ISO date can mean."""
    if not s:
        return None
    parts = s.split("-")
    try:
        return dt.date(
            int(parts[0]),
            int(parts[1]) if len(parts) > 1 else 1,
            int(parts[2]) if len(parts) > 2 else 1,
        )
    except (ValueError, IndexError):
        return None


def date_ceil(s: str | None) -> dt.date | None:
    """Latest calendar date a (partial) ISO date can mean."""
    if not s:
        return None
    parts = s.split("-")
    try:
        y = int(parts[0])
        if len(parts) == 1:
            return dt.date(y, 12, 31)
        m = int(parts[1])
        if len(parts) == 2:
            nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
            return nxt - dt.timedelta(days=1)
        return dt.date(y, m, int(parts[2]))
    except (ValueError, IndexError):
        return None


# ------------------------------------------------------------------ citations
_SUBS = [
    (
        r"(?i)\b(?:cal(?:ifornia)?\.?\s*)?civ(?:il)?\.?\s*code\b\.?\s*(?:sections?|secs?\.?|§+)?\s*",
        "Cal. Civ. Code § ",
    ),
    (
        r"(?i)\b(?:cal(?:ifornia)?\.?\s*)?gov(?:ernment|t)?\.?\s*code\b\.?\s*(?:sections?|secs?\.?|§+)?\s*",
        "Cal. Gov. Code § ",
    ),
    (
        r"(?i)\b(?:cal(?:ifornia)?\.?\s*)?bus(?:iness)?\.?\s*(?:&|and)\s*prof(?:essions)?\.?\s*code\b\.?\s*(?:sections?|secs?\.?|§+)?\s*",
        "Cal. Bus. & Prof. Code § ",
    ),
    (r"(?i)\bN\.?\s?J\.?\s?S\.?\s?A\.?\s*(?:§+\s*)?", "N.J.S.A. "),
    (r"(?i)\bP\.\s?L\.\s?(\d{4}),?\s*c(?:hapter|\.)?\s*0*(\d+)\b", r"P.L.\1, c.\2"),
    (
        r"(?i)\b(?:M\.?\s?G\.?\s?L\.?|Mass\.?\s*Gen\.?\s*Laws?|G\.\s?L\.)\s*(?:ch(?:apter)?|c)\.?\s*(\w+)\s*,?\s*(?:§+|sec(?:tion)?\.?)\s*",
        r"G.L. c. \1, § ",
    ),
    (
        r"(?i)\b(?:M\.?\s?G\.?\s?L\.?|Mass\.?\s*Gen\.?\s*Laws?|G\.\s?L\.)\s*(?:ch(?:apter)?|c)\.?\s*(\w+)\b",
        r"G.L. c. \1",
    ),
    (r"§\s*§\s*", "§§ "),
    (r"§(?=[^\s§])", "§ "),
    (r"\s{2,}", " "),
]


def citation(c: str | None) -> str:
    if not c:
        return ""
    s = c.strip().rstrip(".;,")
    for pat, rep in _SUBS:
        s = re.sub(pat, rep, s)
    return s.strip()


def citation_key(c: str) -> str:
    """Loose comparison key: lowercase alphanumerics of the normalised citation."""
    return re.sub(r"[^a-z0-9]", "", citation(c).lower())
