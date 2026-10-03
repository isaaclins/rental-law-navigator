"""Rental Housing Law Navigator - web app (FastAPI + build-free single page).

Run:  uv run uvicorn web.app:app --port 8765

Data sources, in order of preference:
  * navigator.api (live as-of evaluation), if importable
  * output/{rules,lookups,changes}.json + output/audit.jsonl   (pipeline output)
  * web/fixtures/*  (development fixtures in the same format; clearly labelled in the UI)
Everything is re-read automatically when a file changes, so a pipeline rerun shows up live.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib
import inspect
import json
import re
import threading
from collections import Counter, defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from web.any_address import router as any_address_router

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
STATIC = WEB / "static"
OUTPUT = ROOT / "output"
FIXTURES = WEB / "fixtures"
TRANSLATIONS = WEB / "translations"
STARTER = ROOT / "starter"
TEXT_DIRS = [
    STARTER / "corpus" / "text",
    ROOT / "supplementary" / "text",
    ROOT / "new_docs" / "text",
    ROOT / "new_docs",
]
DEFAULT_AS_OF = "2026-10-01"

CATEGORIES = [
    ("rent_increase_limits", "Rent increases", "How much can the rent go up?"),
    (
        "just_cause_eviction",
        "Eviction protections",
        "Does the landlord need a reason to end the tenancy?",
    ),
    ("security_deposits", "Security deposit", "How large can the deposit be?"),
    (
        "application_screening_fees",
        "Application & move-in fees",
        "What can be charged to apply or move in?",
    ),
    ("screening_restrictions", "Tenant screening", "What may a landlord ask about or consider?"),
    (
        "algorithmic_rent_setting",
        "Algorithmic rent-setting",
        "Can software be used to set the rent?",
    ),
]
CAT_LABEL = {c: l for c, l, _ in CATEGORIES}
STATE_NAMES = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}
CITY_ORDER = [
    "Los Angeles",
    "San Francisco",
    "San Diego",
    "Berkeley",
    "Santa Ana",
    "Jersey City",
    "Hoboken",
    "Newark",
    "Boston",
    "Cambridge",
]
CITY_STATE = {
    "Los Angeles": "CA",
    "San Francisco": "CA",
    "San Diego": "CA",
    "Berkeley": "CA",
    "Santa Ana": "CA",
    "Jersey City": "NJ",
    "Hoboken": "NJ",
    "Newark": "NJ",
    "Boston": "MA",
    "Cambridge": "MA",
}
JUR_ORDER = []
for _s in ("CA", "NJ", "MA"):
    JUR_ORDER.append(_s)
    JUR_ORDER += [f"{c}, {_s}" for c in CITY_ORDER if CITY_STATE[c] == _s]
JUR_CODES = {
    "CA": "CA",
    "NJ": "NJ",
    "MA": "MA",
    "LA": "Los Angeles, CA",
    "SF": "San Francisco, CA",
    "SD": "San Diego, CA",
    "BER": "Berkeley, CA",
    "SA": "Santa Ana, CA",
    "JC": "Jersey City, NJ",
    "HOB": "Hoboken, NJ",
    "NWK": "Newark, NJ",
    "BOS": "Boston, MA",
    "CAM": "Cambridge, MA",
}
CAT_CODES = {
    "RENT": "rent_increase_limits",
    "EVIC": "just_cause_eviction",
    "JC": "just_cause_eviction",
    "DEP": "security_deposits",
    "FEE": "application_screening_fees",
    "SCR": "screening_restrictions",
    "ALG": "algorithmic_rent_setting",
}


# ============================================================== data store ==
def _norm_date(d: str | None) -> str | None:
    """'2024-10' -> '2024-10-01', '2025' -> '2025-01-01'."""
    if not d:
        return None
    d = str(d).strip()
    if re.fullmatch(r"\d{4}", d):
        return d + "-01-01"
    if re.fullmatch(r"\d{4}-\d{2}", d):
        return d + "-01"
    return d[:10]


def _ws(s: str) -> str:
    s = s.replace(" ", " ").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


class Store:
    """Loads pipeline output (or fixtures) and reloads when files change."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sig: tuple = ()
        self.load()

    # ---- file selection
    @staticmethod
    def _pick(name: str) -> tuple[Path | None, str]:
        p = OUTPUT / name
        if p.exists() and p.stat().st_size > 2:
            return p, "pipeline"
        f = FIXTURES / name
        if f.exists():
            return f, "fixture"
        return None, "missing"

    def _signature(self) -> tuple:
        sig = []
        for n in ("rules.json", "lookups.json", "changes.json", "audit.jsonl"):
            p, kind = self._pick(n)
            sig.append((n, str(p), p.stat().st_mtime if p else 0))
        r = ROOT / "data" / "addresses_resolved.csv"
        sig.append(("addr", r.stat().st_mtime if r.exists() else 0))
        for p in sorted(TRANSLATIONS.glob("*.json")):
            sig.append((p.name, p.stat().st_mtime))
        return tuple(sig)

    def maybe_reload(self) -> None:
        if self._signature() != self._sig:
            with self._lock:
                if self._signature() != self._sig:
                    self.load()

    def load(self) -> None:
        self.sources: dict[str, dict] = {}

        def read(name):
            p, kind = self._pick(name)
            self.sources[name] = {
                "kind": kind,
                "path": str(p.relative_to(ROOT)) if p else None,
                "modified": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(
                    timespec="seconds"
                )
                if p
                else None,
            }
            return p

        p = read("rules.json")
        raw = json.loads(p.read_text()) if p else {"rules": []}
        rules = raw["rules"] if isinstance(raw, dict) else raw
        self.rules: dict[str, dict] = {r["team_rule_id"]: r for r in rules}
        self.no_rule: list[dict] = raw.get("no_rule_findings", []) if isinstance(raw, dict) else []
        self.rules_generated = raw.get("generated_at") if isinstance(raw, dict) else None
        p = read("lookups.json")
        lk = json.loads(p.read_text()) if p else {"as_of": DEFAULT_AS_OF, "lookups": {}}
        self.base_as_of = lk.get("as_of", DEFAULT_AS_OF)
        self.lookups: dict[str, list] = lk.get("lookups", {})
        p = read("changes.json")
        self.changes: dict = json.loads(p.read_text()) if p else {}
        p = read("audit.jsonl")
        self.audit: list[dict] = []
        if p:
            for line in p.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        self.audit.append(json.loads(line))
                    except json.JSONDecodeError:
                        self.audit.append({"raw": line})
        # addresses
        ap = ROOT / "data" / "addresses_resolved.csv"
        if not ap.exists():
            ap = STARTER / "data" / "sample_addresses.csv"
        self.addresses: dict[str, dict] = {r["address_id"]: r for r in csv.DictReader(ap.open())}
        # manifest
        self.manifest: dict[str, dict] = {}
        for f in (STARTER / "corpus" / "corpus_manifest.csv", ROOT / "new_docs" / "manifest.csv"):
            if f.exists():
                for r in csv.DictReader(f.open()):
                    self.manifest[r["doc_id"]] = r
        # change tests
        self.tests: list[dict] = []
        for f in (
            STARTER / "dev" / "change_tests.json",
            OUTPUT / "new_tests.json",
            ROOT / "new_docs" / "change_tests.json",
        ):
            if f.exists():
                for t in json.loads(f.read_text()):
                    if t["test_id"] not in {x["test_id"] for x in self.tests}:
                        self.tests.append(t)
        for tid in self.changes:
            if tid not in {x["test_id"] for x in self.tests}:
                self.tests.append(
                    {
                        "test_id": tid,
                        "title": self.changes[tid].get("title", f"Change test {tid}"),
                        "type": self.changes[tid].get("type", "new"),
                        "rule_ids": self.changes[tid].get("rule_ids", []),
                        "expected_behavior": self.changes[tid].get("notes", ""),
                    }
                )
        # translations
        self.tr: dict[str, dict[str, str]] = {}
        for p in TRANSLATIONS.glob("*.json"):
            try:
                self.tr[p.stem] = json.loads(p.read_text())
            except json.JSONDecodeError:
                pass
        # derived
        self.rule_addr_counts = Counter(e["team_rule_id"] for v in self.lookups.values() for e in v)
        self._doc_cache: dict[str, str | None] = {}
        self._verify: dict[str, dict] = {}
        self._sig = self._signature()

    # ---- documents & quote verification
    def doc_text(self, doc_id: str | None) -> str | None:
        if not doc_id:
            return None
        if doc_id not in self._doc_cache:
            txt = None
            for d in TEXT_DIRS:
                p = d / f"{doc_id}.txt"
                if p.exists():
                    txt = p.read_text(errors="replace")
                    break
            self._doc_cache[doc_id] = txt
        return self._doc_cache[doc_id]

    def doc_meta(self, doc_id: str | None) -> dict:
        m = self.manifest.get(doc_id or "", {})
        txt = self.doc_text(doc_id)
        retrieved = m.get("retrieved_at") or ""
        if txt and not retrieved:
            mm = re.search(r"^RETRIEVED:\s*(.+)$", txt, re.M)
            retrieved = mm.group(1).strip() if mm else ""
        stype = m.get("source_type", "")
        if txt and not stype:
            mm = re.search(r"^SOURCE_TYPE:\s*(.+)$", txt, re.M)
            stype = mm.group(1).strip() if mm else ""
        return {
            "doc_id": doc_id,
            "url": m.get("url"),
            "retrieved_at": retrieved,
            "source_type": stype,
            "sha256": m.get("sha256"),
            "has_text": txt is not None,
            "secondary": "secondary" in stype,
        }

    def verify(self, rule: dict) -> dict:
        rid = rule.get("team_rule_id") or rule.get("finding_id")
        if rid not in self._verify:
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

    def t(self, text: str | None, lang: str) -> str | None:
        if not text or lang == "en":
            return text
        table = self.tr.get(lang, {})
        return table.get(hashlib.sha1(text.encode()).hexdigest()[:16], text)

    def has_t(self, text: str | None, lang: str) -> bool:
        return bool(text) and hashlib.sha1(text.encode()).hexdigest()[:16] in self.tr.get(lang, {})


