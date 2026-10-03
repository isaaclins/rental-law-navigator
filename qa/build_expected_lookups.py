"""Build qa/expected_lookups.json: the QA oracle for address results and change tests.

Independent of the product pipeline. Encodes the README result semantics
(applies / unknown / superseded / not_yet_effective / pending; omit = not applicable)
for a stratified sample of ~60 addresses, using the rule ids of qa/expected_rules.json.

Every expected entry has
  expected : the primary answer (None = rule should be omitted)
  accept   : answers that get full credit (ambiguous cases list more than one)
  optional : True for 'possible'-tier rules; omission is never penalised
  why      : one-line reasoning (shown in qa/report.md)

Run:  python3 qa/build_expected_lookups.py
"""

import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAV = pathlib.Path("/home/steward/hacknation/realpage/navigator")
SAMPLE = ROOT / "starter/data/sample_addresses.csv"
RESOLVED = NAV / "data/addresses_resolved.csv"
OUT = ROOT / "qa/expected_lookups.json"

# Stratified sample: every city, missing data, cutoff years, LA/SF cutoffs, new construction,
# small/odd unit counts, NJ missing units, Boston A/ codes, postal-name vs legal-city cases,
# geocoder fallbacks (no house number, bad ZIP).
SAMPLE_IDS = {
    "Los Angeles": [
        "A0001",
        "A0004",
        "A0107",
        "A0432",
        "A0445",
        "A0023",
        "A0405",
        "A0022",
        "A0330",
        "A0200",
        "A0235",
        "A0492",
    ],
    "San Francisco": [
        "A0016",
        "A0072",
        "A0477",
        "A0050",
        "A0081",
        "A0105",
        "A0106",
        "A0398",
        "A0384",
        "A0156",
    ],
    "San Diego": ["A0019", "A0094", "A0322", "A0346", "A0150"],
    "Berkeley": ["A0005", "A0018", "A0025", "A0091"],
    "Jersey City": ["A0008", "A0012", "A0026", "A0139", "A0344", "A0017"],
    "Hoboken": ["A0002", "A0227", "A0168", "A0049", "A0119", "A0040"],
    "Newark": ["A0003", "A0020", "A0104", "A0331", "A0338"],
    "Boston": ["A0036", "A0048", "A0065", "A0093", "A0098", "A0123", "A0362", "A0006"],
    "Cambridge": ["A0199", "A0291", "A0336", "A0071", "A0306"],
}
POSTAL_TO_CITY = {
    "San Ysidro": "San Diego",
    "Allston": "Boston",
    "Brighton": "Boston",
    "Dorchester": "Boston",
    "East Boston": "Boston",
    "Hyde Park": "Boston",
    "Jamaica Plain": "Boston",
    "Mattapan": "Boston",
    "Roxbury": "Boston",
    "South Boston": "Boston",
}
STATE_OF = {
    "Los Angeles": "CA",
    "San Francisco": "CA",
    "San Diego": "CA",
    "Berkeley": "CA",
    "Jersey City": "NJ",
    "Hoboken": "NJ",
    "Newark": "NJ",
    "Boston": "MA",
    "Cambridge": "MA",
}


def E(expected, accept=None, why="", optional=False):
    acc = list(accept) if accept else []
    if expected not in acc:
        acc.insert(0, expected)
    return {"expected": expected, "accept": acc, "optional": optional, "why": why}


def year(r):
    return int(r["year_built"]) if r["year_built"] else None


def units(r):
    return int(float(r["units"])) if r["units"] else None


def ca_state_cap_coverage(y):
    """Civ. Code 1947.12(d)(4)/1946.2(e)(7): CO within previous 15 years exempt (rolling; as of 2026-10-01)."""
    if y is None:
        return "unknown", "no year built: 15-year new-construction exemption cannot be tested"
    if y <= 2010:
        return "applies", f"built {y}: older than 15 years"
    if y == 2011:
        return (
            "unknown",
            "built 2011: cutoff year for the rolling 15-year exemption (CO date unknown)",
        )
    return None, f"built {y}: certificate of occupancy within the last 15 years -> exempt"


