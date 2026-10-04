"""Extend the navigator to a new jurisdiction: add documents + addresses, rerun.  (Not legal advice.)

    python3 geo/lacounty_parcels.py "SANTA MONICA" new_docs/santa-monica/addresses.csv --prefix SM   # or any parcel source
    python3 geo/resolve.py --extension new_docs/santa-monica
    NAVIGATOR_EXTENSION=new_docs/santa-monica python -m navigator extend

new_docs/<slug>/ holds jurisdiction.json (name, state, rule-id code, Census place), manifest.csv (same columns as
the corpus manifest) with text/<doc_id>.txt, and addresses.csv (same columns as sample_addresses.csv).

The run builds on the main extraction (output/rules_reviewed.json) instead of re-reading the whole corpus:
  1. stage 1 + span verification on the new documents only (same prompts, same verifier)
  2. consolidation, evidence-grounded coverage audit and empty-cell probe for the new jurisdiction, with the
     state's reviewed rules as context (precedence, state exemptions, possible preemption)
  3. finalisation of main + new rules together (ids of existing rules do not change), schema validation
  3b. plain-language answers (en + es) for the new rules (navigator/plain.py, checked by code)
  4. address lookups for the extension addresses, pending/as-of change tests for the new rules
  5. metrics: wall time, LLM calls (cached vs new), cost from the CLI envelope, span verification pass rate
Everything goes to output/extension/<slug>/; output/rules.json, lookups.json and changes.json are not touched.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from collections import Counter

from . import changes as C
from . import evaluate as E
from . import extract as X
from . import plain as P
from .config import (
    AUDIT_LOG,
    BASE_OUTPUT_DIR,
    CACHE_DIR,
    DEFAULT_AS_OF,
    EXTENSION,
    EXTENSION_DIR,
    JUR_CODE,
    OUTPUT_DIR,
    RESOLVED_CSV,
    RULES_JSON,
)
from .corpus import extension_doc_rows, load_docs, verify_span

LLM_STAGES = ("extract", "span_fix", "review", "coverage_audit", "probe", "plain")


def log(msg: str) -> None:
    print(f"[extend] {msg}", flush=True)


def _measure(t0: float, rules: list[dict], findings: list[dict], lookups: dict) -> dict:
    calls = [json.loads(line) for line in open(AUDIT_LOG, encoding="utf-8")]
    calls = [
        c for c in calls if c.get("stage") in LLM_STAGES and c.get("prompt_hash") not in (None, "-")
    ]
    cost, secs, chars, missing = 0.0, 0.0, 0, 0
    for c in calls:
        p = CACHE_DIR / f"{c['prompt_hash']}.json"
        rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        if rec.get("cost_usd") is None:
            missing += 1
        cost += rec.get("cost_usd") or 0.0
        secs += rec.get("seconds") or 0.0
        chars += rec.get("prompt_chars") or 0
    spans = [
        (r, verify_span(r["quoted_span_doc_id"], r["quoted_span"]) == r["quoted_span"])
        for r in rules
    ]
    return {
        "wall_seconds_this_run": round(time.time() - t0, 1),
        "llm_calls": len(calls),
        "llm_calls_by_stage": dict(Counter(c["stage"] for c in calls)),
        "llm_calls_served_from_cache_this_run": sum(1 for c in calls if c.get("cached")),
        "llm_seconds_when_first_run": round(secs, 1),
        "llm_cost_usd_when_first_run": round(cost, 4),
        "llm_calls_without_cost_record": missing,
        "prompt_chars_total": chars,
        "rules": len(rules),
        "rules_by_category_status": dict(Counter(f"{r['category']}:{r['status']}" for r in rules)),
        "no_rule_findings": len(findings),
        "verbatim_spans": f"{sum(ok for _, ok in spans)}/{len(spans)}",
        "span_verification": dict(Counter(r.get("span_verification", "") for r in rules)),
        "verification": dict(Counter(r.get("verification", "") for r in rules)),
        "addresses": len(lookups),
        "lookup_results": dict(Counter(e["result"] for v in lookups.values() for e in v)),
    }


def run() -> dict:
    if not EXTENSION_DIR:
        raise SystemExit("set NAVIGATOR_EXTENSION=new_docs/<slug> (see docs/NEW_JURISDICTION.md)")
    t0 = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_LOG.unlink(
        missing_ok=True
    )  # one audit log per extension run, so the metrics describe this run
    new_jurs = [j["name"] for j in EXTENSION["jurisdictions"]]
    all_docs = load_docs()
    ids = {r["doc_id"] for r in extension_doc_rows()}
    docs = [d for d in all_docs if d.doc_id in ids]
    log(
        f"{', '.join(new_jurs)}: {len(docs)} new documents, building on {BASE_OUTPUT_DIR / 'rules_reviewed.json'}"
    )

    # 1. stage 1 on the new documents
    cand_r, cand_f = X.stage1(docs)
    for i, r in enumerate(cand_r):
        r["cand_id"] = f"c{i}"
    for i, f in enumerate(cand_f):
        f["cand_id"] = f"n{i}"
    off_scope = [c for c in cand_r + cand_f if c["jurisdiction"] not in new_jurs]
    if (
        off_scope
    ):  # e.g. state law restated on a city page: the state level comes from the main extraction
        X.audit(
            {
                "stage": "extend_scope",
                "validation": [
                    {
                        "jurisdiction": c["jurisdiction"],
                        "citation": c.get("citation") or c.get("basis_citation"),
                    }
                    for c in off_scope
                ],
            }
        )
        log(
            f"{len(off_scope)} candidates for already covered jurisdictions left to the main extraction"
        )
    (OUTPUT_DIR / "rules_raw.json").write_text(
        json.dumps({"rules": cand_r, "no_rule_findings": cand_f}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )

    # 2. consolidation, coverage audit, empty-cell probe for the new jurisdiction(s)
    base = json.loads((BASE_OUTPUT_DIR / "rules_reviewed.json").read_text(encoding="utf-8"))
    base_r = [r for r in base["rules"] if r["jurisdiction"] not in new_jurs]
    base_f = [f for f in base["no_rule_findings"] if f["jurisdiction"] not in new_jurs]
    cand_r = [c for c in cand_r if c["jurisdiction"] in new_jurs]
    cand_f = [c for c in cand_f if c["jurisdiction"] in new_jurs]
    new_r, new_f = [], []
    for j in new_jurs:
        rs, fs = X._review_jurisdiction(j, base_r + cand_r, base_f + cand_f, all_docs)
        ctx = X._context_for(j, base_r + rs, base_f + fs)
        X._coverage_audit(j, rs, ctx, all_docs)
        pr, pf = X._probe_empty(j, rs, fs, ctx, all_docs)
        new_r += X._cell_consistency(rs + pr, fs + pf)
        new_f += fs + pf
    rules, findings = base_r + new_r, base_f + new_f
    (OUTPUT_DIR / "rules_reviewed.json").write_text(
        json.dumps({"rules": rules, "no_rule_findings": findings}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )

    # 3. finalise main + new together
    doc = X.finalize(rules, findings)
    errs = X.validate(doc)
    X.audit({"stage": "finalize", "n_rules": len(doc["rules"]), "schema_errors": errs})
    RULES_JSON.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    mine = [r for r in doc["rules"] if r["jurisdiction"] in new_jurs]
    mine_f = [f for f in doc["no_rule_findings"] if f["jurisdiction"] in new_jurs]
    log(f"{len(mine)} new rules, {len(mine_f)} no-rule findings, {len(errs)} schema errors")
    for r in mine:
        log(f"  {r['team_rule_id']:12} {r['status']:17} {r['citation']} | {r.get('key_value')}")

    # 3b. plain-language answers (en + es) for the new rules, generated and checked by code (navigator/plain.py)
    t_plain = time.time()
    pl = P.run(rules=doc["rules"], log=log)
    t_plain = round(time.time() - t_plain, 1)

    # 4. lookups for the extension addresses + change tests for pending / future rules of the new jurisdiction
    look = E.run(rules=doc["rules"])["lookups"]
    tests = []
    pend = [r["team_rule_id"] for r in mine if r["status"] == "pending"]
    if pend:
        tests.append(
            {
                "test_id": "X1",
                "title": "Pending local measures",
                "type": "pending",
                "rule_ids": pend,
            }
        )
    for r in mine:
        if r["status"] == "not_yet_effective" and r.get("effective_date"):
            eff = X.N.date_floor(r["effective_date"])
            tests.append(
                {
                    "test_id": f"X{len(tests) + 1}",
                    "title": f"{r['citation']} takes effect",
                    "type": "new_law",
                    "rule_ids": [r["team_rule_id"]],
                    "as_of_before": DEFAULT_AS_OF,
                    "as_of_after": (eff + dt.timedelta(days=1)).isoformat(),
                }
            )
    addrs = E.load_addresses()
    ch = {t["test_id"]: dict(C.run_test(t, doc["rules"], addrs), title=t["title"]) for t in tests}
    (OUTPUT_DIR / "changes.json").write_text(
        json.dumps(ch, indent=1, ensure_ascii=False), encoding="utf-8"
    )

    # 5. metrics
    m = _measure(t0, mine, mine_f, look)
    m.update(
        {
            "jurisdictions": new_jurs,
            "rule_id_codes": {j: JUR_CODE[j] for j in new_jurs},
            "documents": [
                {
                    "doc_id": d.doc_id,
                    "url": d.url,
                    "source_type": d.source_type,
                    "chars": len(d.text),
                }
                for d in docs
            ],
            "addresses_file": str(RESOLVED_CSV.relative_to(BASE_OUTPUT_DIR.parent)),
            "schema_errors": errs,
            "plain_language": {**pl["counts"], "wall_seconds_this_run": t_plain},
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    log(
        json.dumps(
            {
                k: m[k]
                for k in (
                    "wall_seconds_this_run",
                    "llm_calls",
                    "llm_cost_usd_when_first_run",
                    "rules",
                    "verbatim_spans",
                    "lookup_results",
                )
            }
        )
    )
    return m