STORE = Store()


# ================================================== live API (navigator/api.py)
def _live_api():
    try:
        mod = importlib.import_module("navigator.api")
        return mod
    except Exception:
        return None


def _call_live(address_id: str, as_of: str) -> list[dict] | None:
    """Try navigator.api for an as-of evaluation. Accepts a few plausible function names."""
    if STORE.sources.get("rules.json", {}).get("kind") != "pipeline":
        return None  # fixtures: the live engine would read different rules
    mod = _live_api()
    if mod is None:
        return None
    for name in ("lookup_address", "lookup", "evaluate_address", "rules_for_address"):
        fn = getattr(mod, name, None)
        if not callable(fn):
            continue
        try:
            params = inspect.signature(fn).parameters
            kwargs = {"as_of": as_of} if "as_of" in params else {}
            res = fn(address_id, **kwargs)
        except Exception:
            continue
        if isinstance(res, dict):
            res = (
                res.get("lookups") or res.get("results") or res.get(address_id) or res.get("rules")
            )
        if isinstance(res, list) and all(isinstance(x, dict) and "team_rule_id" in x for x in res):
            return res
    return None


def engine_name() -> str:
    if not (OUTPUT / "rules.json").exists():
        return "precomputed"
    mod = _live_api()
    if mod is not None and any(
        callable(getattr(mod, n, None))
        for n in ("lookup_address", "lookup", "evaluate_address", "rules_for_address")
    ):
        return "live"
    return "precomputed"


