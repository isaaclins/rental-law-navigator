"""Ask over every jurisdiction in the data, with no city named in code (#101, 2026-10-04).

- The main corpus: web.app.STORE (output/rules.json, the 500 sample addresses). A city that `navigator ingest-new`
  writes into rules.json is picked up from the rules' own `jurisdiction` field.
- Extensions added with `NAVIGATOR_EXTENSION=new_docs/<slug> python -m navigator extend`: output/extension/<slug>/
  (rules.json is a superset of the main one; its own rules, findings, addresses and lookups are added here) plus
  new_docs/<slug>/jurisdiction.json (name, state, code, postal cities, optional "aliases") and its manifest and texts.

ask_store() returns a read-only view that merges both and is rebuilt whenever any of those files changes, so a city
added while the app runs is answered on the next question (a restart works too). places() gives every covered city
with the names a question may use for it, and zip_city() the ZIP codes of our addresses.
"""

from __future__ import annotations

import csv
import json
import re
import threading
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_LOCK = threading.Lock()
_CACHE: dict = {}


def _ext_root() -> Path:
    from navigator import api as NA

    return NA.EXTENSION_ROOT


def _new_docs() -> Path:
    return ROOT / "new_docs"


def _files() -> list[Path]:
    root = _ext_root()
    out = []
    for pat in ("*/rules.json", "*/summary.json", "*/addresses_resolved.csv", "*/lookups.json"):
        out += sorted(root.glob(pat))
    out += sorted(_new_docs().glob("*/jurisdiction.json")) + sorted(
        _new_docs().glob("*/manifest.csv")
    )
    return out


def ext_sig() -> tuple:
    return tuple((str(p), p.stat().st_mtime) for p in _files() if p.exists())


class Extension:
    """One output/extension/<slug>/ directory: the rules, findings, addresses and documents it adds."""

    def __init__(self, slug: str, base_rules: dict, base_findings: set) -> None:
        self.slug = slug
        d = _ext_root() / slug
        doc = json.loads((d / "rules.json").read_text(encoding="utf-8"))
        summary = {}
        if (d / "summary.json").exists():
            summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        jfile = _new_docs() / slug / "jurisdiction.json"
        jdoc = json.loads(jfile.read_text(encoding="utf-8")) if jfile.exists() else {}
        names = list(
            dict.fromkeys(
                [
                    *(j["name"] for j in jdoc.get("jurisdictions", [])),
                    *summary.get("jurisdictions", []),
                ]
            )
        )
        by_name = {j["name"]: j for j in jdoc.get("jurisdictions", [])}
        self.jurisdictions = [
            {
                "name": n,
                "state": (by_name.get(n) or {}).get("state") or n.rsplit(", ", 1)[-1],
                "code": (by_name.get(n) or {}).get("code"),
                "aliases": [
                    a.lower()
                    for a in [
                        n.split(",")[0],
                        *(by_name.get(n) or {}).get("postal_cities", []),
                        *(by_name.get(n) or {}).get("aliases", []),
                    ]
                    if a
                ],
            }
            for n in names
        ]
        juris = {j["name"] for j in self.jurisdictions}
        # its own rules: the new jurisdiction's, or any id the main corpus doesn't have
        self.rules = {
            r["team_rule_id"]: r
            for r in doc["rules"]
            if r["jurisdiction"] in juris or r["team_rule_id"] not in base_rules
        }
        self.findings = [
            f
            for f in doc.get("no_rule_findings", [])
            if f["jurisdiction"] in juris and f.get("finding_id") not in base_findings
        ]
        self.addresses: dict[str, dict] = {}
        ap = d / "addresses_resolved.csv"
        if ap.exists():
            for row in csv.DictReader(ap.open(encoding="utf-8")):
                self.addresses[row["address_id"]] = row
        self.manifest: dict[str, dict] = {}
        self.text_dirs = [_new_docs() / slug / "text", _new_docs() / slug]
        mp = _new_docs() / slug / "manifest.csv"
        if mp.exists():
            for row in csv.DictReader(mp.open(encoding="utf-8")):
                self.manifest[row["doc_id"]] = row


