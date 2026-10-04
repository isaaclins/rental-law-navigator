"""Protections over time (#stats): how many of the 10 covered cities have each renter protection in force, 2019-2027.

GET /api/stats/protections?lang=en
    -> per protection: the cities covered on the start date (with the laws behind them), every dated step where the
       count changes (the laws that took effect or ended that day, their source links), pending bills and failed
       measures with the count they would reach, and a headline computed from the steps.

Deterministic and computed from output/rules.json only: a rule counts as a protection type by its category plus a
fixed text test on its title / key figure (below), and its status on a date comes from the evaluator
(navigator.evaluate.time_status, the same logic as the address answers). A state law covers every city in that state.
"In force in a city" does not mean every building there is covered: exemptions still apply per address.
Not legal advice.
"""

from __future__ import annotations

import datetime as dt
import re

from fastapi import APIRouter

router = APIRouter()

START = dt.date(2019, 1, 1)
END = dt.date(2027, 12, 31)


def _text(r: dict) -> str:
    return f"{r.get('title') or ''} {r.get('key_value') or ''}"


# (id, category, test on title + key figure). Order = display order.
PROTECTIONS: list[tuple[str, str, object]] = [
    (
        "rent_cap",
        "rent_increase_limits",
        # every rent rule is a cap except a state bar on local rent control (the opposite of a protection)
        lambda r: not re.search(r"\b(bar|ban) on local rent control|preempt", _text(r), re.I),
    ),
    (
        "just_cause",
        "just_cause_eviction",
        # notice, reprisal and relocation rules are not just-cause eviction
        lambda r: bool(re.search(r"\b(just|good)[- ]cause", _text(r), re.I)),
    ),
    (
        "deposit_cap",
        "security_deposits",
        # interest-only rules are not caps
        lambda r: bool(re.search(r"\bcap\b|\bmax|\bmonths?'?s?'? rent", _text(r), re.I)),
    ),
    (
        "fee_cap",
        "application_screening_fees",
        # broker-fee rules are not application-fee caps
        lambda r: bool(
            re.search(r"application (screening )?fee|screening fee|per applica", _text(r), re.I)
        ),
    ),
    (
        "source_of_income",
        "screening_restrictions",
        # criminal-history and credit rules are not source-of-income protection
        lambda r: bool(
            re.search(
                r"source[- ]of[- ](lawful )?income|voucher|public assistance|housing subsid|rental assistance",
                _text(r),
                re.I,
            )
        ),
    ),
    ("algorithmic_ban", "algorithmic_rent_setting", lambda r: True),
]


def _W():
    from web import app as W  # late import: web.app includes this router

    return W


def cities() -> list[dict]:
    W = _W()
    return [
        {"name": c, "state": W.CITY_STATE[c], "jurisdiction": f"{c}, {W.CITY_STATE[c]}"}
        for c in W.CITY_ORDER
    ]


def _unverified(r: dict) -> bool:
    """A rule found only in a source we could not read: every address answer for it is "unknown" (the evaluator)."""
    return r.get("verification") == "unverified_link_only"


def rules_for(pid: str, unverified: bool = False) -> list[dict]:
    """The rules that count for a protection; unverified=True: the ones the address answers call unknown."""
    W = _W()
    _, cat, test = next(p for p in PROTECTIONS if p[0] == pid)
    return [
        r
        for r in W.STORE.rules.values()
        if r.get("category") == cat and test(r) and _unverified(r) == unverified
    ]


def covers(r: dict) -> list[str]:
    """City names a rule covers: a state law covers every city in that state."""
    j = r.get("jurisdiction") or ""
    return [c["name"] for c in cities() if j in (c["state"], c["jurisdiction"])]


def status_on(r: dict, d: dt.date) -> str | None:
    """in_force / not_yet_effective / pending / None (failed or not law yet), from the evaluator."""
    from navigator.evaluate import time_status

    if r.get("status") == "failed":
        return None
    return time_status(r, d)


def start_date(r: dict) -> str | None:
    """The date the evaluator uses as the rule's start (in_force_since for amended long-standing laws)."""
    W = _W()
    key = "in_force_since" if r.get("amends_existing_law") else "effective_date"
    return W._norm_date(r.get(key))


def covered_on(rules: list[dict], d: dt.date) -> dict[str, list[str]]:
    """City -> ids of the rules in force there on d."""
    out: dict[str, list[str]] = {}
    for r in rules:
        if status_on(r, d) == "in_force":
            for c in covers(r):
                out.setdefault(c, []).append(r["team_rule_id"])
    return out


def _candidate_dates(rules: list[dict]) -> list[dt.date]:
    from navigator import normalize as N

    ds = set()
    for r in rules:
        for k in ("enacted_date", "effective_date", "in_force_since", "sunset_date"):
            d = N.date_floor(r.get(k))
            if d and START < d <= END:
                ds.add(d)
    return sorted(ds)