# ============================================================= evaluation ==
def adjust_for_date(entries: list[dict], as_of: str) -> list[dict]:
    """Shift precomputed results (computed at STORE.base_as_of) to another as-of date using effective dates."""
    out = []
    for e in entries:
        r = STORE.rules.get(e["team_rule_id"])
        if not r:
            continue
        e = dict(e)
        eff = _norm_date(r.get("effective_date"))
        if r.get("status") == "pending" or e["result"] == "pending":
            e["result"] = "pending"
        elif eff and as_of < eff:
            if e["result"] != "not_yet_effective":
                e["explanation"] = f"Enacted, but takes effect on {eff} (after {as_of}). " + (
                    e.get("explanation") or ""
                )
            e["result"] = "not_yet_effective"
        elif e["result"] == "not_yet_effective" and eff and as_of >= eff:
            e["result"] = "applies"
            e["explanation"] = f"In effect since {eff}. " + re.sub(
                r"^(Enacted[^.]*\.|Not yet effective[^.]*\.)\s*", "", e.get("explanation") or ""
            )
        out.append(e)
    # a superseded rule only stays superseded if the overriding rule is in force on as_of
    active = {x["team_rule_id"] for x in out if x["result"] in ("applies", "unknown")}
    for e in out:
        if e["result"] == "superseded":
            by = overriders(e["team_rule_id"], {x["team_rule_id"] for x in out})
            if by and not (set(by) & active):
                e["result"] = "applies"
                e["explanation"] = (
                    f"The stricter local rule is not in effect on {as_of}, so this rule governs. "
                    + (e.get("explanation") or "")
                )
    return out


def overriders(rule_id: str, present: set[str]) -> list[str]:
    """Rules at this address that override rule_id (either direction of the 'overrides' field)."""
    res = []
    r = STORE.rules.get(rule_id, {})
    for oid in present:
        o = STORE.rules.get(oid, {})
        if oid != rule_id and rule_id in (o.get("overrides") or []) and o.get("level") == "city":
            res.append(oid)
    # rule_id's own overrides list may name the rule it yields to
    if r.get("level") == "state":
        for oid in r.get("overrides") or []:
            if (
                oid in present
                and STORE.rules.get(oid, {}).get("level") == "city"
                and oid not in res
            ):
                res.append(oid)
    return res


