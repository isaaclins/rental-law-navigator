"""Module C: change tracking.

Each test names key rule ids (e.g. "CA-ALG-01", "MA-ALG-P1"). We resolve them to our extracted rules by
jurisdiction code + category code + enacted/proposal type (+ title keywords to break ties), then:
  as_of     : affected = addresses whose result for those rules changes between as_of_before and as_of_after
  boundary  : affected = addresses where the rules apply (or are unknown) on as_of
  pending   : affected = addresses the pending bills would cover if enacted
  negative  : affected = addresses where a (failed) proposal would have any effect -> normally empty
  new_law   : (ingest-new) affected = addresses the new law covers once effective; before/after rule sets
conflict_flag_address_ids = addresses where any involved entry carries a conflict flag.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import shutil
from pathlib import Path

from . import evaluate as E
from . import normalize as N
from .config import (
    CAT_CODE,
    CHANGE_TESTS_JSON,
    CHANGES_JSON,
    DEFAULT_AS_OF,
    JUR_CODE,
    NEW_DOCS_DIR,
    OUTPUT_DIR,
    RULES_JSON,
)

_CODE_JUR = {v: k for k, v in JUR_CODE.items()}
_CODE_CAT = {v: k for k, v in CAT_CODE.items()} | {
    "JC": "just_cause_eviction",
    "EVICT": "just_cause_eviction",
    "DEPOSIT": "security_deposits",
    "FEES": "application_screening_fees",
    "SCREEN": "screening_restrictions",
    "ALGO": "algorithmic_rent_setting",
}
_STOP = {
    "and",
    "the",
    "of",
    "vs",
    "act",
    "law",
    "local",
    "bans",
    "ban",
    "takes",
    "effect",
    "enacted",
    "not",
    "yet",
    "effective",
    "possible",
    "preemption",
    "pending",
    "bills",
    "bill",
    "question",
    "struck",
    "california",
    "new",
    "jersey",
    "massachusetts",
}


def resolve_rule_ids(test: dict, rules: list[dict]) -> dict[str, list[dict]]:
    out = {}
    words = {
        w
        for w in re.findall(r"[a-z0-9.]+", test.get("title", "").lower())
        if w not in _STOP and len(w) > 1
    }
    for kid in test.get("rule_ids", []):
        parts = kid.upper().split("-")
        jur = _CODE_JUR.get(parts[0])
        cat = _CODE_CAT.get(parts[1]) if len(parts) > 1 else None
        proposal = len(parts) > 2 and parts[2].startswith("P")
        cands = [
            r
            for r in rules
            if (jur is None or r["jurisdiction"] == jur)
            and (cat is None or r["category"] == cat)
            and ((r.get("legal_status") in ("pending_bill", "failed")) == proposal)
        ]
        if len(cands) > 1:

            def score(r):
                hay = " ".join(
                    [
                        r.get("citation", ""),
                        r.get("title", ""),
                        " ".join(r.get("citation_aliases") or []),
                    ]
                ).lower()
                return sum(1 for w in words if w in hay)

            best = max(map(score, cands))
            if best > 0:
                cands = [r for r in cands if score(r) == best]
        out[kid] = cands
    return out


def _results(addrs, rules, ids: set[str], as_of: str) -> dict[str, dict[str, dict]]:
    res = {}
    for f in addrs:
        ents = [e for e in E.evaluate_address(f, rules, as_of) if e["team_rule_id"] in ids]
        res[f.address_id] = {e["team_rule_id"]: e for e in ents}
    return res


def run_test(test: dict, rules: list[dict], addrs=None) -> dict:
    addrs = addrs or E.load_addresses()
    if test.get("type") == "new_law":
        mapping = {
            rid: [r for r in rules if r["team_rule_id"] == rid] for rid in test.get("rule_ids", [])
        }
    else:
        mapping = resolve_rule_ids(test, rules)
    ids = {r["team_rule_id"] for rs in mapping.values() for r in rs}
    ttype = test.get("type")
    per, affected, flagged = {}, [], []
    if ttype in ("as_of", "new_law"):
        b, a = test["as_of_before"], test["as_of_after"]
        rb, ra = _results(addrs, rules, ids, b), _results(addrs, rules, ids, a)
        for f in addrs:
            sb = {k: v["result"] for k, v in rb[f.address_id].items()}
            sa = {k: v["result"] for k, v in ra[f.address_id].items()}
            if sb != sa and sa:
                affected.append(f.address_id)
                per[f.address_id] = {"before": sb, "after": sa}
            if any(
                e["conflict_flag"]
                for e in list(rb[f.address_id].values()) + list(ra[f.address_id].values())
            ):
                flagged.append(f.address_id)
    else:
        r0 = _results(addrs, rules, ids, test.get("as_of", DEFAULT_AS_OF))
        for f in addrs:
            s = {k: v["result"] for k, v in r0[f.address_id].items()}
            if ttype == "pending":
                hit = {k: v for k, v in s.items() if v == "pending"}
            elif ttype == "negative":
                hit = {
                    k: v
                    for k, v in s.items()
                    if v in ("applies", "unknown", "not_yet_effective", "pending", "superseded")
                }
            else:  # boundary
                hit = {k: v for k, v in s.items() if v in ("applies", "unknown")}
            if hit:
                affected.append(f.address_id)
                per[f.address_id] = hit
            if any(e["conflict_flag"] for e in r0[f.address_id].values()):
                flagged.append(f.address_id)
    by_city = {}
    for f in addrs:
        if f.address_id in affected:
            by_city[f.city or f.state] = by_city.get(f.city or f.state, 0) + 1
    rule_desc = {
        kid: [f"{r['team_rule_id']} {r['citation']} [{r['status']}]" for r in rs]
        for kid, rs in mapping.items()
    }
    notes = (
        f"{test.get('title', '')}. Key rules -> ours: {json.dumps(rule_desc, ensure_ascii=False)}. "
        f"{len(affected)} affected addresses ({', '.join(f'{k}: {v}' for k, v in sorted(by_city.items())) or 'none'}); "
        f"{len(flagged)} with conflict flags. Expected: {test.get('expected_behavior', '')}"
    )
    if ttype == "negative" and not any(mapping.values()):
        notes += (
            " No in-force or proposed rule found; the proposal is recorded as failed / not law."
        )
    return {
        "affected_address_ids": affected,
        "conflict_flag_address_ids": flagged,
        "notes": notes,
        "rule_mapping": {k: [r["team_rule_id"] for r in v] for k, v in mapping.items()},
        "per_address": per,
    }


def load_tests() -> list[dict]:
    tests = json.loads(CHANGE_TESTS_JSON.read_text(encoding="utf-8"))
    extra = OUTPUT_DIR / "new_tests.json"
    if extra.exists():
        tests += json.loads(extra.read_text(encoding="utf-8"))
    return tests


def run(rules: list[dict] | None = None) -> dict:
    rules = rules if rules is not None else E.load_rules()
    addrs = E.load_addresses()
    out = {}
    for t in load_tests():
        if t["test_id"] == "T6" and t.get("type") == "new_law":
            t = _refresh_new_law_test(t, rules)
        out[t["test_id"]] = run_test(t, rules, addrs)
        r = out[t["test_id"]]
        print(
            f"[changes] {t['test_id']}: {len(r['affected_address_ids'])} affected, {len(r['conflict_flag_address_ids'])} flagged; "
            f"mapping {r['rule_mapping']}"
        )
    CHANGES_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def _refresh_new_law_test(t: dict, rules: list[dict]) -> dict:
    """Re-derive the new-law test's dates from the (possibly re-extracted) rules of the ingested doc."""
    mine = [r for r in rules if r["source_doc_id"] == t.get("doc_id")]
    if mine:
        t = dict(t)
        t["rule_ids"] = [r["team_rule_id"] for r in mine]
        effs = [N.date_floor(r.get("effective_date")) for r in mine if r.get("effective_date")]
        if effs:
            t["as_of_after"] = (max(effs) + dt.timedelta(days=1)).isoformat()
    return t


