"""Module B: deterministic address lookup.

For each address: jurisdiction stack = state + resolved city. Every rule of those jurisdictions is tested:
  time      : failed -> omitted; enacted after the query date -> omitted; sunset passed -> omitted;
              pending bill -> "pending"; effective after the query date -> "not_yet_effective"
  coverage  : the rule's machine-evaluable `coverage` object vs. year_built / units / use code
              (covered -> applies, excluded -> omitted, fact missing -> "unknown")
  precedence: a state rule that yields to local law -> "superseded" where a local rule of the same
              category applies (or "unknown" when local coverage is unknown)
  conflicts : state rules that may preempt local ones, open questions and unverified sources -> conflict_flag
When in doubt between omitting and "unknown", we answer "unknown" (missing an applicable rule is the worse error).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from dataclasses import dataclass

from . import normalize as N
from .config import CITIES, DEFAULT_AS_OF, LOOKUPS_JSON, RESOLVED_CSV, RULES_JSON, SAMPLE_ADDRESSES

DISCLAIMER = "Not legal advice. Automated reading of public law as of the stated date; verify with the cited source."

# Postal-city -> legal city hints (README 4.1), used only when data/addresses_resolved.csv is absent.
_POSTAL_FALLBACK = {
    "van nuys": "Los Angeles",
    "north hollywood": "Los Angeles",
    "sherman oaks": "Los Angeles",
    "studio city": "Los Angeles",
    "encino": "Los Angeles",
    "reseda": "Los Angeles",
    "canoga park": "Los Angeles",
    "woodland hills": "Los Angeles",
    "san pedro": "Los Angeles",
    "wilmington": "Los Angeles",
    "hollywood": "Los Angeles",
    "tujunga": "Los Angeles",
    "sunland": "Los Angeles",
    "san ysidro": "San Diego",
    "la jolla": "San Diego",
    "dorchester": "Boston",
    "roxbury": "Boston",
    "allston": "Boston",
    "brighton": "Boston",
    "east boston": "Boston",
    "south boston": "Boston",
    "jamaica plain": "Boston",
    "hyde park": "Boston",
    "mattapan": "Boston",
    "roslindale": "Boston",
    "west roxbury": "Boston",
    "charlestown": "Boston",
    "mission hill": "Boston",
}


@dataclass
class Facts:
    address_id: str
    state: str
    city: str | None  # "Boston, MA" style or None
    year_built: int | None
    units_lo: int | None
    units_hi: int | None
    units_note: str
    use: str
    raw: dict
    # Facts only a user can supply (any-address lookup, #39); None = unknown, which keeps the sample behaviour.
    owner_occupied: bool | None = None
    # certificate-of-occupancy / completion date, breaks cutoff-year ties
    co_date: dt.date | None = None
    # sample rows are apartment buildings; a user's address may not be
    multifamily_assumed: bool = True


# ------------------------------------------------------------------ address facts
def _int(v) -> int | None:
    try:
        i = int(float(str(v).strip()))
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


def unit_range(row: dict) -> tuple[int | None, int | None, str]:
    u = _int(row.get("units"))
    if u:
        return u, u, f"{u} units (assessor)"
    desc = (row.get("use_description") or "").upper()
    code = (row.get("use_code") or "").upper()
    nums = [int(x) for x in re.findall(r"(\d+)\s*U\b", desc)]  # NJ MOD-IV style "3S-B-D-6U-H"
    if nums:
        return (
            max(nums),
            None,
            f"at least {max(nums)} units (from use description '{row.get('use_description')}')",
        )
    m = re.search(r"(\d+)\s*(?:-|TO)\s*(\d+)[\s-]*UNIT", desc)
    if m:
        return (
            int(m.group(1)),
            int(m.group(2)),
            f"{m.group(1)}-{m.group(2)} units (use code {row.get('use_code')})",
        )
    m = re.search(r">\s*(\d+)[\s-]*UNIT", desc)
    if m:
        return (
            int(m.group(1)) + 1,
            None,
            f"more than {m.group(1)} units (use code {row.get('use_code')})",
        )
    if re.search(r"FIVE OR MORE|5\+ UNITS|\(5\+", desc):
        return 5, None, f"5 or more units (use code {row.get('use_code')})"
    m = re.search(r"(\d+)\s*UNITS OR MORE", desc)
    if m:
        return int(m.group(1)), None, f"{m.group(1)}+ units (use code {row.get('use_code')})"
    if row.get("state") == "NJ" and code == "4C":
        return 5, None, "5 or more units (NJ property class 4C = apartment building)"
    return None, None, "unit count not in data"


def load_addresses() -> list[Facts]:
    rows = list(
        csv.DictReader(
            open(RESOLVED_CSV if RESOLVED_CSV.exists() else SAMPLE_ADDRESSES, encoding="utf-8")
        )
    )
    out = []
    for r in rows:
        st = (r.get("resolved_state") or r.get("state") or "").strip()
        city = (r.get("resolved_city") or "").strip()
        if not RESOLVED_CSV.exists():
            pc = (r.get("postal_city") or "").strip()
            city = _POSTAL_FALLBACK.get(pc.lower(), pc)
        jur = f"{city}, {st}" if city else None
        if jur not in CITIES:
            jur = None
        lo, hi, note = unit_range(r)
        out.append(
            Facts(
                r["address_id"],
                st,
                jur,
                _int(r.get("year_built")),
                lo,
                hi,
                note,
                f"{r.get('use_code')} {r.get('use_description')}".strip(),
                r,
            )
        )
    return out


# ------------------------------------------------------------------ coverage tests
YES, NO, UNK = "yes", "no", "unknown"


def _cmp_year(y: int, d: dt.date, covered_if: str, basis: str) -> str:
    if covered_if in ("on_or_before", "before"):
        if y < d.year:
            return YES
        if y > d.year:
            return NO
        if covered_if == "on_or_before" and d.month == 12 and d.day == 31:
            return YES
        if covered_if == "before" and d.month == 1 and d.day == 1:
            return NO
        return UNK
    if y > d.year:
        return YES
    if y < d.year:
        return NO
    if covered_if == "on_or_after" and d.month == 1 and d.day == 1:
        return YES
    if covered_if == "after" and d.month == 12 and d.day == 31:
        return NO
    return UNK


def coverage(rule: dict, f: Facts, as_of: dt.date) -> tuple[str, list[str]]:
    cov = rule.get("coverage") or {}
    verdict, why = YES, []

    def worse(v: str, reason: str):
        nonlocal verdict
        why.append(reason)
        if v == NO:
            verdict = NO
        elif v == UNK and verdict == YES:
            verdict = UNK

    lo, hi = f.units_lo, f.units_hi
    mn, mx = cov.get("min_units"), cov.get("max_units")
    if mn:
        if lo is not None and lo >= mn:
            why.append(f"building has {f.units_note}, meets the {mn}+ unit threshold")
        elif hi is not None and hi < mn:
            worse(NO, f"building has {f.units_note}, below the {mn}-unit threshold")
        else:
            worse(UNK, f"coverage needs {mn}+ units; {f.units_note}")
    if mx:
        if hi is not None and hi <= mx:
            why.append(f"building has {f.units_note}, within the {mx}-unit limit")
        elif lo is not None and lo > mx:
            worse(NO, f"building has {f.units_note}, above the {mx}-unit limit")
        else:
            worse(UNK, f"coverage limited to buildings of at most {mx} units; {f.units_note}")
    oo = cov.get("owner_occupied_exemption_max_units")
    if oo:
        if lo is not None and lo > oo:
            why.append(f"owner-occupied exemption (<= {oo} units) cannot apply: {f.units_note}")
        elif f.owner_occupied is False:
            why.append(
                f"not owner-occupied: the owner-occupied exemption (<= {oo} units) does not apply"
            )
        elif f.owner_occupied and hi is not None and hi <= oo:
            worse(NO, f"owner-occupied with {f.units_note}: exempt (<= {oo} units)")
        elif lo is None and (f.owner_occupied or not f.multifamily_assumed):
            worse(UNK, f"exempt if owner-occupied with <= {oo} units; {f.units_note}")
        elif lo is None:
            why.append(
                f"owner-occupied exemption (<= {oo} units) not checkable; sample rows are multifamily buildings"
            )
        else:
            worse(
                UNK,
                f"exempt if owner-occupied with <= {oo} units; owner occupancy is not in the data ({f.units_note})",
            )
    cut = cov.get("construction_cutoff")
    if cut and cut.get("date"):
        d = N.date_floor(N.date(cut["date"]))
        basis = (cut.get("basis") or "certificate_of_occupancy").replace("_", " ")
        if d is None:
            pass
        elif f.co_date is not None and (f.year_built is None or f.year_built == d.year):
            ci = cut.get("covered_if", "on_or_before")
            phr = f"{basis} {ci.replace('_', ' ')} {d.isoformat()}"
            ok = {
                "on_or_before": f.co_date <= d,
                "before": f.co_date < d,
                "on_or_after": f.co_date >= d,
                "after": f.co_date > d,
            }.get(ci, f.co_date <= d)
            if ok:
                why.append(f"certificate date {f.co_date.isoformat()}: meets the cutoff ({phr})")
            else:
                worse(NO, f"certificate date {f.co_date.isoformat()}: outside the cutoff ({phr})")
        elif f.year_built is None:
            worse(
                UNK,
                f"coverage depends on {basis} {cut.get('covered_if', '').replace('_', ' ')} {d.isoformat()}; year built is not in the data",
            )
        else:
            v = _cmp_year(f.year_built, d, cut.get("covered_if", "on_or_before"), basis)
            phr = f"{basis} {cut.get('covered_if', '').replace('_', ' ')} {d.isoformat()}"
            if v == YES:
                why.append(f"built {f.year_built}: meets the cutoff ({phr})")
            elif v == NO:
                worse(NO, f"built {f.year_built}: outside the cutoff ({phr})")
            else:
                worse(
                    UNK,
                    f"built {f.year_built}, the cutoff year; the {basis} date is not in the data ({phr})",
                )
    nce = cov.get("new_construction_exemption")
    if nce and nce.get("years"):
        yrs = int(nce["years"])
        thr = (
            as_of.replace(year=as_of.year - yrs)
            if not (as_of.month == 2 and as_of.day == 29)
            else as_of.replace(year=as_of.year - yrs, day=28)
        )
        filing = nce.get("requires_owner_filing")
        if f.co_date is not None and (f.year_built is None or f.year_built == thr.year):
            if f.co_date <= thr:
                why.append(
                    f"certificate date {f.co_date.isoformat()}: older than the {yrs}-year new-construction exemption"
                )
            elif filing:
                worse(
                    UNK,
                    f"certificate date {f.co_date.isoformat()}: may be exempt as new construction (< {yrs} years) if the owner filed for the exemption; filing not in the data",
                )
            else:
                worse(
                    NO,
                    f"certificate date {f.co_date.isoformat()}: exempt as new construction (within {yrs} years)",
                )
        elif f.year_built is None:
            worse(
                UNK,
                f"exempt if newer than {yrs} years ({thr.isoformat()}); year built is not in the data",
            )
        elif f.year_built < thr.year:
            why.append(
                f"built {f.year_built}: older than the {yrs}-year new-construction exemption"
            )
        elif f.year_built > thr.year:
            if filing:
                worse(
                    UNK,
                    f"built {f.year_built}: may be exempt as new construction (< {yrs} years) if the owner filed for the exemption; filing not in the data",
                )
            else:
                worse(
                    NO,
                    f"built {f.year_built}: exempt as new construction (certificate of occupancy within {yrs} years)",
                )
        else:
            worse(
                UNK,
                f"built {f.year_built}: the {yrs}-year new-construction exemption turns on the exact certificate date ({thr.isoformat()})",
            )
    req = [x for x in (cov.get("requires_unknown_facts") or []) if x]
    if req:
        worse(UNK, "coverage depends on facts not in the data: " + "; ".join(req))
    return verdict, why


# ------------------------------------------------------------------ rule evaluation
def time_status(rule: dict, as_of: dt.date) -> str | None:
    """None -> omit; else pending / not_yet_effective / in_force."""
    ls = rule.get("legal_status") or (
        "pending_bill"
        if rule.get("status") == "pending"
        else "failed"
        if rule.get("status") == "failed"
        else "enacted"
    )
    if ls == "failed":
        return None
    if ls == "pending_bill":
        return "pending"
    enacted = N.date_floor(rule.get("enacted_date"))
    if enacted and enacted > as_of:
        return None
    sunset = N.date_floor(rule.get("sunset_date"))
    if (
        sunset and sunset <= as_of and _sunset_is_repeal(rule)
    ):  # a key-figure period ending does not end the law
        return None
    if rule.get(
        "amends_existing_law"
    ):  # long-standing law: only its first effect matters for existence
        start = N.date_floor(rule.get("in_force_since"))
    else:
        start = N.date_floor(rule.get("effective_date"))
    if start and start > as_of:
        return "not_yet_effective"
    return "in_force"


def _sunset_is_repeal(rule: dict) -> bool:
    kind = rule.get("sunset_kind")
    if kind is None and rule.get("sunset_date"):
        from .extract import sunset_kind

        kind = sunset_kind(rule)
    return kind == "repeal"


def figure_note(rule: dict, as_of: dt.date) -> str:
    """After the period of the current key figure ends, the law still applies; the next figure may not be published yet."""
    end = N.date_floor(rule.get("sunset_date"))
    if end and end < as_of and not _sunset_is_repeal(rule):
        return (
            f" The figure above covers the period ending {rule['sunset_date']}; the law continues after that date,"
            f" but the next periodic figure is not yet published in the corpus - check the current rate."
        )
    return ""


def version_note(rule: dict, as_of: dt.date) -> str:
    """Explain when the query date falls before the current version / figure of a long-standing law."""
    cur = N.date_floor(rule.get("current_version_effective"))
    if rule.get("amends_existing_law") and cur and as_of < cur:
        since = rule.get("in_force_since")
        prior = rule.get("prior_version_note")
        return (
            f" Earlier version in force on {as_of}"
            + (f" (since {since})" if since else "")
            + f"; current version/figure from {rule.get('current_version_effective')}."
            + (f" {prior}" if prior else "")
        )
    return ""


def _applies_here(rule: dict, f: Facts) -> bool:
    if rule["level"] == "state":
        return rule["jurisdiction"] == f.state
    return rule["jurisdiction"] == f.city


def _base_eval(rule: dict, f: Facts, as_of: dt.date):
    ts = time_status(rule, as_of)
    if ts is None:
        return None
    v, why = coverage(rule, f, as_of)
    if v == NO:
        return None
    return ts, v, why


def evaluate_address(
    f: Facts, rules: list[dict], as_of: str | dt.date = DEFAULT_AS_OF
) -> list[dict]:
    as_of_d = dt.date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    here = [r for r in rules if _applies_here(r, f)]
    base = {r["team_rule_id"]: _base_eval(r, f, as_of_d) for r in here}
    out = []
    for r in here:
        b = base[r["team_rule_id"]]
        if b is None:
            continue
        ts, v, why = b
        cov = r.get("coverage") or {}
        cite = r.get("citation", "")
        where = f"{f.city or f.state}" + (
            f" ({r['jurisdiction']} statewide rule)" if r["level"] == "state" else ""
        )
        conflict, notes = False, []
        locals_same = [
            x
            for x in here
            if x["level"] == "city" and x["category"] == r["category"] and x is not r
        ]
        if r["level"] == "state" and cov.get("may_preempt_local_rules") and locals_same:
            conflict = True
            notes.append(
                "possible conflict/preemption with local "
                + ", ".join(f"{x['team_rule_id']} ({x['citation']})" for x in locals_same)
                + " - flagged for human review"
            )
        if r["level"] == "city":
            preempt = [
                x
                for x in here
                if x["level"] == "state"
                and x["category"] == r["category"]
                and (x.get("coverage") or {}).get("may_preempt_local_rules")
                and base.get(x["team_rule_id"])
            ]
            if preempt:
                conflict = True
                notes.append(
                    "state law "
                    + ", ".join(
                        f"{x['team_rule_id']} ({x['citation']}, effective {x.get('effective_date')})"
                        for x in preempt
                    )
                    + " may preempt this ordinance - flagged for human review"
                )
        if (
            r.get("conflict_flag")
            and r.get("conflict_note")
            and not cov.get("may_preempt_local_rules")
            and not (r["level"] == "city" and preempt_note_only(r, here))
        ):
            conflict = True
            notes.append("open question: " + r["conflict_note"])
        if r.get("verification") == "unverified_link_only":
            conflict = True

        if ts == "pending":
            res = "pending"
            expl = f"{cite} is a pending bill, not law, as of {as_of_d}. If enacted it would cover this address in {where}."
        elif ts == "not_yet_effective":
            res = "not_yet_effective"
            expl = f"{cite} is enacted but takes effect {r.get('effective_date')}, after {as_of_d}; it will cover this address in {where}."
            if v == UNK:
                expl += " Coverage then depends on facts not in the data: " + "; ".join(why)
        elif r.get("verification") == "unverified_link_only":
            res = "unknown"
            expl = f"{cite} likely applies in {where}, but its text is only linked (not captured) in the corpus; unverified - check the source."
        elif v == UNK:
            res = "unknown"
            expl = f"{cite} may apply in {where}: " + "; ".join(why) + "."
        else:
            res, expl = (
                "applies",
                f"{cite} applies in {where}" + (": " + "; ".join(why) if why else "") + ".",
            )
            if r.get("key_value"):
                expl += f" Rule: {r['key_value']}."
            if r["level"] == "state" and cov.get("may_preempt_local_rules") and not locals_same:
                expl += (
                    f" This state law restricts local {r['category'].replace('_', ' ')} ordinances; no local ordinance of"
                    f" this kind applies at this address."
                )
            if r["level"] == "state" and cov.get("yields_to_local_rule"):
                gov = [
                    x for x in locals_same if (x.get("coverage") or {}).get("supersedes_state_rule")
                ]
                st = [(x, base.get(x["team_rule_id"])) for x in gov]
                applies_local = [x for x, b2 in st if b2 and b2[0] == "in_force" and b2[1] == YES]
                unk_local = [x for x, b2 in st if b2 and b2[0] == "in_force" and b2[1] == UNK]
                if applies_local:
                    res = "superseded"
                    expl = (
                        f"{cite} would cover this address, but local "
                        + ", ".join(f"{x['team_rule_id']} ({x['citation']})" for x in applies_local)
                        + " governs here; the state rule yields to it."
                    )
                elif unk_local and _complementary(unk_local):
                    res = "superseded"
                    expl = (
                        f"{cite} would cover this address, but one of the complementary local ordinances "
                        + ", ".join(f"{x['team_rule_id']} ({x['citation']})" for x in unk_local)
                        + " governs every building (which one depends on the construction date); the state rule yields."
                    )
                elif unk_local:
                    res = "unknown"
                    expl = (
                        f"{cite} covers this address unless local "
                        + ", ".join(f"{x['team_rule_id']} ({x['citation']})" for x in unk_local)
                        + " applies (then the state rule yields); local coverage is unknown from the data."
                    )
        if ts == "in_force":
            expl += version_note(r, as_of_d) + figure_note(r, as_of_d)
        if notes:
            expl += " Note: " + " ".join(notes)
        out.append(
            {
                "team_rule_id": r["team_rule_id"],
                "result": res,
                "explanation": expl,
                "conflict_flag": conflict,
                "citation": cite,
                "category": r["category"],
            }
        )
    return out


def _complementary(rules: list[dict]) -> bool:
    """True when the rules split all buildings at one construction date (one 'on or before', one 'after')."""
    sides: dict[str, set[str]] = {}
    for x in rules:
        cut = (x.get("coverage") or {}).get("construction_cutoff") or {}
        if cut.get("date"):
            side = "old" if cut.get("covered_if") in ("on_or_before", "before") else "new"
            sides.setdefault(N.date(cut["date"]) or cut["date"], set()).add(side)
    return any(v == {"old", "new"} for v in sides.values())


def preempt_note_only(r: dict, here: list[dict]) -> bool:
    """True when a local rule's conflict note is just the state-preemption note (already handled per address)."""
    note = (r.get("conflict_note") or "").lower()
    return (
        any(
            (x.get("coverage") or {}).get("may_preempt_local_rules")
            for x in here
            if x["level"] == "state"
        )
        and ("preempt" in note)
        and "effective date" not in note
        and "two published" not in note
    )