class AskStore:
    """web.app.STORE plus every extension, read-only. Everything not overridden here comes from STORE."""

    def __init__(self, base, exts: list[Extension], sig: tuple) -> None:
        self._b = base
        self.exts = exts
        self.rules = dict(base.rules)
        self.no_rule = list(base.no_rule)
        self.addresses = dict(base.addresses)
        self.manifest = dict(base.manifest)
        self.address_slug: dict[str, str] = {}
        self.rule_slug: dict[str, str] = {}
        for x in exts:
            for k, r in x.rules.items():
                self.rules.setdefault(k, r)
                self.rule_slug[k] = x.slug
            self.no_rule += x.findings
            for k, a in x.addresses.items():
                if k not in self.addresses:
                    self.addresses[k] = a
                    self.address_slug[k] = x.slug
            for k, m in x.manifest.items():
                self.manifest.setdefault(k, m)
        self._sig = (base._sig, sig)
        self._text: dict[str, str | None] = {}
        self._verify: dict[str, dict] = {}

    def __getattr__(self, k):
        return getattr(self._b, k)

    # documents of extensions live in new_docs/<slug>/
    def doc_text(self, doc_id):
        t = self._b.doc_text(doc_id)
        if t is not None or not doc_id:
            return t
        if doc_id not in self._text:
            found = None
            for x in self.exts:
                m = x.manifest.get(doc_id) or {}
                cands = [ROOT / "new_docs" / x.slug / m["text_file"]] if m.get("text_file") else []
                cands += [dd / f"{doc_id}.txt" for dd in x.text_dirs]
                for p in cands:
                    if p.exists():
                        found = p.read_text(errors="replace")
                        break
                if found is not None:
                    break
            self._text[doc_id] = found
        return self._text[doc_id]

    def doc_meta(self, doc_id):
        meta = self._b.doc_meta(doc_id)
        m = self.manifest.get(doc_id or "")
        if m and not meta.get("url"):
            meta = {
                **meta,
                "url": m.get("url"),
                "retrieved_at": m.get("retrieved_at") or meta.get("retrieved_at"),
                "source_type": m.get("source_type", ""),
                "sha256": m.get("sha256"),
                "secondary": "secondary" in (m.get("source_type") or ""),
            }
        if not meta.get("has_text") and self.doc_text(doc_id) is not None:
            meta = {**meta, "has_text": True}
        return meta

    def verify(self, rule):
        rid = rule.get("team_rule_id") or rule.get("finding_id")
        if (
            rid not in self.rule_slug
            and self._b.doc_text(rule.get("quoted_span_doc_id") or rule.get("source_doc_id"))
            is not None
        ):
            return self._b.verify(rule)
        if rid not in self._verify:
            from web.app import _ws

            txt = self.doc_text(rule.get("quoted_span_doc_id") or rule.get("source_doc_id"))
            span = rule.get("quoted_span") or ""
            res = {"status": "no_text", "label": "Source text not available offline"}
            if txt is not None and span:
                if span in txt:
                    res = {
                        "status": "exact",
                        "label": "Quote found verbatim in source",
                        "offset": txt.find(span),
                    }
                elif _ws(span) in _ws(txt):
                    res = {
                        "status": "normalized",
                        "label": "Quote found in source (whitespace/quotes normalised)",
                    }
                else:
                    res = {
                        "status": "not_found",
                        "label": "Quote NOT found in source text: needs review",
                    }
            self._verify[rid] = res
        return self._verify[rid]


def ask_store():
    from web.app import STORE

    STORE.maybe_reload()
    sig = ext_sig()
    key = (STORE._sig, sig)
    if _CACHE.get("key") != key:
        with _LOCK:
            if _CACHE.get("key") != key:
                base_ids = set(STORE.rules)
                base_f = {f.get("finding_id") for f in STORE.no_rule}
                exts = []
                for p in sorted(_ext_root().glob("*/rules.json")):
                    try:
                        exts.append(Extension(p.parent.name, STORE.rules, base_f))
                    except (OSError, ValueError, KeyError):
                        continue
                _CACHE.update(key=key, store=AskStore(STORE, exts, sig), base_ids=base_ids)
    return _CACHE["store"]


def places(store) -> dict[str, dict]:
    """Every city we have local rules for: {"Santa Monica, CA": {"state": "CA", "aliases": [...], "slug": ...}}."""
    out: dict[str, dict] = {}
    for x in getattr(store, "exts", []):
        for j in x.jurisdictions:
            if ", " in j["name"]:
                out[j["name"]] = {"state": j["state"], "aliases": j["aliases"], "slug": x.slug}
    for r in store.rules.values():  # a city that `ingest-new` added to rules.json
        j = r.get("jurisdiction") or ""
        if ", " in j and j not in out:
            out[j] = {
                "state": j.rsplit(", ", 1)[1],
                "aliases": [j.split(",")[0].lower()],
                "slug": None,
            }
    return out


def zip_city(store, known: set[str]) -> dict[str, str]:
    """ZIP -> the covered city most of our addresses with that ZIP are in."""
    votes: dict[str, Counter] = {}
    for a in store.addresses.values():
        z = (a.get("zip") or "").strip()[:5]
        city = a.get("resolved_city") or ""
        st = a.get("resolved_state") or a.get("state") or ""
        jur = f"{city}, {st}"
        if re.fullmatch(r"\d{5}", z) and jur in known:
            votes.setdefault(z, Counter())[jur] += 1
    return {z: c.most_common(1)[0][0] for z, c in votes.items()}
