#!/usr/bin/env python3
"""Independent QA scorer for the Rental Housing Law Navigator (Hack-Nation 7, RealPage challenge).

Mirrors the four auto-scored components of the challenge brief (75 of 100 points) against our own
hand-built oracle (qa/expected_rules.json, qa/expected_lookups.json), because the official score.py
and dev key were not shipped in the starter pack:

  Extraction accuracy  25  team rules matched to the key by jurisdiction + category + citation;
                           field accuracy on effective date, status, key value, citation
  Address coverage     20  results on the sampled addresses; a missed 'applies' costs 2x other
                           errors; 'unknown' where 'applies' is expected earns half credit
  Citations            15  share of 'applies' answers whose rule has a source and a quoted_span
                           found verbatim (whitespace-normalised) in the supplied corpus text
  Change tracking      15  overlap (Jaccard) with expected affected sets for T1-T5, plus T3 flags
                           (T6 / hour-16 data is not in the starter pack: 3 points per test T1-T5)

Usage:
  python3 qa/score.py                       # score navigator/output/{rules,lookups,changes}.json
  python3 qa/score.py --rules R --lookups L --changes C [--report qa/report.md] [--json out.json]
  python3 qa/score.py --self-test           # score a perfect submission built from the key (sanity check)

Not the official script. Not legal advice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

QA = Path(__file__).resolve().parent
ROOT = QA.parent
NAV_OUT = Path("/home/steward/hacknation/realpage/navigator/output")
CORPUS_DIR = ROOT / "starter/corpus/text"
SUPP_DIR = Path("/home/steward/hacknation/realpage/navigator/supplementary/text")

TIER_W_EXTRACT = {"core": 1.0, "probable": 0.75, "possible": 0.4}
TIER_W_ADDR = {"core": 1.0, "probable": 0.5, "possible": 1.0}
CITIES = [
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
STATE_NAMES = {
    "california": "CA",
    "new jersey": "NJ",
    "massachusetts": "MA",
    "ca": "CA",
    "nj": "NJ",
    "ma": "MA",
}
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
RESULTS = ["applies", "unknown", "superseded", "not_yet_effective", "pending"]


# ----------------------------------------------------------------------------------------- helpers
def ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def quotes(s: str) -> str:
    return s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def norm_jur(j) -> str:
    s = ws(str(j or "")).strip()
    low = s.lower()
    if low in STATE_NAMES:
        return STATE_NAMES[low]
    for c in CITIES:
        if c.lower() in low:
            return f"{c}, {CITY_STATE[c]}"
    return s


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def team_rules_list(doc):
    if isinstance(doc, list):
        return doc, []
    return doc.get("rules", []), doc.get("no_rule_findings", []) or doc.get("no_rule", []) or []


def date_ok(team, accept):
    if not accept:
        return None
    t = str(team or "")
    if not t:
        return False
    return any(
        t.startswith(a) or (len(t) >= 7 and a.startswith(t) and len(t) >= len(a) - 3)
        for a in accept
    )


def cite_ok(rule, pats):
    text = " ".join(
        [str(rule.get("citation") or "")] + [str(x) for x in (rule.get("citation_aliases") or [])]
    )
    return any(re.search(p, text, re.I) for p in pats)


def kv_ok(team_kv, pats):
    if not pats:
        return None
    if not team_kv:
        return False
    return all(re.search(p, str(team_kv), re.I) for p in pats)


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


class Corpus:
    def __init__(self, d: Path, supp: Path | None):
        self.docs = {p.stem: ws(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.txt"))}
        self.docs_q = {k: quotes(v) for k, v in self.docs.items()}
        self.supp = (
            {p.stem: ws(p.read_text(encoding="utf-8")) for p in sorted(supp.glob("*.txt"))}
            if supp and supp.exists()
            else {}
        )
        self.all = "\n".join(self.docs.values())
        self.all_q = quotes(self.all)
        self._cache = {}

    def check(self, span, doc_id=None):
        """-> 'doc' | 'corpus' | 'quotes_only' | 'supplementary_only' | 'missing' | 'short'"""
        key = (span, doc_id)
        if key in self._cache:
            return self._cache[key]
        s = ws(span or "")
        if len(s) < 20:
            res = "short"
        elif doc_id and s in self.docs.get(doc_id, ""):
            res = "doc"
        elif s in self.all:
            res = "corpus"
        elif quotes(s) in self.all_q:
            res = "quotes_only"
        elif any(s in t for t in self.supp.values()):
            res = "supplementary_only"
        else:
            res = "missing"
        self._cache[key] = res
        return res


# ----------------------------------------------------------------------------------------- extraction
def score_extraction(key, team_rules, team_nr):
    krules = key["rules"]
    by_cell = defaultdict(list)
    for i, t in enumerate(team_rules):
        by_cell[
            (norm_jur(t.get("jurisdiction")), str(t.get("category") or "").strip().lower())
        ].append(i)

    def fields(k, t):
        f = {
            "status": str(t.get("status") or "").lower() == k["status"],
            "citation": cite_ok(t, k["citation_patterns"]),
        }
        d = date_ok(t.get("effective_date"), k.get("effective_date_accept") or [])
        if d is not None:
            f["effective_date"] = d
        v = kv_ok(t.get("key_value"), k.get("key_value_patterns") or [])
        if v is not None:
            f["key_value"] = v
        return f

    pairs = []
    for ki, k in enumerate(krules):
        for ti in by_cell.get((k["jurisdiction"], k["category"]), []):
            t = team_rules[ti]
            if cite_ok(t, k["citation_patterns"]):
                f = fields(k, t)
                pairs.append((sum(f.values()) / len(f), ki, ti, f))
    pairs.sort(key=lambda x: -x[0])
    k_match, t_used = {}, {}
    for _sc, ki, ti, f in pairs:
        if ki in k_match or ti in t_used:
            continue
        k_match[ki] = (ti, f, "full")
        t_used[ti] = ki
    # partial: same cell, citation does not match
    for ki, k in enumerate(krules):
        if ki in k_match:
            continue
        cands = [
            ti for ti in by_cell.get((k["jurisdiction"], k["category"]), []) if ti not in t_used
        ]
        if cands:
            ti = cands[0]
            k_match[ki] = (ti, fields(k, team_rules[ti]), "partial")
            t_used[ti] = ki
    # duplicates: unused team rules whose citation matches an already matched key rule in the same cell
    dup_of = {}
    for ti, t in enumerate(team_rules):
        if ti in t_used:
            continue
        for ki, k in enumerate(krules):
            if (norm_jur(t.get("jurisdiction")), str(t.get("category") or "").lower()) == (
                k["jurisdiction"],
                k["category"],
            ) and cite_ok(t, k["citation_patterns"]):
                dup_of[ti] = ki
                break

    credit = total_w = 0.0
    per_rule = []
    field_tot = Counter()
    field_ok = Counter()
    for ki, k in enumerate(krules):
        w = TIER_W_EXTRACT[k["tier"]]
        total_w += w
        m = k_match.get(ki)
        if not m:
            per_rule.append({"key": k, "match": None, "kind": "missing", "credit": 0.0, "w": w})
            continue
        ti, f, kind = m
        for name, ok in f.items():
            field_tot[name] += 1
            field_ok[name] += bool(ok)
        fm = sum(f.values()) / len(f)
        c = w * (0.5 + 0.5 * fm) if kind == "full" else w * 0.25
        credit += c
        per_rule.append(
            {"key": k, "match": team_rules[ti], "kind": kind, "fields": f, "credit": c, "w": w}
        )

    # no-rule findings: violation = unmatched in_force / not_yet_effective team rule in that cell
    nr_viol, nr_found = [], []
    team_nr_cells = {
        (norm_jur(n.get("jurisdiction")), str(n.get("category") or "").lower()) for n in team_nr
    }
    for n in key["no_rule_findings"]:
        cell = (n["jurisdiction"], n["category"])
        bad = [
            team_rules[ti]
            for ti in by_cell.get(cell, [])
            if ti not in t_used
            and ti not in dup_of
            and str(team_rules[ti].get("status") or "").lower() in ("in_force", "not_yet_effective")
        ]
        if bad and n["tier"] == "core":
            nr_viol.append((n, bad))
        if cell in team_nr_cells:
            nr_found.append(n)
    extras = [
        team_rules[ti] for ti in range(len(team_rules)) if ti not in t_used and ti not in dup_of
    ]
    matched_team = len(t_used) + len(dup_of)
    precision = matched_team / max(1, matched_team + len(extras) + len(nr_viol))
    recall = credit / total_w if total_w else 0
    pts = 25 * (0.85 * recall + 0.15 * precision)
    core = [r for r in per_rule if r["key"]["tier"] == "core"]
    return {
        "points": pts,
        "recall_credit": recall,
        "precision": precision,
        "core_found": sum(1 for r in core if r["kind"] == "full"),
        "core_total": len(core),
        "all_found": sum(1 for r in per_rule if r["kind"] == "full"),
        "all_total": len(per_rule),
        "field_acc": {k: (field_ok[k], field_tot[k]) for k in field_tot},
        "per_rule": per_rule,
        "extras": extras,
        "nr_violations": nr_viol,
        "nr_found": nr_found,
        "team_to_key": {**{ti: ki for ti, ki in t_used.items()}, **dup_of},
    }


# ----------------------------------------------------------------------------------------- addresses
def score_addresses(key, exp, team_rules, team_lookups, ext):
    krules = key["rules"]
    kid_of_team = {}
    for ti, ki in ext["team_to_key"].items():
        tid = team_rules[ti].get("team_rule_id")
        if tid:
            kid_of_team[tid] = krules[ki]["key_rule_id"]
    tier = {k["key_rule_id"]: k["tier"] for k in krules}
    lk = team_lookups.get("lookups", team_lookups) if isinstance(team_lookups, dict) else {}
    earned = possible = 0.0
    rows, unmapped = [], Counter()
    stats = Counter()
    for aid, a in exp["lookups"].items():
        entries = lk.get(aid)
        if entries is None:
            stats["addresses_missing"] += 1
            entries = []
        team = defaultdict(list)
        for e in entries:
            k = kid_of_team.get(e.get("team_rule_id"))
            if k:
                team[k].append(str(e.get("result") or "").lower())
            else:
                unmapped[e.get("team_rule_id")] += 1
        for kid, x in a["expected"].items():
            vals = team.get(kid, [])
            acc = x["accept"]
            t = next((v for v in vals if v in acc), vals[0] if vals else None)
            w_t = TIER_W_ADDR[tier.get(kid, "core")]
            if x["optional"]:
                if t is None:
                    continue
                ok = t in acc
                earned += w_t * ok
                possible += w_t
                if not ok:
                    rows.append((aid, a, kid, x, t, "wrong (optional rule)", w_t))
                continue
            w = (2.0 if x["expected"] == "applies" else 1.0) * w_t
            if t in acc and not (t is None and x["expected"] is not None and None not in acc):
                if x["expected"] is None and t is None:
                    continue  # correctly omitted; no points at stake
                earned += w
                possible += w
                stats["correct"] += 1
            elif x["expected"] is None:
                possible += w_t
                stats["false_positive"] += 1
                rows.append((aid, a, kid, x, t, "false positive (should be omitted)", w_t))
            elif x["expected"] == "applies" and t == "unknown":
                earned += 0.5 * w
                possible += w
                stats["unknown_for_applies"] += 1
                rows.append((aid, a, kid, x, t, "unknown (half credit)", 0.5 * w))
            elif t is None:
                possible += w
                stats["missed_applies" if x["expected"] == "applies" else "missed_other"] += 1
                rows.append(
                    (aid, a, kid, x, t, "MISSED" if x["expected"] == "applies" else "missing", w)
                )
            else:
                possible += w
                stats["wrong_result"] += 1
                rows.append((aid, a, kid, x, t, "wrong result", w))
        for kid, vals in team.items():
            if kid not in a["expected"]:
                w_t = TIER_W_ADDR[tier.get(kid, "core")]
                possible += w_t
                stats["false_positive"] += 1
                rows.append(
                    (
                        aid,
                        a,
                        kid,
                        None,
                        vals[0],
                        "false positive (rule does not cover this address)",
                        w_t,
                    )
                )
    pts = 20 * earned / possible if possible else 0.0
    return {
        "points": pts,
        "earned": earned,
        "possible": possible,
        "rows": rows,
        "stats": stats,
        "unmapped": unmapped,
        "n_addr": len(exp["lookups"]),
        "team_addr_count": len(lk),
    }


def full_audit(key, team_rules, team_lookups, ext):
    """Unscored: apply the oracle logic to all 500 addresses and count disagreements per key rule."""
    sys.path.insert(0, str(QA))
    import csv

    import build_expected_lookups as B

    tiers = B.load_tiers()
    resolved = (
        {r["address_id"]: r for r in csv.DictReader(open(B.RESOLVED))}
        if B.RESOLVED.exists()
        else {}
    )
    kid_of_team = {
        team_rules[ti].get("team_rule_id"): key["rules"][ki]["key_rule_id"]
        for ti, ki in ext["team_to_key"].items()
    }
    lk = team_lookups.get("lookups", team_lookups) if isinstance(team_lookups, dict) else {}
    out = defaultdict(Counter)
    examples = defaultdict(list)
    n = 0
    for r in csv.DictReader(open(B.SAMPLE)):
        city = B.city_of(r, resolved)
        if city not in B.STATE_OF:
            continue
        n += 1
        exp = B.apply_tiers(B.expected_for(r, city), tiers)
        team = defaultdict(list)
        for e in lk.get(r["address_id"], []) or []:
            k = kid_of_team.get(e.get("team_rule_id"))
            if k:
                team[k].append(str(e.get("result") or "").lower())
        for kid, x in exp.items():
            vals = team.get(kid, [])
            t = next((v for v in vals if v in x["accept"]), vals[0] if vals else None)
            if t in x["accept"] or (x["optional"] and t is None):
                continue
            label = f"expected {x['expected'] or 'omit'}, team {t or 'omitted'}"
            out[kid][label] += 1
            if len(examples[(kid, label)]) < 4:
                examples[(kid, label)].append(
                    f"{r['address_id']} ({city}, built {r['year_built'] or '-'}, units {r['units'] or '-'})"
                )
        for kid, vals in team.items():
            if kid not in exp:
                label = f"reported ({vals[0]}) where the rule does not cover the address"
                out[kid][label] += 1
                if len(examples[(kid, label)]) < 4:
                    examples[(kid, label)].append(f"{r['address_id']} ({city})")
    return {
        "n": n,
        "by_rule": out,
        "examples": examples,
        "total": sum(sum(c.values()) for c in out.values()),
    }


# ----------------------------------------------------------------------------------------- citations
def score_citations(team_rules, team_lookups, corpus):
    by_id = {r.get("team_rule_id"): r for r in team_rules}
    lk = team_lookups.get("lookups", team_lookups) if isinstance(team_lookups, dict) else {}
    tot = ok = 0
    reasons = Counter()
    per_rule = defaultdict(lambda: [0, 0, ""])
    for _aid, entries in lk.items():
        for e in entries or []:
            if str(e.get("result") or "").lower() != "applies":
                continue
            tot += 1
            tid = e.get("team_rule_id")
            r = by_id.get(tid)
            if not r:
                res = "rule_not_in_rules_json"
            elif not (r.get("source_doc_id") or r.get("source_url")):
                res = "no_source"
            else:
                res = corpus.check(
                    r.get("quoted_span"), r.get("quoted_span_doc_id") or r.get("source_doc_id")
                )
            good = res in ("doc", "corpus")
            ok += good
            reasons[res] += 1
            pr = per_rule[tid]
            pr[0] += 1
            pr[1] += good
            pr[2] = res
    rule_checks = Counter()
    bad_rules = []
    for r in team_rules:
        res = corpus.check(
            r.get("quoted_span"), r.get("quoted_span_doc_id") or r.get("source_doc_id")
        )
        rule_checks[res] += 1
        if res not in ("doc", "corpus"):
            bad_rules.append((r, res))
    share = ok / tot if tot else 0.0
    return {
        "points": 15 * share,
        "ok": ok,
        "total": tot,
        "reasons": reasons,
        "per_rule": per_rule,
        "rule_checks": rule_checks,
        "bad_rules": bad_rules,
    }


# ----------------------------------------------------------------------------------------- changes
def score_changes(exp, team_changes):
    out = {}
    for tid in ["T1", "T2", "T3", "T4", "T5"]:
        e = exp["changes"][tid]
        t = (team_changes or {}).get(tid) or {}
        aff = t.get("affected_address_ids") or []
        j = jaccard(e["affected"], aff)
        row = {
            "jaccard": j,
            "team_n": len(set(aff)),
            "exp_n": len(e["affected"]),
            "missing": sorted(set(e["affected"]) - set(aff)),
            "extra": sorted(set(aff) - set(e["affected"])),
            "present": bool(t),
        }
        if tid == "T3":
            fl = t.get("conflict_flag_address_ids") or []
            jf = jaccard(e["conflict_flags"], fl)
            row.update(
                flag_jaccard=jf,
                flag_team_n=len(set(fl)),
                flag_exp_n=len(e["conflict_flags"]),
                flag_missing=sorted(set(e["conflict_flags"]) - set(fl)),
                flag_extra=sorted(set(fl) - set(e["conflict_flags"])),
            )
            row["score"] = 0.5 * j + 0.5 * jf
        else:
            row["score"] = j
        out[tid] = row
    pts = 3 * sum(r["score"] for r in out.values())
    return {"points": pts, "tests": out, "t6": (team_changes or {}).get("T6")}


# ----------------------------------------------------------------------------------------- sanity checks
def sanity(key, team_rules, team_lookups, exp, ext):
    issues = []
    lk = team_lookups.get("lookups", team_lookups) if isinstance(team_lookups, dict) else {}
    if isinstance(team_lookups, dict) and team_lookups.get("as_of") not in (None, "2026-10-01"):
        issues.append(f"lookups.json as_of is {team_lookups.get('as_of')!r}, expected '2026-10-01'")
    if len(lk) != 500:
        issues.append(f"lookups.json covers {len(lk)} addresses (README requires all 500)")
    by_id = {r.get("team_rule_id"): r for r in team_rules}
    bar_ids = {
        team_rules[ti].get("team_rule_id")
        for ti, ki in ext["team_to_key"].items()
        if key["rules"][ki]["key_rule_id"] == "MA-RENT-01"
    }  # c.40P is a bar, not a cap
    ma_ids = set(exp["changes"]["T4"]["affected"])
    caps = Counter()
    for aid in ma_ids:
        for e in lk.get(aid, []) or []:
            r = by_id.get(e.get("team_rule_id")) or {}
            if (
                e.get("team_rule_id") not in bar_ids
                and r.get("category") == "rent_increase_limits"
                and e.get("result") in ("applies", "not_yet_effective", "pending")
            ):
                caps[e.get("team_rule_id")] += 1
    if caps:
        issues.append(
            "rent-increase rule reported for MA addresses (T5 says never report a rent cap in Boston/Cambridge): "
            + ", ".join(f"{k} x{v}" for k, v in caps.items())
        )
    bad_res = Counter(
        e.get("result") for es in lk.values() for e in (es or []) if e.get("result") not in RESULTS
    )
    if bad_res:
        issues.append(f"invalid result values: {dict(bad_res)}")
    dup = [k for k, v in Counter(r.get("team_rule_id") for r in team_rules).items() if v > 1]
    if dup:
        issues.append(f"duplicate team_rule_id in rules.json: {dup[:10]}")
    unknown_ids = Counter(
        e.get("team_rule_id")
        for es in lk.values()
        for e in (es or [])
        if e.get("team_rule_id") not in by_id
    )
    if unknown_ids:
        issues.append(
            f"lookups reference rule ids missing from rules.json: {dict(unknown_ids.most_common(8))}"
        )
    req = [
        "team_rule_id",
        "jurisdiction",
        "level",
        "category",
        "status",
        "title",
        "requirement",
        "citation",
        "source_url",
        "quoted_span",
    ]
    miss = Counter(f for r in team_rules for f in req if not r.get(f))
    if miss:
        issues.append(f"schema: required fields empty: {dict(miss)}")
    return issues


# ----------------------------------------------------------------------------------------- self-test submission
def perfect_submission(key, exp):
    rules = []
    for k in key["rules"]:
        rules.append(
            {
                "team_rule_id": k["key_rule_id"],
                "jurisdiction": k["jurisdiction"],
                "level": k["level"],
                "category": k["category"],
                "status": k["status"],
                "title": k["title"],
                "requirement": k["title"],
                "key_value": k["key_value"],
                "effective_date": (k["effective_date_accept"] or [None])[0],
                "citation": k["citation"],
                "source_doc_id": k["source_doc_id"],
                "source_url": "x",
                "quoted_span": k["quoted_span"] or "",
            }
        )
    lookups = {}
    for aid, a in exp["lookups"].items():
        lookups[aid] = [
            {"team_rule_id": kid, "result": x["expected"]}
            for kid, x in a["expected"].items()
            if x["expected"]
        ]
    changes = {
        t: {
            "affected_address_ids": v["affected"],
            "conflict_flag_address_ids": v.get("conflict_flags", []),
        }
        for t, v in exp["changes"].items()
    }
    return {"rules": rules}, {"as_of": "2026-10-01", "lookups": lookups}, changes


# ----------------------------------------------------------------------------------------- report
def bar(frac, n=20):
    f = max(0.0, min(1.0, frac))
    return "#" * round(f * n) + "." * (n - round(f * n))


def print_summary(res, key, exp, paths, color):
    B = "\033[1m" if color else ""
    R = "\033[0m" if color else ""
    E, A, C, T = res["extraction"], res["addresses"], res["citations"], res["changes"]
    total = E["points"] + A["points"] + C["points"] + T["points"]
    n_core = sum(1 for r in key["rules"] if r["tier"] == "core")
    W = 78
    print("=" * W)
    print(
        f"{B} RENTAL HOUSING LAW NAVIGATOR - QA SCORE (independent key, not the official score.py){R}"
    )
    print(
        f" as of 2026-10-01 | key: {len(key['rules'])} rules ({n_core} core) + {len(key['no_rule_findings'])} no-rule findings"
        f" | {A['n_addr']} sampled addresses"
    )
    print("=" * W)
    fa = E["field_acc"]
    fstr = " ".join(f"{k.split('_')[0]} {v[0]}/{v[1]}" for k, v in sorted(fa.items()))
    tt = T["tests"]
    lines = [
        (
            "Extraction accuracy",
            E["points"],
            25,
            f"core {E['core_found']}/{E['core_total']}, all {E['all_found']}/{E['all_total']}, precision {E['precision']:.0%}",
        ),
        (
            "Address coverage",
            A["points"],
            20,
            f"{A['earned']:.0f}/{A['possible']:.0f} pts, missed-applies {A['stats']['missed_applies']}, FP {A['stats']['false_positive']}",
        ),
        (
            "Citations",
            C["points"],
            15,
            f"{C['ok']}/{C['total']} 'applies' answers with a verbatim corpus span",
        ),
        (
            "Change tracking T1-T5",
            T["points"],
            15,
            " ".join(f"{k} {v['score']:.2f}" for k, v in tt.items()),
        ),
    ]
    print(f" {'Component':<24}{'Score':>7}{'Max':>6}   {'':20}  Detail")
    print("-" * W)
    for name, p, m, d in lines:
        print(f" {name:<24}{p:7.1f}{m:6d}   {bar(p / m)}  {d}")
    print("-" * W)
    print(f"{B} {'AUTO-SCORED TOTAL':<24}{total:7.1f}{75:6d}   {bar(total / 75)}{R}")
    print("=" * W)
    print(f" field accuracy (matched rules): {fstr}")
    print(
        f" no-rule findings: {len(E['nr_violations'])} violated (in-force rule reported where the key says none),"
        f" {len(E['nr_found'])}/{len(key['no_rule_findings'])} explicitly reported"
    )
    au = res["audit"]
    print(
        f" full-sample audit (all {au['n']} addresses, unscored): {au['total']} disagreements with the oracle logic"
    )
    if res["sanity"]:
        print(" sanity checks:")
        for s in res["sanity"]:
            print(f"   ! {s}")
    print(f" inputs: {paths['rules']} | {paths['lookups']} | {paths['changes']}")
    print(" detail: " + str(paths["report"]))
    print("=" * W)
    return total


def write_report(res, key, exp, paths, total):
    E, A, C, T = res["extraction"], res["addresses"], res["citations"], res["changes"]
    L = []
    L.append("# QA score report (independent key)\n")
    L.append(
        "Not the official `score.py` (not shipped in the starter pack). Oracle: `qa/expected_rules.json`, "
        "`qa/expected_lookups.json`. Not legal advice.\n"
    )
    L.append(f"Inputs: `{paths['rules']}`, `{paths['lookups']}`, `{paths['changes']}`\n")
    L.append("| Component | Score | Max |\n|---|---:|---:|")
    L.append(f"| Extraction accuracy | {E['points']:.1f} | 25 |")
    L.append(f"| Address coverage | {A['points']:.1f} | 20 |")
    L.append(f"| Citations | {C['points']:.1f} | 15 |")
    L.append(f"| Change tracking (T1-T5) | {T['points']:.1f} | 15 |")
    L.append(f"| **Auto-scored total** | **{total:.1f}** | **75** |\n")
    if res["sanity"]:
        L.append("## Sanity checks\n")
        L += [f"- {s}" for s in res["sanity"]]
        L.append("")
    # extraction
    L.append("## 1. Extraction\n")
    L.append(
        f"Weighted recall credit {E['recall_credit']:.1%}, precision {E['precision']:.1%}; "
        f"core rules matched {E['core_found']}/{E['core_total']}.\n"
    )
    miss = [r for r in E["per_rule"] if r["kind"] != "full"]
    L.append("### Missing / citation-mismatched key rules (by points at stake)\n")
    L.append(
        "| Key rule | Tier | Jurisdiction | Category | Expected citation | Status | Team match |\n|---|---|---|---|---|---|---|"
    )
    for r in sorted(miss, key=lambda r: -(r["w"] - r["credit"])):
        k = r["key"]
        tm = r["match"]
        tms = f"{tm.get('team_rule_id')} cites `{tm.get('citation')}`" if tm else "none"
        L.append(
            f"| {k['key_rule_id']} | {k['tier']} | {k['jurisdiction']} | {k['category']} | {k['citation']} | {k['status']} | {tms} |"
        )
    L.append("\n### Field errors on matched rules\n")
    L.append("| Key rule | Team rule | Field | Expected | Team |\n|---|---|---|---|---|")
    for r in E["per_rule"]:
        if r["kind"] != "full":
            continue
        k, t = r["key"], r["match"]
        for f, ok in r["fields"].items():
            if ok:
                continue
            if f == "status":
                ev, tv = k["status"], t.get("status")
            elif f == "effective_date":
                ev, tv = " or ".join(k["effective_date_accept"]), t.get("effective_date")
            elif f == "key_value":
                ev, tv = (
                    f"{k['key_value']} (needs /{'/ & /'.join(k['key_value_patterns'])}/)",
                    t.get("key_value"),
                )
            else:
                ev, tv = k["citation"], t.get("citation")
            L.append(f"| {k['key_rule_id']} | {t.get('team_rule_id')} | {f} | {ev} | {tv} |")
    L.append("\n### Team rules not in the key (possible false positives, or gaps in our key)\n")
    for t in E["extras"]:
        L.append(
            f"- `{t.get('team_rule_id')}` {t.get('jurisdiction')} / {t.get('category')} / {t.get('status')}: "
            f"{t.get('title')} - `{t.get('citation')}`"
        )
    if E["nr_violations"]:
        L.append("\n### No-rule findings violated\n")
        for n, bad in E["nr_violations"]:
            L.append(
                f"- {n['finding_id']} {n['jurisdiction']} / {n['category']}: {n['finding']} -> team reports "
                + ", ".join(f"`{b.get('team_rule_id')}` ({b.get('status')})" for b in bad)
            )
    # addresses
    L.append("\n## 2. Address coverage\n")
    st = A["stats"]
    L.append(
        f"{A['earned']:.1f} of {A['possible']:.1f} weighted points on {A['n_addr']} sampled addresses "
        f"(team lookups cover {A['team_addr_count']} addresses). Counts: {dict(st)}.\n"
    )
    by_rule = defaultdict(lambda: [0.0, Counter()])
    for _aid, _a, kid, _x, _t, why, w in A["rows"]:
        by_rule[kid][0] += w
        by_rule[kid][1][why] += 1
    L.append("### Errors grouped by key rule (weighted points lost)\n")
    L.append("| Key rule | Points lost | Errors |\n|---|---:|---|")
    for kid, (w, c) in sorted(by_rule.items(), key=lambda kv: -kv[1][0]):
        L.append(f"| {kid} | {w:.1f} | {', '.join(f'{k}: {v}' for k, v in c.items())} |")
    L.append("\n### Every address error\n")
    L.append(
        "| Address | City | Built | Units | Key rule | Expected | Team | Error | Why expected |\n|---|---|---|---|---|---|---|---|---|"
    )
    for aid, a, kid, x, t, why, _w in sorted(A["rows"], key=lambda r: (r[0], r[2])):
        ev = (
            (x["expected"] or "omit")
            + (
                ""
                if not x or len(x["accept"]) == 1
                else " (also ok: " + ", ".join(str(v or "omit") for v in x["accept"][1:]) + ")"
            )
            if x
            else "omit"
        )
        L.append(
            f"| {aid} | {a['city']} | {a['year_built'] or '-'} | {a['units'] or '-'} | {kid} | {ev} | {t or 'omitted'} | {why} | {x['why'] if x else '-'} |"
        )
    if A["unmapped"]:
        L.append(
            "\nTeam rule ids in sampled lookups that map to no key rule: "
            + ", ".join(f"`{k}` x{v}" for k, v in A["unmapped"].most_common())
        )
    au = res["audit"]
    L.append(
        f"\n### Full-sample audit (unscored): oracle logic applied to all {au['n']} addresses\n"
    )
    L.append(f"{au['total']} disagreements. Grouped by key rule:\n")
    L.append("| Key rule | Disagreement | Count | Examples |\n|---|---|---:|---|")
    for kid, c in sorted(au["by_rule"].items(), key=lambda kv: -sum(kv[1].values())):
        for label, cnt in c.most_common():
            L.append(f"| {kid} | {label} | {cnt} | {'; '.join(au['examples'][(kid, label)])} |")
    # citations
    L.append("\n## 3. Citations\n")
    L.append(
        f"{C['ok']}/{C['total']} 'applies' answers backed by a source and a verbatim corpus span. "
        f"Outcome counts: {dict(C['reasons'])}.\n"
    )
    L.append("Rule-level span check over all rules: " + str(dict(C["rule_checks"])) + "\n")
    bad = [(tid, v) for tid, v in C["per_rule"].items() if v[1] < v[0]]
    if bad:
        L.append("| Team rule | 'applies' answers | failing | span check |\n|---|---:|---:|---|")
        for tid, (n, okn, why) in sorted(bad, key=lambda kv: -(kv[1][0] - kv[1][1])):
            L.append(f"| {tid} | {n} | {n - okn} | {why} |")
    # changes
    L.append("\n## 4. Change tracking\n")
    L.append(
        "| Test | Score | Team n | Expected n | Missing | Extra |\n|---|---:|---:|---:|---|---|"
    )
    for tid, r in T["tests"].items():
        L.append(
            f"| {tid} | {r['score']:.2f} | {r['team_n']} | {r['exp_n']} | {len(r['missing'])} {r['missing'][:8]} | "
            f"{len(r['extra'])} {r['extra'][:8]} |"
        )
    t3 = T["tests"]["T3"]
    L.append(
        f"\nT3 conflict flags: Jaccard {t3['flag_jaccard']:.2f} (team {t3['flag_team_n']}, expected {t3['flag_exp_n']}); "
        f"missing {t3['flag_missing'][:10]}, extra {t3['flag_extra'][:10]}."
    )
    L.append(
        f"\nT6 (hour-16 fictional Cambridge ordinance): {'present in changes.json' if T['t6'] else 'not scored (data not in starter pack)'}."
    )
    Path(paths["report"]).write_text("\n".join(L) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--rules", default=str(NAV_OUT / "rules.json"))
    ap.add_argument("--lookups", default=str(NAV_OUT / "lookups.json"))
    ap.add_argument("--changes", default=str(NAV_OUT / "changes.json"))
    ap.add_argument("--key", default=str(QA / "expected_rules.json"))
    ap.add_argument("--expected", default=str(QA / "expected_lookups.json"))
    ap.add_argument("--corpus", default=str(CORPUS_DIR))
    ap.add_argument("--report", default=str(QA / "report.md"))
    ap.add_argument("--json", help="write a machine-readable summary here")
    ap.add_argument(
        "--self-test", action="store_true", help="score a perfect submission built from the key"
    )
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args()

    key, exp = load_json(a.key), load_json(a.expected)
    corpus = Corpus(Path(a.corpus), SUPP_DIR)
    if a.self_test:
        r, l, c = perfect_submission(key, exp)
        tmp = Path(tempfile.mkdtemp(prefix="qa-selftest-"))
        for name, obj in (("rules", r), ("lookups", l), ("changes", c)):
            (tmp / f"{name}.json").write_text(json.dumps(obj))
        a.rules, a.lookups, a.changes = (
            str(tmp / "rules.json"),
            str(tmp / "lookups.json"),
            str(tmp / "changes.json"),
        )
        a.report = str(tmp / "report.md")
    for p in (a.rules, a.lookups, a.changes):
        if not Path(p).exists():
            sys.exit(f"missing input: {p}")
    team_rules, team_nr = team_rules_list(load_json(a.rules))
    team_lookups = load_json(a.lookups)
    team_changes = load_json(a.changes)

    ext = score_extraction(key, team_rules, team_nr)
    res = {
        "extraction": ext,
        "addresses": score_addresses(key, exp, team_rules, team_lookups, ext),
        "citations": score_citations(team_rules, team_lookups, corpus),
        "changes": score_changes(exp, team_changes),
        "sanity": sanity(key, team_rules, team_lookups, exp, ext),
        "audit": full_audit(key, team_rules, team_lookups, ext),
    }
    paths = {"rules": a.rules, "lookups": a.lookups, "changes": a.changes, "report": a.report}
    color = sys.stdout.isatty() and not a.no_color and not os.environ.get("NO_COLOR")
    total = print_summary(res, key, exp, paths, color)
    write_report(res, key, exp, paths, total)
    if a.self_test:
        import shutil

        shutil.rmtree(Path(a.rules).parent, ignore_errors=True)
    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "total": round(total, 2),
                    "extraction": round(ext["points"], 2),
                    "addresses": round(res["addresses"]["points"], 2),
                    "citations": round(res["citations"]["points"], 2),
                    "changes": round(res["changes"]["points"], 2),
                    "changes_detail": {
                        k: round(v["score"], 3) for k, v in res["changes"]["tests"].items()
                    },
                },
                indent=1,
            )
        )


if __name__ == "__main__":
    main()
