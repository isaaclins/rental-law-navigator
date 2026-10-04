"""Draft a rent-increase notice for a building (#96): the landlord-side twin of the renter letter (#122).

POST /api/notice
    {"address_id": "A0027"} or {"place": {...}, "facts": {...}, "address_text": "..."}
    + "current_rent", optional "last_increase" (date), "new_rent", "start" (date), "cpi", "as_of" (the day the
      notice is drafted), "lang"
    -> {"start", "deadline", "new_rent", "verdict", "notice_verdict", "letter": {"blocks", "text"}, "checks",
        "help", "fields", ...}

Every amount and date comes from the same engine as /api/check (web.check.run_check, called with the start date
as the effective date and the deadline as the notice date):
  - new rent: as given, else the highest lawful rent when the cap is a known figure for the start date;
  - start: as given, else the first day of a month on or after both the last increase + 12 months (when the rule
    limits increases to one a year) and the drafting day + the notice period;
  - deadline: start - the notice period of the state's rule (CA-NOTICE-INC: 30 days for an increase under 10%).
A fixed template, no LLM. The checks say what was checked against the rules in our sources; they are not a
compliance certification. Names, unit and contact typed into the draft stay in the browser. Not legal advice.
"""

from __future__ import annotations

import datetime as dt
import re

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from web import check as C
from web import letter as LT
from web.any_address import FactsIn, PlaceIn, _limit

router = APIRouter()

FIELDS = {
    "en": {
        "tenant": "[Tenant name(s)]",
        "unit": "[Unit]",
        "owner": "[Owner or agent name]",
        "contact": "[Phone or email]",
        "given": "[Date given]",
    },
    "es": {
        "tenant": "[Nombre(s) del inquilino]",
        "unit": "[Unidad]",
        "owner": "[Nombre del propietario o agente]",
        "contact": "[Teléfono o correo]",
        "given": "[Fecha de entrega]",
    },
}
FIELD_LABELS = {
    "en": {
        "tenant": "Tenant name(s)",
        "unit": "Unit",
        "owner": "Owner or agent name",
        "contact": "Phone or email",
        "given": "Date given",
    },
    "es": {
        "tenant": "Nombre(s) del inquilino",
        "unit": "Unidad",
        "owner": "Nombre del propietario o agente",
        "contact": "Teléfono o correo",
        "given": "Fecha de entrega",
    },
}
ANNUAL = re.compile(
    r"once (?:every|per|a) (?:12 months|year)|12-month period|\bannual|\byearly|per year", re.I
)
WITH_NOTICE = re.compile(r"rent increase notice|with (?:any|each|the|a) (?:rent )?increase", re.I)


class NoticeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address_id: str | None = Field(None, pattern=r"^[A-Za-z0-9-]{1,20}$")
    place: PlaceIn | None = None
    facts: FactsIn = FactsIn()
    address_text: str | None = Field(None, max_length=200)
    current_rent: float = Field(gt=0, le=1_000_000)
    last_increase: dt.date | None = None
    new_rent: float | None = Field(None, gt=0, le=1_000_000)
    start: dt.date | None = None
    cpi: float | None = Field(None, ge=-20, le=30)
    as_of: dt.date | None = None
    lang: str = Field("en", pattern="^(en|es)$")


def money2(n: float) -> str:
    return f"${n:,.2f}"


def plus_months(d: dt.date, n: int) -> dt.date:
    return C._add_months(d, n)


def first_of_month_on_or_after(d: dt.date) -> dt.date:
    if d.day == 1:
        return d
    return dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def _check(body: NoticeIn, new: float, start: dt.date, notice: dt.date | None) -> dict:
    """The same call /api/check gets for this notice."""
    return C.run_check(C.CheckIn(**check_body(body, new, start, notice)))