def local_rent_control(city, r):
    y = year(r)
    if city == "Los Angeles":
        if y is None:
            return "unknown", "RSO depends on CO on/before 1978-10-01; no year built"
        if y <= 1977:
            return "applies", f"built {y}: before the RSO cutoff (CO on/before 1978-10-01)"
        if y == 1978:
            return "unknown", "built 1978: RSO cutoff year (CO on/before 1978-10-01) -> unknown"
        return None, f"built {y}: after the RSO cutoff"
    if city == "San Francisco":
        if y is None:
            return "unknown", "SF rent limits depend on CO on/before 1979-06-13; no year built"
        if y <= 1978:
            return "applies", f"built {y}: CO on/before 1979-06-13"
        if y == 1979:
            return "unknown", "built 1979: SF cutoff year -> unknown"
        return None, f"built {y}: after the SF rent-control cutoff (just cause still applies)"
    if city == "Berkeley":
        return (
            "unknown",
            "Berkeley fully covered only if built before 1980; no year built in the data",
        )
    return None, "no local rent control"


def expected_for(r, city):
    y, u = year(r), units(r)
    out = {}
    st = STATE_OF[city]
    if st == "CA":
        local_id = {
            "Los Angeles": "LA-RENT-01",
            "San Francisco": "SF-RENT-01",
            "Berkeley": "BRK-RENT-01",
        }.get(city)
        lrc, lwhy = local_rent_control(city, r)
        if local_id:
            out[local_id] = E(lrc, [None] if lrc is None else None, lwhy)
        scov, swhy = ca_state_cap_coverage(y)
        if lrc == "applies":
            out["CA-RENT-01"] = E(
                "superseded", None, "local rent control applies and is stricter (1947.12(d)(3))"
            )
        elif lrc == "unknown":
            out["CA-RENT-01"] = E(
                "unknown",
                ["superseded"],
                "depends on whether local rent control covers the unit: " + lwhy,
            )
        elif city == "San Diego":
            out["CA-RENT-01"] = E(
                "unknown", None, "San Diego has no year built: 15-year exemption untestable"
            )
        else:
            out["CA-RENT-01"] = E(scov, ["unknown"] if y in (2010, 2011) else None, swhy)
        # just cause
        if city in ("Los Angeles", "San Francisco"):
            lid = "LA-JC-01" if city == "Los Angeles" else "SF-JC-01"
            out[lid] = E(
                "applies",
                None,
                "local just cause covers every multifamily unit (RSO/JCO; SF 37.9 incl. post-1979 units)",
            )
            if city == "Los Angeles":
                out["LA-JC-02"] = E(
                    "applies",
                    ["unknown"],
                    "Resident Protections Ordinance (demolition for new construction)",
                )
            else:
                out["SF-JC-02"] = E(
                    "applies", None, "relocation payments for no-fault evictions (37.9C)"
                )
            acc = [None] if (y is not None and y >= 2012) else (["unknown"] if y is None else None)
            out["CA-JC-01"] = E("superseded", acc, "local just-cause ordinance governs (1946.2(i))")
        elif city == "Berkeley":
            out["BRK-JC-01"] = E(
                "applies",
                ["unknown"],
                "fully and partially covered units have just cause; 5+ unit use code",
            )
            out["CA-JC-01"] = E(
                "superseded", ["unknown"], "local just-cause ordinance governs (1946.2(i))"
            )
        elif city == "San Diego":
            out["SD-JC-01"] = E("unknown", None, "SD TPO exempts CO within 15 years; no year built")
            out["CA-JC-01"] = E(
                "unknown",
                ["superseded"],
                "SD TPO governs if covered; both exempt new construction; no year built",
            )
        # deposits
        if city == "San Francisco" and r["use_code"] == "TIC":
            out["CA-DEP-01"] = E(
                "unknown",
                ["applies"],
                "TIC building '4 units or less' vs units=5: small-landlord exception not excludable",
            )
        elif u is not None and u >= 5:
            out["CA-DEP-01"] = E(
                "applies", None, f"{u} units: small-landlord 2-month exception cannot apply"
            )
        else:
            out["CA-DEP-01"] = E(
                "applies", ["unknown"], "unit count missing but use code says 5+ units"
            )
        out["CA-FEE-01"] = E("applies", None, "statewide")
        out["CA-SCR-01"] = E("applies", None, "statewide FEHA")
        out["CA-ALG-01"] = E("applies", None, "in force since 2026-01-01 (AB 325)")
        out["CA-SCR-02"] = E("applies", ["unknown"], "statewide FEHA regulations", optional=True)
        if city == "San Francisco":
            out["SF-ALG-01"] = E("applies", None, "citywide since 2024-10-14")
            out["SF-SCR-01"] = E(
                "unknown", None, "Fair Chance Ordinance covers affordable housing only; not in data"
            )
            out["SF-DEP-01"] = E("applies", ["unknown"], "deposit interest", optional=True)
        if city == "Los Angeles":
            out["LA-DEP-01"] = E(
                "applies" if lrc == "applies" else "unknown",
                ["unknown", "applies"],
                "RSO deposit interest",
                optional=True,
            )
        if city == "San Diego":
            out["SD-ALG-01"] = E("applies", None, "citywide since June 2025")
            out["SD-SCR-01"] = E(
                "applies",
                ["unknown"],
                "citywide source-of-income ordinance (text link-only)",
                optional=True,
            )
        if city == "Berkeley":
            out["BRK-ALG-01"] = E(
                "applies", None, "in force (2026-03-01 per ordinance / Jan 2026 per law-firm alert)"
            )
            out["BRK-SCR-01"] = E(
                "applies",
                ["unknown"],
                "Fair Chance; owner-occupied 1-3 unit exemption cannot apply to 5+ units",
            )
            out["BRK-FEE-01"] = E("applies", None, "citywide screening-fee rules")
            out["BRK-DEP-01"] = E(
                "applies", ["unknown"], "deposit interest for covered units", optional=True
            )
    elif st == "NJ":
        small = u is not None and u <= 2
        why_small = "units=2 in the data (description says 93U): owner-occupied small-premises exemption cannot be excluded"
        for rid, label in (
            ("NJ-JC-01", "Anti-Eviction Act"),
            ("NJ-DEP-01", "Security Deposit Act"),
            ("NJ-SCR-01", "Fair Chance in Housing Act"),
        ):
            if small:
                out[rid] = E("unknown", ["applies"], why_small)
            else:
                out[rid] = E(
                    "applies",
                    ["unknown"],
                    f"{label}: class 4C apartment building; owner-occupied small-premises exemption cannot apply",
                )
        out["NJ-FEE-01"] = (
            E(None, ["unknown"], "units=2: one-/two-family dwellings exempt")
            if small
            else E(
                "applies",
                ["unknown"],
                "$50 cap in force since 2026-05-01; class 4C is not a 1-2 family dwelling",
            )
        )
        out["NJ-SCR-02"] = (
            E(
                "unknown",
                ["applies"],
                "LAD exempts a unit in an owner-occupied two-family dwelling; units=2",
            )
            if small
            else E("applies", None, "LAD source of lawful income")
        )
        out["NJ-JC-02"] = E(
            "unknown" if small else "applies", ["applies", "unknown"], "reprisal protection"
        )
        out["NJ-ALG-01"] = E("not_yet_effective", None, "FAIR Act effective 2027-07-01")
        if city == "Jersey City":
            out["JC-ALG-01"] = E("applies", None, "Jersey City ban in force since June 2025 (T2)")
            if y is None:
                out["JC-RENT-01"] = E(
                    "unknown",
                    None,
                    "no year built (30-year new-construction exemption) and no unit count (1-4 units exempt)",
                )
            else:
                out["JC-RENT-01"] = E(
                    "unknown",
                    ["applies"],
                    f"built {y}; unit count missing (1-4 unit exemption), description '{r['use_description']}'",
                )
        if city == "Hoboken":
            out["HOB-ALG-01"] = E("applies", None, "Hoboken ban in force since July 2025 (T2)")
            if y is not None and y >= 1997:
                out["HOB-RENT-01"] = E(
                    None,
                    ["unknown"],
                    f"built {y}: new construction exempt from rent control for 30 years",
                )
            else:
                out["HOB-RENT-01"] = E(
                    "unknown",
                    ["applies"],
                    "no year built: 30-year new-construction exemption untestable",
                )
        if city == "Newark":
            out["NWK-RENT-01"] = E("unknown", ["applies"], "no year built / unit count for Newark")
    elif st == "MA":
        out["MA-DEP-01"] = E("applies", None, "statewide c.186 15B")
        out["MA-FEE-01"] = E("applies", None, "statewide c.186 15B(1)(b)")
        out["MA-FEE-02"] = E("applies", None, "broker-fee rule in force since 2025-08-01")
        out["MA-SCR-01"] = E("applies", ["unknown"], "c.151B 4(10)")
        out["MA-ALG-P1"] = E("pending", None, "S.2983 pending (T4)")
        out["MA-ALG-P2"] = E("pending", None, "H.5222 pending (T4)")
        out["MA-RENT-01"] = E(
            "applies", None, "c.40P bar on local rent control (never a cap)", optional=True
        )
        out["MA-SCR-02"] = E("applies", ["unknown"], "CORI regs", optional=True)
        out["MA-JC-01"] = E("applies", None, "notice-to-quit rules (c.186 11-12)")
        out["MA-JC-02"] = E("applies", None, "reprisal protection (c.186 18)")
        out["MA-JC-03"] = E("applies", None, "nonpayment notice-to-quit form (c.186 31)")
        if city == "Boston":
            out["BOS-JC-01"] = E("applies", None, "HSNA notice", optional=True)
            out["BOS-SCR-01"] = E(
                "unknown", ["applies"], "only DND-funded / IDP housing", optional=True
            )
            out["BOS-SCR-02"] = E("applies", None, "Boston fair housing", optional=True)
        if city == "Cambridge":
            out["CAM-JC-01"] = E("applies", None, "notice ordinance", optional=True)
            out["CAM-SCR-01"] = E("applies", None, "Cambridge fair housing", optional=True)
    return out


