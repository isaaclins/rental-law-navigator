"""Self-check: schema, verbatim spans, coverage matrix, lookups sanity, change tests T1-T5, open questions."""

from __future__ import annotations

import io
import json
from collections import Counter
from contextlib import redirect_stdout

from . import evaluate as E
from .config import (
    CATEGORIES,
    CHANGES_JSON,
    CITIES,
    JURISDICTIONS,
    LOOKUPS_JSON,
    RULES_JSON,
    SELFCHECK_TXT,
)
from .corpus import get_doc, verify_span

RESULTS = {"applies", "unknown", "superseded", "not_yet_effective", "pending"}
SHORT = {
    "rent_increase_limits": "RENT",
    "just_cause_eviction": "EVIC",
    "security_deposits": "DEP",
    "application_screening_fees": "FEE",
    "screening_restrictions": "SCR",
    "algorithmic_rent_setting": "ALG",
}

# Brief p.3 examples, used ONLY to report recall of the extraction (never as a source of rules).
BRIEF_CHECKLIST = [
    ("CA", "rent_increase_limits", "1947.12"),
    ("San Francisco, CA", "rent_increase_limits", "37"),
    ("Los Angeles, CA", "rent_increase_limits", "151"),
    ("MA", "rent_increase_limits", "40p"),
    ("CA", "just_cause_eviction", "1946.2"),
    ("NJ", "just_cause_eviction", "2a:18-61.1"),
    ("CA", "security_deposits", "1950.5"),
    ("NJ", "security_deposits", "46:8-21.2"),
    ("MA", "security_deposits", "15b"),
    ("CA", "application_screening_fees", "1950.6"),
    ("NJ", "application_screening_fees", "405"),
    ("MA", "application_screening_fees", "15b"),
    ("MA", "application_screening_fees", "87ddd"),
    ("NJ", "screening_restrictions", "fair chance|46:8-52|110"),
    ("CA", "screening_restrictions", "12955"),
    ("CA", "algorithmic_rent_setting", "16729|325"),
    ("San Francisco, CA", "algorithmic_rent_setting", "37.10c"),
    ("San Diego, CA", "algorithmic_rent_setting", "98.110"),
    ("Berkeley, CA", "algorithmic_rent_setting", "13.63"),
    ("Santa Ana, CA", "algorithmic_rent_setting", "ns-3090|3090"),
    ("Jersey City, NJ", "algorithmic_rent_setting", "218"),
    ("Hoboken, NJ", "algorithmic_rent_setting", "158"),
    ("NJ", "algorithmic_rent_setting", "c.43|56:9"),
    ("MA", "algorithmic_rent_setting", "2983"),
    ("MA", "algorithmic_rent_setting", "5222"),
]


