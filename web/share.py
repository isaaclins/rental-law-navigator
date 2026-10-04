"""Share an answer (#117): a frozen, cited permalink with a link-preview card.

    /s/<address_id>/<topic>/<as_of>            server-rendered page (works without JS), Open Graph + Twitter tags
    /s/<address_id>/<topic>/<as_of>/card.png   1200x630 preview card (web/og_card.py), cached on disk
    /api/share/<address_id>/<topic>/<as_of>    the same answer as JSON for the share sheet (features/share.js)

No database: the answer is recomputed deterministically from the address, topic and as-of date. A short content
hash of the answer (`v`) rides along in the shared link, so a later data change is visible on the page.
The wording follows the address page (app.js topicSummary / whyLine / lawQuote), so both say the same thing.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from web.any_address import RateLimit, client_ip
from web.source_notes import note as source_note

router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "web" / "static"
ORIGIN = os.environ.get("PUBLIC_ORIGIN", "https://navigator.isaaclins.com").rstrip("/")
ASOF_MIN, ASOF_MAX = "2020-01-01", "2030-12-31"  # the app's as-of range (app.js ASOF_MIN/MAX)

# short, readable slugs in the link -> the app's topic ids
TOPICS = {}
TOPICS = {
    "rent": "rent_increase_limits",
    "eviction": "just_cause_eviction",
    "deposit": "security_deposits",
    "fees": "application_screening_fees",
    "screening": "screening_restrictions",
    "pricing": "algorithmic_rent_setting",
}
SLUG_OF = {v: k for k, v in TOPICS.items()}
ID_RE = re.compile(r"A\d{4}")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
VER_RE = re.compile(r"[0-9a-f]{7}")

# city photo per legal city (the address page's CITIES list); others get the generic building
CITY_IMG = {
    "San Francisco": "san-francisco",
    "Berkeley": "berkeley",
    "Los Angeles": "los-angeles",
    "San Diego": "san-diego",
    "Boston": "boston",
    "Cambridge": "cambridge",
    "Newark": "newark",
    "Jersey City": "jersey-city",
    "Hoboken": "hoboken",
}
STATE_NAMES = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}

# The app's own strings (app.js EN, i18n/es.json ES) for the answer, plus this page's own.
EN = {
    "pq_rent_increase_limits": "Can they raise my rent?",
    "pq_just_cause_eviction": "Can they make me move out?",
    "pq_security_deposits": "How big can the deposit be?",
    "pq_application_screening_fees": "What can they charge me to apply?",
    "pq_screening_restrictions": "Can they turn me down for a voucher or a record?",
    "pq_algorithmic_rent_setting": "Can a computer set my rent?",
    "why_city": "{p} has its own law for this, and it covers your building.",
    "why_state": "A {p} law covers your building.",
    "why_replaces": "It is stricter than the state rule, so it wins.",
    "why_later": "A new law starts on {d}.",
    "why_nolimit": "{p} law sets no limit here.",
    "why_exempt": "There is a rule, but your building does not fall under it.",
    "why_none": "We found no state or city law on this.",
    "why_unknown": "It depends on {f}. Public records don't say.",
    "why_unknown_other": "It depends on a fact we can't see in public records.",
    "why_new": "Your building is too new for the cap (built {y}).",
    "pf_year": "when your building was built",
    "pf_units": "how many homes are in your building",
    "pf_owner": "whether the owner lives there",
    "pf_tenancy": "how long you have lived there",
    "pf_other": "a fact we can't see in public records",
    "l1_unknown": "We can't tell yet.",
    "l1_later": "Not yet. Starts {d}.",
    "l1_exempt_rent": "No limit for your building.",
    "l1_exempt": "This rule doesn't cover your building.",
    "l1_none_rent": "We found no rent cap here.",
    "l1_none": "No special rule here.",
    "tr_note": "Translated by machine. The law's words stay in English.",
    "official_site": "Official site",
    # this page
    "today": "See today's answer",
    "today_diff": "Today's answer is different: {a}",
    "changed": "The data behind this answer changed after the link was shared. This page shows the current data for {d}.",
    "checked": "quote checked word for word",
    "checked_s": "Word for word",
    "retrieved": "retrieved {d}",
    "nla": "Not legal advice.",
    "nla_body": "Public law with citations, for information only. Check the source, and for your situation a tenant group, housing agency or lawyer.",
    "built": "built {y}",
    "units": "{n} units",
    "units_min": "{n}+ units",
    "share": "Share",
    "checked_card": "Checked {d}",
    "asof_card": "As of {d}",
    "nla_card": "Not legal advice",
    "answer_asof": "Answer as of {d}",
    "law_show": "Show me the law",
    "strip_s": "Quoted word for word. Not legal advice.",
    "strip_ab": "About",
    "strip_xs": "Quoted sources. Not legal advice.",
    "foot_src": "Not legal advice · from {p} official {n}",
    "foot_none": "Not legal advice · from public state and city law",
    "n_rent": "rent rules",
    "n_eviction": "eviction rules",
    "n_deposit": "deposit rules",
    "n_fees": "application fee rules",
    "n_screening": "tenant screening rules",
    "n_pricing": "rent-software rules",
    "nf_title": "This link doesn't open an answer",
    "nf_body": "It may be cut off or mistyped. Look up the address instead.",
    "nf_go": "Look up an address",
    "no_quote": "No law to quote here: we found no state or city rule on this.",
    "home_aria": "Clause and Effect, home",
}
ES_OWN = {
    "today": "Ver la respuesta de hoy",
    "today_diff": "La respuesta de hoy es otra: {a}",
    "changed": "Los datos de esta respuesta cambiaron después de compartir el enlace. Esta página muestra los datos actuales para el {d}.",
    "checked": "cita comprobada palabra por palabra",
    "checked_s": "Palabra por palabra",
    "retrieved": "consultado el {d}",
    "nla": "No es asesoría legal.",
    "nla_body": "Leyes públicas con citas, solo para informar. Revise la fuente y, para su caso, consulte a un grupo de inquilinos, una oficina de vivienda o un abogado.",
    "built": "construido en {y}",
    "units": "{n} unidades",
    "units_min": "{n}+ unidades",
    "share": "Compartir",
    "checked_card": "Comprobado el {d}",
    "asof_card": "Al {d}",
    "nla_card": "No es asesoría legal",
    "answer_asof": "Respuesta al {d}",
    "foot_src": "No es asesoría legal · según las {n} oficiales de {p}",
    "foot_none": "No es asesoría legal · según leyes públicas estatales y locales",
    "n_rent": "reglas de renta",
    "n_eviction": "reglas de desalojo",
    "n_deposit": "reglas de depósito",
    "n_fees": "reglas de cuotas de solicitud",
    "n_screening": "reglas de selección de inquilinos",
    "n_pricing": "reglas sobre software de rentas",
    "nf_title": "Este enlace no abre una respuesta",
    "nf_body": "Puede estar cortado o mal escrito. Busque la dirección.",
    "nf_go": "Buscar una dirección",
    "no_quote": "No hay ley que citar: no encontramos una regla estatal ni local sobre esto.",
    "home_aria": "Clause and Effect, inicio",
}


@lru_cache(maxsize=1)
def _es() -> dict:
    try:
        d = json.loads((STATIC / "i18n" / "es.json").read_text())
    except (OSError, json.JSONDecodeError):
        d = {}
    return {**d, **ES_OWN}


def t(key: str, lang: str) -> str:
    if lang == "es":
        v = _es().get(key)
        if v:
            return v
    return EN.get(key, key)


def tf(key: str, lang: str, **kw) -> str:
    s = t(key, lang)
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


MON_EN = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
MON_ES = "ene feb mar abr may jun jul ago sept oct nov dic".split()


def fmt_date(d: str | None, lang: str) -> str:
    """Like app.js fmtDate (en-US "Oct 1, 2026", es-US "1 oct 2026")."""
    if not d:
        return ""
    d = str(d)[:10]
    try:
        x = dt.date.fromisoformat(
            d if len(d) == 10 else (d + "-01" if len(d) == 7 else d + "-01-01")
        )
    except ValueError:
        return d
    if len(d) == 4:
        return str(x.year)
    if len(d) == 7:
        return (
            f"{MON_ES[x.month - 1]} {x.year}" if lang == "es" else f"{MON_EN[x.month - 1]} {x.year}"
        )
    if lang == "es":
        return f"{x.day} {MON_ES[x.month - 1]} {x.year}"
    return f"{MON_EN[x.month - 1]} {x.day}, {x.year}"


def cap(s: str | None) -> str:
    s = str(s or "")
    return re.sub(r"^\s*\w", lambda m: m.group(0).upper(), s, count=1)


def title_case(s: str | None) -> str:
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), str(s or "").lower())


def host(u: str | None) -> str:
    try:
        return (urlparse(u or "").hostname or "").removeprefix("www.")
    except ValueError:
        return ""


def shown_quote(q: str | None) -> str:
    """app.js shownQuote: trim a scraped tail back to the last complete clause and mark the cut with an ellipsis."""
    orig = str(q or "").strip()
    s = orig
    o, c = s.rfind("("), s.rfind(")")
    if o > c:
        s = s[:o].strip()
    end = re.compile(r"[.;:!?\"”)\]]$")
    if end.search(s) and s == orig:
        return s
    cut = max(s.rfind(". "), s.rfind("; "), s.rfind(": "))
    if not end.search(s) and cut > len(s) * 0.5:
        s = s[: cut + 1]
    return re.sub(r"[\s,;:–-]+$", "", s) + " …"


RANK = {
    "applies": 0,
    "unknown": 1,
    "not_yet_effective": 2,
    "superseded": 3,
    "pending": 4,
    "failed": 5,
}


def ordered(items: list[dict]) -> list[dict]:
    """app.js ordered(): the governing rule first."""

    def key(x):
        r = x["rule"]
        return (
            RANK.get(x["result"], 9),
            0 if x.get("overrides_here") else 1,
            r.get("headline_priority") if r.get("headline_priority") is not None else 1.5,
            0 if r.get("level") == "state" else 1,
        )

    return sorted(items, key=key)


def _plain_ok(r: dict, as_of: str) -> bool:
    return bool(r.get("answer_display")) and not (r.get("plain_until") and as_of > r["plain_until"])


def _headline_of(item: dict, as_of: str) -> str | None:
    r = item["rule"]
    if item.get("headline"):
        return item["headline"]
    if r.get("headline_until") and as_of > r["headline_until"]:
        return r.get("headline_after")
    return r.get("headline_display")


def _place(r: dict, lang: str) -> str:
    j = r.get("jurisdiction") or ""
    if r.get("level") == "state":
        return t(STATE_NAMES.get(j, j), lang)
    return re.sub(r", ..$", "", j)


def _fact_kind(item: dict) -> str | None:
    f = f"{item.get('missing_fact') or ''} {' '.join(item.get('needs_fact') or [])}"
    if re.search(r"certificate|year", f, re.I):
        return "year"
    if re.search(r"unit", f, re.I):
        return "units"
    if re.search(r"owner", f, re.I):
        return "owner"
    return None


def _plain_fact(item: dict, lang: str) -> str:
    f = f"{item.get('missing_fact') or ''} {' '.join(item.get('needs_fact') or [])}"
    for pat, k in (
        (r"certificate|year", "pf_year"),
        (r"unit", "pf_units"),
        (r"owner", "pf_owner"),
        (r"tenancy|moved", "pf_tenancy"),
    ):
        if re.search(pat, f, re.I):
            return t(k, lang)
    return t("pf_other", lang)


def summarize(cat: dict, d: dict, as_of: str, lang: str) -> dict:
    """The topic's answer, why-line and quote, worded like the address page."""
    items = ordered(cat.get("enacted") or [])
    top = items[0] if items else None
    a = d["address"]
    quote = None
    if top:
        r = top["rule"]
        if top["result"] == "unknown":
            line = t("l1_unknown", lang)
        elif top["result"] == "not_yet_effective" and not _plain_ok(r, as_of):
            line = tf(
                "l1_later",
                lang,
                d=fmt_date(r.get("effective_date_norm") or r.get("effective_date"), lang),
            )
        else:
            line = (
                (r.get("answer_display") if _plain_ok(r, as_of) else _headline_of(top, as_of))
                or r.get("key_value_display")
                or r.get("key_value")
                or r.get("title_display")
                or r.get("title")
            )
        place = _place(r, lang)
        if top["result"] == "applies" and _plain_ok(r, as_of) and r.get("why_display"):
            why = r["why_display"]
        elif top["result"] == "unknown":
            why = (
                tf("why_unknown", lang, f=_plain_fact(top, lang))
                if _fact_kind(top)
                else t("why_unknown_other", lang)
            )
        elif top["result"] == "not_yet_effective":
            why = tf(
                "why_later",
                lang,
                d=fmt_date(r.get("effective_date_norm") or r.get("effective_date"), lang),
            )
        elif r.get("removes_protection"):
            why = tf("why_nolimit", lang, p=place)
        else:
            why = tf("why_state" if r.get("level") == "state" else "why_city", lang, p=place)
            if any(x["result"] == "superseded" for x in items):
                why += " " + t("why_replaces", lang)
        if r.get("quoted_span"):
            src = r.get("source") or {}
            quote = {
                "text": shown_quote(r["quoted_span"]),
                "citation": r.get("citation") or "",
                "url": r.get("source_url") or "",
                "retrieved": (src.get("retrieved_at") or r.get("retrieved_at") or "")[:10],
                "verified": (r.get("quote_check") or {}).get("status") in ("exact", "normalized"),
                "rule": r["team_rule_id"],
                # the quote is from another document than the cited law: amber note, not "word for word"
                "note": source_note(r["team_rule_id"], lang),
            }
        rules = [(x["rule"]["team_rule_id"], x["result"]) for x in items]
        src_place = place
        rules.append((str(r.get("key_value")), str(r.get("effective_date")), _plain_ok(r, as_of)))
    else:
        ex = (cat.get("excluded") or [None])[0]
        rent = cat["id"] == "rent_increase_limits"
        if ex:
            line = t("l1_exempt_rent" if rent else "l1_exempt", lang)
            y = a.get("year_built")
            why = (
                tf("why_new", lang, y=y)
                if y
                and re.search(
                    r"new|construct|certificate|built|year", " ".join(ex.get("reasons") or []), re.I
                )
                else t("why_exempt", lang)
            )
        else:
            line = t("l1_none_rent" if rent else "l1_none", lang)
            why = t("why_none", lang)
        f = (cat.get("no_rule_findings") or [None])[0]
        if f and f.get("quoted_span"):
            quote = {
                "text": shown_quote(f["quoted_span"]),
                "citation": f.get("citation") or "",
                "url": f.get("source_url") or "",
                "retrieved": ((f.get("source") or {}).get("retrieved_at") or "")[:10],
                "verified": (f.get("quote_check") or {}).get("status") in ("exact", "normalized"),
                "rule": f.get("finding_id") or "",
            }
        rules = [("excluded" if ex else "none", "")]
        src_place = ""
    return {
        "answer": cap(line),
        "why": why,
        "quote": quote,
        "rules": rules,
        "source_place": src_place if quote else "",
    }


