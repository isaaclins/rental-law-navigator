"""Any address (#39): evaluate a geocoded jurisdiction + building facts the user supplies. Not legal advice.

evaluate_user("CA", "Los Angeles, CA", {"year_built": 1962, "units": 8}, "2026-10-01")
  -> results (same entries as evaluate_address) where every `unknown` carries `needs_fact`: the user facts that
     would turn it into a definite answer, found by re-running the evaluator with probe values for each missing fact
     (so indirect dependencies, e.g. a state rule that yields to a local rule whose coverage depends on the year,
     are found too). `fact_counts` = how many unknowns each missing fact resolves; `fact_depends` = how many answers
     change with a fact the user already gave.
Nothing here stores or logs addresses: the evaluator only sees state, city and the facts.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import itertools
import json

from . import evaluate as E
from . import normalize as N
from .config import BASE_OUTPUT_DIR, CITIES, STATES

FACT_KEYS = ("year_built", "units", "owner_occupied", "certificate_of_occupancy_date")
EXTENSION_ROOT = BASE_OUTPUT_DIR / "extension"


def extension_cities() -> dict[str, str]:
    """'Santa Monica, CA' -> 'santa-monica' for jurisdictions added with `navigator extend`."""
    out = {}
    for p in sorted(EXTENSION_ROOT.glob("*/summary.json")):
        for j in json.loads(p.read_text(encoding="utf-8")).get("jurisdictions", []):
            out[j] = p.parent.name
    return out


def covered_cities() -> dict[str, list[str]]:
    """State -> city jurisdictions with local rules in the corpus (main + extensions)."""
    out: dict[str, list[str]] = {s: [] for s in STATES}
    for j in list(CITIES) + list(extension_cities()):
        st = j.rsplit(", ", 1)[-1]
        if st in out and j not in out[st]:
            out[st].append(j)
    return out


def rules_for(jurisdiction: str | None) -> tuple[list[dict], list[dict], str | None]:
    """Rule set that covers the jurisdiction: the main corpus, or an extension's (a superset of the main one)."""
    from . import api

    slug = extension_cities().get(jurisdiction or "")
    if slug:
        rules, findings, _ = api._extension(slug)
        return rules, findings, slug
    return api.load_rules(), api.no_rule_findings(), None


def make_facts(state: str, jurisdiction: str | None, user: dict) -> E.Facts:
    co = user.get("certificate_of_occupancy_date")
    co = dt.date.fromisoformat(co) if isinstance(co, str) else co
    year = user.get("year_built") or (co.year if co else None)
    units = user.get("units")
    note = f"{units} units (you entered)" if units else "unit count not given"
    return E.Facts(
        "custom",
        state,
        jurisdiction,
        year,
        units,
        units,
        note,
        "",
        {"resolution_method": "census_oneline_live", "source": "user"},
        owner_occupied=user.get("owner_occupied"),
        co_date=co,
        multifamily_assumed=False,
    )


# ------------------------------------------------------------------ which fact resolves an unknown
def _probes(rules: list[dict], f: E.Facts, as_of: dt.date) -> dict[str, list]:
    """Probe values per missing fact: the boundaries the rules actually test, plus extremes."""
    years, units, dates = {1900, as_of.year}, {1, 100}, set()
    for r in rules:
        cov = r.get("coverage") or {}
        cut = cov.get("construction_cutoff") or {}
        d = N.date_floor(N.date(cut["date"])) if cut.get("date") else None
        if d:
            years |= {d.year - 1, d.year, d.year + 1}
            dates |= {d - dt.timedelta(days=1), d, d + dt.timedelta(days=1)}
        nce = cov.get("new_construction_exemption") or {}
        if nce.get("years"):
            thr = as_of.replace(year=as_of.year - int(nce["years"]), day=min(as_of.day, 28))
            years |= {thr.year - 1, thr.year, thr.year + 1}
            dates |= {thr - dt.timedelta(days=1), thr, thr + dt.timedelta(days=1)}
        for k in ("min_units", "max_units", "owner_occupied_exemption_max_units"):
            if cov.get(k):
                units |= {int(cov[k]) - 1, int(cov[k]), int(cov[k]) + 1}
    out: dict[str, list] = {}
    if f.year_built is None:
        out["year_built"] = sorted(years)
    if f.units_lo is None:
        out["units"] = sorted(u for u in units if u > 0)
    if f.owner_occupied is None:
        out["owner_occupied"] = [True, False]
    if f.co_date is None and f.year_built is not None:
        out["certificate_of_occupancy_date"] = sorted(
            {d for d in dates if d.year == f.year_built}
            | {dt.date(f.year_built, 1, 1), dt.date(f.year_built, 12, 31)}
        )
    return out


def _with(f: E.Facts, key: str, v) -> E.Facts:
    if key == "year_built":
        return dataclasses.replace(f, year_built=v)
    if key == "units":
        return dataclasses.replace(f, units_lo=v, units_hi=v, units_note=f"{v} units")
    if key == "owner_occupied":
        return dataclasses.replace(f, owner_occupied=v)
    return dataclasses.replace(f, co_date=v)