def _hdr(t: str) -> None:
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def _check(ok: bool, msg: str, fails: list) -> None:
    print(("  PASS " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def _body(fails: list) -> None:
    from .extract import validate

    doc = json.loads(RULES_JSON.read_text(encoding="utf-8"))
    rules, nrf = doc["rules"], doc.get("no_rule_findings", [])
    by_id = {r["team_rule_id"]: r for r in rules}

    _hdr("1. rules.json: schema + verbatim quoted spans")
    errs = validate(doc)
    _check(
        not errs,
        f"{len(rules)} rules validate against rule_record.schema.json ({len(errs)} errors)",
        fails,
    )
    for e in errs[:10]:
        print("     ", e)
    ids = [r["team_rule_id"] for r in rules]
    _check(len(ids) == len(set(ids)), "team_rule_ids are unique", fails)
    bad, official, secondary = [], 0, 0
    for r in rules:
        d = r.get("quoted_span_doc_id") or r["source_doc_id"]
        if not verify_span(d, r["quoted_span"]):
            bad.append(r["team_rule_id"])
        doc_obj = get_doc(d)
        if doc_obj and doc_obj.origin in ("corpus", "new"):
            official += 1
        else:
            secondary += 1
    _check(
        not bad,
        f"every quoted_span found verbatim (whitespace-normalised) in its document; failures: {bad}",
        fails,
    )
    print(
        f"  spans from starter corpus/new docs: {official}; from fetched link-only secondary sources: {secondary}"
    )
    nbad = [
        n["finding_id"]
        for n in nrf
        if n.get("quoted_span")
        and not verify_span(n.get("quoted_span_doc_id") or n["source_doc_id"], n["quoted_span"])
    ]
    nspan = sum(1 for n in nrf if n.get("quoted_span"))
    _check(
        not nbad,
        f"{len(nrf)} no-rule findings ({nspan} with a quote), every quote verbatim; failures: {nbad}",
        fails,
    )

    _hdr(
        "2. coverage matrix (jurisdiction x category): F=in force, N=not yet effective, P=pending, X=failed, U=unverified, - = no-rule finding"
    )
    print(f"  {'':20}" + "".join(f"{SHORT[c]:>10}" for c in CATEGORIES))
    empty = []
    for j in JURISDICTIONS:
        row = []
        for c in CATEGORIES:
            cell = [r for r in rules if r["jurisdiction"] == j and r["category"] == c]
            s = "".join(
                "U"
                if r.get("verification") == "unverified_link_only"
                else {"in_force": "F", "not_yet_effective": "N", "pending": "P", "failed": "X"}[
                    r["status"]
                ]
                for r in cell
            )
            if any(n["jurisdiction"] == j and n["category"] == c for n in nrf):
                s += "-"
            if not s:
                empty.append((j, c))
            row.append(s or ".")
        print(f"  {j:20}" + "".join(f"{x:>10}" for x in row))
    st = Counter(r["status"] for r in rules)
    print(
        f"  totals: {len(rules)} rules {dict(st)}; {len(nrf)} no-rule findings; empty cells: {len(empty)}"
    )

    _hdr("3. recall vs. the brief's example list (sanity check only)")
    import re as _re

    miss = []
    for j, c, pat in BRIEF_CHECKLIST:
        hit = [
            r
            for r in rules
            if r["jurisdiction"] == j
            and r["category"] == c
            and _re.search(
                pat,
                (
                    r["citation"]
                    + " "
                    + " ".join(r.get("citation_aliases") or [])
                    + " "
                    + r["title"]
                ).lower(),
            )
        ]
        print(
            f"  {'ok  ' if hit else 'MISS'} {j:18} {SHORT[c]:5} {pat:22} -> {', '.join(h['team_rule_id'] + ' ' + h['citation'] for h in hit)}"
        )
        if not hit:
            miss.append((j, c, pat))
    _check(not miss, f"all {len(BRIEF_CHECKLIST)} brief examples found", fails)

    _hdr("4. lookups.json")
    lk = json.loads(LOOKUPS_JSON.read_text(encoding="utf-8"))
    addrs = E.load_addresses()
    look = lk["lookups"]
    _check(
        set(look) == {f.address_id for f in addrs} and len(look) == 500,
        f"covers all addresses ({len(look)})",
        fails,
    )
    ents = [e for v in look.values() for e in v]
    _check(all(e["result"] in RESULTS for e in ents), "all result values valid", fails)
    _check(
        all(e["team_rule_id"] in by_id for e in ents),
        "all team_rule_ids exist in rules.json",
        fails,
    )
    _check(
        all(e.get("explanation") and isinstance(e.get("conflict_flag"), bool) for e in ents),
        "explanation + conflict_flag on every entry",
        fails,
    )
    print(
        f"  results: {dict(Counter(e['result'] for e in ents))}; entries per address: {len(ents) / max(1, len(look)):.1f}"
    )
    applies = [e for e in ents if e["result"] == "applies"]
    cited = [
        e
        for e in applies
        if by_id[e["team_rule_id"]].get("quoted_span")
        and (
            get_doc(by_id[e["team_rule_id"]].get("quoted_span_doc_id"))
            or get_doc(by_id[e["team_rule_id"]]["source_doc_id"])
        )
    ]
    in_corpus = [
        e
        for e in cited
        if (get_doc(by_id[e["team_rule_id"]]["quoted_span_doc_id"]).origin in ("corpus", "new"))
    ]
    print(
        f"  citation proxy: {len(cited)}/{len(applies)} applies answers carry a verified span; "
        f"{len(in_corpus)}/{len(applies)} ({100 * len(in_corpus) / max(1, len(applies)):.1f}%) quote the starter corpus text itself"
    )
    print("  per city (applies/unknown/superseded/nye/pending per address, mean):")
    for city in list(CITIES):
        fs = [f for f in addrs if f.city == city]
        if not fs:
            continue
        c = Counter(e["result"] for f in fs for e in look[f.address_id])
        print(
            f"    {city:18} n={len(fs):3} "
            + " ".join(
                f"{k}={c.get(k, 0) / len(fs):.1f}"
                for k in ("applies", "unknown", "superseded", "not_yet_effective", "pending")
            )
        )

    _hdr("5. change tests T1-T5")
    ch = json.loads(CHANGES_JSON.read_text(encoding="utf-8"))
    st_of = {f.address_id: f.state for f in addrs}
    city_of = {f.address_id: f.city for f in addrs}
    ca = {a for a, s in st_of.items() if s == "CA"}
    nj = {a for a, s in st_of.items() if s == "NJ"}
    ma = {a for a, s in st_of.items() if s == "MA"}
    jc_hob = {a for a, c in city_of.items() if c in ("Jersey City, NJ", "Hoboken, NJ")}
    for tid in sorted(ch):
        t = ch[tid]
        print(
            f"  {tid}: affected={len(t['affected_address_ids'])} conflict_flags={len(t.get('conflict_flag_address_ids', []))} mapping={t.get('rule_mapping')}"
        )
        print(f"      {t['notes'][:400]}")
    if "T1" in ch:
        a = set(ch["T1"]["affected_address_ids"])
        _check(a == ca, f"T1 affected == all CA addresses ({len(a)}/{len(ca)})", fails)
        pa = ch["T1"]["per_address"]
        _check(
            all(
                set(v["before"].values()) <= {"not_yet_effective"}
                and set(v["after"].values()) <= {"applies"}
                for v in pa.values()
            ),
            "T1 not_yet_effective on 2025-12-31 -> applies on 2026-01-02",
            fails,
        )
    if "T2" in ch:
        pa = ch["T2"]["per_address"]
        m = ch["T2"]["rule_mapping"]
        hob, jc = set(m.get("HOB-ALG-01", [])), set(m.get("JC-ALG-01", []))
        _check(bool(hob) and bool(jc), f"T2 both local bans resolved ({hob}, {jc})", fails)
        _check(
            all(city_of[a] == "Hoboken, NJ" for a, v in pa.items() if set(v) & hob),
            "T2 HOB ban only in Hoboken",
            fails,
        )
        _check(
            all(city_of[a] == "Jersey City, NJ" for a, v in pa.items() if set(v) & jc),
            "T2 JC ban only in Jersey City",
            fails,
        )
        _check(not any(city_of[a] == "Newark, NJ" for a in pa), "T2 neither ban in Newark", fails)
        _check(
            {a for a in pa} == jc_hob,
            f"T2 every JC/Hoboken address covered ({len(pa)}/{len(jc_hob)})",
            fails,
        )
    if "T3" in ch:
        a = set(ch["T3"]["affected_address_ids"])
        _check(a == nj, f"T3 affected == all NJ addresses ({len(a)}/{len(nj)})", fails)
        pa = ch["T3"]["per_address"]
        _check(
            all(
                set(v["before"].values()) <= {"not_yet_effective"}
                and set(v["after"].values()) <= {"applies"}
                for v in pa.values()
            ),
            "T3 not_yet_effective on 2026-10-01 -> applies on 2027-07-02",
            fails,
        )
        fl = set(ch["T3"]["conflict_flag_address_ids"])
        _check(
            fl == jc_hob,
            f"T3 conflict flags == Jersey City + Hoboken ({len(fl)}/{len(jc_hob)})",
            fails,
        )
    if "T4" in ch:
        a = set(ch["T4"]["affected_address_ids"])
        _check(a == ma, f"T4 affected == all MA addresses ({len(a)}/{len(ma)})", fails)
        _check(
            len(ch["T4"]["rule_mapping"].get("MA-ALG-P1", []))
            + len(ch["T4"]["rule_mapping"].get("MA-ALG-P2", []))
            >= 2,
            "T4 both pending bills resolved",
            fails,
        )
        _check(
            all(
                e["result"] == "pending"
                for a2 in ma
                for e in look[a2]
                if by_id[e["team_rule_id"]].get("legal_status") == "pending_bill"
            ),
            "T4 bills reported as pending (never in force) in lookups",
            fails,
        )
    if "T5" in ch:
        _check(not ch["T5"]["affected_address_ids"], "T5 affected set empty", fails)
        failed = [
            r
            for r in rules
            if r["jurisdiction"] == "MA"
            and r["category"] == "rent_increase_limits"
            and r["status"] == "failed"
        ]
        _check(
            bool(failed),
            f"T5 ballot question recorded as failed: {[r['team_rule_id'] + ' ' + r['citation'] for r in failed]}",
            fails,
        )
        caps = [
            (a2, e["team_rule_id"])
            for a2 in ma
            for e in look[a2]
            if by_id[e["team_rule_id"]]["category"] == "rent_increase_limits"
            and by_id[e["team_rule_id"]]["level"] == "city"
        ]
        _check(
            not caps,
            f"T5 no local rent cap reported for any Boston/Cambridge address ({len(caps)} found)",
            fails,
        )
        st_rent = Counter(
            e["team_rule_id"] + " " + by_id[e["team_rule_id"]]["citation"] + " -> " + e["result"]
            for a2 in ma
            for e in look[a2]
            if by_id[e["team_rule_id"]]["category"] == "rent_increase_limits"
        )
        print(
            f"      state-level rent entries on MA addresses (should be the state bar on rent control only): {dict(st_rent)}"
        )

    _hdr("6. known open questions (README section 9) surfaced as conflict flags")
    checks = [
        (
            "Berkeley algorithmic ban: two effective dates",
            lambda r: (
                r["jurisdiction"] == "Berkeley, CA" and r["category"] == "algorithmic_rent_setting"
            ),
        ),
        (
            "NJ FAIR Act may preempt JC/Hoboken bans",
            lambda r: (
                r["jurisdiction"] in ("NJ", "Jersey City, NJ", "Hoboken, NJ")
                and r["category"] == "algorithmic_rent_setting"
            ),
        ),
        (
            "LA RSO formula: two effective dates",
            lambda r: (
                r["jurisdiction"] == "Los Angeles, CA" and r["category"] == "rent_increase_limits"
            ),
        ),
        (
            "CA screening-fee cap: no single official 2026 figure",
            lambda r: r["jurisdiction"] == "CA" and r["category"] == "application_screening_fees",
        ),
    ]
    for name, pred in checks:
        rs = [r for r in rules if pred(r)]
        flagged = [r for r in rs if r.get("conflict_flag") and r.get("conflict_note")]
        _check(
            bool(flagged),
            f"{name}: "
            + (
                "; ".join(f"{r['team_rule_id']}: {r['conflict_note'][:160]}" for r in flagged)
                or "not flagged"
            ),
            fails,
        )

    _hdr("7. rules list")
    for r in rules:
        print(
            f"  {r['team_rule_id']:12} {r['status']:17} {str(r.get('effective_date')):10} {r['citation'][:45]:45} | {(r.get('key_value') or '')[:60]}"
            + ("  [CONFLICT]" if r.get("conflict_flag") else "")
            + (f"  [{r.get('verification')}]" if r.get("verification") != "primary_source" else "")
        )
    print("\n  no-rule findings:")
    for n in nrf:
        print(
            f"  {n['finding_id']:6} {n['jurisdiction']:18} {SHORT[n['category']]:5} {(n.get('finding') or '')[:110]}"
        )


def run() -> int:
    fails: list[str] = []
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            _body(fails)
        except FileNotFoundError as e:
            print(f"missing output file: {e}")
            fails.append(str(e))
        print(f"\nSELFCHECK: {'OK' if not fails else f'{len(fails)} check(s) failed'}")
        for f in fails:
            print("  -", f)
    text = buf.getvalue()
    print(text)
    SELFCHECK_TXT.write_text(text, encoding="utf-8")
    return 0 if not fails else 1