# ---------------------------------------------------------------- validation
def check_params(address_id: str, topic: str, as_of: str) -> tuple[str, str, str]:
    """Strict: a known address id (exact form), a known topic slug, an ISO date in the app's range. Else 404."""
    from web import app as W  # late import: web.app includes this router

    if not ID_RE.fullmatch(address_id or "") or address_id not in W.STORE.addresses:
        raise HTTPException(404, "unknown address")
    if topic not in TOPICS:
        raise HTTPException(404, "unknown topic")
    if not DATE_RE.fullmatch(as_of or ""):
        raise HTTPException(404, "bad date")
    try:
        dt.date.fromisoformat(as_of)
    except ValueError:
        raise HTTPException(404, "bad date") from None
    if not (ASOF_MIN <= as_of <= ASOF_MAX):
        raise HTTPException(404, "date out of range")
    return address_id, topic, as_of


def norm_lang(lang: str | None) -> str:
    return "es" if lang == "es" else "en"


def today() -> str:
    return min(max(dt.date.today().isoformat(), ASOF_MIN), ASOF_MAX)


@lru_cache(maxsize=2048)
def _answer(address_id: str, topic: str, as_of: str, lang: str, sig: tuple) -> dict:
    from web import app as W

    d = W.build_address(address_id, as_of, lang)
    cat = next(c for c in d["categories"] if c["id"] == TOPICS[topic])
    s = summarize(cat, d, as_of, lang)
    a, j = d["address"], d["jurisdiction"]
    city = j.get("city") or a.get("postal_city") or ""
    img = CITY_IMG.get(city, "hero-building-card")
    units = a.get("units")
    facts = [f"{t(city, lang)}, {a['state']}" if city else a["state"]]
    if a.get("year_built"):
        facts.append(tf("built", lang, y=a["year_built"]))
    if units:
        facts.append(tf("units", lang, n=units))
    elif a.get("units_min"):
        facts.append(tf("units_min", lang, n=a["units_min"]))
    street = title_case(a["street_address"])
    # the data version: a content hash of what the answer says and rests on (not of the wording language)
    basis = json.dumps(
        [
            address_id,
            topic,
            as_of,
            s["rules"],
            (s["quote"] or {}).get("text"),
            (s["quote"] or {}).get("citation"),
            (s["quote"] or {}).get("url"),
        ],
        ensure_ascii=False,
    )
    v = hashlib.sha1(basis.encode()).hexdigest()[:7]
    q = t("pq_" + TOPICS[topic], lang)
    return {
        **s,
        "address_id": address_id,
        "topic": topic,
        "category": TOPICS[topic],
        "as_of": as_of,
        "lang": lang,
        "question": q,
        "street": street,
        "city": city,
        "state": a["state"],
        "facts": " · ".join(facts),
        "image": img,
        "v": v,
        "title": f"{q} · {street}",
    }


