"""Check a rent increase, deposit, application fee, notice or termination against the rules at an address (#40).

POST /api/check
    {"address_id": "A0001"}  or  {"place": {"state": "CA", "jurisdiction": "Los Angeles, CA"}, "facts": {...}}
    + "current_rent", "new_rent" or "increase_pct", "notice_date", "effective_date",
      optional "deposit", "application_fee", "termination" ("none" | "reason" | "no_reason"), "moved_in", "cpi"
    -> one verdict per item: kind ok | over | short | unknown | none, the numbers behind it, the fact that is missing
       (never guessed) and the deciding rule(s) with their verbatim quote and source.

Deterministic: rules come from output/rules.json via the evaluator (navigator.evaluate), caps are parsed from each
rule's key_value / requirement text by the small parsers below. No LLM at runtime, no invented figures: a cap the
data does not state for the date in question (a CPI value, next year's percentage) is reported as missing.
Not legal advice. Nothing is stored.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from web.any_address import FactsIn, PlaceIn, RateLimit, _limit

router = APIRouter()
CHECK_LIMIT = RateLimit(60, 60.0)

NUM = r"(\d+(?:\.\d+)?)"
MDY = r"(\d{1,2}/\d{1,2}/\d{4})"
MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "january february march april may june july august september october november december".split()
    )
}
DASH = r"\s*(?:[–—-]|through|to)\s*"


# ------------------------------------------------------------------ parsers (pure, unit-tested)
def _mdy(s: str) -> dt.date:
    m, d, y = (int(x) for x in s.split("/"))
    return dt.date(y, m, d)


def _long(s: str) -> dt.date:
    mm = re.match(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s.strip())
    return dt.date(int(mm.group(3)), MONTHS[mm.group(1).lower()], int(mm.group(2)))


def parse_rent_cap(*texts: str | None) -> dict:
    """Rent-cap figures stated in a rule's text.

    periods: [(pct, start, end)] from '3% for 7/1/2025–6/30/2026', '1.6% (3/1/2026–2/28/2027)',
             '1.6% of base rent for March 1, 2026 through February 28, 2027', '2026 AGA 1.0%' (calendar year)
    formula: cap = min(max, base + share * CPI) from '5% + CPI, max 10%', 'Lesser of 3% or 80% of CPI change',
             '65% of CPI, max 5%'
    bar:     the state forbids local rent control ('state bar on local rent control')
    """
    periods: list[tuple[float, dt.date, dt.date]] = []
    formula = None
    bar = False
    for text in texts:
        if not text:
            continue
        for m in re.finditer(NUM + r"%\s*(?:for|\()\s*" + MDY + DASH + MDY, text):
            periods.append((float(m.group(1)), _mdy(m.group(2)), _mdy(m.group(3))))
        long_d = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
        for m in re.finditer(NUM + r"%[^.;()]{0,30}?\bfor\s+" + long_d + DASH + long_d, text):
            periods.append((float(m.group(1)), _long(m.group(2)), _long(m.group(3))))
        for m in re.finditer(r"\b(\d{4}) AGA (?:is )?" + NUM + "%", text):
            y = int(m.group(1))
            periods.append((float(m.group(2)), dt.date(y, 1, 1), dt.date(y, 12, 31)))
        if formula is None:
            if m := re.search(NUM + r"%\s*\+\s*CPI,?\s*max\s*" + NUM + "%", text):
                formula = {"base": float(m.group(1)), "share": 1.0, "max": float(m.group(2))}
            elif m := re.search(
                r"[Ll](?:esser|ower) of "
                + NUM
                + r"%(?: per year)?,? or "
                + NUM
                + r"% of (?:the )?(?:percent change in the )?(?:CPI|Consumer Price Index)",
                text,
            ):
                formula = {"base": 0.0, "share": float(m.group(2)) / 100, "max": float(m.group(1))}
            elif m := re.search(NUM + r"% of CPI,?\s*max\s*" + NUM + "%", text):
                formula = {"base": 0.0, "share": float(m.group(1)) / 100, "max": float(m.group(2))}
        if re.search(
            r"bar on local rent control|may not enact, maintain or enforce rent control", text, re.I
        ):
            bar = True
    uniq = sorted(set(periods), key=lambda p: p[1])
    return {"periods": uniq, "formula": formula, "bar": bar}


def cap_on(parsed: dict, day: dt.date, cpi: float | None = None) -> dict:
    """The cap in percent on `day`. {'pct': x, 'basis': ...} or {'pct': None, 'need': ..., 'max'?: ...}."""
    for pct, start, end in parsed["periods"]:
        if start <= day <= end:
            return {
                "pct": pct,
                "basis": "period",
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
    f = parsed["formula"]
    if f:
        if cpi is not None:
            pct = round(max(0.0, min(f["max"], f["base"] + f["share"] * cpi)), 4)
            return {"pct": pct, "basis": "formula", "cpi": cpi, **f}
        return {"pct": None, "need": "cpi", **f}
    if parsed["bar"]:
        return {"pct": None, "basis": "no_cap"}
    return {"pct": None, "need": "rate_figure"}


def rent_verdict(cur: float, new: float, cap: dict) -> dict:
    """Compare an increase with a cap from cap_on (kind ok | over | unknown, plus the numbers)."""
    inc = round((new - cur) / cur * 100, 4)
    v = {"current_rent": round(cur, 2), "new_rent": round(new, 2), "increase_pct": round(inc, 2)}
    if inc <= 0:
        return {"kind": "ok", "code": "no_increase", "values": v}
    pct = cap.get("pct")
    if pct is not None:
        top = round(cur * (1 + pct / 100), 2)
        v |= {"cap_pct": pct, "max_rent": top}
        if new <= top + 0.005:
            return {"kind": "ok", "code": "within", "values": v}
        v |= {"over_amount": round(new - top, 2), "over_pct": round(inc - pct, 2)}
        return {"kind": "over", "code": "over", "values": v}
    if cap.get("need") == "cpi":
        hi = cap["max"]
        v |= {"cap_max": hi, "cap_base": cap["base"], "cpi_share": cap["share"]}
        if inc > hi + 1e-9:
            top = round(cur * (1 + hi / 100), 2)
            v |= {
                "max_rent": top,
                "over_amount": round(new - top, 2),
                "over_pct": round(inc - hi, 2),
            }
            return {"kind": "over", "code": "over_max", "values": v}
        # allowed exactly when base + share * CPI >= increase
        v["cpi_needed"] = round((inc - cap["base"]) / cap["share"], 2)
        return {"kind": "unknown", "code": "need_cpi", "values": v, "need": {"key": "cpi"}}
    return {"kind": "unknown", "code": "need_figure", "values": v}


def parse_deposit_cap(text: str | None) -> dict | None:
    """'1 month's rent (2 months for qualifying small landlords)' -> {'months': 1, 'alt_months': 2};
    '1.5 months' rent' -> 1.5; "Max = first month's rent" -> 1. Interest-only rules -> None."""
    if not text:
        return None
    alt = None
    if m := re.search(r"\(\s*" + NUM + r" months?\b[^)]*\bfor\b", text):
        alt = float(m.group(1))
    if m := re.search(NUM + r" months?['’]?s?['’]? rent", text):
        return {"months": float(m.group(1)), "alt_months": alt}
    if re.search(r"first month['’]s rent", text, re.I):
        return {"months": 1.0, "alt_months": alt}
    return None