def check_body(body: NoticeIn, new: float, start: dt.date, notice: dt.date | None) -> dict:
    out = {
        "current_rent": body.current_rent,
        "new_rent": new,
        "effective_date": start.isoformat(),
        "lang": body.lang,
        "facts": body.facts.model_dump(mode="json"),
    }
    if notice and notice <= start:
        out["notice_date"] = notice.isoformat()
    if body.address_id:
        out["address_id"] = body.address_id
    else:
        out["place"] = body.place.model_dump(mode="json")
    if body.cpi is not None:
        out["cpi"] = body.cpi
    return out


# What our sources do say about an increase notice where they state no number of days (NJ: D067, the Anti-Eviction
# Act's notice to quit and notice of rent increase)
NOTICE_NOTE = {
    "NJ": {
        "doc_id": "D067",
        "cite": "N.J.S.A. 2A:18-61.1 et seq.",
        "quote": "before an owner can evict a tenant for nonpayment of an increased rent, they must first serve the"
        " tenant with a valid notice to quit and notice of rent increase.",
        "en": "In New Jersey, a rent increase needs a notice to quit and a notice of the increase; our sources don't"
        " state the number of days.",
        "es": "En Nueva Jersey, un aumento de renta necesita un aviso de desalojo y un aviso del aumento; nuestras"
        " fuentes no indican el número de días.",
    }
}


def _notice_rule(state: str, increase_pct: float | None) -> dict | None:
    W = C._web()
    for r in C.NOTICE_RULES:
        if state not in r["states"] or W.STORE.verify(r).get("status") not in (
            "exact",
            "normalized",
        ):
            continue
        if increase_pct is not None and increase_pct < r["below_pct"]:
            return r
    return None


def _address(body: NoticeIn) -> tuple[str | None, str | None]:
    """(street, 'City, ST 94118')."""
    if body.address_id:
        from navigator import api as NA

        f = NA._addresses().get(body.address_id.upper())
        if not f:
            return None, None
        raw = f.raw
        street = re.sub(
            r"\b[a-z]", lambda m: m.group(0).upper(), (raw.get("street_address") or "").lower()
        )
        zip_ = re.search(r"\b(\d{5})\s*$", raw.get("matched_address") or "") or re.search(
            r"\d{5}", raw.get("zip") or ""
        )
        city = f"{raw.get('postal_city') or (f.city or '').split(',')[0]}, {f.state}"
        return street or None, city + (
            f" {zip_.group(1) if zip_.groups() else zip_.group(0)}" if zip_ else ""
        )
    parts = [x.strip() for x in (body.address_text or "").split(",") if x.strip()]
    if not parts:
        return None, body.place.jurisdiction if body.place else None

    def cap(w: str) -> str:
        return re.sub(r"\b[a-z]", lambda m: m.group(0).upper(), w.lower()) if w.isupper() else w

    street, rest = cap(parts[0]), parts[1:]
    zip_ = rest.pop() if rest and re.fullmatch(r"\d{5}(-\d{4})?", rest[-1]) else None
    st = rest.pop() if rest and re.fullmatch(r"[A-Za-z]{2}", rest[-1]) else None
    city = ", ".join(cap(x) for x in rest)
    line = ", ".join(x for x in (city, st.upper() if st else None) if x) + (
        f" {zip_}" if zip_ else ""
    )
    return street, line or (body.place.jurisdiction if body.place else None)