def answer(address_id: str, topic: str, as_of: str, lang: str) -> dict:
    from web import app as W

    W.STORE.maybe_reload()
    return _answer(address_id, topic, as_of, lang, W.STORE._sig)


def share_path(a: dict) -> str:
    return f"/s/{a['address_id']}/{a['topic']}/{a['as_of']}"


def share_query(a: dict, *, version: bool = True) -> str:
    parts = []
    if a["lang"] == "es":
        parts.append("lang=es")
    if version:
        parts.append(f"v={a['v']}")
    return ("?" + "&".join(parts)) if parts else ""


def card_url(a: dict) -> str:
    return f"{ORIGIN}{share_path(a)}/card.png{share_query(a)}"


def public_json(a: dict) -> dict:
    url = f"{ORIGIN}{share_path(a)}{share_query(a)}"
    return {
        "url": url,
        "path": share_path(a) + share_query(a),
        "title": a["title"],
        "text": a["answer"],
        "question": a["question"],
        "answer": a["answer"],
        "why": a["why"],
        "street": a["street"],
        "as_of": a["as_of"],
        "as_of_label": fmt_date(a["as_of"], a["lang"]),
        "lang": a["lang"],
        "v": a["v"],
        "image": f"{share_path(a)}/card.png{share_query(a)}",
        "image_abs": card_url(a),
        "host": host(ORIGIN),
        "citation": (a["quote"] or {}).get("citation", ""),
    }