def load_rules(path=RULES_JSON) -> list[dict]:
    return json.loads(open(path, encoding="utf-8").read())["rules"]


def run(
    as_of: str = DEFAULT_AS_OF, out: str | None = None, rules: list[dict] | None = None
) -> dict:
    rules = rules if rules is not None else load_rules()
    addrs = load_addresses()
    look = {}
    for f in addrs:
        look[f.address_id] = [
            {
                k: e[k]
                for k in ("team_rule_id", "result", "explanation", "conflict_flag", "citation")
            }
            for e in evaluate_address(f, rules, as_of)
        ]
    doc = {
        "as_of": as_of,
        "disclaimer": DISCLAIMER,
        "jurisdiction_source": str(
            RESOLVED_CSV.name if RESOLVED_CSV.exists() else "postal-city fallback"
        ),
        "lookups": look,
    }
    path = out or (
        LOOKUPS_JSON if as_of == DEFAULT_AS_OF else LOOKUPS_JSON.with_name(f"lookups_{as_of}.json")
    )
    from pathlib import Path

    Path(path).write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    n = sum(len(v) for v in look.values())
    from collections import Counter

    c = Counter(e["result"] for v in look.values() for e in v)
    print(f"[evaluate] as of {as_of}: {len(look)} addresses, {n} entries {dict(c)} -> {path}")
    return doc
