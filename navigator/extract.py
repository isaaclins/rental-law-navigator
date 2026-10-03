"""Module A: automated rule extraction.

Stage 1  per document (chunked when long): LLM -> candidate rules + no-rule findings.
Stage 2  deterministic: verify every quoted_span verbatim (retry with the LLM, then snap to the closest
         exact passage, else drop), normalise jurisdiction / category / dates / citations.
Stage 3  per jurisdiction: LLM consolidation + completeness pass over all candidates and the full text of
         the jurisdiction's documents (merges duplicates, fills empty categories, records no-rule findings).
Stage 4  deterministic finalisation: span re-verification, dedupe, status as of the query date, ids,
         overrides/interaction links, conflict flags, schema validation -> output/rules.json.
Every LLM call is cached and written to output/audit.jsonl.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from . import normalize as N
from .config import (
    AUDIT_LOG,
    CAT_CODE,
    CATEGORIES,
    CITIES,
    DEFAULT_AS_OF,
    JUR_CODE,
    JURISDICTIONS,
    OUTPUT_DIR,
    RAW_RULES_JSON,
    RULES_JSON,
    STATES,
)
from .corpus import (
    Doc,
    chunks,
    get_doc,
    link_only_rows,
    load_docs,
    new_doc_rows,
    snap_span,
    verify_span,
)
from .llm import MAX_PARALLEL, call_llm
from .prompts import (
    COVERAGE_AUDIT_SCHEMA,
    COVERAGE_AUDIT_SYSTEM,
    EXTRACT_SCHEMA,
    PROBE_SCHEMA,
    PROBE_SYSTEM,
    PROMPT_VERSION,
    REVIEW_SCHEMA,
    REVIEW_SYSTEM,
    SPAN_FIX_SCHEMA,
    SYSTEM,
    coverage_audit_prompt,
    extract_prompt,
    probe_prompt,
    review_prompt,
    span_fix_prompt,
)

_audit_lock = threading.Lock()


def audit(entry: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "prompt_version": PROMPT_VERSION,
        **entry,
    }
    with _audit_lock, open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log(msg: str) -> None:
    print(f"[extract] {msg}", flush=True)


# ------------------------------------------------------------------ stage 1 + 2
def _verify_or_snap(doc_id: str, span: str) -> tuple[str | None, str]:
    exact = verify_span(doc_id, span)
    if exact:
        return exact, "verbatim"
    snapped, ratio = snap_span(doc_id, span, min_ratio=0.8)
    if snapped:
        return snapped, f"snapped({ratio:.2f})"
    return None, f"not_found(best {ratio:.2f})"


def _normalise_record(r: dict, doc: Doc) -> dict | None:
    j = N.jurisdiction(r.get("jurisdiction"))
    c = N.category(r.get("category"))
    if not j or not c:
        return None
    r["jurisdiction"], r["category"], r["level"] = j, c, N.level_for(j)
    for k in ("effective_date", "enacted_date", "sunset_date"):
        if k in r:
            r[k] = N.date(r.get(k))
    if "citation" in r:
        r["citation"] = N.citation(r.get("citation"))
    if "basis_citation" in r:
        r["basis_citation"] = N.citation(r.get("basis_citation"))
    r["source_doc_id"] = r.get("source_doc_id") or doc.doc_id
    return r


def _extract_doc(doc: Doc) -> tuple[list[dict], list[dict]]:
    rules, findings = [], []
    parts = chunks(doc)
    for ci, (_, text) in enumerate(parts):
        parsed, meta = call_llm(
            SYSTEM,
            extract_prompt(doc, text, ci, len(parts)),
            EXTRACT_SCHEMA,
            tag=f"extract:{doc.doc_id}:{ci}",
        )
        got_r, got_f = parsed.get("rules", []) or [], parsed.get("no_rule_findings", []) or []
        validation = []
        for r in got_r:
            r["_chunk"] = ci
            nr = _normalise_record(r, doc)
            validation.append(
                {
                    "title": r.get("title"),
                    "jurisdiction": r.get("jurisdiction"),
                    "category": r.get("category"),
                    "kept": nr is not None,
                }
            )
            if nr:
                rules.append(nr)
        for f in got_f:
            nf = _normalise_record(f, doc)
            if nf:
                findings.append(nf)
        audit(
            {
                "stage": "extract",
                "doc_id": doc.doc_id,
                "chunk": ci,
                "n_chunks": len(parts),
                "model": meta["model"],
                "prompt_hash": meta["prompt_hash"],
                "cached": meta["cached"],
                "raw_output": meta["raw"],
                "validation": validation,
            }
        )
    # span verification with one LLM retry for failures
    pending = []
    for i, r in enumerate(rules + findings):
        exact, how = _verify_or_snap(doc.doc_id, r.get("quoted_span", ""))
        r["_span_check"] = how
        if exact:
            r["quoted_span"] = exact
        else:
            r["_fix_id"] = str(i)
            pending.append(r)
    if pending:
        items = [
            {
                "id": r["_fix_id"],
                "title": r.get("title") or r.get("finding", ""),
                "citation": r.get("citation") or r.get("basis_citation") or "",
                "quoted_span": r.get("quoted_span", ""),
            }
            for r in pending
        ]
        try:
            parsed, meta = call_llm(
                SYSTEM, span_fix_prompt(doc, items), SPAN_FIX_SCHEMA, tag=f"spanfix:{doc.doc_id}"
            )
            fixes = {f["id"]: f["quoted_span"] for f in parsed.get("fixes", [])}
        except Exception as e:  # noqa: BLE001
            fixes, meta = {}, {"model": "-", "prompt_hash": "-", "cached": False, "raw": str(e)}
        results = []
        for r in pending:
            exact, how = _verify_or_snap(doc.doc_id, fixes.get(r["_fix_id"], ""))
            if not exact:  # last resort: snap the original span with a looser threshold
                exact, ratio = snap_span(doc.doc_id, r.get("quoted_span", ""), min_ratio=0.55)
                how = f"snapped_loose({ratio:.2f})" if exact else "dropped"
            r["_span_check"] = f"retry:{how}"
            if exact:
                r["quoted_span"] = exact
            results.append({"id": r["_fix_id"], "result": r["_span_check"]})
        audit(
            {
                "stage": "span_fix",
                "doc_id": doc.doc_id,
                "model": meta["model"],
                "prompt_hash": meta["prompt_hash"],
                "cached": meta["cached"],
                "raw_output": meta["raw"],
                "validation": results,
            }
        )
    keep = lambda r: not r["_span_check"].endswith("dropped")  # noqa: E731
    return [r for r in rules if keep(r)], [f for f in findings if keep(f)]


def stage1(docs: list[Doc]) -> tuple[list[dict], list[dict]]:
    rules, findings = [], []
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
        for doc, (rs, fs) in zip(docs, ex.map(_extract_doc, docs), strict=True):
            log(f"{doc.doc_id}: {len(rs)} rules, {len(fs)} no-rule findings")
            rules += rs
            findings += fs
    for i, r in enumerate(rules):
        r["cand_id"] = f"c{i}"
    for i, f in enumerate(findings):
        f["cand_id"] = f"n{i}"
    return rules, findings


# ------------------------------------------------------------------ stage 3
def _docs_for(jur: str, cands: list[dict], all_docs: list[Doc]) -> list[Doc]:
    ids = {r["source_doc_id"] for r in cands}
    tag = jur  # manifest tags are "CA" or "City, ST"
    out = [d for d in all_docs if d.jurisdictions == tag or d.doc_id in ids]
    if (
        not out and jur not in STATES
    ):  # no local documents at all: give the state's documents for the completeness check
        out = [d for d in all_docs if d.jurisdictions == N.state_of(jur)]
    return sorted(out, key=lambda d: d.doc_id)


def _link_only_for(jur: str, captured: set[str]) -> list[dict]:
    return [
        r for r in link_only_rows() if r["jurisdictions"] == jur and r["doc_id"] not in captured
    ]


def _compact(r: dict) -> dict:
    keep = [
        "cand_id",
        "source_doc_id",
        "jurisdiction",
        "level",
        "category",
        "legal_status",
        "title",
        "requirement",
        "key_value",
        "coverage_conditions",
        "exemptions",
        "penalty",
        "interaction",
        "effective_date",
        "effective_date_note",
        "enacted_date",
        "sunset_date",
        "citation",
        "citation_aliases",
        "quoted_span",
        "confidence",
        "conflict_note",
        "review_note",
        "coverage",
        "finding",
        "basis_citation",
    ]
    return {k: r[k] for k in keep if k in r and r[k] not in (None, "", [])}


def _is_official(doc_id: str | None) -> bool:
    d = get_doc(doc_id) if doc_id else None
    return bool(d and d.is_primary)


def _context_for(jur: str, rules: list[dict], findings: list[dict]) -> list[dict]:
    if jur in STATES:
        return [
            c
            for c in rules + findings
            if c["level"] == "city" and N.state_of(c["jurisdiction"]) == jur
        ]
    return [c for c in rules + findings if c["jurisdiction"] == N.state_of(jur)]


def _review_jurisdiction(jur: str, rules: list[dict], findings: list[dict], all_docs: list[Doc]):
    cands = [r for r in rules if r["jurisdiction"] == jur] + [
        f for f in findings if f["jurisdiction"] == jur
    ]
    docs = _docs_for(jur, cands, all_docs)
    captured = {d.doc_id for d in all_docs}
    context = _context_for(jur, rules, findings)
    prompt = review_prompt(
        jur, [_compact(c) for c in cands], docs, _link_only_for(jur, captured), context
    )
    parsed, meta = call_llm(REVIEW_SYSTEM, prompt, REVIEW_SCHEMA, tag=f"review:{jur}", timeout=1800)
    out_r, out_f, validation = [], [], []
    by_cand = {c["cand_id"]: c for c in cands}
    doc_ids = [d.doc_id for d in docs]
    for kind, items, sink in (
        ("rule", parsed.get("rules", []), out_r),
        ("no_rule", parsed.get("no_rule_findings", []), out_f),
    ):
        for r in items:
            src_doc = get_doc(r.get("source_doc_id", "")) or (docs[0] if docs else None)
            r = _normalise_record(r, src_doc) if src_doc else None
            if not r or r["jurisdiction"] != jur:
                validation.append(
                    {
                        "kind": kind,
                        "title": (r or {}).get("title"),
                        "result": "dropped: jurisdiction/category",
                    }
                )
                continue
            exact, how, span_doc = _resolve_span(r, by_cand, doc_ids)
            if not exact:
                if (
                    kind == "no_rule"
                ):  # a finding may stand without a quote; never ship an unverified one
                    r["quoted_span"], r["_span_check"], r["span_doc_id"] = None, "no_span", ""
                    sink.append(r)
                    validation.append(
                        {"kind": kind, "title": r.get("finding"), "result": "kept without span"}
                    )
                    continue
                validation.append(
                    {"kind": kind, "title": r.get("title"), "result": f"dropped: span {how}"}
                )
                continue
            r["quoted_span"], r["_span_check"], r["span_doc_id"] = exact, how, span_doc
            if not r.get("unverified_link_only"):
                r["source_doc_id"] = (
                    span_doc  # the cited source is the document the quote comes from
                )
            validation.append(
                {
                    "kind": kind,
                    "title": r.get("title") or r.get("finding"),
                    "result": f"kept ({how} in {span_doc})",
                }
            )
            sink.append(r)
    # every candidate must be accounted for: merged, or dropped with a reason; otherwise it is restored
    accounted = {c for r in parsed.get("rules", []) for c in (r.get("from_candidates") or [])}
    dropped = {
        d["cand_id"]: d.get("reason", "") for d in parsed.get("dropped_candidates", []) or []
    }
    have = {(r["category"], N.citation_key(r.get("citation", ""))) for r in out_r}
    restored = []
    for c in cands:
        cid = c["cand_id"]
        if cid in accounted or cid in dropped or not cid.startswith("c"):
            continue
        if (c["category"], N.citation_key(c.get("citation", ""))) in have:
            continue
        rc = dict(
            c,
            from_candidates=[cid],
            span_doc_id=c["source_doc_id"],
            review_note="restored: not accounted for in consolidation",
        )
        out_r.append(rc)
        have.add((c["category"], N.citation_key(c.get("citation", ""))))
        restored.append(cid)
    audit(
        {
            "stage": "review",
            "jurisdiction": jur,
            "model": meta["model"],
            "prompt_hash": meta["prompt_hash"],
            "cached": meta["cached"],
            "raw_output": meta["raw"],
            "validation": validation,
            "dropped_candidates": dropped,
            "restored_candidates": restored,
            "input_candidates": [c["cand_id"] for c in cands],
            "input_docs": doc_ids,
        }
    )
    log(
        f"review {jur}: {len(cands)} candidates -> {len(out_r)} rules ({len(restored)} restored), {len(out_f)} no-rule findings"
    )
    return out_r, out_f


def _resolve_span(r: dict, by_cand: dict, doc_ids: list[str]) -> tuple[str | None, str, str]:
    """Verify the record's quote; prefer official corpus documents, then merged candidates' verified quotes."""
    span = r.get("quoted_span") or ""
    order = [r.get("source_doc_id")] + [
        by_cand[c]["source_doc_id"] for c in r.get("from_candidates", []) if c in by_cand
    ]
    order += [d for d in doc_ids if d not in order]
    order = [d for d in dict.fromkeys(order) if d and get_doc(d)]
    found = [(d, verify_span(d, span)) for d in order]
    found = [(d, e) for d, e in found if e]
    off = [(d, e) for d, e in found if _is_official(d)]
    if off:
        return off[0][1], "verbatim", off[0][0]
    merged = [
        by_cand[c]
        for c in r.get("from_candidates", [])
        if c in by_cand and by_cand[c].get("quoted_span")
    ]
    off_c = [c for c in merged if _is_official(c["source_doc_id"])]
    if (
        off_c
    ):  # quote is only in a secondary source, but a merged candidate quotes an official document
        return off_c[0]["quoted_span"], "from_official_candidate", off_c[0]["source_doc_id"]
    if found:
        return found[0][1], "verbatim", found[0][0]
    if merged:
        return merged[0]["quoted_span"], "from_candidate", merged[0]["source_doc_id"]
    for d in order[:3]:
        snapped, ratio = snap_span(d, span, min_ratio=0.8)
        if snapped:
            return snapped, f"snapped({ratio:.2f})", d
    return None, "not_found", ""


_COV_FIELDS = [
    "min_units",
    "max_units",
    "construction_cutoff",
    "new_construction_exemption",
    "owner_occupied_exemption_max_units",
    "requires_unknown_facts",
]


def _audit_docs(jur: str, rules_j: list[dict], all_docs: list[Doc]) -> list[Doc]:
    ids = {r.get("source_doc_id") for r in rules_j} | {r.get("span_doc_id") for r in rules_j}
    docs = [d for d in all_docs if d.jurisdictions == jur or d.doc_id in ids]
    if jur not in STATES:
        docs += [d for d in all_docs if d.jurisdictions == N.state_of(jur) and d.is_primary]
    return sorted({d.doc_id: d for d in docs}.values(), key=lambda d: d.doc_id)


def _cell_consistency(rules: list[dict], findings: list[dict]) -> list[dict]:
    """A cell the reviewer found to have no rule keeps that finding; situational rules there (coverage turns on facts
    not in the data) are excluded and logged instead of contradicting it."""
    nr_cells = {(f["jurisdiction"], f["category"]) for f in findings}
    keep, excluded = [], []
    for r in rules:
        situational = bool((r.get("coverage") or {}).get("requires_unknown_facts"))
        if (
            (r["jurisdiction"], r["category"]) in nr_cells
            and r.get("legal_status") == "enacted"
            and situational
            and not r.get("unverified_link_only")
        ):
            excluded.append(
                {
                    "citation": r.get("citation"),
                    "jurisdiction": r["jurisdiction"],
                    "category": r["category"],
                    "reason": "situational rule in a cell the consolidation found to have no rule at this level",
                }
            )
            continue
        keep.append(r)
    if excluded:
        audit({"stage": "cell_consistency", "validation": excluded})
        log(f"cell consistency: excluded {len(excluded)} situational rules")
    return keep


def _coverage_audit(
    jur: str, rules_j: list[dict], context: list[dict], all_docs: list[Doc]
) -> None:
    """Evidence-grounded second look at coverage objects; a value is accepted only with a verbatim evidence quote."""
    if not rules_j:
        return
    docs = _audit_docs(jur, rules_j, all_docs)
    refs = [
        {
            "ref": f"r{i}",
            "category": r["category"],
            "title": r.get("title"),
            "citation": r.get("citation"),
            "legal_status": r.get("legal_status"),
            "key_value": r.get("key_value"),
            "coverage": r.get("coverage") or {},
            "quote_source": "official"
            if _is_official(r.get("span_doc_id") or r.get("source_doc_id"))
            else "secondary",
        }
        for i, r in enumerate(rules_j)
    ]
    parsed, meta = call_llm(
        COVERAGE_AUDIT_SYSTEM,
        coverage_audit_prompt(jur, refs, docs, context),
        COVERAGE_AUDIT_SCHEMA,
        tag=f"coverage-audit:{jur}",
        timeout=1800,
    )
    doc_ids = [d.doc_id for d in docs]
    changes = []
    for a in parsed.get("audits", []):
        try:
            r = rules_j[int(str(a.get("rule_ref", "")).lstrip("r"))]
        except (ValueError, IndexError):
            continue
        cov = dict(r.get("coverage") or {})
        new = a.get("coverage") or {}
        ev_ok = set()
        for ev in a.get("evidence", []) or []:
            if ev.get("doc_id") in doc_ids and verify_span(ev["doc_id"], ev.get("quoted_span", "")):
                ev_ok.add(ev.get("field"))
        for f in _COV_FIELDS:
            nv, ov = new.get(f), cov.get(f)
            if nv not in (None, [], "", 0) and nv != ov and f in ev_ok:
                cov[f] = nv
                changes.append({"rule": r.get("citation"), "field": f, "old": ov, "new": nv})
        for f in ("yields_to_local_rule", "supersedes_state_rule", "may_preempt_local_rules"):
            if new.get(f) and not cov.get(f):
                cov[f] = True
                changes.append({"rule": r.get("citation"), "field": f, "old": False, "new": True})
        r["coverage"] = cov
        oq = a.get("official_quote") or {}
        if (
            not r.get("unverified_link_only")
            and not _is_official(r.get("span_doc_id") or r.get("source_doc_id"))
            and oq.get("doc_id") in doc_ids
            and _is_official(oq["doc_id"])
        ):
            exact = verify_span(oq["doc_id"], oq.get("quoted_span", ""))
            if exact:
                changes.append(
                    {
                        "rule": r.get("citation"),
                        "field": "quoted_span",
                        "old": r.get("span_doc_id"),
                        "new": oq["doc_id"],
                    }
                )
                r["quoted_span"], r["span_doc_id"], r["source_doc_id"], r["_span_check"] = (
                    exact,
                    oq["doc_id"],
                    oq["doc_id"],
                    "official_quote",
                )
    audit(
        {
            "stage": "coverage_audit",
            "jurisdiction": jur,
            "model": meta["model"],
            "prompt_hash": meta["prompt_hash"],
            "cached": meta["cached"],
            "raw_output": meta["raw"],
            "validation": changes,
        }
    )
    log(f"coverage audit {jur}: {len(changes)} evidence-backed changes")


def _probe_empty(
    jur: str, rules_j: list[dict], findings_j: list[dict], context: list[dict], all_docs: list[Doc]
):
    """Empty jurisdiction x category cells: systematic no-rule findings, or unverified rules held in link-only sources."""
    filled = {r["category"] for r in rules_j} | {f["category"] for f in findings_j}
    empty = [c for c in CATEGORIES if c not in filled]
    if not empty:
        return [], []
    docs = _audit_docs(jur, rules_j, all_docs)
    captured = {d.doc_id for d in all_docs}
    lo = _link_only_for(jur, captured)
    ctx = [r for r in rules_j] + context
    parsed, meta = call_llm(
        PROBE_SYSTEM,
        probe_prompt(jur, empty, docs, lo, ctx),
        PROBE_SCHEMA,
        tag=f"probe:{jur}",
        timeout=1800,
    )
    lo_ids = {r["doc_id"] for r in lo}
    new_r, new_f, validation = [], [], []
    for cell in parsed.get("cells", []):
        cat = N.category(cell.get("category"))
        if cat not in empty:
            continue
        span, sdoc = None, ""
        if cell.get("quoted_span") and cell.get("span_doc_id") and get_doc(cell["span_doc_id"]):
            span = verify_span(cell["span_doc_id"], cell["quoted_span"])
            sdoc = cell["span_doc_id"] if span else ""
        if cell.get("verdict") == "no_rule":
            new_f.append(
                {
                    "jurisdiction": jur,
                    "level": N.level_for(jur),
                    "category": cat,
                    "finding": cell.get("reason"),
                    "basis_citation": N.citation(cell.get("basis_citation")),
                    "quoted_span": span,
                    "source_doc_id": sdoc or (docs[0].doc_id if docs else ""),
                    "span_doc_id": sdoc,
                    "confidence": cell.get("confidence"),
                    "_span_check": "verbatim" if span else "no_span",
                }
            )
            validation.append(
                {"category": cat, "result": "no_rule finding" + ("" if span else " (no span)")}
            )
        elif (
            cell.get("verdict") == "rule_in_link_only_source"
            and (cell.get("confidence") or 0) >= 0.8
            and cell.get("rule")
        ):
            rr = dict(cell["rule"])
            if rr.get("source_doc_id") not in lo_ids or not span:
                validation.append(
                    {
                        "category": cat,
                        "result": "rejected: needs a listed link-only source and a verifiable span",
                    }
                )
                continue
            rr.update(
                {
                    "jurisdiction": jur,
                    "category": cat,
                    "unverified_link_only": True,
                    "quoted_span": span,
                    "span_doc_id": sdoc,
                    "from_candidates": [],
                    "_span_check": "verbatim",
                    "confidence": min(float(rr.get("confidence") or 0.4), 0.4),
                    "conflict_note": (rr.get("conflict_note") or "")
                    + f" Unverified: text held in link-only source "
                    f"{rr.get('source_doc_id')} could not be captured; quote from {sdoc} supports the general proposition.",
                }
            )
            rr = _normalise_record(rr, get_doc(sdoc))
            if rr:
                rr["source_doc_id"] = cell["rule"].get("source_doc_id")
                rr["legal_status"] = rr.get("legal_status") or "enacted"
                rr.setdefault(
                    "coverage",
                    {
                        "requires_unknown_facts": [],
                        "yields_to_local_rule": False,
                        "supersedes_state_rule": False,
                        "may_preempt_local_rules": False,
                    },
                )
                new_r.append(rr)
                validation.append(
                    {"category": cat, "result": f"unverified rule {rr.get('citation')}"}
                )
        else:
            validation.append({"category": cat, "result": cell.get("verdict")})
    audit(
        {
            "stage": "probe",
            "jurisdiction": jur,
            "model": meta["model"],
            "prompt_hash": meta["prompt_hash"],
            "cached": meta["cached"],
            "raw_output": meta["raw"],
            "validation": validation,
        }
    )
    log(
        f"probe {jur}: {len(empty)} empty cells -> {len(new_r)} unverified rules, {len(new_f)} no-rule findings"
    )
    return new_r, new_f


def review_new_doc(
    jur: str, cand_r: list[dict], cand_f: list[dict], doc: Doc, existing: list[dict]
):
    """Consolidate a newly ingested document's candidates for one jurisdiction without touching existing rules."""
    cands = [r for r in cand_r + cand_f if r["jurisdiction"] == jur]
    if not cands:
        return [], []
    prompt = review_prompt(jur, [_compact(c) for c in cands], [doc], [], existing) + (
        "\n\nThis is a NEWLY ADDED document. Output only rules and findings supported by this document; existing rules "
        "(context) are already recorded and must not be repeated. If the new law amends or replaces an existing rule, say so in "
        "interaction."
    )
    parsed, meta = call_llm(
        REVIEW_SYSTEM, prompt, REVIEW_SCHEMA, tag=f"review-new:{doc.doc_id}:{jur}", timeout=1800
    )
    by_cand = {c["cand_id"]: c for c in cands}
    out_r, out_f, validation = [], [], []
    for kind, items, sink in (
        ("rule", parsed.get("rules", []), out_r),
        ("no_rule", parsed.get("no_rule_findings", []), out_f),
    ):
        for r in items:
            r["source_doc_id"] = doc.doc_id
            r = _normalise_record(r, doc)
            if not r or r["jurisdiction"] != jur:
                continue
            exact, how, span_doc = _resolve_span(r, by_cand, [doc.doc_id])
            validation.append(
                {"kind": kind, "title": r.get("title") or r.get("finding"), "result": how}
            )
            if exact:
                r["quoted_span"], r["_span_check"], r["span_doc_id"] = exact, how, span_doc
                sink.append(r)
    audit(
        {
            "stage": "review_new",
            "doc_id": doc.doc_id,
            "jurisdiction": jur,
            "model": meta["model"],
            "prompt_hash": meta["prompt_hash"],
            "cached": meta["cached"],
            "raw_output": meta["raw"],
            "validation": validation,
        }
    )
    return out_r, out_f