def _results(f: E.Facts, rules: list[dict], as_of: dt.date) -> dict[str, str]:
    return {e["team_rule_id"]: e["result"] for e in E.evaluate_address(f, rules, as_of)}


def needs_facts(f: E.Facts, rules: list[dict], as_of: dt.date, base: list[dict]) -> dict:
    """needs_fact per unknown rule id, plus counts per fact."""
    here = [r for r in rules if E._applies_here(r, f)]
    probes = _probes(here, f, as_of)
    unknown = [e["team_rule_id"] for e in base if e["result"] == "unknown"]
    needs: dict[str, list[str]] = {rid: [] for rid in unknown}

    def resolved(res: dict[str, str], rid: str) -> bool:
        return res.get(rid) != "unknown"  # omitted (does not apply) is a definite answer too

    for key, vals in probes.items():
        runs = [_results(_with(f, key, v), rules, as_of) for v in vals]
        for rid in unknown:
            if any(resolved(res, rid) for res in runs):
                needs[rid].append(key)
    # unknowns that need two facts together (e.g. units and owner occupancy for an exemption)
    open_ids = [rid for rid in unknown if not needs[rid]]
    if open_ids:
        for (k1, v1s), (k2, v2s) in itertools.combinations(probes.items(), 2):
            runs = [
                _results(_with(_with(f, k1, a), k2, b), rules, as_of)
                for a, b in itertools.product(v1s, v2s)
            ]
            for rid in open_ids:
                if not needs[rid] and any(resolved(res, rid) for res in runs):
                    needs[rid] = [k1, k2]
    # facts the user gave: how many answers would change with another value
    given = {
        "year_built": f.year_built is not None,
        "units": f.units_lo is not None,
        "owner_occupied": f.owner_occupied is not None,
        "certificate_of_occupancy_date": f.co_date is not None,
    }
    base_map = {e["team_rule_id"]: e["result"] for e in base}
    depends = {}
    full = _probes(
        here,
        dataclasses.replace(f, year_built=None, units_lo=None, owner_occupied=None, co_date=None),
        as_of,
    )
    if f.year_built is not None:
        full["certificate_of_occupancy_date"] = _probes(
            here, dataclasses.replace(f, co_date=None), as_of
        ).get("certificate_of_occupancy_date", [])
    for key, ok in given.items():
        if not ok:
            continue
        changed = set()
        for v in full.get(key, []):
            res = _results(_with(f, key, v), rules, as_of)
            changed |= {
                rid for rid in set(res) | set(base_map) if res.get(rid) != base_map.get(rid)
            }
        depends[key] = len(changed)
    counts = {k: sum(1 for v in needs.values() if k in v) for k in FACT_KEYS if k in probes}
    return {"needs": needs, "fact_counts": counts, "fact_depends": depends}


def _other_reason(rule: dict) -> str | None:
    cov = rule.get("coverage") or {}
    if rule.get("verification") == "unverified_link_only":
        return "The source is only linked, not captured; check the official text."
    req = [x for x in (cov.get("requires_unknown_facts") or []) if x]
    if req:
        return "Depends on: " + "; ".join(req) + "."
    if (cov.get("new_construction_exemption") or {}).get("requires_owner_filing"):
        return "Depends on whether the owner filed for the new-construction exemption."
    return None


def evaluate_user(state: str, jurisdiction: str | None, user: dict, as_of: str) -> dict:
    """Evaluate a live-geocoded address with user-supplied facts. `jurisdiction` is 'City, ST' or None."""
    if state not in STATES:
        raise ValueError(f"state {state!r} is not covered")
    if jurisdiction is not None and jurisdiction not in covered_cities()[state]:
        raise ValueError(f"jurisdiction {jurisdiction!r} is not covered in {state}")
    rules, findings, ext = rules_for(jurisdiction)
    as_of_d = dt.date.fromisoformat(as_of)
    f = make_facts(state, jurisdiction, user)
    base = E.evaluate_address(f, rules, as_of_d)
    nf = needs_facts(f, rules, as_of_d, base)
    by_id = {r["team_rule_id"]: r for r in rules}
    for e in base:
        if e["result"] == "unknown":
            e["needs_fact"] = nf["needs"].get(e["team_rule_id"], [])
            if not e["needs_fact"]:
                e["needs_other"] = _other_reason(by_id[e["team_rule_id"]])
    return {
        "as_of": as_of,
        "disclaimer": E.DISCLAIMER,
        "state": state,
        "jurisdiction": jurisdiction,
        "extension": ext,
        "facts": {
            "year_built": f.year_built,
            "units": f.units_lo,
            "owner_occupied": f.owner_occupied,
            "certificate_of_occupancy_date": f.co_date.isoformat() if f.co_date else None,
        },
        "results": base,
        "fact_counts": nf["fact_counts"],
        "fact_depends": nf["fact_depends"],
        "rules": by_id,
        "no_rule_findings": [n for n in findings if n["jurisdiction"] in (state, jurisdiction)],
    }
