"""Rent increases the question states, checked by code, not by the model (#101, 2026-10-04).

"10% every six months", "3% and then 4%", "6% once", "two 5% raises this year", "three increases in 12 months":
parse_increases() reads them; compute() adds them up over 12 months (compounded, as the caps compare with the rent a
year earlier) and checks the total against the cap of the governing rule (web/check.py: the same parsers as the
Check page) and the number of increases against the rule's own count limit ("at most two increases", "once every 12
months"). The answer's verdict follows this computation; the model only explains it.
"""

from __future__ import annotations

import datetime as dt
import re

WORDN = {
    "one": 1,
    "once": 1,
    "two": 2,
    "twice": 2,
    "three": 3,
    "thrice": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "un": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "seis": 6,
}
_PCT = r"(\d+(?:\.\d+)?)\s*(?:%|percent|por ciento)"
_N = r"(\d+|one|two|three|four|five|six|un|una|dos|tres|cuatro|seis)"


def _n(w: str) -> int:
    return int(w) if w.isdigit() else WORDN[w.lower()]


LIMIT_PCT = re.compile(  # a % that names the rule's limit ("the LA 3% limit", "a cap of 5%"), not an increase
    r"\b(?:cap|limit|ceiling|maximum|tope|l[ií]mite)\s+(?:of|is|was|de|es)\s+"
    + _PCT
    + r"|"
    + _PCT
    + r"\s*(?:rent\s+)?(?:increase\s+|raise\s+)?(?:limit|cap|ceiling|maximum|rule|figure|allowance)\b",
    re.I,
)