# ------------------------------------------------------------------ stage 4
def status_as_of(rule: dict, as_of: str = DEFAULT_AS_OF) -> str:
    ls = rule.get("legal_status", "enacted")
    if ls == "pending_bill":
        return "pending"
    if ls == "failed":
        return "failed"
    eff = N.date_floor(rule.get("effective_date"))
    if eff and eff > dt.date.fromisoformat(as_of):
        return "not_yet_effective"
    return "in_force"


def _dedupe(rules: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for r in sorted(rules, key=lambda r: -(r.get("confidence") or 0)):
        k = (
            r["jurisdiction"],
            r["category"],
            N.citation_key(r.get("citation", "")),
            r.get("legal_status"),
        )
        if k in seen:
            keep = seen[k]
            keep.setdefault("merged_titles", []).append(r.get("title"))
            continue
        seen[k] = r
    return list(seen.values())


def _source_meta(doc_id: str) -> tuple[str, str, str]:
    d = get_doc(doc_id)
    if d:
        return d.url, d.retrieved_at, d.source_type
    for row in link_only_rows():
        if row["doc_id"] == doc_id:
            return row["url"], "", row["source_type"] + " (link-only, text not captured)"
    return "", "", ""


def finalize(rules: list[dict], findings: list[dict], as_of: str = DEFAULT_AS_OF) -> dict:
    rules = _dedupe(rules)
    # ids
    out = []
    for jur in JURISDICTIONS + sorted({r["jurisdiction"] for r in rules} - set(JURISDICTIONS)):
        for cat in CATEGORIES:
            cell = [r for r in rules if r["jurisdiction"] == jur and r["category"] == cat]
            enacted = sorted(
                [r for r in cell if r.get("legal_status") == "enacted"],
                key=lambda r: (
                    r.get("unverified_link_only", False),
                    r.get("effective_date") or "",
                    r.get("citation", ""),
                ),
            )
            other = sorted(
                [r for r in cell if r.get("legal_status") != "enacted"],
                key=lambda r: r.get("citation", ""),
            )
            for i, r in enumerate(enacted, 1):
                r["team_rule_id"] = f"{JUR_CODE.get(jur, 'X')}-{CAT_CODE[cat]}-{i:02d}"
                out.append(r)
            for i, r in enumerate(other, 1):
                r["team_rule_id"] = f"{JUR_CODE.get(jur, 'X')}-{CAT_CODE[cat]}-P{i}"
                out.append(r)
    final = []
    for r in out:
        cov = r.get("coverage") or {}
        unverified = bool(r.get("unverified_link_only"))
        url, retrieved, stype = _source_meta(r["source_doc_id"])
        rec = {
            "team_rule_id": r["team_rule_id"],
            "jurisdiction": r["jurisdiction"],
            "level": r["level"],
            "category": r["category"],
            "status": status_as_of(r, as_of),
            "title": r.get("title", ""),
            "requirement": r.get("requirement", ""),
            "key_value": r.get("key_value"),
            "coverage_conditions": r.get("coverage_conditions"),
            "exemptions": r.get("exemptions"),
            "overrides": [],
            "interaction": r.get("interaction"),
            "effective_date": r.get("effective_date"),
            "citation": r.get("citation", ""),
            "source_doc_id": r["source_doc_id"],
            "source_url": url,
            "quoted_span": r["quoted_span"],
            "confidence": min(float(r.get("confidence") or 0.5), 0.4 if unverified else 1.0),
            "conflict_flag": bool(r.get("conflict_note")) or unverified,
            "conflict_note": r.get("conflict_note"),
            # extensions (allowed by the schema; used by the evaluator and the UI)
            "coverage": cov,
            "legal_status": r.get("legal_status", "enacted"),
            "penalty": r.get("penalty"),
            "effective_date_note": r.get("effective_date_note"),
            "enacted_date": r.get("enacted_date"),
            "sunset_date": r.get("sunset_date"),
            "citation_aliases": r.get("citation_aliases") or [],
            "retrieved_at": retrieved,
            "source_type": stype,
            "quoted_span_doc_id": r.get("span_doc_id") or r["source_doc_id"],
            "span_verification": r.get("_span_check", ""),
            "review_note": r.get("review_note"),
            "verification": "unverified_link_only"
            if unverified
            else ("primary_source" if not stype.startswith("secondary") else "secondary_source"),
            "extracted_from_candidates": r.get("from_candidates", []),
        }
        final.append(rec)
    _link_interactions(final)
    enacted_cells = {
        (r["jurisdiction"], r["category"])
        for r in final
        if r["legal_status"] == "enacted" and r.get("verification") != "unverified_link_only"
    }
    findings = [f for f in findings if (f["jurisdiction"], f["category"]) not in enacted_cells]
    nr = []
    for i, f in enumerate(
        sorted(
            findings,
            key=lambda f: (
                JURISDICTIONS.index(f["jurisdiction"])
                if f["jurisdiction"] in JURISDICTIONS
                else 99,
                CATEGORIES.index(f["category"]),
            ),
        ),
        1,
    ):
        url, retrieved, _ = _source_meta(f["source_doc_id"])
        nr.append(
            {
                "finding_id": f"NR-{i:02d}",
                "jurisdiction": f["jurisdiction"],
                "level": f["level"],
                "category": f["category"],
                "status": "no_rule",
                "finding": f.get("finding"),
                "citation": f.get("basis_citation"),
                "source_doc_id": f["source_doc_id"],
                "source_url": url,
                "quoted_span": f["quoted_span"],
                "quoted_span_doc_id": f.get("span_doc_id") or f["source_doc_id"],
                "confidence": f.get("confidence"),
            }
        )
    return {
        "as_of": as_of,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "disclaimer": "Not legal advice. Automated extraction from the supplied corpus; verify against the cited source.",
        "rules": final,
        "no_rule_findings": nr,
    }


def _link_interactions(rules: list[dict]) -> None:
    """Populate overrides/interaction between state rules that yield to (or may preempt) local rules of the same category."""
    for s in [r for r in rules if r["level"] == "state"]:
        cov = s.get("coverage") or {}
        locals_ = [
            r
            for r in rules
            if r["level"] == "city"
            and r["category"] == s["category"]
            and N.state_of(r["jurisdiction"]) == s["jurisdiction"]
            and r["status"] in ("in_force", "not_yet_effective")
        ]
        if cov.get("yields_to_local_rule"):
            sup = [r for r in locals_ if (r.get("coverage") or {}).get("supersedes_state_rule")]
            s["overrides"] = sorted({*s["overrides"], *(r["team_rule_id"] for r in sup)})
            for r in sup:
                r["overrides"] = sorted({*r["overrides"], s["team_rule_id"]})
                if not r.get("interaction"):
                    r["interaction"] = (
                        f"Governs instead of {s['team_rule_id']} ({s['citation']}) where both cover a unit."
                    )
            if sup and not s.get("interaction"):
                s["interaction"] = "Yields to local rules where they cover the unit: " + ", ".join(
                    r["team_rule_id"] for r in sup
                )
        if cov.get("may_preempt_local_rules") and locals_:
            ids = [r["team_rule_id"] for r in locals_]
            s["overrides"] = sorted({*s["overrides"], *ids})
            s["conflict_flag"] = True
            note = f"May preempt or conflict with local rules {', '.join(ids)}; flagged for human review."
            s["conflict_note"] = (
                s.get("conflict_note") + " " if s.get("conflict_note") else ""
            ) + note
            for r in locals_:
                r["conflict_flag"] = True
                n2 = f"State rule {s['team_rule_id']} ({s['citation']}) may preempt this ordinance once effective ({s.get('effective_date')})."
                if n2 not in (r.get("conflict_note") or ""):
                    r["conflict_note"] = (
                        r.get("conflict_note") + " " if r.get("conflict_note") else ""
                    ) + n2


def validate(doc: dict) -> list[str]:
    import jsonschema

    from .config import SCHEMA_JSON

    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    errs = []
    for r in doc["rules"]:
        for e in jsonschema.Draft202012Validator(schema).iter_errors(r):
            errs.append(f"{r.get('team_rule_id')}: {e.message}")
    return errs


def run(docs: list[Doc] | None = None, review: bool = True, out_path=RULES_JSON) -> dict:
    all_docs = load_docs()
    docs = docs or all_docs
    log(f"stage 1: {len(docs)} documents")
    rules, findings = stage1(docs)
    RAW_RULES_JSON.parent.mkdir(parents=True, exist_ok=True)
    RAW_RULES_JSON.write_text(
        json.dumps({"rules": rules, "no_rule_findings": findings}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    if review:
        jurs = list(
            JURISDICTIONS
        )  # every jurisdiction gets a completeness review, even without candidates
        fr, ff = [], []
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
            for rs, fs in ex.map(
                lambda j: _review_jurisdiction(j, rules, findings, all_docs), jurs
            ):
                fr += rs
                ff += fs
        # evidence-grounded coverage audit, then systematic treatment of empty jurisdiction x category cells
        ctxs = {j: _context_for(j, fr, ff) for j in jurs}
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
            list(
                ex.map(
                    lambda j: _coverage_audit(
                        j, [r for r in fr if r["jurisdiction"] == j], ctxs[j], all_docs
                    ),
                    jurs,
                )
            )
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
            res = list(
                ex.map(
                    lambda j: _probe_empty(
                        j,
                        [r for r in fr if r["jurisdiction"] == j],
                        [f for f in ff if f["jurisdiction"] == j],
                        ctxs[j],
                        all_docs,
                    ),
                    jurs,
                )
            )
        for rs, fs in res:
            fr += rs
            ff += fs
        fr = _cell_consistency(fr, ff)
        rules, findings = fr, ff
    (OUTPUT_DIR / "rules_reviewed.json").write_text(
        json.dumps({"rules": rules, "no_rule_findings": findings}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    doc = finalize(rules, findings)
    errs = validate(doc)
    audit(
        {
            "stage": "finalize",
            "n_rules": len(doc["rules"]),
            "n_no_rule": len(doc["no_rule_findings"]),
            "schema_errors": errs,
        }
    )
    out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    log(
        f"wrote {out_path} ({len(doc['rules'])} rules, {len(doc['no_rule_findings'])} no-rule findings, {len(errs)} schema errors)"
    )
    return doc


def new_doc_ids() -> list[str]:
    return [r["doc_id"] for r in new_doc_rows()]


__all__ = ["run", "stage1", "finalize", "status_as_of", "validate", "audit", "STATES", "CITIES"]
