"""Letter to the landlord about a rent increase over the limit (#122).

POST /api/letter
    the /api/check body (address_id or place, current_rent, new_rent or increase_pct, dates, facts, cpi, lang)
    + optional "letter_date" (the reader's today) and "address_text" (the address typed for any address)
    -> {"lang", "verdict": the rent verdict of /api/check, "letter": {"blocks": [...], "text"}, "summary": [...],
        "help": {...}, "fields": {...}, "title"}
    422 {"detail": "not_over"} when the check does not find the increase over the limit.

A fixed template, filled only from run_check's result: every amount, percentage, date, quote and link in the letter
is the engine's. No LLM at runtime. What the reader types into the letter (name, unit, landlord's name) never
reaches the server: the letter carries field markers that the browser fills in. Not legal advice. Nothing is stored.

Blocks: {"k": kind, "s": [segment]} with kind date | from | re | salute | p | quote | src | sign, and a segment
{"t": text} (optional "b": bold, "href": link) | {"f": field} | {"br": 1}.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from urllib.parse import quote, urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from web import check as C
from web.any_address import _limit

router = APIRouter()

FIELDS = {
    "en": {"name": "[Your name]", "unit": "[Unit]", "landlord": "[Landlord's name]"},
    "es": {"name": "[Su nombre]", "unit": "[Unidad]", "landlord": "[Nombre del arrendador]"},
}
FIELD_LABELS = {
    "en": {"name": "Your name", "unit": "Unit", "landlord": "Landlord's name"},
    "es": {"name": "Su nombre", "unit": "Unidad", "landlord": "Nombre del arrendador"},
}

# The plain name of each rent cap and who states the quoted sentence (the source's publisher).
LAW = {
    "SF-RENT-01": {
        "en": ("the San Francisco Rent Ordinance", "The city's Rent Board states:"),
        "es": (
            "la Ordenanza de Rentas de San Francisco",
            "La Junta de Rentas de la ciudad indica:",
        ),
    },
    "LA-RENT-01": {
        "en": (
            "the Los Angeles Rent Stabilization Ordinance",
            "The city's Housing Department states:",
        ),
        "es": (
            "la Ordenanza de Estabilización de Rentas de Los Ángeles",
            "El Departamento de Vivienda de la ciudad indica:",
        ),
    },
    "BER-RENT-01": {
        "en": ("the Berkeley Rent Stabilization Ordinance", "The city's Rent Board states:"),
        "es": (
            "la Ordenanza de Estabilización de Rentas de Berkeley",
            "La Junta de Rentas de la ciudad indica:",
        ),
    },
    "SA-RENT-01": {
        "en": ("the Santa Ana Rent Stabilization Ordinance", "The city states:"),
        "es": ("la Ordenanza de Estabilización de Rentas de Santa Ana", "La ciudad indica:"),
    },
    "CA-RENT-01": {
        "en": ("the California Tenant Protection Act", "The law states:"),
        "es": ("la Ley de Protección al Inquilino de California", "La ley establece:"),
    },
}

# What the city's own source says can raise the maximum beyond the yearly percentage (the letter must not claim a
# hard maximum). Only what the sources say: banked increases are in Berkeley's (D006: "a landlord who has 'banked'
# (unused) AGAs from previous years"); SF's lists capital-improvement petitions (D083), LA's the RSO and SCEP
# surcharges (D041, D042).
EXCEPTIONS = {
    "BER-RENT-01": {
        "en": "This does not count unused (banked) increases from earlier years, which Berkeley allows, or other"
        " exceptions.",
        "es": "Esto no cuenta los aumentos no usados (acumulados) de años anteriores, que Berkeley permite, ni otras"
        " excepciones.",
    },
    "SF-RENT-01": {
        "en": "This does not count increases the Rent Board approves on a petition, such as for capital"
        " improvements, or other exceptions.",
        "es": "Esto no cuenta los aumentos que la Junta de Rentas aprueba por petición, como por mejoras de capital,"
        " ni otras excepciones.",
    },
    "LA-RENT-01": {
        "en": "This does not count the RSO and code-enforcement (SCEP) surcharges the city allows, or other"
        " exceptions.",
        "es": "Esto no cuenta los recargos RSO y SCEP que la ciudad permite, ni otras excepciones.",
    },
}
STATE = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}
STATE_ES = {"CA": "California", "NJ": "Nueva Jersey", "MA": "Massachusetts"}

# Official offices from our sources (same pages as web/ask.py OFFICIAL, checked 2026-10-04).
HELP = {
    "San Francisco, CA": (
        "San Francisco Rent Board",
        "the San Francisco Rent Board",
        "la Junta de Rentas de San Francisco",
        "https://sf.gov/departments/rent-board",
    ),
    "Los Angeles, CA": (
        "Los Angeles Housing Department",
        "the Los Angeles Housing Department",
        "el Departamento de Vivienda de Los Ángeles",
        "https://housing.lacity.gov/residents",
    ),
    "Berkeley, CA": (
        "Berkeley Rent Board",
        "the Berkeley Rent Board",
        "la Junta de Rentas de Berkeley",
        "https://rentboard.berkeleyca.gov",
    ),
    "Jersey City, NJ": (
        "Jersey City Office of Landlord/Tenant Relations",
        "the Jersey City Office of Landlord/Tenant Relations",
        "la Oficina de Relaciones entre Arrendadores e Inquilinos de Jersey City",
        "https://www.jerseycitynj.gov/landlordtenant",
    ),
    "NJ": (
        "NJ DCA: Truth in Renting",
        "the New Jersey Department of Community Affairs",
        "el Departamento de Asuntos Comunitarios de Nueva Jersey",
        "https://www.nj.gov/dca/codes/publications/pdf_lti/t_i_r.pdf",
    ),
}
HELP_ANY = (
    "USA.gov: Tenant rights",
    "a local tenant organization or legal aid office",
    "una organización local de inquilinos o una oficina de asistencia legal",
    "https://www.usa.gov/tenant-rights",
)

MONTHS_EN = (
    "January February March April May June July August September October November December".split()
)
MONTHS_ES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()


class LetterIn(C.CheckIn):
    letter_date: dt.date | None = None
    address_text: str | None = Field(None, max_length=200)


# ------------------------------------------------------------------ formatting (as in features/check.js)
def money(n: float) -> str:
    return f"${n:,.2f}" if round(n, 2) % 1 else f"${n:,.0f}"


def num(n: float) -> str:
    s = f"{n:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def pct(n: float) -> str:
    return num(round(n, 2)) + "%"


def article(n: str) -> str:
    """'a' or 'an' before a number as it is read: an 8.33%, an 11%, an 18%, an 80%; a 1.5%, a 110% (EN only)."""
    digits = re.sub(r"[^0-9.]", "", n)
    whole = digits.split(".")[0]
    if (
        digits.startswith("8")
        or whole in ("11", "18")
        or (len(whole) in (5, 8) and whole[:2] in ("11", "18"))
    ):
        return "an"
    return "a"


def long_date(d: dt.date | str, lang: str) -> str:
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    if lang == "es":
        return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"
    return f"{MONTHS_EN[d.month - 1]} {d.day}, {d.year}"


def short_date(d: dt.date | str, lang: str) -> str:
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    if lang == "es":
        return f"{d.day} {MONTHS_ES[d.month - 1][:3]} {d.year}"
    return f"{MONTHS_EN[d.month - 1][:3]} {d.day}, {d.year}"


def quote_text(q: str) -> str:
    """The verbatim quote, cut before a parenthesis the source text leaves open (a link label), marked with …"""
    q = re.sub(r"\s+", " ", q or "").strip()
    if q.count("(") > q.count(")"):
        q = q[: q.rfind("(")].rstrip(" ,;:") + " …"
    if q[:1].islower():
        q = "… " + q
    return q


def short_url(u: str) -> str:
    p = urlparse(u or "")
    host = p.netloc.removeprefix("www.")
    path = p.path.rstrip("/")
    s = host + path
    return s if len(s) <= 64 else s[:61] + "…"


def _street(body: LetterIn) -> tuple[str | None, str | None]:
    """(street, 'City, ST') of the address the check ran for."""
    if body.address_id:
        from navigator import api as NA

        f = NA._addresses().get(body.address_id.upper())
        raw = f.raw if f else {}
        street = (raw.get("street_address") or "").strip()
        street = re.sub(r"\b[a-z]", lambda m: m.group(0).upper(), street.lower())
        city = raw.get("postal_city") or (f.city or "").split(",")[0] if f else ""
        return street or None, f"{city}, {f.state}" if f else None
    if body.address_text:
        parts = [p.strip() for p in body.address_text.split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[0], ", ".join(parts[1:])
        return parts[0] if parts else None, body.place.jurisdiction if body.place else None
    return None, body.place.jurisdiction if body.place and body.place.jurisdiction else None


def T(text: str, **kw) -> dict:
    return {"t": text, **kw}


def F(name: str) -> dict:
    return {"f": name}


BR = {"br": 1}

# The public site, for the QR code and footer of the PDF (features/paper.js)
SITE = os.environ.get("PUBLIC_ORIGIN", "https://navigator.isaaclins.com").rstrip("/")


def retrieved(url: str | None, fallback: str | None = None) -> str | None:
    """The day our copy of a source was retrieved (YYYY-MM-DD), from the source manifest by URL."""
    W = C._web()
    for m in W.STORE.manifest.values():
        if url and m.get("url") == url and m.get("retrieved_at"):
            return m["retrieved_at"][:10]
    return (fallback or "")[:10] or None


def verify_url(address_id: str | None, place: dict, as_of: str, lang: str) -> str:
    """Where the reader of the letter can check the rule: the address's shared rent answer, else the city's rules."""
    from web import share as SH

    q = "?lang=es" if lang == "es" else ""
    if address_id:
        try:
            a, _, d = SH.check_params(address_id.upper(), "rent", as_of)
            return f"{SITE}/s/{a}/rent/{d}{q}"
        except HTTPException:
            pass
    j = (place or {}).get("jurisdiction") or (place or {}).get("state")
    return f"{SITE}/#/rules/{quote(j)}" if j else f"{SITE}/"


def paper_address(body) -> tuple[str | None, str | None]:
    """(street, 'City, ST 94118') for the PDF: the notice's address lines, which carry the ZIP."""
    from web.notice import _address

    return _address(body)


