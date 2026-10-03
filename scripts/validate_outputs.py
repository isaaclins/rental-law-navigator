#!/usr/bin/env python3
"""Validate the submission files in output/ against the starter pack contract.

Checks
  rules.json    every record validates against starter/schema/rule_record.schema.json,
                team_rule_ids are unique, and every quoted_span appears verbatim
                (whitespace-normalized) in the text of its source document.
  lookups.json  {"as_of", "lookups"} covering every address in starter/data/sample_addresses.csv,
                valid result values, explanation + conflict_flag on every entry, and every
                team_rule_id present in rules.json.
  changes.json  one entry per change test in starter/dev/change_tests.json with
                affected_address_ids, optional conflict_flag_address_ids and notes; all ids known.

Files that do not exist yet are skipped (exit 0) unless --require is given.

Usage
  uv run --no-project --with jsonschema python scripts/validate_outputs.py [--output-dir output] [--require]

Dependencies: Python 3.10+ standard library and jsonschema. Not legal advice.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - guidance for local runs
    sys.exit("jsonschema is required: pip install jsonschema  (or: uv run --with jsonschema ...)")

ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "starter"
SCHEMA = STARTER / "schema" / "rule_record.schema.json"
ADDRESSES = STARTER / "data" / "sample_addresses.csv"
CHANGE_TESTS = STARTER / "dev" / "change_tests.json"
# Where source document text may live: the starter corpus first, then fetched link-only
# sources and newly ingested documents (if the pipeline produces them).
TEXT_DIRS = [
    STARTER / "corpus" / "text",
    ROOT / "supplementary" / "text",
    ROOT / "new_docs" / "text",
    ROOT / "new_docs",
]
RESULTS = {"applies", "unknown", "superseded", "not_yet_effective", "pending"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_REPORTED = 25  # per check, to keep logs readable

# Typographic characters that commonly differ between a PDF/HTML capture and a copied quote.
_TRANSLATE = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        " ": " ",
        "…": "...",
    }
)
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Collapse all whitespace runs to one space and unify typographic quotes and dashes."""
    return _WS.sub(" ", text.translate(_TRANSLATE)).strip()


class Report:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.summary: list[tuple[str, str, str]] = []
        self.in_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    def error(self, file: str, msg: str) -> None:
        self.errors.append((file, msg))

    def errors_for(self, file: str) -> list[str]:
        return [m for f, m in self.errors if f == file]

    def row(self, file: str, status: str, detail: str) -> None:
        self.summary.append((file, status, detail))
        print(f"[{status}] {file}: {detail}")
        for msg in self.errors_for(file)[:MAX_REPORTED]:
            print(f"    - {msg}")
            if self.in_actions:
                print(f"::error file=output/{file}::{msg}")
        extra = len(self.errors_for(file)) - MAX_REPORTED
        if extra > 0:
            print(f"    ... and {extra} more")

    def write_step_summary(self) -> None:
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not path:
            return
        lines = ["### Output validation", "", "| File | Status | Detail |", "|---|---|---|"]
        lines += [f"| `{f}` | {s} | {d} |" for f, s, d in self.summary]
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


class DocTexts:
    """Lazy, cached access to normalized source document text by doc_id."""

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    def get(self, doc_id: str) -> str | None:
        if doc_id not in self._cache:
            text = None
            for d in TEXT_DIRS:
                p = d / f"{doc_id}.txt"
                if p.is_file():
                    text = normalize(p.read_text(encoding="utf-8"))
                    break
            self._cache[doc_id] = text
        return self._cache[doc_id]


def span_found(span: str, doc_text: str) -> bool:
    """True if the span occurs verbatim after normalization.

    An elided quote ("first part ... second part") passes when every part of at least
    20 characters occurs in the document, in order.
    """
    s = normalize(span).strip(" .")
    if s in doc_text:
        return True
    parts = [p.strip(" .") for p in s.split("...")]
    if len(parts) < 2 or not any(len(p) >= 20 for p in parts):
        return False
    pos = 0
    for part in parts:
        if not part:
            continue
        i = doc_text.find(part, pos)
        if i < 0:
            return False
        pos = i + len(part)
    return True