def parse_fee_cap(key_value: str | None, effective: str | None) -> dict | None:
    """Application-fee cap.
    '$30 base ..., CPI-adjusted annually since 1998 ($68.96 for 2026 ...)' -> {'figures': {2026: 68.96}}
    '$50 per application, CPI-adjusted annually' (effective 2026-05-01) -> $50 for the 12 months from that date
    'First, last, security deposit, lock/key only' -> {'amount': 0} (a fee is not among the allowed charges)."""
    if not key_value:
        return None
    kv = key_value
    figures = {
        int(m.group(2)): float(m.group(1)) for m in re.finditer(r"\$" + NUM + r" for (\d{4})", kv)
    }
    if figures:
        return {"figures": figures}
    if m := re.search(r"\$" + NUM + r" (?:base )?per (?:applicant|application)", kv):
        amt = float(m.group(1))
        if re.search(r"CPI", kv):
            if re.search(r"\bbase\b", kv):
                return None  # only the historic base figure: not a current cap
            start = dt.date.fromisoformat(effective) if effective and len(effective) == 10 else None
            if not start:
                return None
            end = start.replace(year=start.year + 1) - dt.timedelta(days=1)
            return {"window": (amt, start, end)}
        return {"amount": amt}
    if re.search(r"\bonly\b", kv) and not re.search(r"fee|application", kv, re.I):
        return {"amount": 0.0, "not_listed": True}
    return None