# ------------------------------------------------------------------ the template
def build(body: LetterIn, result: dict) -> dict:
    lang = body.lang
    es = lang == "es"
    rent = next((v for v in result["verdicts"] if v["id"] == "rent"), None)
    if not rent or rent.get("code") not in ("over", "over_max"):
        raise HTTPException(422, "not_over")
    notice = next((v for v in result["verdicts"] if v["id"] == "notice"), None)
    x = rent["values"]
    cap = rent.get("cap") or {}
    rule = (rent.get("rules") or [{}])[0]
    juris = result["place"].get("jurisdiction")
    state = result["place"].get("state")
    cur, new, top = x["current_rent"], x["new_rent"], x["max_rent"]
    limit = x["cap_max"] if rent["code"] == "over_max" else x["cap_pct"]
    factor = num(1 + limit / 100)
    today = body.letter_date or dt.date.today()

    law, says = (LAW.get(rule.get("id")) or {}).get(lang) or (None, None)
    if not law:
        place = (juris or "").split(",")[0] if rule.get("level") == "city" else None
        if place:
            law = f"la ley de rentas de {place}" if es else f"the {place} rent law"
            says = "La ciudad indica:" if es else "The city states:"
        else:
            st = (STATE_ES if es else STATE).get(state, state)
            law = f"la ley de {st}" if es else f"{st} law"
            says = "La ley establece:" if es else "The law states:"
    cite = rule.get("citation")

    street, city = _street(body)
    blocks: list[dict] = []
    blocks.append({"k": "date", "s": [T(long_date(today, lang))]})
    sender = [F("name"), BR]
    if street:
        sender += [T(street + ", "), F("unit")]
    else:
        sender += [F("unit")]
    if city:
        sender += [BR, T(city)]
    blocks.append({"k": "from", "s": sender})
    if body.notice_date:
        re_line = (
            f"Asunto: aviso de aumento de renta del {long_date(body.notice_date, lang)}"
            if es
            else f"Re: Rent increase notice dated {long_date(body.notice_date, lang)}"
        )
    else:
        re_line = "Asunto: aviso de aumento de renta" if es else "Re: Rent increase notice"
    blocks.append({"k": "re", "s": [T(re_line, b=True)]})
    blocks.append(
        {
            "k": "salute",
            "s": [T("Estimado/a "), F("landlord"), T(":")]
            if es
            else [T("Dear "), F("landlord"), T(",")],
        }
    )

    eff = body.effective_date
    if es:
        p1 = [
            T("Su aviso aumenta mi renta de "),
            T(money(cur), b=True),
            T(" a "),
            T(money(new), b=True),
            T(" al mes"),
        ]
        p1 += [T(f" a partir del {long_date(eff, lang)}")] if eff else []
        p1 += [T(f". Es un aumento del {pct(x['increase_pct'])}.")]
    else:
        p1 = [
            T("Your notice raises my rent from "),
            T(money(cur), b=True),
            T(" to "),
            T(money(new), b=True),
            T(" a month"),
        ]
        p1 += [T(f" from {long_date(eff, lang)}")] if eff else []
        p1 += [T(f". That is {article(pct(x['increase_pct']))} {pct(x['increase_pct'])} increase.")]
    blocks.append({"k": "p", "s": p1})

    covered = (
        f"Considero que mi vivienda está cubierta por {law}"
        if es
        else f"I believe my unit is covered by {law}"
    )
    covered += f" ({cite}). " if cite and cite.lower() not in law.lower() else ". "
    blocks.append({"k": "p", "s": [T(covered + says)]})
    # quote the sentence that states the figure this letter uses (letter_quote), else the rule's own quote
    q, qurl = (
        (rule["letter_quote"], rule.get("letter_quote_url"))
        if rule.get("letter_quote") and cap.get("basis") == "period"
        else (rule.get("quote"), rule.get("url"))
    )
    blocks.append({"k": "quote", "s": [T("“" + quote_text(q or "") + "”")]})
    sources = [
        {
            "cite": cite,
            "url": qurl,
            "retrieved": retrieved(qurl, rule.get("retrieved")),
        }
    ]
    if qurl:
        blocks.append(
            {
                "k": "src",
                "s": [
                    T("Fuente (texto original en inglés): " if es else "Source: "),
                    T(short_url(qurl), href=qurl),
                ],
            }
        )

    math = f" ({money(cur)} × {factor})"
    if rent["code"] == "over_max":
        p3 = (
            f"Incluso con el límite más alto que permite la ley, del {pct(limit)}, mi renta puede ser como máximo de "
            if es
            else f"Even at the highest limit the law allows, {pct(limit)}, my rent can be at most "
        )
    elif cap.get("basis") == "formula":
        p3 = (
            f"Con un cambio del costo de vida (IPC) del {pct(cap['cpi'])}, el límite es del {pct(limit)}, así que mi renta puede ser como máximo de "
            if es
            else f"With a cost-of-living (CPI) change of {pct(cap['cpi'])}, the limit is {pct(limit)}, so my rent can be at most "
        )
    else:
        p3 = (
            f"Con un límite del {pct(limit)}, mi renta puede ser como máximo de "
            if es
            else f"At {pct(limit)}, my rent can be at most "
        )
    ask = "Le pido que me envíe un aviso corregido." if es else "Please send me a corrected notice."
    short = notice if notice and notice.get("kind") == "short" else None
    blocks.append(
        {
            "k": "p",
            "s": [
                T(p3),
                T(money(top), b=True),
                T(
                    (" al mes" if es else " a month")
                    + math
                    + "."
                    + (
                        " " + EXCEPTIONS[rule["id"]]["es" if es else "en"]
                        if rule.get("id") in EXCEPTIONS
                        else ""
                    )
                    + ("" if short else " " + ask)
                ),
            ],
        }
    )
    if short:
        n = short["values"]
        nr = (short.get("rules") or [{}])[0]
        st = (STATE_ES if es else STATE).get(state, state)
        if es:
            by = f" (según {nr['stated_by']})" if nr.get("stated_by") else ""
            under = (
                f" para un aumento de menos del {pct(nr['below_pct'])}"
                if nr.get("below_pct")
                else ""
            )
            txt = (
                f"Además, el aviso llegó {n['days_given']} días antes del aumento. La ley de {st} exige "
                f"{n['days_needed']} días de aviso por escrito{under}{by}, así que el"
                f" aumento no puede entrar en vigor antes del {long_date(n['earliest'], lang)}."
            )
        else:
            by = f" (as stated by {nr['stated_by']})" if nr.get("stated_by") else ""
            under = f" for an increase under {pct(nr['below_pct'])}" if nr.get("below_pct") else ""
            txt = (
                f"The notice also came {n['days_given']} days before the increase. {st} law requires "
                f"{n['days_needed']} days' written notice{under}{by}, so the increase cannot"
                f" take effect before {long_date(n['earliest'], lang)}."
            )
        blocks.append({"k": "p", "s": [T(txt)]})
        if nr.get("quote"):
            blocks.append({"k": "quote", "s": [T("“" + quote_text(nr["quote"]) + "”")]})
            sources.append(
                {
                    "cite": nr.get("citation"),
                    "url": nr.get("url"),
                    "retrieved": retrieved(nr.get("url"), nr.get("retrieved")),
                }
            )
        if nr.get("url"):
            blocks.append(
                {
                    "k": "src",
                    "s": [
                        T("Fuente (texto original en inglés): " if es else "Source: "),
                        T(short_url(nr["url"]), href=nr["url"]),
                    ],
                }
            )

        blocks.append({"k": "p", "s": [T(ask)]})

    blocks.append({"k": "sign", "s": [T("Atentamente," if es else "Thank you,"), BR, F("name")]})

    # the side panel: what the letter says, in three checks
    inc = f"+{pct(x['increase_pct'])}"
    if eff:
        inc += (
            f", a partir del {short_date(eff, lang)}"
            if es
            else f", starting {short_date(eff, lang)}"
        )
    if rent["code"] == "over_max":
        lim_t = (
            f"El límite es como máximo del {pct(limit)}"
            if es
            else f"The limit is at most {pct(limit)}"
        )
        lim_s = "Sea cual sea el IPC" if es else "Whatever the CPI"
    elif cap.get("basis") == "formula":
        lim_t = f"El límite es del {pct(limit)}" if es else f"The limit is {pct(limit)}"
        lim_s = (
            f"Con un IPC del {pct(cap['cpi'])}" if es else f"With a CPI change of {pct(cap['cpi'])}"
        )
    else:
        lim_t = f"El límite es del {pct(limit)}" if es else f"The limit is {pct(limit)}"
        lim_s = (
            (
                f"Hasta el {short_date(cap['end'], lang)}"
                if es
                else f"Until {short_date(cap['end'], lang)}"
            )
            if cap.get("end")
            else ""
        )
    lim_s = " · ".join(s for s in (lim_s, cite) if s)
    summary = [
        {
            "t": (
                f"Recibió {money(cur)} → {money(new)}"
                if es
                else f"You got {money(cur)} → {money(new)}"
            ),
            "s": inc,
        },
        {"t": lim_t, "s": lim_s},
        {
            "t": "Usted pide un aviso corregido" if es else "You ask for a corrected notice",
            "s": (f"Como máximo {money(top)} al mes" if es else f"At most {money(top)} a month"),
        },
    ]
    if short:
        n = short["values"]
        summary.append(
            {
                "t": "El aviso fue muy corto" if es else "The notice was too short",
                "s": (
                    f"Se requieren {n['days_needed']} días, recibió {n['days_given']}"
                    if es
                    else f"{n['days_needed']} days needed, {n['days_given']} given"
                ),
            }
        )

    office = HELP.get(juris or "") or HELP.get(state or "") or HELP_ANY
    help_ = {
        "name": (
            "USA.gov: derechos de los inquilinos"
            if office is HELP_ANY
            else "NJ DCA: Truth in Renting"
            if office is HELP["NJ"]
            else re.sub(r"^(la|el) ", "", office[2])
        )
        if es
        else office[0],
        "url": office[3],
        "line": (
            f"Lea la fuente citada. {office[2][0].upper() + office[2][1:]} o una organización de inquilinos pueden ayudarle."
            if office is not HELP_ANY
            else f"Lea la fuente citada. {office[2][0].upper() + office[2][1:]} puede ayudarle."
        )
        if es
        else (
            f"Read the cited source. {office[1][0].upper() + office[1][1:]} or a tenant organization can help."
            if office is not HELP_ANY
            else f"Read the cited source. {office[1][0].upper() + office[1][1:]} can help."
        ),
    }
    title = ("Carta al arrendador" if es else "Letter to landlord") + (
        f" - {street}" if street else ""
    )
    p_street, p_city = paper_address(body)
    paper = {
        "street": p_street or street,
        "city": p_city or city,
        "sources": sources,
        "verify": verify_url(body.address_id, result["place"], result["as_of"], lang),
        "site": SITE,
    }
    return {
        "lang": lang,
        "as_of": result["as_of"],
        "paper": paper,
        "verdict": rent,
        "notice": short,
        "letter": {"blocks": blocks, "text": to_text(blocks, lang)},
        "summary": summary,
        "help": help_,
        "fields": FIELDS[lang],
        "field_labels": FIELD_LABELS[lang],
        "title": title,
    }


def to_text(
    blocks: list[dict], lang: str, values: dict | None = None, fields: dict | None = None
) -> str:
    """The letter as plain text; fields as typed (values) or as their [placeholder]."""
    fields = fields or FIELDS[lang]
    out = []
    for b in blocks:
        s = ""
        for seg in b["s"]:
            if "br" in seg:
                s += "\n"
            elif "f" in seg:
                s += (values or {}).get(seg["f"]) or fields[seg["f"]]
            else:
                s += seg["href"] if seg.get("href") else seg["t"]
        out.append(s)
    return "\n\n".join(out) + "\n"


@router.post("/api/letter")
def letter(body: LetterIn, request: Request):
    _limit(C.CHECK_LIMIT, request)
    return build(body, C.run_check(body))