def parse_increases(q: str) -> dict | None:
    """{"pcts": [10, 10], "count": 2, "window": "12 months"} or None when the question states no increase."""
    t = LIMIT_PCT.sub(" ", q.lower())
    pcts = [float(x) for x in re.findall(_PCT, t)]
    # 10% every six months / 5% every 4 months / 10% cada seis meses
    m = re.search(
        _PCT
        + r"\s*(?:increase\s*|raise\s*|hike\s*)?(?:every|each|cada)\s+"
        + _N
        + r"\s+(?:months?|meses)",
        t,
    )
    if m:
        k = max(1, 12 // max(1, _n(m.group(2))))
        return {"pcts": [float(m.group(1))] * k, "count": k, "how": "every"}
    # 10% twice a year / two 5% increases this year / dos aumentos del 5%
    m = re.search(
        _PCT
        + r"\s*(?:increase|raise|hike)?s?\s*(twice|thrice|two times|three times|dos veces|tres veces|(\d) times)"
        r"\s*(?:a|per|in a|in one|this|each|in the same|al|en un|por)?\s*(?:year|12 months|twelve months|a[nñ]o)?",
        t,
    )
    if m:
        w = m.group(2)
        k = (
            int(m.group(3))
            if m.group(3)
            else {
                "twice": 2,
                "two times": 2,
                "dos veces": 2,
                "thrice": 3,
                "three times": 3,
                "tres veces": 3,
            }[w]
        )
        return {"pcts": [float(m.group(1))] * k, "count": k, "how": "times"}
    m = re.search(
        r"\b" + _N + r"\s+(?:separate\s+)?" + _PCT + r"\s*(?:increases|raises|hikes)", t
    ) or re.search(r"\b" + _N + r"\s+(?:aumentos|subidas)\s+de(?:l)?\s+" + _PCT, t)
    if m:
        k = _n(m.group(1))
        return {"pcts": [float(m.group(2))] * k, "count": k, "how": "times"}
    # three increases in 12 months (no %)
    m = re.search(r"\b" + _N + r"\s+(?:rent\s+)?(?:increases|raises|hikes|aumentos)\b", t)
    if m and _n(m.group(1)) >= 2 and len(pcts) <= 1:
        k = _n(m.group(1))
        return {"pcts": pcts * k if pcts else [], "count": k, "how": "count"}
    if len(pcts) >= 2 and re.search(
        r"\b(?:and|then|plus|another|later|followed by|y|luego|despu[eé]s|otro)\b|\+", t
    ):
        return {"pcts": pcts, "count": len(pcts), "how": "list"}
    if len(pcts) == 1 and re.search(
        r"\b(?:raise|raising|increase|increasing|go up|goes up|hike|subir|suban|aumento|aumentar)\b",
        t,
    ):
        once = bool(re.search(r"\bonce\b|\buna vez\b", t))
        return {"pcts": pcts, "count": 1, "how": "once" if once else "single"}
    return None


def total(pcts: list[float]) -> float:
    f = 1.0
    for p in pcts:
        f *= 1 + p / 100
    return round((f - 1) * 100, 2)


def count_limit(rule: dict) -> int | None:
    """The number of increases the rule allows in 12 months, if it says."""
    text = " ".join(str(rule.get(k) or "") for k in ("requirement", "key_value", "quoted_span"))
    if re.search(
        r"\bonce (?:per|every|a|each) (?:12 months|twelve months|year)\b|\bonce per 12", text, re.I
    ):
        return 1
    m = re.search(
        r"\b(?:at most|no more than|not more than|up to)\s+(one|two|three|\d)\s+(?:increases|increments)",
        text,
        re.I,
    )
    if m:
        return _n(m.group(1))
    if re.search(r"more than two increments", text, re.I):
        return 2
    return None


def compute(parsed: dict, ctx_body: dict, as_of: str) -> dict | None:
    """Check the stated increases at a place: ctx_body is web.check.CheckIn input (address_id or place)."""
    from web import check as C

    try:
        body = C.CheckIn(
            **ctx_body, as_of=dt.date.fromisoformat(as_of), current_rent=1000, increase_pct=0.0
        )
        ctx = C._context(body, dt.date.fromisoformat(as_of))
    except Exception:  # noqa: BLE001 - an unknown place: no computed verdict
        return None
    pcts = parsed["pcts"]
    tot = total(pcts) if pcts else None
    rv = C.check_rent(ctx, 1000.0, 1000.0 * (1 + (tot or 0) / 100), None, "en")
    rule_id = rv["rules"][0]["id"] if rv.get("rules") else None
    rule = ctx["rules"].get(rule_id) if rule_id else None
    conditional = False
    if rv.get("code") == "need_fact" and rule:
        # the engine can't tell whether the cap covers this home (no building facts): check against that cap anyway
        # and say so ("if the cap covers your home")
        cap = C.cap_on(
            C.parse_rent_cap(rule.get("key_value"), rule.get("requirement")),
            dt.date.fromisoformat(as_of),
        )
        rv = {
            **C.rent_verdict(1000.0, 1000.0 * (1 + (tot or 0) / 100), cap),
            "rules": rv["rules"],
            "cap": cap,
        }
        conditional = True
    limit = count_limit(rule) if rule else None
    out = {
        "pcts": pcts,
        "total": tot,
        "count": parsed["count"],
        "how": parsed["how"],
        "rule_id": rule_id,
        "count_limit": limit,
        "cap": rv.get("cap"),
        "code": rv.get("code"),
        "kind": rv.get("kind"),
        "values": rv.get("values") or {},
        "need": rv.get("need"),
    }
    count_over = bool(limit and parsed["count"] > limit)
    if tot is None:  # only a count was stated
        out["verdict"] = "over" if count_over else "unknown"
    elif rv.get("kind") == "over" or count_over:
        out["verdict"] = "over"
    elif rv.get("kind") == "ok":
        out["verdict"] = "ok"
    elif rv.get("code") == "need_cpi" and tot <= (rv.get("values") or {}).get("cap_base", -1):
        out["verdict"] = "ok"  # within the fixed part of '5% + CPI': allowed unless prices fell
    elif rv.get("kind") == "none":
        out["verdict"] = "no_cap"
    else:
        out["verdict"] = "unknown"
    out["count_over"] = count_over
    if not conditional and rule_id:  # the engine can't tell yet whether that rule covers the home
        conditional = any(
            e["team_rule_id"] == rule_id and e["result"] == "unknown" for e in ctx["entries"]
        )
    out["conditional"] = conditional
    return out


def sentence(c: dict, lang: str, place_label: str, *, asked_date: bool = False) -> tuple[str, str]:
    """(answer line, why line) for the computed verdict, in plain words. ("", "") when the computation can't say
    more than the model (no figure to compare with); the why line is "" when it would only repeat the question."""
    pc = lambda x: (f"{x:g}%" if lang == "en" else f"{x:g} %").replace(" %", "%")  # noqa: E731
    parts = " + ".join(pc(p) for p in c["pcts"]) if c["pcts"] else ""
    tot = c.get("total")
    cap = c.get("cap") or {}
    v = c.get("values") or {}
    cap_txt = (
        pc(cap["pct"])
        if cap.get("pct") is not None
        else (
            (
                f"{v.get('cap_base', 5):g}% plus inflation, at most {v.get('cap_max', 10):g}%"
                if lang == "en"
                else f"{v.get('cap_base', 5):g}% más la inflación, como máximo {v.get('cap_max', 10):g}%"
            )
            if c.get("code") in ("need_cpi", "over_max") or "cap_max" in v
            else None
        )
    )
    many = len(c["pcts"]) > 1
    total_txt = (
        (
            f"{parts} add up to {pc(tot)} over 12 months"
            if lang == "en"
            else f"{parts} suman {pc(tot)} en 12 meses"
        )
        if many and tot is not None
        else (
            f"{'An' if re.match(r'(?:8|11|18)(?:\D|$)', pc(tot)) else 'A'} {pc(tot)} increase"
            if lang == "en"
            else f"Un aumento del {pc(tot)}"
        )
        if tot is not None
        else ""
    )
    lim = c.get("count_limit")
    cond = c.get("conditional")
    if c["verdict"] == "over":
        a = (
            (
                "No, not if the cap covers your home."
                if cond
                else "No, that's more than the law allows."
            )
            if lang == "en"
            else (
                "No, si el tope cubre su vivienda."
                if cond
                else "No, eso es más de lo que permite la ley."
            )
        )
        reasons = []
        if c.get("count_over"):
            reasons.append(
                f"{c['count']} increases in 12 months is more than the {lim} allowed"
                if lang == "en"
                else f"{c['count']} aumentos en 12 meses son más de los {lim} permitidos"
            )
        if (
            tot is not None
            and (c.get("kind") == "over" or c.get("code") in ("over", "over_max"))
            and cap_txt
        ):
            reasons.append(
                f"{total_txt}, above the limit of {cap_txt}"
                if lang == "en"
                else f"{total_txt}, por encima del límite de {cap_txt}"
            )
        why = ("; ".join(reasons) or total_txt) + "."
    elif c["verdict"] == "ok":
        a = (
            ("Yes, if the cap covers your home." if cond else "Yes, that's within the limit.")
            if lang == "en"
            else ("Sí, si el tope cubre su vivienda." if cond else "Sí, está dentro del límite.")
        )
        why = (
            (
                f"{total_txt}, within the limit of {cap_txt}"
                if lang == "en"
                else f"{total_txt}, dentro del límite de {cap_txt}"
            )
            if cap_txt
            else total_txt
        )
        if lim and c["count"] <= lim and c["count"] > 1:
            why += (
                f", in {c['count']} increases (up to {lim} allowed)"
                if lang == "en"
                else f", en {c['count']} aumentos (se permiten hasta {lim})"
            )
        why += "."
    elif c["verdict"] == "no_cap":
        a = "No rent cap covers this." if lang == "en" else "Ningún tope de renta cubre esto."
        why = (
            f"{total_txt}; our sources show no rent cap for {place_label}."
            if lang == "en"
            else f"{total_txt}; nuestras fuentes no muestran tope de renta para {place_label}."
        )
    else:
        need = (c.get("need") or {}).get("key")
        if c.get("code") == "need_cpi":
            a = (
                "It depends on local inflation."
                if lang == "en"
                else "Depende de la inflación local."
            )
            why = (
                f"{total_txt}: allowed only if {v.get('cap_base', 5):g}% plus local inflation is at least that, and never above {v.get('cap_max', 10):g}%."
                if lang == "en"
                else f"{total_txt}: solo se permite si {v.get('cap_base', 5):g}% más la inflación local llega a eso, y nunca más de {v.get('cap_max', 10):g}%."
            )
        elif need == "rate_figure":
            a = (
                (
                    "Our sources don't give the limit for that date."
                    if asked_date
                    else "Our sources don't give the current limit."
                )
                if lang == "en"
                else (
                    "Nuestras fuentes no dan el límite para esa fecha."
                    if asked_date
                    else "Nuestras fuentes no dan el límite actual."
                )
            )
            why = ""
        elif not cap_txt:  # no figure to check against: the model explains what decides it
            return "", ""
        else:
            a = "It depends on the building." if lang == "en" else "Depende del edificio."
            why = (
                f"{total_txt}; whether it's allowed depends on facts about the building we don't know."
                if lang == "en"
                else f"{total_txt}; depende de datos del edificio que no conocemos."
            )
    if why and cond and c["verdict"] in ("over", "ok", "unknown") and c.get("code") != "need_fact":
        why = (
            ("If the cap covers your home: " if lang == "en" else "Si el tope cubre su vivienda: ")
            + why[0].lower()
            + why[1:]
        )
    return a, why.strip()


_MONEY = r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"


def _amt(s: str) -> float:
    return float(s.replace(",", ""))


def parse_money(q: str) -> dict:
    """The rent and the increase the person names in dollars: {"rent": 1450.0, "inc": 200.0, "new": 1650.0}
    (each key only when said). Persona Keisha: "if my rent is $1,450, how much is that in dollars?"."""
    t = q.lower()
    out: dict = {}
    m = re.search(
        r"\b(?:rent|renta|alquiler)\b(?:\s+(?!by\b|to\b|up\b|a\b|another\b)[a-z',.-]+){0,4}?\s*"
        r"(?:is|of|was|es|de|era|now|ahora|:)?\s*(?:about\s+|around\s+)?" + _MONEY,
        t,
    ) or re.search(r"\b(?:pay|paying|pagar|pago|pagamos)\s+" + _MONEY, t)
    m = m or re.search(
        _MONEY
        + r"\s*(?:a month|/month|/mo\b|per month|monthly|al mes|por mes|mensuales|rent|de renta|de alquiler)",
        t,
    )
    if m:
        out["rent"] = _amt(m.group(1))
    m = re.search(r"\b(?:from|de)\s+" + _MONEY + r"\s+(?:to|a)\s+" + _MONEY, t)
    if m and _amt(m.group(2)) > _amt(m.group(1)):
        return {"rent": _amt(m.group(1)), "new": _amt(m.group(2))}
    m = re.search(
        r"\b(?:by|another|extra|more of|de|otros)\s+"
        + _MONEY
        + r"|\b(?:sub\w*|aument\w*|raise|increase)(?:\s+\w+){0,3}?\s+"
        + _MONEY
        + r"|"
        + _MONEY
        + r"\s*(?:more|increase|raise|hike|extra|de aumento|más)\b",
        t,
    )
    if m:
        out["inc"] = _amt(next(g for g in m.groups() if g))
    m = re.search(r"\b(?:to|up to|a)\s+" + _MONEY, t)
    if m and "rent" in out and _amt(m.group(1)) > out["rent"]:
        out["new"] = _amt(m.group(1))
    if "rent" in out and "inc" in out and out["inc"] >= out["rent"]:
        out.pop("inc")  # "$1,450 by $1,600": not an increase amount
    return out


def _usd(x: float) -> str:
    return f"${x:,.0f}" if abs(x - round(x)) < 0.005 else f"${x:,.2f}"


def money_pct(m: dict) -> float | None:
    """The % a dollar increase is, when the rent is known."""
    if not m.get("rent"):
        return None
    inc = (
        m.get("inc")
        if m.get("inc") is not None
        else (m["new"] - m["rent"] if m.get("new") else None)
    )
    return round(inc / m["rent"] * 100, 2) if inc else None


def money_line(m: dict, pcts: list[float], lang: str) -> str:
    """Arithmetic only, never a verdict: '10% of $1,450 is $145, so the rent would go from $1,450 to $1,595.'"""
    rent = m.get("rent")
    if not rent:
        return ""
    if m.get("inc") is not None or m.get("new"):
        inc = m["inc"] if m.get("inc") is not None else m["new"] - rent
        p = round(
            inc / rent * 100, 2
        )  # two decimals: "2.86%" next to a 2.87% limit, never a rounded "2.9%"
        return (
            f"{_usd(inc)} on {_usd(rent)} is {'an' if re.match(r'(?:8|11|18)(?:\D|$)', f'{p:g}') else 'a'} {p:g}% increase, so the rent would go from {_usd(rent)} to {_usd(rent + inc)}."
            if lang == "en"
            else f"{_usd(inc)} sobre {_usd(rent)} es un aumento del {p:g}%: la renta pasaría de {_usd(rent)} a {_usd(rent + inc)}."
        )
    if len(pcts) == 1:
        inc = rent * pcts[0] / 100
        return (
            f"{pcts[0]:g}% of {_usd(rent)} is {_usd(inc)}, so the rent would go from {_usd(rent)} to {_usd(rent + inc)}."
            if lang == "en"
            else f"El {pcts[0]:g}% de {_usd(rent)} son {_usd(inc)}: la renta pasaría de {_usd(rent)} a {_usd(rent + inc)}."
        )
    if pcts:
        new = rent * (1 + total(pcts) / 100)
        return (
            f"{' + '.join(f'{p:g}%' for p in pcts)} on {_usd(rent)} takes the rent to {_usd(new)} ({_usd(new - rent)} more)."
            if lang == "en"
            else f"{' + '.join(f'{p:g}%' for p in pcts)} sobre {_usd(rent)} lleva la renta a {_usd(new)} ({_usd(new - rent)} más)."
        )
    return ""