# -------------------------------------------------------------------- routes
@router.get("/api/share/{address_id}/{topic}/{as_of}")
def share_api(address_id: str, topic: str, as_of: str, lang: str = "en"):
    a = answer(*check_params(address_id, topic, as_of), norm_lang(lang))
    return public_json(a)


CARD_LIMIT = RateLimit(30, 60.0)  # fresh renders per client per minute (cache hits are free)
CARD_ALL = RateLimit(240, 60.0)  # and for everyone together


@router.api_route(
    "/s/{address_id}/{topic}/{as_of}/card.png", methods=["GET", "HEAD"], include_in_schema=False
)
def share_card(request: Request, address_id: str, topic: str, as_of: str, lang: str = "en"):
    from web import og_card

    a = answer(*check_params(address_id, topic, as_of), norm_lang(lang))
    path = og_card.cached(a)
    if path is None:
        if not (CARD_LIMIT.allow(client_ip(request)) and CARD_ALL.allow("*")):
            raise HTTPException(429, "Too many preview images. Please wait a minute.")
        path = og_card.render_cached(a, fmt_date, t)
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.api_route(
    "/s/{address_id}/{topic}/{as_of}", methods=["GET", "HEAD"], include_in_schema=False
)
def share_page(address_id: str, topic: str, as_of: str, lang: str = "en", v: str | None = None):
    lang = norm_lang(lang)
    try:
        check_params(address_id, topic, as_of)
    except HTTPException:
        return HTMLResponse(
            not_found_html(lang), status_code=404, headers={"Cache-Control": "no-store"}
        )
    a = answer(address_id, topic, as_of, lang)
    now = today()
    today_a = answer(address_id, topic, now, lang) if now != as_of else a
    shared_v = v if v and VER_RE.fullmatch(v) else None
    return HTMLResponse(
        page_html(a, today_a, now, shared_v),
        headers={"Cache-Control": "public, max-age=300", "Content-Language": lang},
    )


