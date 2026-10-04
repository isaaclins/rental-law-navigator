"""How this answer was made (features/howmade.js): who decided what, per rule, from the pipeline's own records.

GET /api/howmade            -> {"rules": {rule_id: summary}}   (small; the client fetches it once)
GET /api/howmade/{rule_id}  -> summary + the extraction log entry: the model's own output for this rule

Every field comes from a file the pipeline wrote, nothing is invented here:
  * output/audit.jsonl          stage "extract": which model read the rule's source document, when, prompt version
  * output/plain_language.json  who wrote the short answer: "reviewed" (web/headlines.py) or "generated" by the
                                model and checked by code (navigator/plain.py), with the checks that failed
  * output/rules.json           (via web.app.STORE) the rule's source document
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
PLAIN_JSON = Path(__file__).resolve().parent.parent / "output" / "plain_language.json"


def _web():
    from web import app as W  # late import: web.app includes this router

    return W


def _plain(path: Path = PLAIN_JSON) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("records", {})
    except (OSError, ValueError):
        return {}


def _words(s: str) -> set[str]:
    return {
        w
        for w in "".join(c.lower() if c.isalnum() else " " for c in str(s or "")).split()
        if len(w) > 2
    }


def raw_rule(entry: dict, rule: dict) -> dict | None:
    """The rule as the model wrote it in this extraction entry: the one whose quote overlaps the final quote most."""
    try:
        out = json.loads(entry.get("raw_output") or "{}")
    except (TypeError, ValueError):
        return None
    cands = out.get("rules") if isinstance(out, dict) else None
    if not cands:
        return None
    want = _words(rule.get("quoted_span")) or _words(rule.get("title"))

    def score(c: dict) -> float:
        got = _words(c.get("quoted_span")) or _words(c.get("title"))
        return len(want & got) / max(1, len(want | got))

    best = max(cands, key=score)
    return best if score(best) >= 0.3 else None


def build(audit: list[dict], rules: dict[str, dict], plain: dict[str, dict]) -> dict[str, dict]:
    """rule_id -> {read: {...} | None, worded: {...} | None}."""
    by_doc: dict[str, list[int]] = {}
    for i, e in enumerate(audit):
        if e.get("stage") == "extract" and e.get("doc_id"):
            by_doc.setdefault(e["doc_id"], []).append(i)
    out: dict[str, dict] = {}
    for rid, r in rules.items():
        doc = r.get("source_doc_id")
        read = None
        idxs = by_doc.get(doc) or []
        if idxs:
            last = audit[idxs[-1]]
            # the first time this exact prompt (same hash) was logged: when the model actually read it
            first = next(
                audit[i] for i in idxs if audit[i].get("prompt_hash") == last.get("prompt_hash")
            )
            read = {
                "doc_id": doc,
                "model": last.get("model"),
                "prompt_version": last.get("prompt_version"),
                "at": first.get("ts"),
                "log": idxs[-1],
                "runs": len(idxs),
            }
        p = plain.get(rid) or {}
        worded = None
        if p:
            v = p.get("validation") or {}
            worded = {
                "source": p.get("source"),
                "method": p.get("method"),  # model | template
                "model": p.get("model"),
                "needs_review": bool(p.get("needs_review")),
                "review_reasons": p.get("review_reasons") or [],
                "checks_passed": v.get("passed"),
                "attempts": len(v.get("attempts") or []),
            }
        out[rid] = {"read": read, "worded": worded}
    return out


_CACHE: dict = {}


def summary() -> dict[str, dict]:
    W = _web()
    key = (
        id(W.STORE.audit),
        len(W.STORE.audit),
        id(W.STORE.rules),
        PLAIN_JSON.stat().st_mtime if PLAIN_JSON.exists() else 0,
    )
    if _CACHE.get("key") != key:
        _CACHE.update(key=key, data=build(W.STORE.audit, W.STORE.rules, _plain()))
    return _CACHE["data"]


@router.get("/api/howmade")
def howmade_all():
    return {"rules": summary()}


@router.get("/api/howmade/{rule_id}")
def howmade_one(rule_id: str):
    W = _web()
    s = summary().get(rule_id)
    r = W.STORE.rules.get(rule_id)
    if not s or not r:
        raise HTTPException(404, "no such rule")
    entry = W.STORE.audit[s["read"]["log"]] if s["read"] else None
    log = None
    if entry:
        log = {
            k: entry.get(k)
            for k in ("ts", "stage", "doc_id", "model", "prompt_version", "prompt_hash", "cached")
        }
        log["model_output"] = raw_rule(entry, r)
    return {**s, "rule_id": rule_id, "log_entry": log}