# ------------------------------------------------------------------ ingest a new law (e.g. the hour-16 ordinance)
def ingest_new(
    path: str, jurisdiction: str | None = None, url: str = "", test_id: str = "T6"
) -> dict:
    from . import extract as X
    from .corpus import docs_by_id, get_doc

    src = Path(path)
    NEW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    man = NEW_DOCS_DIR / "manifest.csv"
    rows = list(csv.DictReader(open(man, encoding="utf-8"))) if man.exists() else []
    existing = {r["text_file"]: r for r in rows}
    if src.name in existing:
        doc_id = existing[src.name]["doc_id"]
    else:
        doc_id = f"N{len(rows) + 1:03d}"
        now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%MZ")
        rows.append(
            {
                "doc_id": doc_id,
                "jurisdictions": jurisdiction or "",
                "url": url or f"file://{src.name}",
                "source_type": "official (new document ingested during event)",
                "retrieved_at": now,
                "text_file": src.name,
            }
        )
        with open(man, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    if src.resolve() != (NEW_DOCS_DIR / src.name).resolve():
        shutil.copy(src, NEW_DOCS_DIR / src.name)
    docs_by_id.cache_clear()
    doc = get_doc(doc_id)
    print(f"[ingest] {doc_id} <- {src} ({len(doc.text)} chars)")

    # extraction: stage 1 on the new doc + consolidation of its candidates against existing context
    cand_r, cand_f = X.stage1([doc])
    for i, r in enumerate(cand_r):
        r["cand_id"] = f"{doc_id}c{i}"
    for i, f in enumerate(cand_f):
        f["cand_id"] = f"{doc_id}n{i}"
    jurs = sorted(
        {r["jurisdiction"] for r in cand_r + cand_f} | ({jurisdiction} if jurisdiction else set())
    )
    reviewed_path = OUTPUT_DIR / "rules_reviewed.json"
    reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
    reviewed["rules"] = [r for r in reviewed["rules"] if r.get("source_doc_id") != doc_id]
    reviewed["no_rule_findings"] = [
        f for f in reviewed["no_rule_findings"] if f.get("source_doc_id") != doc_id
    ]
    for j in jurs:
        ctx_existing = [r for r in reviewed["rules"] if r["jurisdiction"] in (j, N.state_of(j))]
        nr, nf = X.review_new_doc(j, cand_r, cand_f, doc, ctx_existing)
        reviewed["rules"] += nr
        reviewed["no_rule_findings"] += nf
    reviewed_path.write_text(json.dumps(reviewed, indent=1, ensure_ascii=False), encoding="utf-8")
    final = X.finalize(reviewed["rules"], reviewed["no_rule_findings"])
    errs = X.validate(final)
    RULES_JSON.write_text(json.dumps(final, indent=1, ensure_ascii=False), encoding="utf-8")
    new_rules = [r for r in final["rules"] if r["source_doc_id"] == doc_id]
    print(f"[ingest] {len(new_rules)} new rules ({len(errs)} schema errors):")
    for r in new_rules:
        print(
            f"   {r['team_rule_id']} {r['jurisdiction']} {r['category']} {r['citation']} status={r['status']} "
            f"effective={r.get('effective_date')} | {r['key_value']}"
        )
    effs = [N.date_floor(r.get("effective_date")) for r in new_rules if r.get("effective_date")]
    after = (max(effs) + dt.timedelta(days=1)).isoformat() if effs else DEFAULT_AS_OF
    test = {
        "test_id": test_id,
        "title": f"New law {doc_id} ({src.name})",
        "type": "new_law",
        "doc_id": doc_id,
        "rule_ids": [r["team_rule_id"] for r in new_rules],
        "as_of_before": DEFAULT_AS_OF,
        "as_of_after": after,
        "expected_behavior": "Extracted unaided; affected addresses get the new rule once it takes effect.",
    }
    # register test (keyed by our own rule ids, which resolve_rule_ids matches by jurisdiction/category code)
    extra = OUTPUT_DIR / "new_tests.json"
    tests = [
        t
        for t in (json.loads(extra.read_text()) if extra.exists() else [])
        if t["test_id"] != test_id
    ] + [test]
    extra.write_text(json.dumps(tests, indent=1), encoding="utf-8")
    E.run(rules=final["rules"])
    res = run(final["rules"])
    t6 = res[test_id]
    print(
        f"[ingest] {test_id}: {len(t6['affected_address_ids'])} affected addresses; before {DEFAULT_AS_OF} vs after {after}"
    )
    return t6
