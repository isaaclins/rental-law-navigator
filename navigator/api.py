"""Importable functions for the web layer (FastAPI etc.). Not legal advice.

from navigator import api
api.load_rules()                          -> list of rule records (output/rules.json)
api.lookup("A0001", as_of="2026-10-01")   -> jurisdiction stack + rule results with citations
api.lookup({"state": "CA", "resolved_city": "San Francisco", "year_built": 1962, "units": 20, ...})
api.changes("T3")                         -> affected addresses / conflict flags for a change test
api.address_ids(), api.get_rule(id), api.no_rule_findings()
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import changes as C
from . import evaluate as E
from .config import CHANGES_JSON, CITIES, DEFAULT_AS_OF, RULES_JSON

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
    rules = load_rules()
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
    findings = [n for n in no_rule_findings() if n["jurisdiction"] in (f.state, f.city)]
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


def changes(test_id: str | None = None) -> dict:
    data = (
        json.loads(CHANGES_JSON.read_text(encoding="utf-8")) if CHANGES_JSON.exists() else C.run()
    )
    return data if test_id is None else data.get(test_id, {})


def run_change_test(test: dict) -> dict:
    """Run an ad-hoc change test definition (same shape as starter/dev/change_tests.json)."""
    return C.run_test(test, load_rules())