def _law(r: dict, lang: str, cities_added: list[str] | None = None) -> dict:
    W = _W()
    return {
        "id": r["team_rule_id"],
        "title": W.STORE.t(r.get("title"), lang) or r.get("title"),
        "jurisdiction": r.get("jurisdiction"),
        "level": r.get("level"),
        "date": start_date(r),
        "source_url": r.get("source_url"),
        "citation": r.get("citation"),
        **({"cities": cities_added} if cities_added is not None else {}),
    }


def protection(pid: str, lang: str = "en") -> dict:
    rules = rules_for(pid)
    by_id = {r["team_rule_id"]: r for r in rules}
    order = [c["name"] for c in cities()]
    cur = covered_on(rules, START)
    initial = {
        "date": START.isoformat(),
        "count": len(cur),
        "cities": [c for c in order if c in cur],
        "laws": [
            _law(by_id[rid], lang, [c for c in order if rid in cur.get(c, [])])
            for rid in dict.fromkeys(x for c in order for x in cur.get(c, []))
        ],
    }
    steps = []
    for d in _candidate_dates(rules):
        nxt = covered_on(rules, d)
        if set(nxt) != set(cur):
            added = [c for c in order if c in nxt and c not in cur]
            removed = [c for c in order if c in cur and c not in nxt]
            prev_day = d - dt.timedelta(days=1)
            laws = []
            for r in rules:
                rid = r["team_rule_id"]
                now_in = status_on(r, d) == "in_force"
                was_in = status_on(r, prev_day) == "in_force"
                if now_in and not was_in:
                    hit = [c for c in added if rid in nxt.get(c, [])]
                    if hit:
                        laws.append({**_law(r, lang, hit), "change": "starts"})
                elif was_in and not now_in:
                    hit = [c for c in removed if rid in cur.get(c, [])]
                    if hit:
                        laws.append({**_law(r, lang, hit), "change": "ends"})
            steps.append(
                {
                    "date": d.isoformat(),
                    "count": len(nxt),
                    "delta": len(nxt) - len(cur),
                    "added": added,
                    "removed": removed,
                    "laws": laws,
                }
            )
        cur = nxt
    final = set(cur)
    # cities where the only rule of this kind is unverified: every answer there is "unknown", so the chart counts
    # them apart ("we can't tell yet"), never as in force
    unk = covered_on(rules_for(pid, unverified=True), END)
    unknown = [c for c in order if c in unk and c not in final]

    def proposals(kind: str) -> list[dict]:
        out = []
        for r in rules:
            if r.get("status") != kind:
                continue
            gain = [c for c in order if c in covers(r) and c not in final]
            out.append({**_law(r, lang, gain), "count_if_passed": len(final) + len(gain)})
        return out

    return {
        "id": pid,
        "category": next(p[1] for p in PROTECTIONS if p[0] == pid),
        "initial": initial,
        "steps": steps,
        "final": {"count": len(final), "cities": [c for c in order if c in final]},
        "unknown": {
            "count": len(unknown),
            "cities": unknown,
            "laws": [
                _law(r, lang, [c for c in unknown if r["team_rule_id"] in unk.get(c, [])])
                for r in rules_for(pid, unverified=True)
                if any(r["team_rule_id"] in unk.get(c, []) for c in unknown)
            ],
        },
        "pending": proposals("pending"),
        "failed": proposals("failed"),
        "rule_ids": sorted(by_id),
    }


def count_on(pid: str, d: dt.date) -> int:
    return len(covered_on(rules_for(pid), d))


def headline(ps: list[dict]) -> dict | None:
    """The protection whose city count changed most over the chart window, with its first and last step."""
    best = None
    for p in ps:
        if not p["steps"]:
            continue
        a = p["steps"][0]["count"] - p["steps"][0]["delta"]
        b = p["steps"][-1]["count"]
        score = (abs(b - a), len(p["steps"]))
        if best is None or score > best[0]:
            best = (score, p, a, b)
    if not best:
        return None
    _, p, a, b = best
    pending_gain = sorted({c for x in p["pending"] for c in x["cities"]})
    return {
        "protection": p["id"],
        "from": a,
        "to": b,
        "from_year": int(p["steps"][0]["date"][:4]),
        "to_year": int(p["steps"][-1]["date"][:4]),
        "without": [
            c
            for c in (x["name"] for x in cities())
            if c not in p["final"]["cities"] and c not in p["unknown"]["cities"]
        ],
        "unknown": p["unknown"]["cities"],
        "pending_bills": len(p["pending"]),
        "pending_cities": pending_gain,
    }


@router.get("/api/stats/protections")
def protections(lang: str = "en"):
    W = _W()
    ps = [protection(pid, lang) for pid, _, _ in PROTECTIONS]
    return {
        "start": START.isoformat(),
        "end": END.isoformat(),
        "cities": cities(),
        "protections": ps,
        "headline": headline(ps),
        "source": {
            "rules_file": W.STORE.sources.get("rules.json", {}).get("path"),
            "rules_total": len(W.STORE.rules),
            "rules_used": sum(len(p["rule_ids"]) for p in ps),
            "retrieved": W.STORE.base_as_of,
        },
    }