def evaluate(address_id: str, as_of: str) -> tuple[list[dict], str]:
    live = _call_live(address_id, as_of)
    if live is not None:
        return live, "live"
    base = STORE.lookups.get(address_id, [])
    if as_of == STORE.base_as_of:
        return base, "precomputed"
    return adjust_for_date(base, as_of), "precomputed+as_of"


MISSING_HINTS = [
    (
        r"certificate|year built|building age|construct|built",
        "Year built / certificate-of-occupancy date",
    ),
    (r"owner|landlord type|natural person|corporat", "Owner type"),
    (r"unit count|number of units|units", "Number of units"),
    (r"exempt|filing|registration", "Exemption filing / registration status"),
    (r"tenan(cy|t) (length|duration)|12 months", "Length of tenancy"),
]


def missing_fact(expl: str) -> str:
    for pat, label in MISSING_HINTS:
        if re.search(pat, expl or "", re.I):
            return label
    return "A fact not contained in the public data"


def rule_view(r: dict, lang: str) -> dict:
    v = STORE.verify(r)
    src = STORE.doc_meta(r.get("quoted_span_doc_id") or r.get("source_doc_id"))
    if r.get("retrieved_at") and not src.get("retrieved_at"):
        src["retrieved_at"] = r["retrieved_at"]
    return {
        **r,
        "source_verification": r.get("verification")
        if isinstance(r.get("verification"), str)
        else None,
        "span_doc_id": r.get("quoted_span_doc_id") or r.get("source_doc_id"),
        "effective_date_norm": _norm_date(r.get("effective_date")),
        "category_label": CAT_LABEL.get(r.get("category"), r.get("category")),
        "requirement_display": STORE.t(r.get("requirement"), lang),
        "title_display": STORE.t(r.get("title"), lang),
        "key_value_display": STORE.t(r.get("key_value"), lang)
        if isinstance(r.get("key_value"), str)
        else r.get("key_value"),
        "conflict_note_display": STORE.t(r.get("conflict_note"), lang),
        "interaction_display": STORE.t(r.get("interaction"), lang),
        "translated": lang != "en" and STORE.has_t(r.get("requirement"), lang),
        "quote_check": v,
        "source": src,
        "addresses_count": STORE.rule_addr_counts.get(r["team_rule_id"], 0),
        "low_confidence": (r.get("confidence") is not None and r.get("confidence") < 0.7),
    }


def address_facts(a: dict) -> dict:
    def val(k):
        v = (a.get(k) or "").strip()
        return v or None

    facts = {
        "address_id": a["address_id"],
        "street_address": a["street_address"],
        "postal_city": a["postal_city"],
        "state": a["state"],
        "zip": val("zip"),
        "year_built": val("year_built"),
        "units": val("units"),
        "use_code": val("use_code"),
        "use_description": val("use_description"),
        "source_dataset": a.get("source_dataset"),
        "retrieved_at": a.get("retrieved_at"),
    }
    facts["missing"] = [k for k in ("year_built", "units", "zip") if not facts[k]]
    return facts


def jurisdiction(a: dict) -> dict:
    st = a.get("resolved_state") or a["state"]
    city = a.get("resolved_city") or ""
    county = a.get("county") or ""
    stack = [{"level": "state", "name": STATE_NAMES.get(st, st), "code": st, "jurisdiction": st}]
    if county:
        if city == "San Francisco":
            stack.append(
                {
                    "level": "county",
                    "name": "City & County of San Francisco",
                    "note": "consolidated city-county",
                }
            )
        else:
            stack.append(
                {"level": "county", "name": county, "note": "no county-level rules in scope"}
            )
    if city:
        stack.append(
            {
                "level": "city",
                "name": city if city != "San Francisco" else "San Francisco",
                "jurisdiction": f"{city}, {st}",
            }
        )
    else:
        stack.append(
            {
                "level": "city",
                "name": a.get("census_place") or "Unincorporated area",
                "jurisdiction": None,
                "note": "outside the cities in scope: no city rules",
            }
        )
    try:
        conf = float(a.get("resolution_confidence") or 0)
    except ValueError:
        conf = 0
    return {
        "stack": stack,
        "state": st,
        "city": city,
        "county": county,
        "census_place": a.get("census_place"),
        "method": a.get("resolution_method", "postal_city"),
        "confidence": conf,
        "note": a.get("resolution_note", ""),
        "lat": a.get("lat"),
        "lon": a.get("lon"),
        "matched_address": a.get("matched_address"),
        "postal_differs": bool(city) and city != a["postal_city"],
    }