def load_json(path: Path, rep: Report, name: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        rep.error(name, f"cannot parse JSON: {e}")
        return None


def address_ids() -> list[str]:
    with ADDRESSES.open(encoding="utf-8", newline="") as fh:
        return [r["address_id"] for r in csv.DictReader(fh)]


def check_rules(path: Path, rep: Report) -> set[str] | None:
    name = "rules.json"
    data = load_json(path, rep, name)
    if data is None:
        rep.row(name, "FAIL", "invalid JSON")
        return None
    records = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(records, list):
        rep.error(name, 'expected a list of rule records or {"rules": [...]}')
        rep.row(name, "FAIL", "wrong top-level shape")
        return None

    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    docs = DocTexts()
    ids = Counter()
    for i, rec in enumerate(records):
        rid = rec.get("team_rule_id", f"#{i}") if isinstance(rec, dict) else f"#{i}"
        for err in sorted(validator.iter_errors(rec), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(record)"
            rep.error(name, f"{rid}: schema: {where}: {err.message}")
        if not isinstance(rec, dict):
            continue
        ids[rec.get("team_rule_id")] += 1
        span = rec.get("quoted_span")
        if not isinstance(span, str) or not span.strip():
            continue  # already reported by the schema
        # Pipelines may quote a different document than the primary source (e.g. a fetched
        # link-only page); quoted_span_doc_id names it explicitly when present.
        doc_id = rec.get("quoted_span_doc_id") or rec.get("source_doc_id")
        if not doc_id:
            rep.error(name, f"{rid}: no source_doc_id, quoted_span cannot be verified")
            continue
        text = docs.get(doc_id)
        if text is None:
            rep.error(name, f"{rid}: source document {doc_id} has no text file")
        elif not span_found(span, text):
            rep.error(name, f"{rid}: quoted_span not found verbatim in {doc_id}: {span[:80]!r}")
    for rid, n in ids.items():
        if n > 1:
            rep.error(name, f"duplicate team_rule_id {rid!r} ({n}x)")

    n_err = len(rep.errors_for(name))
    rep.row(name, "FAIL" if n_err else "PASS", f"{len(records)} records, {n_err} errors")
    return {r["team_rule_id"] for r in records if isinstance(r, dict) and "team_rule_id" in r}


def check_lookups(path: Path, rep: Report, rule_ids: set[str] | None, addrs: list[str]) -> None:
    name = "lookups.json"
    data = load_json(path, rep, name)
    if not isinstance(data, dict) or not isinstance(data.get("lookups"), dict):
        if data is not None:
            rep.error(name, 'expected {"as_of": "YYYY-MM-DD", "lookups": {address_id: [...]}}')
        rep.row(name, "FAIL", "wrong top-level shape")
        return
    as_of = data.get("as_of")
    if not (isinstance(as_of, str) and DATE_RE.match(as_of)):
        rep.error(name, f"as_of must be a YYYY-MM-DD date, got {as_of!r}")
    lookups = data["lookups"]
    missing = sorted(set(addrs) - set(lookups))
    unknown = sorted(set(lookups) - set(addrs))
    if missing:
        rep.error(name, f"{len(missing)} addresses missing, e.g. {missing[:5]}")
    if unknown:
        rep.error(name, f"{len(unknown)} unknown address ids, e.g. {unknown[:5]}")
    n_entries = 0
    for aid, entries in lookups.items():
        if not isinstance(entries, list):
            rep.error(name, f"{aid}: expected a list of entries")
            continue
        for e in entries:
            n_entries += 1
            if not isinstance(e, dict):
                rep.error(name, f"{aid}: entry is not an object")
                continue
            rid = e.get("team_rule_id")
            if not isinstance(rid, str) or not rid:
                rep.error(name, f"{aid}: entry without team_rule_id")
            elif rule_ids is not None and rid not in rule_ids:
                rep.error(name, f"{aid}: team_rule_id {rid!r} not in rules.json")
            if e.get("result") not in RESULTS:
                rep.error(name, f"{aid}/{rid}: invalid result {e.get('result')!r}")
            if not isinstance(e.get("explanation"), str) or not e["explanation"].strip():
                rep.error(name, f"{aid}/{rid}: missing explanation")
            if not isinstance(e.get("conflict_flag"), bool):
                rep.error(name, f"{aid}/{rid}: conflict_flag must be a boolean")
    n_err = len(rep.errors_for(name))
    detail = f"{len(lookups)}/{len(addrs)} addresses, {n_entries} entries, {n_err} errors"
    rep.row(name, "FAIL" if n_err else "PASS", detail)


def check_changes(path: Path, rep: Report, addrs: list[str]) -> None:
    name = "changes.json"
    data = load_json(path, rep, name)
    if not isinstance(data, dict):
        if data is not None:
            rep.error(name, "expected {test_id: {affected_address_ids, notes, ...}}")
        rep.row(name, "FAIL", "wrong top-level shape")
        return
    expected = [t["test_id"] for t in json.loads(CHANGE_TESTS.read_text(encoding="utf-8"))]
    for tid in expected:
        if tid not in data:
            rep.error(name, f"change test {tid} missing")
    known = set(addrs)
    for tid, t in data.items():
        if not isinstance(t, dict):
            rep.error(name, f"{tid}: expected an object")
            continue
        for key, required in (("affected_address_ids", True), ("conflict_flag_address_ids", False)):
            ids = t.get(key)
            if ids is None:
                if required:
                    rep.error(name, f"{tid}: {key} missing")
                continue
            if not isinstance(ids, list) or not all(isinstance(a, str) for a in ids):
                rep.error(name, f"{tid}: {key} must be a list of address ids")
                continue
            bad = sorted(set(ids) - known)
            if bad:
                rep.error(name, f"{tid}: {key} has {len(bad)} unknown ids, e.g. {bad[:5]}")
            if len(ids) != len(set(ids)):
                rep.error(name, f"{tid}: {key} contains duplicates")
        if not isinstance(t.get("notes"), str):
            rep.error(name, f"{tid}: notes must be a string")
    n_err = len(rep.errors_for(name))
    detail = f"{len(data)} tests ({', '.join(sorted(data))}), {n_err} errors"
    rep.row(name, "FAIL" if n_err else "PASS", detail)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--output-dir", default=str(ROOT / "output"), help="default: output/")
    ap.add_argument("--require", action="store_true", help="fail if an output file is missing")
    args = ap.parse_args(argv)
    out = Path(args.output_dir)

    rep = Report()
    addrs = address_ids()
    rules_path, lookups_path, changes_path = (
        out / "rules.json",
        out / "lookups.json",
        out / "changes.json",
    )

    def skip(file: str) -> None:
        if args.require:
            rep.error(file, f"{file} not found in {out}")
            rep.row(file, "FAIL", "missing")
        else:
            rep.row(file, "SKIP", "not produced yet")

    rule_ids = check_rules(rules_path, rep) if rules_path.exists() else skip("rules.json")
    if lookups_path.exists():
        check_lookups(lookups_path, rep, rule_ids, addrs)
    else:
        skip("lookups.json")
    if changes_path.exists():
        check_changes(changes_path, rep, addrs)
    else:
        skip("changes.json")

    rep.write_step_summary()
    if rep.errors:
        print(f"\nFAILED: {len(rep.errors)} error(s)")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