def fee_cap_on(parsed: dict, day: dt.date) -> dict:
    if "amount" in parsed:
        return {"amount": parsed["amount"], "not_listed": parsed.get("not_listed", False)}
    if "window" in parsed:
        amt, start, end = parsed["window"]
        if start <= day <= end:
            return {"amount": amt, "until": end.isoformat()}
        return {"amount": None, "year": day.year}
    if day.year in parsed["figures"]:
        return {"amount": parsed["figures"][day.year], "year": day.year}
    return {"amount": None, "year": day.year}


JUST_CAUSE = re.compile(
    r"just cause|good cause|listed causes|listed (?:at-fault|no-fault)|only for (?:one of )?\d+ listed",
    re.I,
)


def tenancy_minimum(rule: dict) -> tuple[int, str] | None:
    """'Just cause after 12 months' -> (12, 'month'); 'After 30 days of tenancy' -> (30, 'day')."""
    for text in (rule.get("key_value"), rule.get("requirement")):
        if text and (m := re.search(r"\bafter (\d+) (month|day)s?\b", text, re.I)):
            return int(m.group(1)), m.group(2).lower()
    return None


def _add_months(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    for day in (d.day, 30, 29, 28):
        try:
            return dt.date(y, m, day)
        except ValueError:
            continue
    raise ValueError(d)


# ------------------------------------------------------------------ notice of a rent increase
# The extracted rules carry no notice period for rent increases. This one sentence from a corpus document states it
# for California; it is used only while its quote is found verbatim in that document (checked by STORE.verify).
NOTICE_RULES = [
    {
        "team_rule_id": "CA-NOTICE-INC",
        "jurisdiction": "CA",
        "level": "state",
        "category": "rent_increase_limits",
        "status": "in_force",
        "states": ["CA"],
        "days": 30,
        "below_pct": 10.0,
        "title": "Advance notice of a rent increase",
        "title_es": "Aviso previo de un aumento de renta",
        "requirement": "State law requires 30 days' written notice before a rent increase of less than 10%.",
        "requirement_es": "La ley estatal exige 30 días de aviso por escrito antes de un aumento de renta de menos del 10%.",
        "key_value": "30 days' written notice for increases under 10%",
        "citation": "California state law, as stated by the Los Angeles Housing Department",
        "citation_es": "Ley estatal de California, según el Departamento de Vivienda de Los Ángeles",
        "source_url": "https://housing.lacity.gov/rso-rent-increase-calculator",
        "source_doc_id": "D042",
        "quoted_span": "State law requires landlords to provide 30 days' written advance notice of rent increases of less than 10%.",
        "retrieved_at": "2026-10-01T22:36Z",
    }
]


# ------------------------------------------------------------------ request
class CheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address_id: str | None = Field(None, pattern=r"^[A-Za-z0-9-]{1,20}$")
    place: PlaceIn | None = None
    facts: FactsIn = FactsIn()
    as_of: dt.date | None = None
    current_rent: float | None = Field(None, gt=0, le=1_000_000)
    new_rent: float | None = Field(None, gt=0, le=1_000_000)
    increase_pct: float | None = Field(None, ge=-100, le=1000)
    notice_date: dt.date | None = None
    effective_date: dt.date | None = None
    deposit: float | None = Field(None, ge=0, le=1_000_000)
    application_fee: float | None = Field(None, ge=0, le=100_000)
    termination: Literal["none", "reason", "no_reason"] = "none"
    moved_in: dt.date | None = None
    cpi: float | None = Field(None, ge=-20, le=30)
    lang: Literal["en", "es"] = "en"

    @model_validator(mode="after")
    def _check(self):
        if not self.address_id and not self.place:
            raise ValueError("address_id or place is required")
        for d in (self.notice_date, self.effective_date, self.as_of, self.moved_in):
            if d and not (dt.date(1950, 1, 1) <= d <= dt.date(2035, 12, 31)):
                raise ValueError("dates must lie between 1950 and 2035")
        if self.notice_date and self.effective_date and self.effective_date < self.notice_date:
            raise ValueError("the increase cannot take effect before the notice was given")
        return self


# ------------------------------------------------------------------ evaluation context
def _web():
    from web import app as W  # late import: web.app includes this router

    return W


def _context(body: CheckIn, day: dt.date) -> dict:
    from navigator import api as NA
    from navigator import evaluate as E
    from navigator import user_facts as U

    user = {k: v for k, v in body.facts.model_dump(mode="json").items() if v is not None}
    if body.address_id:
        f = NA._addresses().get(body.address_id.upper())
        if not f:
            raise HTTPException(404, f"Unknown address {body.address_id}")
        if user.get("year_built") and f.year_built is None:
            f = dataclasses.replace(f, year_built=user["year_built"])
        if user.get("units") and f.units_lo is None:
            u = user["units"]
            f = dataclasses.replace(
                f, units_lo=u, units_hi=u, units_note=f"{u} units (you entered)"
            )
        if user.get("owner_occupied") is not None:
            f = dataclasses.replace(f, owner_occupied=user["owner_occupied"])
        rules, findings = NA.load_rules(), NA.no_rule_findings()
        a = f.raw
        label = f"{a.get('street_address', '')}, {a.get('postal_city', '')}, {f.state}"
    else:
        p = body.place
        if p.state not in U.covered_cities():
            raise HTTPException(422, f"state {p.state!r} is not covered")
        if p.jurisdiction and p.jurisdiction not in U.covered_cities()[p.state]:
            raise HTTPException(422, f"jurisdiction {p.jurisdiction!r} is not covered")
        rules, findings, _ = U.rules_for(p.jurisdiction)
        f = U.make_facts(p.state, p.jurisdiction, user)
        label = p.jurisdiction or p.state
    entries = E.evaluate_address(f, rules, day)
    needs = (
        U.needs_facts(f, rules, day, entries)["needs"]
        if any(e["result"] == "unknown" for e in entries)
        else {}
    )
    juris = {f.state, f.city} - {None}
    return {
        "f": f,
        "day": day,
        "rules": {r["team_rule_id"]: r for r in rules},
        "entries": entries,
        "needs": needs,
        "findings": [n for n in findings if n.get("jurisdiction") in juris],
        "juris": juris,
        "label": label,
    }


def _src(r: dict, lang: str) -> dict:
    W = _web()
    v = W.rule_view(r, lang)
    s = v.get("source") or {}
    es = lang == "es"
    return {
        "id": r["team_rule_id"],
        "title": (r.get("title_es") if es else None) or v.get("title_display") or r.get("title"),
        "requirement": (r.get("requirement_es") if es else None)
        or v.get("requirement_display")
        or r.get("requirement"),
        "citation": (r.get("citation_es") if es else None) or r.get("citation"),
        "jurisdiction": r.get("jurisdiction"),
        "level": r.get("level"),
        "url": r.get("source_url"),
        "quote": r.get("quoted_span"),
        "retrieved": s.get("retrieved_at") or r.get("retrieved_at"),
        "doc": v.get("span_doc_id") if s.get("has_text") else None,
        "check": (v.get("quote_check") or {}).get("status"),
    }


def _finding_src(n: dict, lang: str) -> dict:
    W = _web()
    meta = W.STORE.doc_meta(n.get("quoted_span_doc_id") or n.get("source_doc_id"))
    return {
        "id": n.get("finding_id"),
        "title": None,
        "requirement": W.STORE.t(n.get("finding"), lang),
        "citation": n.get("citation"),
        "jurisdiction": n.get("jurisdiction"),
        "url": n.get("source_url") or meta.get("url"),
        "quote": n.get("quoted_span"),
        "retrieved": meta.get("retrieved_at"),
        "doc": (n.get("quoted_span_doc_id") or n.get("source_doc_id"))
        if meta.get("has_text")
        else None,
        "check": W.STORE.verify(n).get("status"),
    }


def _need_for(ctx: dict, e: dict) -> dict:
    """The fact that would settle an 'unknown' evaluator result."""
    keys = ctx["needs"].get(e["team_rule_id"]) or []
    if keys:
        return {"key": keys[0], "keys": keys}
    from navigator import user_facts as U

    other = U._other_reason(ctx["rules"][e["team_rule_id"]])
    return {"key": "other", "label": other or _web().missing_fact(e.get("explanation", ""))}


def _in_cat(ctx: dict, cat: str, results=("applies", "unknown")) -> list[dict]:
    out = [
        e
        for e in ctx["entries"]
        if e["result"] in results and ctx["rules"][e["team_rule_id"]].get("category") == cat
    ]
    return sorted(out, key=lambda e: ctx["rules"][e["team_rule_id"]].get("level") != "city")


def _excluded(ctx: dict, cat: str, lang: str) -> list[dict]:
    """In-force rules of this place that the evaluator rules out for this building, with its reasons."""
    from navigator import evaluate as E

    present = {e["team_rule_id"] for e in ctx["entries"]}
    out = []
    for r in ctx["rules"].values():
        if (
            r.get("category") != cat
            or r["team_rule_id"] in present
            or r.get("jurisdiction") not in ctx["juris"]
        ):
            continue
        if E.time_status(r, ctx["day"]) != "in_force":
            continue
        verdict, why = E.coverage(r, ctx["f"], ctx["day"])
        if verdict == E.NO:
            out.append(
                {
                    **_src(r, lang),
                    "reasons": [
                        w for w in why if re.search(r"exempt|outside|below|above|cannot", w)
                    ]
                    or why,
                }
            )
    return out


# ------------------------------------------------------------------ the five checks
def check_rent(ctx: dict, cur: float, new: float, cpi: float | None, lang: str) -> dict:
    items = _in_cat(ctx, "rent_increase_limits")
    unknown = [e for e in items if e["result"] == "unknown"]
    if unknown:
        e = unknown[0]
        base = rent_verdict(cur, new, {"pct": None})
        return {
            "id": "rent",
            "kind": "unknown" if base["code"] != "no_increase" else "ok",
            "code": "need_fact" if base["code"] != "no_increase" else "no_increase",
            "values": base["values"],
            "need": _need_for(ctx, e) if base["code"] != "no_increase" else None,
            "rules": [_src(ctx["rules"][x["team_rule_id"]], lang) for x in unknown],
        }
    if not items:
        v = rent_verdict(cur, new, {"pct": None})["values"]
        return {
            "id": "rent",
            "kind": "none",
            "code": "no_cap",
            "values": v,
            "rules": [],
            "excluded": _excluded(ctx, "rent_increase_limits", lang),
            "findings": [
                _finding_src(n, lang)
                for n in ctx["findings"]
                if n.get("category") == "rent_increase_limits"
            ],
        }
    e = items[0]
    r = ctx["rules"][e["team_rule_id"]]
    parsed = parse_rent_cap(r.get("key_value"), r.get("requirement"))
    cap = cap_on(parsed, ctx["day"], cpi)
    if cap.get("basis") == "no_cap":
        v = rent_verdict(cur, new, {"pct": None})["values"]
        return {
            "id": "rent",
            "kind": "none",
            "code": "state_bar",
            "values": v,
            "rules": [_src(r, lang)],
        }
    out = {"id": "rent", **rent_verdict(cur, new, cap), "rules": [_src(r, lang)], "cap": cap}
    if out["code"] == "need_figure":
        out["need"] = {
            "key": "rate_figure",
            "jurisdiction": r.get("jurisdiction"),
            "date": ctx["day"].isoformat(),
        }
    out["cap"] = {k: v for k, v in cap.items() if k not in ("need",)}
    return out


def check_notice(
    ctx: dict, increase_pct: float, notice: dt.date | None, effective: dt.date
) -> dict:
    W = _web()
    state = ctx["f"].state
    rules = [
        r
        for r in NOTICE_RULES
        if state in r["states"] and W.STORE.verify(r).get("status") in ("exact", "normalized")
    ]
    if increase_pct <= 0:
        return None
    if not notice:
        return {
            "id": "notice",
            "kind": "unknown",
            "code": "need_fact",
            "need": {"key": "notice_date"},
            "rules": [],
        }
    days = (effective - notice).days
    v = {"days_given": days, "increase_pct": round(increase_pct, 2)}
    rule = next((r for r in rules if increase_pct < r["below_pct"]), None)
    if not rule:
        need = {"key": "notice_rule_10"} if rules else {"key": "notice_rule", "state": state}
        return {
            "id": "notice",
            "kind": "unknown",
            "code": "need_rule",
            "values": v,
            "need": need,
            "rules": [],
        }
    v["days_needed"] = rule["days"]
    v["earliest"] = (notice + dt.timedelta(days=rule["days"])).isoformat()
    kind = "ok" if days >= rule["days"] else "short"
    return {"id": "notice", "kind": kind, "code": kind, "values": v, "rule_ref": rule}


def check_deposit(ctx: dict, deposit: float, rent: float | None, lang: str) -> dict:
    items = [
        e
        for e in _in_cat(ctx, "security_deposits")
        if parse_deposit_cap(ctx["rules"][e["team_rule_id"]].get("key_value"))
    ]
    v = {"deposit": round(deposit, 2)}
    if not items:
        return {
            "id": "deposit",
            "kind": "none",
            "code": "no_cap",
            "values": v,
            "rules": [],
            "findings": [
                _finding_src(n, lang)
                for n in ctx["findings"]
                if n.get("category") == "security_deposits"
            ],
        }
    e = items[0]
    r = ctx["rules"][e["team_rule_id"]]
    src = [_src(r, lang)]
    if e["result"] == "unknown":
        return {
            "id": "deposit",
            "kind": "unknown",
            "code": "need_fact",
            "values": v,
            "need": _need_for(ctx, e),
            "rules": src,
        }
    if not rent:
        return {
            "id": "deposit",
            "kind": "unknown",
            "code": "need_fact",
            "values": v,
            "need": {"key": "rent"},
            "rules": src,
        }
    cap = parse_deposit_cap(r.get("key_value"))
    top = round(rent * cap["months"], 2)
    v |= {"rent": round(rent, 2), "months": cap["months"], "max": top}
    if deposit <= top + 0.005:
        return {"id": "deposit", "kind": "ok", "code": "within", "values": v, "rules": src}
    if cap.get("alt_months"):
        alt = round(rent * cap["alt_months"], 2)
        v |= {"alt_months": cap["alt_months"], "alt_max": alt}
        if deposit <= alt + 0.005:
            cond = (r.get("coverage") or {}).get("landlord_size_condition")
            return {
                "id": "deposit",
                "kind": "unknown",
                "code": "need_landlord",
                "values": v,
                "need": {"key": "landlord_small", "label": cond},
                "rules": src,
            }
        top = alt
    v |= {"over_amount": round(deposit - top, 2), "limit": top}
    return {"id": "deposit", "kind": "over", "code": "over", "values": v, "rules": src}


def check_fee(ctx: dict, fee: float, lang: str) -> dict:
    v = {"fee": round(fee, 2)}
    items = []
    for e in _in_cat(ctx, "application_screening_fees"):
        r = ctx["rules"][e["team_rule_id"]]
        p = parse_fee_cap(
            r.get("key_value"), r.get("current_version_effective") or r.get("effective_date")
        )
        if p:
            items.append((e, r, p))
    if not items:
        return {
            "id": "fee",
            "kind": "none",
            "code": "no_cap",
            "values": v,
            "rules": [],
            "findings": [
                _finding_src(n, lang)
                for n in ctx["findings"]
                if n.get("category") == "application_screening_fees"
            ],
        }
    e, r, p = items[0]
    src = [_src(r, lang)]
    if e["result"] == "unknown":
        return {
            "id": "fee",
            "kind": "unknown",
            "code": "need_fact",
            "values": v,
            "need": _need_for(ctx, e),
            "rules": src,
        }
    cap = fee_cap_on(p, ctx["day"])
    if fee == 0:
        return {
            "id": "fee",
            "kind": "ok",
            "code": "within",
            "values": v | {"max": cap.get("amount")},
            "rules": src,
        }
    if cap["amount"] is None:
        return {
            "id": "fee",
            "kind": "unknown",
            "code": "need_figure",
            "values": v,
            "need": {"key": "fee_figure", "year": cap["year"]},
            "rules": src,
        }
    v["max"] = cap["amount"]
    if cap.get("not_listed"):
        return {
            "id": "fee",
            "kind": "over",
            "code": "not_listed",
            "values": v | {"over_amount": round(fee, 2)},
            "rules": src,
        }
    if fee <= cap["amount"] + 0.005:
        return {"id": "fee", "kind": "ok", "code": "within", "values": v, "rules": src}
    return {
        "id": "fee",
        "kind": "over",
        "code": "over",
        "values": v | {"over_amount": round(fee - cap["amount"], 2)},
        "rules": src,
    }


def check_termination(ctx: dict, mode: str, moved_in: dt.date | None, lang: str) -> dict:
    def jc(e):
        r = ctx["rules"][e["team_rule_id"]]
        return JUST_CAUSE.search(f"{r.get('key_value') or ''} {r.get('requirement') or ''}")

    items = [e for e in _in_cat(ctx, "just_cause_eviction") if jc(e)]
    applies = [e for e in items if e["result"] == "applies"]
    if not applies:
        unknown = [e for e in items if e["result"] == "unknown"]
        if unknown:
            e = unknown[0]
            return {
                "id": "termination",
                "kind": "unknown",
                "code": "need_fact",
                "need": _need_for(ctx, e),
                "rules": [_src(ctx["rules"][e["team_rule_id"]], lang)],
            }
        return {"id": "termination", "kind": "none", "code": "no_reason_rule", "rules": []}
    r = ctx["rules"][applies[0]["team_rule_id"]]
    src = [_src(r, lang)]
    if mode == "reason":
        return {
            "id": "termination",
            "kind": "unknown",
            "code": "reason_check",
            "need": {"key": "reason_on_list"},
            "rules": src,
        }
    minimum = tenancy_minimum(r)
    v = {}
    if minimum:
        n, unit = minimum
        v = {"min": n, "unit": unit}
        if not moved_in:
            return {
                "id": "termination",
                "kind": "unknown",
                "code": "need_fact",
                "values": v,
                "need": {"key": "moved_in"},
                "rules": src,
            }
        start = _add_months(moved_in, n) if unit == "month" else moved_in + dt.timedelta(days=n)
        v["protected_from"] = start.isoformat()
        if ctx["day"] < start:
            return {
                "id": "termination",
                "kind": "none",
                "code": "not_yet_protected",
                "values": v,
                "rules": src,
            }
    return {
        "id": "termination",
        "kind": "over",
        "code": "reason_required",
        "values": v,
        "rules": src,
    }


# ------------------------------------------------------------------ endpoint
def run_check(body: CheckIn) -> dict:
    W = _web()
    day = (
        body.effective_date
        or body.as_of
        or body.notice_date
        or dt.date.fromisoformat(W.DEFAULT_AS_OF)
    )
    ctx = _context(body, day)
    lang = body.lang
    cur = body.current_rent
    new = body.new_rent
    if new is None and body.increase_pct is not None and cur:
        new = round(cur * (1 + body.increase_pct / 100), 2)
    out = []
    if cur and new:
        rv = check_rent(ctx, cur, new, body.cpi, lang)
        out.append(rv)
        inc = (new - cur) / cur * 100
        if body.effective_date:
            nv = check_notice(ctx, inc, body.notice_date, body.effective_date)
            if nv:
                if nv.get("rule_ref"):
                    nv["rules"] = [_src(nv.pop("rule_ref"), lang)]
                out.append(nv)
        else:
            out.append(
                {
                    "id": "notice",
                    "kind": "unknown",
                    "code": "need_fact",
                    "need": {"key": "effective_date"},
                    "rules": [],
                }
            )
    elif cur or new or body.increase_pct is not None:
        out.append(
            {
                "id": "rent",
                "kind": "unknown",
                "code": "need_input",
                "need": {"key": "current_rent" if not cur else "new_rent"},
                "rules": [],
            }
        )
    if body.deposit is not None:
        out.append(check_deposit(ctx, body.deposit, new or cur, lang))
    if body.application_fee is not None:
        out.append(check_fee(ctx, body.application_fee, lang))
    if body.termination != "none":
        out.append(check_termination(ctx, body.termination, body.moved_in, lang))
    f = ctx["f"]
    return {
        "as_of": day.isoformat(),
        "lang": lang,
        "place": {"label": ctx["label"], "state": f.state, "jurisdiction": f.city},
        "facts": {
            "year_built": f.year_built,
            "units": f.units_lo,
            "owner_occupied": f.owner_occupied,
        },
        "verdicts": out,
        "disclaimer": "Not legal advice. Public law with citations, for information only.",
    }


@router.post("/api/check")
def check(body: CheckIn, request: Request):
    _limit(CHECK_LIMIT, request)
    return run_check(body)