def build_address(address_id: str, as_of: str, lang: str) -> dict:
    a = STORE.addresses.get(address_id)
    if not a:
        raise HTTPException(404, f"Unknown address {address_id}")
    entries, engine = evaluate(address_id, as_of)
    present = {e["team_rule_id"] for e in entries}
    jur = jurisdiction(a)
    stack_j = {s.get("jurisdiction") for s in jur["stack"] if s.get("jurisdiction")}
    cats = []
    counts = Counter()
    for cid, label, question in CATEGORIES:
        enacted, pending, notlaw = [], [], []
        for e in entries:
            r = STORE.rules.get(e["team_rule_id"])
            if not r or r.get("category") != cid:
                continue
            counts[e["result"]] += 1
            item = {
                "result": e["result"],
                "explanation": STORE.t(e.get("explanation"), lang),
                "explanation_en": e.get("explanation"),
                "conflict_flag": bool(e.get("conflict_flag") or r.get("conflict_flag")),
                "rule": rule_view(r, lang),
            }
            if e["result"] == "superseded":
                by = overriders(r["team_rule_id"], present)
                item["superseded_by"] = [
                    {
                        "id": b,
                        "title": STORE.rules[b].get("title"),
                        "jurisdiction": STORE.rules[b].get("jurisdiction"),
                    }
                    for b in by
                ]
            if r.get("level") == "city":
                yields = [o for o in (r.get("overrides") or []) if o in present]
                if yields:
                    item["overrides_here"] = [
                        {
                            "id": o,
                            "title": STORE.rules[o].get("title"),
                            "jurisdiction": STORE.rules[o].get("jurisdiction"),
                        }
                        for o in yields
                    ]
            if e["result"] == "unknown":
                item["missing_fact"] = missing_fact(e.get("explanation", ""))
            (pending if e["result"] == "pending" else enacted).append(item)
        # failed proposals in this address's jurisdictions: show as "not law"
        for r in STORE.rules.values():
            if (
                r.get("category") == cid
                and r.get("status") == "failed"
                and r.get("jurisdiction") in stack_j
                and r["team_rule_id"] not in present
            ):
                notlaw.append(
                    {
                        "result": "failed",
                        "explanation": STORE.t(
                            "Proposal failed or was withdrawn. It is not law and does not apply.",
                            lang,
                        ),
                        "conflict_flag": False,
                        "rule": rule_view(r, lang),
                    }
                )
        order = {"applies": 0, "unknown": 1, "superseded": 2, "not_yet_effective": 3}
        enacted.sort(key=lambda x: (order.get(x["result"], 9), x["rule"].get("level") != "city"))
        findings = [
            {
                **f,
                "source": STORE.doc_meta(f.get("quoted_span_doc_id") or f.get("source_doc_id")),
                "quote_check": STORE.verify(f),
                "finding_display": STORE.t(f.get("finding"), lang),
            }
            for f in STORE.no_rule
            if f.get("category") == cid and f.get("jurisdiction") in stack_j
        ]
        cats.append(
            {
                "id": cid,
                "label": label,
                "question": question,
                "enacted": enacted,
                "pending": pending,
                "not_law": notlaw,
                "no_rule": not enacted,
                "no_rule_findings": findings,
            }
        )
    return {
        "as_of": as_of,
        "engine": engine,
        "lang": lang,
        "address": address_facts(a),
        "jurisdiction": jur,
        "categories": cats,
        "summary": dict(counts),
        "conflicts": sum(
            1 for c in cats for i in c["enacted"] + c["pending"] if i["conflict_flag"]
        ),
        "data_kind": STORE.sources.get("lookups.json", {}).get("kind"),
    }


# ============================================================ change tests ==
def rules_for_test(t: dict) -> list[str]:
    """Map the answer-key ids in a change test to our team_rule_ids."""
    ch = STORE.changes.get(t["test_id"], {})
    if ch.get("rule_mapping"):
        ids = [x for v in ch["rule_mapping"].values() for x in v if x in STORE.rules]
        if ids or t.get("type") == "negative":
            return list(dict.fromkeys(ids))
    if ch.get("rule_ids"):
        return [x for x in ch["rule_ids"] if x in STORE.rules]
    out = []
    for kid in t.get("rule_ids", []):
        if kid in STORE.rules:
            out.append(kid)
            continue
        parts = kid.split("-")
        jur = JUR_CODES.get(parts[0])
        cat = CAT_CODES.get(parts[1]) if len(parts) > 1 else None
        pend = len(parts) > 2 and parts[2].startswith("P")
        for r in STORE.rules.values():
            if r.get("jurisdiction") == jur and r.get("category") == cat:
                is_prop = r.get("status") in ("pending", "failed")
                if is_prop == pend and r["team_rule_id"] not in out:
                    out.append(r["team_rule_id"])
    return out