# ---------------------------------------------------------------------- HTML
def _e(s) -> str:
    return escape(str(s if s is not None else ""), quote=True)


def _asset(rel: str) -> str:
    from web import app as W

    f = STATIC / rel
    return f"/static/{rel}?v={W.asset_hash(f)}" if f.is_file() else f"/static/{rel}"


ICON_LOCK = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>'
ICON_ALERT = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/></svg>'
ICON_CHECK = (
    '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.2 4.2L19 7"/></svg>'
)
ICON_EXT = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 5h5v5M19 5l-8 8M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4"/></svg>'
ICON_SHARE = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15V4M8 8l4-4 4 4M5 12v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg>'
ICON_ARROW = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'


def _head(title: str, lang: str, extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{_e(title)}</title>
{extra}
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/static/icons/favicon-32.png" type="image/png">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
<link rel="preload" href="/static/fonts/InterVariable-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/static/fonts/InstrumentSerif-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{_asset("app.css")}">
<link rel="stylesheet" href="{_asset("mobile.css")}">
<link rel="stylesheet" href="{_asset("features/share.css")}">
<link rel="stylesheet" href="{_asset("features/mobile-v4.css")}">
</head>"""


def _chrome_top(lang: str, path: str, query_es: str, query_en: str) -> str:
    seg = (
        f'<a href="{_e(path + query_en)}" data-lang="en" lang="en" hreflang="en" aria-pressed="{str(lang == "en").lower()}">EN</a>'
        f'<a href="{_e(path + query_es)}" data-lang="es" lang="es" hreflang="es" aria-pressed="{str(lang == "es").lower()}">ES</a>'
    )
    return f"""<body class="sh-body">
<p class="strip sh-strip"><span class="strip-s">{_e(t("strip_s", lang))}</span><span class="strip-xs">{_e(t("strip_xs", lang))}</span> <a class="strip-ab" href="/#/audit">{_e(t("strip_ab", lang))}</a></p>
<header class="nav sh-nav" id="nav">
  <div class="nav-inner">
    <a class="brand" href="/" aria-label="{_e(t("home_aria", lang))}"><span class="brand-mark" aria-hidden="true">§</span><span class="brand-word">Clause <i>&amp;</i> Effect</span></a>
    <div class="nav-tools"><div class="seg sh-seg" role="group" aria-label="Language">{seg}</div></div>
  </div>
</header>"""


def _footer(lang: str, line: str | None = None) -> str:
    return f"""<footer class="sh-foot"><p>{_e(line or t("foot_none", lang))}</p></footer>"""


def foot_line(a: dict) -> str:
    lang, p = a["lang"], a.get("source_place")
    if not p:
        return t("foot_none", lang)
    if lang == "en":
        p = p + ("'" if p.endswith("s") else "'s")
    return tf("foot_src", lang, p=p, n=t("n_" + a["topic"], lang))


def page_html(a: dict, today_a: dict, now: str, shared_v: str | None) -> str:
    lang = a["lang"]
    path = share_path(a)
    url = f"{ORIGIN}{path}{share_query(a)}"
    canonical = f"{ORIGIN}{path}{share_query(a, version=False)}"
    img = card_url(a)
    q = a["quote"]
    as_of_l = fmt_date(a["as_of"], lang)
    cite_line = (q or {}).get("citation", "")
    img_alt = f"{a['answer']} {a['street']}, {a['city']}. {cite_line}. Clause & Effect".replace(
        " . ", " "
    )
    alt_lang = "es" if lang == "en" else "en"
    meta = f"""<meta name="description" content="{_e(a["answer"] + " " + a["why"])}">
<link rel="canonical" href="{_e(canonical)}">
<link rel="alternate" hreflang="{alt_lang}" href="{_e(f"{ORIGIN}{path}" + ("?lang=es" if alt_lang == "es" else ""))}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Clause &amp; Effect">
<meta property="og:locale" content="{"es_US" if lang == "es" else "en_US"}">
<meta property="og:url" content="{_e(url)}">
<meta property="og:title" content="{_e(a["title"])}">
<meta property="og:description" content="{_e(a["answer"])}">
<meta property="og:image" content="{_e(img)}">
<meta property="og:image:secure_url" content="{_e(img)}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{_e(img_alt)}">
<meta property="article:published_time" content="{_e(a["as_of"])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_e(a["title"])}">
<meta name="twitter:description" content="{_e(a["answer"])}">
<meta name="twitter:image" content="{_e(img)}">
<meta name="twitter:image:alt" content="{_e(img_alt)}">"""
    keep_v = f"v={shared_v}" if shared_v else ""  # the language switch keeps the shared version
    q_en = "?" + keep_v if keep_v else ""
    q_es = "?lang=es" + ("&" + keep_v if keep_v else "")
    notes = []
    if shared_v and shared_v != a["v"]:
        notes.append(
            f'<p class="sh-note sh-changed" role="status">{_e(tf("changed", lang, d=as_of_l))}</p>'
        )
    if today_a["v"] != a["v"] and today_a["answer"] != a["answer"]:
        notes.append(f'<p class="sh-note">{_e(tf("today_diff", lang, a=today_a["answer"]))}</p>')
    today_href = f"/#/a/{a['address_id']}"
    today_attrs = f'href="{_e(today_href)}" data-today data-cat="{_e(a["category"])}" data-asof="{_e(now)}" data-lang="{lang}"'
    law = ""
    if q:
        bits = [f"<span>{_e(q['citation'])}</span>"] if q["citation"] else []
        if q["url"]:
            bits.append(
                f'<a href="{_e(q["url"])}" target="_blank" rel="noopener noreferrer">{_e(host(q["url"]) or t("official_site", lang))}{ICON_EXT}</a>'
            )
        if q["retrieved"]:
            bits.append(
                f'<span class="sh-ret">{_e(tf("retrieved", lang, d=fmt_date(q["retrieved"], lang)))}</span>'
            )
        note = q.get("note")
        check = (
            f'<p class="src-note">{ICON_ALERT}<span><b>{_e(note["lead"])}</b> {_e(note["text"])}</span></p>'
            if note
            # phones (features/mobile-v4.css): one line "Word for word · retrieved <date>" instead of the long phrase
            else f'<p class="sh-ok">{ICON_CHECK}'
            + (
                f'<span class="sh-ok-l">{_e(t("checked", lang))}</span><span class="sh-ok-r">{_e(t("checked_s", lang))} · '
                f"{_e(tf('retrieved', lang, d=fmt_date(q['retrieved'], lang)))}</span>"
                if q["retrieved"]
                else _e(t("checked", lang))
            )
            + "</p>"
            if q["verified"]
            else ""
        )
        tr = f'<p class="sh-tr">{_e(t("tr_note", lang))}</p>' if lang != "en" else ""
        law = f"""{tr}<blockquote class="sh-quote" lang="en" cite="{_e(q["url"])}">“{_e(q["text"])}”</blockquote>
        <p class="sh-cite">{"".join(bits)}</p>{check}"""
    else:
        law = f'<p class="sh-noquote">{_e(t("no_quote", lang))}</p>'
    share_data = _e(json.dumps(public_json(a), ensure_ascii=False))
    # phones (features/mobile-v4.css): the street photo as a strip with the address on it
    street_ph = (
        f'<img class="sh-ph" src="/static/img/street/{_e(a["image"])}-m.webp" alt="" loading="lazy" decoding="async" onerror="this.remove()">'
        if (STATIC / "img" / "street" / f"{a['image']}-m.webp").is_file()
        else ""
    )
    return (
        _head(
            f"{a['title']} · Clause & Effect",
            lang,
            meta + f'\n<meta name="ce:data-version" content="{_e(a["v"])}">',
        )
        + _chrome_top(lang, path, q_es, q_en)
        + f"""
<main id="main" class="sh-main" data-share-page data-v="{_e(a["v"])}" data-cat="{_e(a["category"])}">
  <p class="sh-asof">{ICON_LOCK}<span>{_e(tf("answer_asof", lang, d=as_of_l))}</span></p>
  {"".join(notes)}
  <p class="sh-addr"><img src="/static/img/{_e(a["image"])}-sm.webp" alt="" width="44" height="34" onerror="this.remove()">{street_ph}<span>{_e(a["street"] + (", " + a["city"] if a["city"] else ""))}</span></p>
  <p class="sh-q">{_e(a["question"])}</p>
  <h1 class="sh-a">{_e(a["answer"])}</h1>
  <p class="sh-why">{_e(a["why"])}</p>
  <div class="sh-acts">
    <a class="btn primary sh-go" {today_attrs}>{_e(t("today", lang))}{ICON_ARROW}</a>
    <button type="button" class="sh-share" data-share="{share_data}" hidden>{ICON_SHARE}<span>{_e(t("share", lang))}</span></button>
  </div>
  <details class="sh-law">
    <summary><span>{_e(t("law_show", lang))}</span><svg class="ico chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg></summary>
    <div class="sh-law-in">
      {law}
      <p class="sh-nla"><b>{_e(t("nla", lang))}</b> {_e(t("nla_body", lang))}</p>
    </div>
  </details>
  <p class="sh-nla sh-nla-m"><b>{_e(t("nla", lang))}</b> {_e(t("nla_body", lang))}</p>
</main>
"""
        + _footer(lang, foot_line(a))
        + f'\n<script data-cfasync="false" src="{_asset("features/share.js")}" type="module"></script>'
        + f'\n<script data-cfasync="false" src="{_asset("features/mobile-v4.js")}" type="module"></script>\n</body>\n</html>\n'
    )


def not_found_html(lang: str) -> str:
    return (
        _head(
            f"{t('nf_title', lang)} · Clause & Effect",
            lang,
            '<meta name="robots" content="noindex">',
        )
        + _chrome_top(lang, "/", "?lang=es", "")
        + f"""
<main id="main" class="sh-main sh-nf">
  <h1 class="sh-a">{_e(t("nf_title", lang))}</h1><p class="sh-why">{_e(t("nf_body", lang))}</p>
  <div class="sh-acts"><a class="btn primary" href="/">{_e(t("nf_go", lang))}{ICON_ARROW}</a></div>
</main>
"""
        + _footer(lang)
        + "\n</body>\n</html>\n"
    )
