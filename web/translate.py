"""Pre-generate Spanish text for the renter view (stretch goal), cached.

Collects every unique English string the UI shows from the rule data (titles,
plain-language requirements, key values, conflict notes, lookup explanations),
translates only the ones not yet cached, in batches, via the headless Claude CLI
(`claude -p --model sonnet`), and stores them in web/translations/es.json keyed by
sha1(text)[:16]. Citations, quoted source spans and rule ids are never translated:
the legal text stays in the original English.

Run:  python3 web/translate.py [--limit N]     (reruns only translate new strings)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "translations" / "es.json"
LOG = ROOT / "web" / "translations" / "es.log.jsonl"
BATCH = 50

PROMPT = """You translate short plain-language summaries of US rental housing law from English into clear, neutral US Spanish for renters (reading level: general public).
Rules:
- Keep citations, section numbers, bill numbers (e.g. AB 325, S.2983), rule ids (e.g. CA-ALG-01), dollar amounts, percentages and dates exactly as written.
- Keep official names of laws/ordinances in English, optionally followed by a short Spanish gloss in parentheses the first time.
- Do not add advice, do not soften or strengthen the meaning, do not add information.
- Return ONLY a JSON object mapping each input key to its Spanish translation. No markdown fences, no commentary.

Input JSON:
"""


def key(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def plain_expected(s: str | None) -> str:
    """Change-test 'expected' text for people: no JSON rule maps, no snake_case status tokens (#73)."""
    s = re.sub(r"Key rules -> ours: \{.*?\}\.\s*", "", s or "")
    s = re.sub(r"\b[a-z]+(?:_[a-z]+)+\b", lambda m: m.group(0).replace("_", " "), s)
    s = s.replace("not yet effective", "not yet in effect").strip()
    return s[:1].upper() + s[1:]


TEST_FILES = (
    "starter/dev/change_tests.json",
    "output/new_tests.json",
    "new_docs/change_tests.json",
)


def load(name: str):
    for d in (ROOT / "output", ROOT / "web" / "fixtures"):
        p = d / name
        if p.exists() and p.stat().st_size > 2:
            return json.loads(p.read_text())
    return None


def collect() -> list[str]:
    texts: list[str] = ["Proposal failed or was withdrawn. It is not law and does not apply."]
    rules = load("rules.json") or {"rules": []}
    for f in rules.get("no_rule_findings", []) if isinstance(rules, dict) else []:
        if f.get("finding"):
            texts.append(f["finding"])
    rules = rules["rules"] if isinstance(rules, dict) else rules
    for r in rules:
        for f in ("title", "requirement", "key_value", "conflict_note", "interaction"):
            if isinstance(r.get(f), str) and r[f].strip():
                texts.append(r[f])
    for f in TEST_FILES:  # change-test titles and expected behaviour (#74)
        if (ROOT / f).exists():
            for t in json.loads((ROOT / f).read_text()):
                texts += [t.get("title") or "", plain_expected(t.get("expected_behavior"))]
    texts = [t for t in texts if t]
    lk = load("lookups.json") or {"lookups": {}}
    for entries in lk["lookups"].values():
        for e in entries:
            if e.get("explanation"):
                texts.append(e["explanation"])
    seen, out = set(), []
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def translate_batch(items: dict[str, str]) -> dict[str, str]:
    prompt = PROMPT + json.dumps(items, ensure_ascii=False, indent=0)
    for attempt in range(3):
        try:
            res = subprocess.run(
                ["claude", "-p", "--model", "sonnet"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,
            )
            txt = res.stdout.strip()
            if txt.startswith("```"):
                txt = txt.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(txt[txt.find("{") : txt.rfind("}") + 1])
            return {k: v for k, v in data.items() if k in items and isinstance(v, str)}
        except Exception as e:  # retry on malformed output / timeouts
            print(f"  batch failed (attempt {attempt + 1}): {e}", file=sys.stderr)
            time.sleep(3)
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max new strings this run (0 = all)")
    args = ap.parse_args()
    cache: dict[str, str] = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [t for t in collect() if key(t) not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(cache)} cached, {len(todo)} to translate", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(todo), BATCH):
        chunk = todo[i : i + BATCH]
        items = {key(t): t for t in chunk}
        got = translate_batch(items)
        cache.update(got)
        OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))
        with LOG.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "model": "claude sonnet (claude -p)",
                        "requested": len(items),
                        "received": len(got),
                    }
                )
                + "\n"
            )
        print(f"  batch {i // BATCH + 1}: {len(got)}/{len(items)}", file=sys.stderr)
    print(f"done: {len(cache)} strings in {OUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