def result_counts(rule_ids: list[str], as_of: str) -> dict:
    res: dict[str, Counter] = {rid: Counter() for rid in rule_ids}
    for entries in STORE.lookups.values():
        adj = (
            entries
            if as_of == STORE.base_as_of
            else adjust_for_date([e for e in entries if e["team_rule_id"] in res], as_of)
        )
        for e in adj:
            if e["team_rule_id"] in res:
                res[e["team_rule_id"]][e["result"]] += 1
    return {k: dict(v) for k, v in res.items()}


def city_breakdown(ids: list[str]) -> dict:
    c = Counter()
    for i in ids:
        a = STORE.addresses.get(i)
        if a:
            c[a.get("resolved_city") or a["postal_city"]] += 1
    return dict(
        sorted(c.items(), key=lambda kv: CITY_ORDER.index(kv[0]) if kv[0] in CITY_ORDER else 99)
    )


def build_change(t: dict, lang: str) -> dict:
    ch = STORE.changes.get(t["test_id"], {})
    rids = rules_for_test(t)
    before = t.get("as_of_before") or t.get("as_of") or STORE.base_as_of
    after = t.get("as_of_after") or t.get("as_of") or STORE.base_as_of
    affected = ch.get("affected_address_ids", [])
    conflicts = ch.get("conflict_flag_address_ids", [])
    return {
        **t,
        "our_rule_ids": rids,
        "rules": [rule_view(STORE.rules[r], lang) for r in rids],
        "before_date": before,
        "after_date": after,
        "before": result_counts(rids, before),
        "after": result_counts(rids, after),
        "affected_address_ids": affected,
        "affected_count": len(affected),
        "affected_by_city": city_breakdown(affected),
        "conflict_flag_address_ids": conflicts,
        "conflict_by_city": city_breakdown(conflicts),
        "notes": ch.get("notes"),
        "in_changes_json": t["test_id"] in STORE.changes,
    }