def apply_tiers(out, tiers):
    """possible-tier rules are optional (omission never penalised); everything else is scored."""
    for kid, x in out.items():
        x["optional"] = tiers.get(kid) == "possible"
    return out


def load_tiers():
    key = json.loads((ROOT / "qa/expected_rules.json").read_text())
    return {r["key_rule_id"]: r["tier"] for r in key["rules"]}


def city_of(row, resolved):
    rr = resolved.get(row["address_id"])
    if rr and rr.get("resolved_city"):
        return rr["resolved_city"]
    return POSTAL_TO_CITY.get(row["postal_city"], row["postal_city"])


def main():
    resolved = (
        {r["address_id"]: r for r in csv.DictReader(open(RESOLVED))} if RESOLVED.exists() else {}
    )
    rows = {r["address_id"]: r for r in csv.DictReader(open(SAMPLE))}

    tiers = load_tiers()
    lookups = {}
    for city, ids in SAMPLE_IDS.items():
        for aid in ids:
            r = rows[aid]
            assert city_of(r, resolved) == city, (aid, city_of(r, resolved), city)
            lookups[aid] = {
                "city": city,
                "state": STATE_OF[city],
                "postal_city": r["postal_city"],
                "year_built": r["year_built"] or None,
                "units": r["units"] or None,
                "use": f"{r['use_code']} {r['use_description']}",
                "expected": apply_tiers(expected_for(r, city), tiers),
            }

    by_city = {}
    for aid in rows:
        by_city.setdefault(city_of(rows[aid], resolved), []).append(aid)
    ca = sorted(
        a
        for c in ("Los Angeles", "San Francisco", "San Diego", "Berkeley")
        for a in by_city.get(c, [])
    )
    nj = sorted(a for c in ("Jersey City", "Hoboken", "Newark") for a in by_city.get(c, []))
    ma = sorted(a for c in ("Boston", "Cambridge") for a in by_city.get(c, []))
    jc_hob = sorted(by_city.get("Jersey City", []) + by_city.get("Hoboken", []))
    changes = {
        "T1": {
            "affected": ca,
            "why": "AB 325: not_yet_effective 2025-12-31 -> applies 2026-01-02 for every CA address",
        },
        "T2": {
            "affected": jc_hob,
            "why": "JC-ALG-01 only Jersey City, HOB-ALG-01 only Hoboken, neither Newark",
            "per_rule": {
                "JC-ALG-01": sorted(by_city.get("Jersey City", [])),
                "HOB-ALG-01": sorted(by_city.get("Hoboken", [])),
            },
        },
        "T3": {
            "affected": nj,
            "conflict_flags": jc_hob,
            "why": "FAIR Act applies 2027-07-02 to every NJ address; JC+Hoboken flagged (possible preemption of local bans)",
        },
        "T4": {
            "affected": ma,
            "why": "pending bills would affect every Boston and Cambridge address",
        },
        "T5": {"affected": [], "why": "ballot question struck: no rent cap anywhere in MA"},
    }
    out = {
        "about": "QA oracle for address results (README semantics) and change tests. Jurisdictions from "
        "navigator/data/addresses_resolved.csv (24 spot-checked via the Census geocoder: 19 matched with 0 mismatches, 5 had no Census match and use plausible fallbacks).",
        "as_of": "2026-10-01",
        "lookups": lookups,
        "changes": changes,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    n = sum(len(v["expected"]) for v in lookups.values())
    print(f"{len(lookups)} addresses, {n} expected entries -> {OUT}")
    print({k: len(v["affected"]) for k, v in changes.items()})


if __name__ == "__main__":
    main()
