"""Importable functions for the web layer (FastAPI etc.). Not legal advice.

from navigator import api
api.load_rules()                          -> list of rule records (output/rules.json)
api.lookup("A0001", as_of="2026-10-01")   -> jurisdiction stack + rule results with citations
api.lookup({"state": "CA", "resolved_city": "San Francisco", "year_built": 1962, "units": 20, ...})
api.changes("T3")                         -> affected addresses / conflict flags for a change test
api.address_ids(), api.get_rule(id), api.no_rule_findings()
api.extensions()                          -> jurisdictions added with `navigator extend` (docs/NEW_JURISDICTION.md)
api.extension_lookup("santa-monica", "SM001", as_of="2026-10-01")   -> same shape as lookup(), extension data
api.lookup_user("CA", "Los Angeles, CA", {"year_built": 1962, "units": 8}, as_of="2026-10-01")
                                          -> any geocoded address + user facts; unknowns carry needs_fact (#39)
"""

from __future__ import annotations

import csv
import json
from functools import lru_cache

from . import changes as C
from . import evaluate as E
from .config import BASE_OUTPUT_DIR, CHANGES_JSON, CITIES, DEFAULT_AS_OF, RULES_JSON

DISCLAIMER = E.DISCLAIMER


@lru_cache(maxsize=1)
def _rules_doc(mtime: float = 0.0) -> dict:
    return json.loads(RULES_JSON.read_text(encoding="utf-8"))


def _doc() -> dict:
    return _rules_doc(RULES_JSON.stat().st_mtime)


def load_rules() -> list[dict]:
    return _doc()["rules"]


def no_rule_findings() -> list[dict]:
    return _doc().get("no_rule_findings", [])


def get_rule(rule_id: str) -> dict | None:
    return next((r for r in load_rules() if r["team_rule_id"] == rule_id), None)


@lru_cache(maxsize=1)
def _addresses() -> dict[str, E.Facts]:
    return {f.address_id: f for f in E.load_addresses()}


def address_ids() -> list[str]:
    return list(_addresses())


def _facts_from_dict(d: dict) -> E.Facts:
    st = (d.get("resolved_state") or d.get("state") or "").strip()
    city = (d.get("resolved_city") or d.get("city") or "").strip()
    jur = city if city in CITIES else (f"{city}, {st}" if f"{city}, {st}" in CITIES else None)
    lo, hi, note = E.unit_range({**d, "state": st})
    return E.Facts(
        d.get("address_id", "custom"),
        st,
        jur,
        E._int(d.get("year_built")),
        lo,
        hi,
        note,
        f"{d.get('use_code', '')} {d.get('use_description', '')}".strip(),
        d,
    )


def lookup(address: str | dict, as_of: str = DEFAULT_AS_OF) -> dict:
    f = _addresses()[address] if isinstance(address, str) else _facts_from_dict(address)
    return _lookup(f, load_rules(), no_rule_findings(), as_of)


def _lookup(f: E.Facts, rules: list[dict], all_findings: list[dict], as_of: str) -> dict:
    by_id = {r["team_rule_id"]: r for r in rules}
    results = E.evaluate_address(f, rules, as_of)
    for e in results:
        r = by_id[e["team_rule_id"]]
        e.update(
            {
                "title": r["title"],
                "requirement": r["requirement"],
                "key_value": r.get("key_value"),
                "level": r["level"],
                "jurisdiction": r["jurisdiction"],
                "effective_date": r.get("effective_date"),
                "status": r["status"],
                "source_url": r["source_url"],
                "source_doc_id": r["source_doc_id"],
                "retrieved_at": r.get("retrieved_at"),
                "quoted_span": r["quoted_span"],
                "confidence": r.get("confidence"),
                "conflict_note": r.get("conflict_note"),
                "verification": r.get("verification"),
            }
        )
    stack = [{"level": "state", "name": f.state}] + (
        [{"level": "city", "name": f.city}] if f.city else []
    )
    findings = [n for n in all_findings if n["jurisdiction"] in (f.state, f.city)]
    return {
        "address_id": f.address_id,
        "as_of": as_of,
        "disclaimer": DISCLAIMER,
        "jurisdiction_stack": stack,
        "facts": {
            "year_built": f.year_built,
            "units": f.units_note,
            "use": f.use,
            "street_address": f.raw.get("street_address"),
            "postal_city": f.raw.get("postal_city"),
            "resolution_method": f.raw.get("resolution_method"),
            "resolution_note": f.raw.get("resolution_note"),
        },
        "results": results,
        "no_rule_findings": findings,
    }


# ------------------------------------------------------------------ extension jurisdictions (navigator extend)
EXTENSION_ROOT = BASE_OUTPUT_DIR / "extension"


def extensions() -> list[dict]:
    """Jurisdictions added live with `navigator extend`, with their measured numbers (summary.json)."""
    out = []
    for p in sorted(EXTENSION_ROOT.glob("*/summary.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        out.append(
            {
                "slug": p.parent.name,
                "label": f"extension: {', '.join(s['jurisdictions'])}, added live",
                "address_ids": list(_extension(p.parent.name)[2]),
                **s,
            }
        )
    return out


@lru_cache(maxsize=8)
def _extension(slug: str) -> tuple[list[dict], list[dict], dict[str, E.Facts]]:
    d = EXTENSION_ROOT / slug
    doc = json.loads((d / "rules.json").read_text(encoding="utf-8"))
    cities = {r["jurisdiction"] for r in doc["rules"] if r["level"] == "city"}
    facts = {}
    for r in csv.DictReader(open(d / "addresses_resolved.csv", encoding="utf-8")):
        st, city = r.get("resolved_state") or r["state"], r.get("resolved_city") or ""
        lo, hi, note = E.unit_range(r)
        facts[r["address_id"]] = E.Facts(
            r["address_id"],
            st,
            f"{city}, {st}" if f"{city}, {st}" in cities else None,
            E._int(r.get("year_built")),
            lo,
            hi,
            note,
            f"{r.get('use_code')} {r.get('use_description')}".strip(),
            r,
        )
    # the main jurisdictions' rules come from the current output/rules.json (review fixes, earlier-version evidence),
    # so an extension address and a main address answer the same rule the same way
    main = {r["team_rule_id"]: r for r in load_rules()}
    rules = [
        main[r["team_rule_id"]]
        if r["team_rule_id"] in main and main[r["team_rule_id"]]["citation"] == r["citation"]
        else r
        for r in doc["rules"]
    ]
    return rules, doc.get("no_rule_findings", []), facts


def extension_lookup(slug: str, address_id: str, as_of: str = DEFAULT_AS_OF) -> dict:
    rules, findings, facts = _extension(slug)
    out = _lookup(facts[address_id], rules, findings, as_of)
    out["extension"] = slug
    return out


def lookup_user(
    state: str, jurisdiction: str | None, facts: dict, as_of: str = DEFAULT_AS_OF
) -> dict:
    """Any address (#39): live-geocoded state/city + building facts the user supplies (navigator/user_facts.py)."""
    from . import user_facts

    return user_facts.evaluate_user(state, jurisdiction, facts, as_of)


def changes(test_id: str | None = None) -> dict:
    data = (
        json.loads(CHANGES_JSON.read_text(encoding="utf-8")) if CHANGES_JSON.exists() else C.run()
    )
    return data if test_id is None else data.get(test_id, {})


def run_change_test(test: dict) -> dict:
    """Run an ad-hoc change test definition (same shape as starter/dev/change_tests.json)."""
    return C.run_test(test, load_rules())