# ===================================================================== app ==
app = FastAPI(
    title="Rental Housing Law Navigator",
    version="0.1",
    description="Address-level rental housing rules with citations. Not legal advice.",
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.include_router(any_address_router)  # POST /api/resolve, /api/evaluate: any address (#39)


@app.middleware("http")
async def reload_mw(request, call_next):
    path = request.url.path
    if path.startswith("/api"):
        STORE.maybe_reload()
    resp = await call_next(request)
    if path.startswith("/api"):
        resp.headers["X-Not-Legal-Advice"] = "Information about public law only; not legal advice."
        resp.headers["Cache-Control"] = "no-store"
    elif path.startswith("/static/"):
        # Immutable only when the URL carries the current content hash; otherwise revalidate.
        v = request.query_params.get("v")
        f = STATIC / path.removeprefix("/static/")
        ok = v and resp.status_code == 200 and f.is_file() and v == asset_hash(f)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable" if ok else "no-cache"
    else:
        resp.headers["Cache-Control"] = "no-store"
    return resp


_HASHES: dict[Path, tuple[float, str]] = {}


def asset_hash(f: Path) -> str:
    """sha1 of the file content (10 chars), cached per mtime."""
    m = f.stat().st_mtime
    hit = _HASHES.get(f)
    if not hit or hit[0] != m:
        hit = (m, hashlib.sha1(f.read_bytes()).hexdigest()[:10])
        _HASHES[f] = hit
    return hit[1]


def _as_of(v: str | None) -> str:
    v = v or DEFAULT_AS_OF
    try:
        dt.date.fromisoformat(v)
    except ValueError:
        raise HTTPException(400, "as_of must be YYYY-MM-DD") from None
    return v


@app.get("/api/meta")
def meta():
    rules = list(STORE.rules.values())
    return {
        "default_as_of": DEFAULT_AS_OF,
        "base_as_of": STORE.base_as_of,
        "engine": engine_name(),
        "sources": STORE.sources,
        "counts": {
            "rules": len(rules),
            "addresses": len(STORE.addresses),
            "documents": len(STORE.manifest),
            "by_status": dict(Counter(r.get("status") for r in rules)),
            "conflicts": sum(1 for r in rules if r.get("conflict_flag")),
            "cities": dict(
                Counter(a.get("resolved_city") or "(outside)" for a in STORE.addresses.values())
            ),
        },
        "languages": ["en"] + sorted(STORE.tr),
        "categories": [{"id": c, "label": l, "question": q} for c, l, q in CATEGORIES],
        "disclaimer": "Not legal advice. This tool summarises public law from a fixed corpus for information only. "
        "Check the cited source and, for your situation, a tenant organisation, housing agency or attorney.",
    }


@app.get("/api/addresses")
def addresses():
    return [
        {
            "id": a["address_id"],
            "street": a["street_address"],
            "postal_city": a["postal_city"],
            "city": a.get("resolved_city") or "",
            "state": a["state"],
            "zip": a.get("zip", ""),
            "year_built": a.get("year_built", ""),
            "units": a.get("units", ""),
        }
        for a in STORE.addresses.values()
    ]


@app.get("/api/extensions")
def extensions():
    """Jurisdictions added live with `navigator extend` (docs/NEW_JURISDICTION.md); separate from the main 500."""
    api = _live_api()
    return api.extensions() if api and hasattr(api, "extensions") else []


@app.get("/api/extension/{slug}/address/{address_id}")
def extension_address(slug: str, address_id: str, as_of: str | None = None):
    api = _live_api()
    try:
        return api.extension_lookup(slug, address_id.upper(), _as_of(as_of))
    except (AttributeError, FileNotFoundError, KeyError):
        raise HTTPException(404, f"no extension address {slug}/{address_id}") from None


@app.get("/api/address/{address_id}")
def address(address_id: str, as_of: str | None = None, lang: str = "en"):
    return build_address(address_id.upper(), _as_of(as_of), lang)


@app.get("/api/rules")
def rules(lang: str = "en"):
    return [
        rule_view(r, lang)
        for r in sorted(
            STORE.rules.values(),
            key=lambda r: (
                JUR_ORDER.index(r["jurisdiction"]) if r.get("jurisdiction") in JUR_ORDER else 99,
                [c for c, _, _ in CATEGORIES].index(r["category"])
                if r.get("category") in CAT_LABEL
                else 9,
                r["team_rule_id"],
            ),
        )
    ]


@app.get("/api/rules/{rule_id}")
def rule(rule_id: str, lang: str = "en"):
    r = STORE.rules.get(rule_id)
    if not r:
        raise HTTPException(404, "unknown rule")
    results = Counter(
        e["result"] for v in STORE.lookups.values() for e in v if e["team_rule_id"] == rule_id
    )
    return {**rule_view(r, lang), "results": dict(results)}


@app.get("/api/coverage")
def coverage():
    cells = defaultdict(lambda: defaultdict(list))
    for r in STORE.rules.values():
        cells[r.get("jurisdiction")][r.get("category")].append(
            {"id": r["team_rule_id"], "status": r.get("status"), "title": r.get("title")}
        )
    no_rule = STORE.no_rule
    nr_cells = defaultdict(dict)
    for f in no_rule:
        nr_cells[f.get("jurisdiction")][f.get("category")] = {
            "id": f.get("finding_id"),
            "finding": f.get("finding"),
            "citation": f.get("citation"),
        }
    jurs = [j for j in JUR_ORDER] + [j for j in cells if j not in JUR_ORDER]
    return {
        "jurisdictions": jurs,
        "categories": [{"id": c, "label": l} for c, l, _ in CATEGORIES],
        "cells": {j: {c: cells[j][c] for c, _, _ in CATEGORIES} for j in jurs},
        "no_rule_findings": no_rule,
        "no_rule_cells": {j: nr_cells.get(j, {}) for j in jurs},
    }


@app.get("/api/changes")
def changes(lang: str = "en"):
    return [build_change(t, lang) for t in STORE.tests]


@app.get("/api/timeline")
def timeline():
    ev = []
    for r in STORE.rules.values():
        d = _norm_date(r.get("effective_date"))
        if d and r.get("status") in ("in_force", "not_yet_effective"):
            ev.append(
                {
                    "date": d,
                    "id": r["team_rule_id"],
                    "title": r.get("title"),
                    "jurisdiction": r.get("jurisdiction"),
                    "category": r.get("category"),
                    "status": r.get("status"),
                    "addresses": STORE.rule_addr_counts.get(r["team_rule_id"], 0),
                }
            )
    return sorted(ev, key=lambda e: e["date"])


@app.get("/api/snapshot")
def snapshot(as_of: str | None = None):
    """Per-rule result counts across all sample addresses on a date (for the timeline slider)."""
    d = _as_of(as_of)
    return {"as_of": d, "rules": result_counts(list(STORE.rules), d)}


@app.get("/api/audit")
def audit(limit: int = Query(300, le=5000), q: str = ""):
    docs = []
    rules_by_doc = Counter(r.get("source_doc_id") for r in STORE.rules.values())
    for did, m in STORE.manifest.items():
        docs.append(
            {
                **m,
                "rules_extracted": rules_by_doc.get(did, 0),
                "text_available": STORE.doc_text(did) is not None,
            }
        )
    entries = list(enumerate(STORE.audit))
    if q:
        ql = q.lower()
        entries = [(i, e) for i, e in entries if ql in json.dumps(e).lower()]
    ver = Counter(STORE.verify(r)["status"] for r in STORE.rules.values())
    ver_src = Counter(
        r.get("verification")
        for r in STORE.rules.values()
        if isinstance(r.get("verification"), str)
    )
    geo = Counter(a.get("resolution_method", "") for a in STORE.addresses.values())
    return {
        "sources": STORE.sources,
        "documents": docs,
        "audit_total": len(STORE.audit),
        "audit": [audit_summary(i, e) for i, e in entries[-limit:][::-1]],
        "verification": dict(ver),
        "source_verification": dict(ver_src),
        "geocoding": dict(geo),
        "geocoding_notes": [
            {
                "id": a["address_id"],
                "street": a["street_address"],
                "postal_city": a["postal_city"],
                "city": a.get("resolved_city"),
                "method": a.get("resolution_method"),
                "confidence": a.get("resolution_confidence"),
                "note": a.get("resolution_note"),
            }
            for a in STORE.addresses.values()
            if a.get("resolution_method") != "census_batch"
            or (a.get("resolved_city") != a["postal_city"])
        ],
    }


def audit_summary(i: int, e: dict) -> dict:
    """Compact view of one audit entry (raw model output is fetched on demand)."""
    out = {"idx": i}
    for k, v in e.items():
        if k == "raw_output":
            try:
                parsed = json.loads(v) if isinstance(v, str) else v
                out["n_rules"] = len(parsed.get("rules", [])) if isinstance(parsed, dict) else None
                if isinstance(parsed, dict) and parsed.get("doc_summary"):
                    out["doc_summary"] = str(parsed["doc_summary"])[:240]
            except (json.JSONDecodeError, AttributeError):
                out["n_rules"] = None
            out["raw_chars"] = len(v) if isinstance(v, str) else None
        elif k == "validation" and isinstance(v, list):
            out["validation_items"] = len(v)
        elif isinstance(v, (dict, list)):
            sv = json.dumps(v, ensure_ascii=False)
            out[k] = sv if len(sv) <= 160 else sv[:157] + "..."
        else:
            sv = str(v)
            out[k] = v if len(sv) <= 160 else sv[:157] + "..."
    return out


@app.get("/api/audit/entry/{idx}")
def audit_entry(idx: int):
    if not 0 <= idx < len(STORE.audit):
        raise HTTPException(404, "no such audit entry")
    return STORE.audit[idx]


@app.get("/api/source/{doc_id}")
def source(doc_id: str, rule_id: str | None = None):
    txt = STORE.doc_text(doc_id)
    if txt is None:
        raise HTTPException(404, "no text for this document (link-only source)")
    hl = None
    if rule_id and rule_id in STORE.rules:
        span = STORE.rules[rule_id].get("quoted_span") or ""
        i = txt.find(span)
        if i >= 0:
            hl = [i, i + len(span)]
    return {"doc_id": doc_id, "meta": STORE.doc_meta(doc_id), "text": txt, "highlight": hl}


@app.get("/api/i18n/{lang}")
def i18n(lang: str):
    p = STATIC / "i18n" / f"{lang}.json"
    if not p.exists():
        return {}
    return JSONResponse(json.loads(p.read_text()))


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "rules": len(STORE.rules),
        "lookups": len(STORE.lookups),
        "engine": engine_name(),
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    """Serve the shell with content-hashed asset URLs, so CDN caches never mix old and new files."""
    html = (STATIC / "index.html").read_text()

    def versioned(m: re.Match) -> str:
        rel = m.group(1)
        f = STATIC / rel
        return f"/static/{rel}?v={asset_hash(f)}" if f.is_file() else m.group(0)

    # every /static/*.css|js reference, with or without an old ?v= (fonts keep plain URLs so the
    # <link rel=preload> matches the url() in app.css; font files never change under the same name)
    html = re.sub(r"/static/([\w./-]+?\.(?:css|js))(?:\?v=[\w.-]+)?(?=[\"'])", versioned, html)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