def build(body: NoticeIn) -> dict:
    lang, es = body.lang, body.lang == "es"
    W = C._web()
    today = body.as_of or dt.date.fromisoformat(W.DEFAULT_AS_OF)
    cur = body.current_rent

    # 1. the start date: one increase a year where the rule says so, and enough notice from today
    probe = _check(
        body, body.new_rent or round(cur * 1.5, 2), body.start or plus_months(today, 2), None
    )
    rent0 = next(v for v in probe["verdicts"] if v["id"] == "rent")
    rule = (rent0.get("rules") or [{}])[0]
    from navigator import api as NA

    rid = rule.get("id")
    full = next((r for r in NA.load_rules() if r["team_rule_id"] == rid), {})
    text = " ".join(
        str(x or "")
        for x in (full.get("requirement"), full.get("quoted_span"), full.get("key_value"))
    )
    annual = (
        bool(rid) and bool(ANNUAL.search(text)) and rent0.get("code") not in ("no_cap", "state_bar")
    )
    state = probe["place"]["state"]
    earliest_year = plus_months(body.last_increase, 12) if annual and body.last_increase else None

    def settle(start: dt.date, new: float | None):
        res = _check(body, new or round(cur * 1.5, 2), start, None)
        rv = next(v for v in res["verdicts"] if v["id"] == "rent")
        if not new and rv.get("code") == "over":
            new = rv["values"]["max_rent"]  # the highest lawful rent for this start date
        inc = round((new - cur) / cur * 100, 4) if new else None
        if inc is None and rv.get("cap", {}).get("pct") is not None:
            inc = rv["cap"]["pct"]  # notice period for an increase up to the cap
        nr = _notice_rule(state, inc) if inc is not None else _notice_rule(state, 0.0)
        return new, nr

    if body.start:
        start = body.start
        new, nr = settle(start, body.new_rent)
    else:
        start = first_of_month_on_or_after(
            max(earliest_year or today, today + dt.timedelta(days=1))
        )
        new, nr = settle(start, body.new_rent)
        if nr and start - dt.timedelta(days=nr["days"]) < today:
            start = first_of_month_on_or_after(today + dt.timedelta(days=nr["days"]))
            new, nr = settle(start, body.new_rent)
    deadline = start - dt.timedelta(days=nr["days"]) if nr else None

    # 2. the final check: exactly what /api/check returns for this notice
    # (no new rent yet: a 0.01% probe shows the cap's state without assuming an amount)
    result = _check(body, new or round(cur * 1.0001, 2), start, deadline)
    rent = next(v for v in result["verdicts"] if v["id"] == "rent")
    notice_v = next((v for v in result["verdicts"] if v["id"] == "notice"), None)
    if not new:
        rent = {**rent, "values": {**rent.get("values", {}), "new_rent": None}}
    x = rent.get("values") or {}
    rule = (rent.get("rules") or [{}])[0]
    cite = rule.get("citation")
    juris = result["place"].get("jurisdiction")
    office = LT.HELP.get(juris or "") or LT.HELP.get(state or "") or LT.HELP_ANY
    office_name = office[2] if es else office[1]
    if office is LT.HELP_ANY:
        office_name = "la oficina de vivienda de la ciudad" if es else "the city's housing office"
    code = rent.get("code")
    cap_known = code in ("within", "over") and x.get("cap_pct") is not None
    is_over = bool(new) and code in ("over", "over_max")
    too_late = deadline is not None and deadline < today
    too_soon = earliest_year is not None and start < earliest_year

    # 3. the notice
    street, city = _address(body)
    blocks: list[dict] = []
    T, F, BR = LT.T, LT.F, LT.BR
    D = lambda d: LT.long_date(d, lang)  # noqa: E731
    blocks.append(
        {"k": "title", "s": [T("AVISO DE AUMENTO DE RENTA" if es else "NOTICE OF RENT INCREASE")]}
    )
    to = [
        T("Para: " if es else "To: "),
        F("tenant"),
        T(" y todos los demás ocupantes" if es else " and all other occupants"),
        BR,
    ]
    if street:
        to += [T(street + ", "), F("unit")]
    else:
        to += [F("unit")]
    if city:
        to += [T(", " + city)]
    blocks.append({"k": "to", "s": to})
    # a notice of increase: a new rent at or below the current one is never printed (no "an increase of $-237,574")
    shown_new = new if new and cur and new > cur else None
    new_seg = (
        T(money2(shown_new), v=1, over=1 if is_over else None)
        if shown_new
        else T("[nueva renta]" if es else "[new rent]", ph=1)
    )
    p1 = [
        T("Su renta mensual aumentará de " if es else "Your monthly rent will increase from "),
        T(money2(cur), v=1),
        T(" a " if es else " to "),
        new_seg,
    ]
    if shown_new:
        d_amt, d_pct = round(new - cur, 2), LT.pct((new - cur) / cur * 100)
        p1 += [
            T(
                f", un aumento de {money2(d_amt)} ({d_pct})"
                if es
                else f", an increase of {money2(d_amt)} ({d_pct})"
            )
        ]
    p1 += [T(", a partir del " if es else ", starting "), T(D(start), v=1), T(".")]
    blocks.append({"k": "p", "s": p1})

    law, says = (LT.LAW.get(rule.get("id")) or {}).get(lang) or (None, None)
    # quote the sentence that states what the notice relies on (letter_quote: the figure, or the governing rule)
    if rule.get("letter_quote") and (rent.get("cap", {}).get("basis") == "period" or not cap_known):
        rule = {
            **rule,
            "quote": rule["letter_quote"],
            "url": rule.get("letter_quote_url") or rule.get("url"),
        }
    if rule.get("quote") and code not in ("no_cap", "state_bar", "need_fact"):
        if not law:
            place = (juris or "").split(",")[0]
            law = (
                (f"la ley de rentas de {place}" if es else f"the {place} rent law")
                if place
                else ("la ley estatal" if es else "state law")
            )
            says = "La norma indica:" if es else "The rule states:"
        if cap_known and not is_over:
            basis = (
                f"Este aumento está dentro del límite de {law}"
                if es
                else f"This increase is within the limit of {law}"
            )
        else:
            basis = (
                f"Este aumento se rige por {law}" if es else f"This increase is governed by {law}"
            )
        basis += f" ({cite}). " if cite and cite.lower() not in law.lower() else ". "
        blocks.append({"k": "p", "s": [T(basis + says)]})
        blocks.append({"k": "quote", "s": [T("“" + LT.quote_text(rule["quote"]) + "”")]})
        if rule.get("url"):
            blocks.append(
                {
                    "k": "src",
                    "s": [
                        T((cite + " · ") if cite else ""),
                        T(LT.short_url(rule["url"]), href=rule["url"]),
                    ],
                }
            )
    if nr:
        p3 = (
            f"Este aviso se entrega al menos {nr['days']} días antes de que empiece la nueva renta. "
            if es
            else f"This notice is given at least {nr['days']} days before the new rent starts. "
        )
    else:
        p3 = ""
    p3 += (
        "Todas las demás condiciones de su contrato siguen igual."
        if es
        else "All other terms of your tenancy stay the same."
    )
    blocks.append({"k": "p", "s": [T(p3)]})
    given_ph = (
        (
            f"[a más tardar el {LT.short_date(deadline, lang)}]"
            if es
            else f"[on or before {LT.short_date(deadline, lang)}]"
        )
        if deadline and not too_late
        else FIELDS[lang]["given"]
    )
    fields = {**FIELDS[lang], "given": given_ph}
    blocks.append(
        {
            "k": "sign",
            "s": [
                F("owner"),
                T(" · "),
                F("contact"),
                BR,
                T("Fecha de entrega: " if es else "Date given: "),
                F("given"),
            ],
        }
    )

    # 4. checked against the rules in our sources
    checks: list[dict] = []
    src = (
        {"cite": cite, "quote": LT.quote_text(rule.get("quote") or ""), "url": rule.get("url")}
        if rule.get("quote")
        else {}
    )
    until = rent.get("cap", {}).get("end")
    if cap_known:
        hi = (
            f"Máximo permitido: {LT.money(x['max_rent'])}"
            if es
            else f"Highest allowed: {LT.money(x['max_rent'])}"
        )
        if until:
            hi += (
                f" · hasta el {LT.short_date(until, lang)}"
                if es
                else f" · until {LT.short_date(until, lang)}"
            )
        if rent.get("cap", {}).get("basis") == "formula":
            c = rent["cap"]["cpi"]
            hi += f" · con un IPC del {LT.pct(c)}" if es else f" · with a CPI change of {LT.pct(c)}"
        if is_over:
            checks.append(
                {
                    "st": "over",
                    "t": (
                        f"Supera el límite del {LT.pct(x['cap_pct'])} por {LT.money(x['over_amount'])}"
                        if es
                        else f"Over the {LT.pct(x['cap_pct'])} cap by {LT.money(x['over_amount'])}"
                    ),
                    "s": hi,
                    **src,
                }
            )
        else:
            checks.append(
                {
                    "st": "ok",
                    "t": (
                        f"Dentro del límite del {LT.pct(x['cap_pct'])}"
                        if es
                        else f"Within the {LT.pct(x['cap_pct'])} cap"
                    ),
                    "s": hi,
                    **src,
                }
            )
    elif code == "over_max":
        checks.append(
            {
                "st": "over" if new else "info",
                "t": (
                    f"Supera el máximo del {LT.pct(x['cap_max'])}"
                    if es
                    else f"Over the {LT.pct(x['cap_max'])} maximum"
                ),
                "s": (
                    f"Máximo permitido: {LT.money(x['max_rent'])}, sea cual sea el IPC"
                    if es
                    else f"Highest allowed: {LT.money(x['max_rent'])}, whatever the CPI"
                ),
                **src,
            }
        )
    elif code == "need_cpi":
        if new:
            msg = (
                f"Dentro del límite solo si el cambio del IPC es de al menos {LT.pct(x['cpi_needed'])}. Indique el IPC."
                if es
                else f"Within the cap only if the CPI change is at least {LT.pct(x['cpi_needed'])}. Enter the CPI."
            )
        else:
            one = x.get("cpi_share", 1) == 1
            sh = LT.pct(x.get("cpi_share", 1) * 100)
            base = f"{LT.pct(x['cap_base'])} + " if x.get("cap_base") else ""
            msg = (
                f"{base}{'el' if one else sh + ' del'} cambio del IPC, como máximo {LT.pct(x['cap_max'])}. Indique el IPC."
                if es
                else f"{base}{'the' if one else sh + ' of the'} CPI change, at most {LT.pct(x['cap_max'])}. Enter the CPI."
            )
        checks.append(
            {
                "st": "info",
                "t": (
                    "El límite depende del IPC local" if es else "The cap depends on the local CPI"
                ),
                "s": msg,
                "need": "cpi",
                **src,
            }
        )
    elif code == "need_figure":
        checks.append(
            {
                "st": "info",
                "t": (
                    f"Sin cifra para el {LT.short_date(start, lang)}"
                    if es
                    else f"No figure for {LT.short_date(start, lang)}"
                ),
                "s": (
                    f"Nuestras fuentes no tienen el aumento permitido para esa fecha. Consulte: {office_name}."
                    if es
                    else f"Our sources have no allowed increase for that date yet. Check with {office_name}."
                ),
                **src,
            }
        )
    elif code == "need_fact":
        need = rent.get("need") or {}
        what = {
            "year_built": ("the year built", "el año de construcción"),
            "units": ("the number of units", "el número de unidades"),
            "owner_occupied": ("whether the owner lives there", "si el dueño vive allí"),
        }.get(
            need.get("key"),
            ("a fact not in public data", "un dato que no está en los datos públicos"),
        )
        checks.append(
            {
                "st": "info",
                "t": (
                    "Si hay un límite depende de un dato"
                    if es
                    else "Whether a cap applies depends on a fact"
                ),
                "s": (f"Falta: {what[1]}." if es else f"Missing: {what[0]}."),
                **src,
            }
        )
    elif code in ("no_cap", "state_bar"):
        checks.append(
            {
                "st": "info",
                "t": (
                    "Ningún límite de renta en nuestras fuentes"
                    if es
                    else "No rent cap in our sources"
                ),
                "s": (
                    "Para este edificio en esta fecha." if es else "For this building on this date."
                ),
                **src,
            }
        )
    if nr and not new:
        nsrc = {
            "cite": nr["citation_es" if es else "citation"],
            "quote": nr["quoted_span"],
            "url": nr["source_url"],
        }
        checks.append(
            {
                "st": "info",
                "t": ("Plazo de aviso" if es else "Notice period"),
                "s": (
                    f"{nr['days']} días para un aumento de menos del {LT.pct(nr['below_pct'])}: entréguelo a más tardar el {LT.short_date(deadline, lang)} para el {LT.short_date(start, lang)}"
                    if es
                    else f"{nr['days']} days for an increase under {LT.pct(nr['below_pct'])}: give it by {LT.short_date(deadline, lang)} for {LT.short_date(start, lang)}"
                ),
                **nsrc,
            }
        )
    elif nr:
        nsrc = {
            "cite": nr["citation_es" if es else "citation"],
            "quote": nr["quoted_span"],
            "url": nr["source_url"],
        }
        if too_late:
            checks.append(
                {
                    "st": "over",
                    "t": (
                        f"Muy tarde para {nr['days']} días de aviso"
                        if es
                        else f"Too late for {nr['days']} days' notice"
                    ),
                    "s": (
                        f"Para empezar el {LT.short_date(start, lang)} había que darlo antes del {LT.short_date(deadline, lang)}."
                        if es
                        else f"For {LT.short_date(start, lang)} it had to be given by {LT.short_date(deadline, lang)}."
                    ),
                    **nsrc,
                }
            )
        else:
            checks.append(
                {
                    "st": "ok",
                    "t": (f"{nr['days']} días de aviso" if es else f"{nr['days']} days' notice"),
                    "s": (
                        f"Entréguelo a más tardar el {LT.short_date(deadline, lang)} para el {LT.short_date(start, lang)}"
                        if es
                        else f"Give it by {LT.short_date(deadline, lang)} for {LT.short_date(start, lang)}"
                    ),
                    **nsrc,
                }
            )
    else:
        st = (LT.STATE_ES if es else LT.STATE).get(state, state)
        note = NOTICE_NOTE.get(state)
        if note:
            meta = C._web().STORE.doc_meta(note["doc_id"])
            checks.append(
                {
                    "st": "info",
                    "t": ("Plazo de aviso" if es else "Notice period"),
                    "s": note["es" if es else "en"],
                    "cite": note["cite"],
                    "quote": note["quote"],
                    "url": meta.get("url"),
                }
            )
        else:
            checks.append(
                {
                    "st": "info",
                    "t": ("Plazo de aviso" if es else "Notice period"),
                    "s": (
                        f"Nuestras fuentes no indican el plazo de aviso para este aumento en {st}."
                        if es
                        else f"Our sources do not state the notice period for this increase in {st}."
                    ),
                }
            )
    if annual:
        if not body.last_increase:
            checks.append(
                {
                    "st": "info",
                    "t": "Un aumento al año" if es else "One increase a year",
                    "s": "Indique la fecha del último aumento para revisarlo."
                    if es
                    else "Add the date of the last increase to check it.",
                }
            )
        elif too_soon:
            checks.append(
                {
                    "st": "over",
                    "t": "Menos de 12 meses desde el último aumento"
                    if es
                    else "Less than 12 months after the last increase",
                    "s": (
                        f"Lo más pronto: {LT.short_date(earliest_year, lang)}"
                        if es
                        else f"Earliest: {LT.short_date(earliest_year, lang)}"
                    ),
                }
            )
        else:
            checks.append(
                {
                    "st": "ok",
                    "t": "Un aumento al año" if es else "One increase a year",
                    "s": (
                        f"Último aumento: {LT.short_date(body.last_increase, lang)}"
                        if es
                        else f"Last increase {LT.short_date(body.last_increase, lang)}"
                    ),
                }
            )
    others = []
    for e in result_rules(body, start):
        for s in re.split(r"(?<=[.;])\s+", e.get("requirement") or ""):
            if WITH_NOTICE.search(s):
                others.append((e, s))
    if others:
        e, s = others[0]
        checks.append(
            {
                "st": "info",
                "t": "Otros avisos requeridos" if es else "Other required notices",
                "s": (
                    f"{e.get('citation')}: {s} (resumen en inglés)"
                    if es
                    else f"{e.get('citation')}: {s}"
                ),
                "url": e.get("source_url"),
            }
        )
    else:
        checks.append(
            {
                "st": "info",
                "t": "Otros avisos requeridos" if es else "Other required notices",
                "s": (
                    f"Ninguno en nuestras fuentes para esta dirección. Consulte: {office_name}."
                    if es
                    else f"None in our sources for this address. Check with {office_name}."
                ),
            }
        )

    title = ("Aviso de aumento de renta" if es else "Rent increase notice") + (
        f" - {street}" if street else ""
    )
    # for the PDF (features/paper.js): the sources the notice cites, with the day our copy was retrieved
    sources = []
    if rule.get("quote") and code not in ("no_cap", "state_bar", "need_fact") and rule.get("url"):
        sources.append(
            {
                "cite": cite,
                "url": rule["url"],
                "retrieved": LT.retrieved(rule["url"], rule.get("retrieved")),
            }
        )
    if nr:
        sources.append(
            {
                "cite": nr["citation_es" if es else "citation"],
                "url": nr["source_url"],
                "retrieved": LT.retrieved(nr["source_url"], nr.get("retrieved_at")),
            }
        )
    paper = {
        "street": street,
        "city": city,
        "sources": sources,
        "verify": LT.verify_url(body.address_id, result["place"], start.isoformat(), lang),
        "site": LT.SITE,
    }
    return {
        "paper": paper,
        "lang": lang,
        "as_of": today.isoformat(),
        "current_rent": cur,
        "new_rent": new,
        "start": start.isoformat(),
        "deadline": deadline.isoformat() if deadline else None,
        "notice_days": nr["days"] if nr else None,
        "last_increase": body.last_increase.isoformat() if body.last_increase else None,
        "earliest_by_year": earliest_year.isoformat() if earliest_year else None,
        "annual": annual,
        "over": is_over or too_late or too_soon,
        "check_body": check_body(body, new or cur, start, deadline),
        "verdict": rent,
        "notice_verdict": notice_v,
        "letter": {"blocks": blocks, "text": LT.to_text(blocks, lang, fields=fields)},
        "checks": checks,
        "help": {
            "name": (
                re.sub(r"^(la|el) ", "", office[2])
                if es and office is not LT.HELP_ANY
                else office[0]
            ),
            "url": office[3],
        },
        "fields": fields,
        "field_labels": FIELD_LABELS[lang],
        "title": title,
    }


def result_rules(body: NoticeIn, start: dt.date) -> list[dict]:
    """In-force rent-increase rules that apply (or may apply) to this building on the start date."""
    from navigator import evaluate as E

    cb = C.CheckIn(**{**check_body(body, body.current_rent, start, None)})
    ctx = C._context(cb, start)
    return [
        ctx["rules"][e["team_rule_id"]]
        for e in C._in_cat(ctx, "rent_increase_limits")
        if E.time_status(ctx["rules"][e["team_rule_id"]], start) == "in_force"
    ]


@router.post("/api/notice")
def notice(body: NoticeIn, request: Request):
    _limit(C.CHECK_LIMIT, request)
    if not body.address_id and not body.place:
        from fastapi import HTTPException

        raise HTTPException(422, "address_id or place is required")
    return build(body)
