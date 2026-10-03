"""Build FIXTURE output files for the web app (used only until output/*.json exist).

These are NOT the submission. They follow the starter schemas exactly so the UI can be
built and tested before the extraction pipeline has run. Quoted spans are copied
verbatim from the corpus by searching for a needle, so citation checks still pass.

Run: python3 web/fixtures/make_fixtures.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TEXT_DIRS = [ROOT / "starter" / "corpus" / "text", ROOT / "supplementary" / "text"]
MANIFEST = {
    r["doc_id"]: r for r in csv.DictReader((ROOT / "starter/corpus/corpus_manifest.csv").open())
}


def span(doc: str, needle: str, n: int = 260) -> str:
    for d in TEXT_DIRS:
        p = d / f"{doc}.txt"
        if p.exists():
            t = p.read_text()
            i = t.find(needle)
            if i < 0:
                raise SystemExit(f"needle not found in {doc}: {needle}")
            s = t[i : i + n]
            cut = s.rfind(". ")
            if cut > 60:
                s = s[: cut + 1]
            return s.strip()
    raise SystemExit(f"doc missing {doc}")


def url(doc: str) -> str:
    return MANIFEST[doc]["url"]


R = []


def rule(
    rid,
    jur,
    cat,
    status,
    title,
    req,
    key,
    cov,
    exm,
    eff,
    cit,
    doc,
    needle,
    conf=0.9,
    overrides=(),
    interaction=None,
    conflict=False,
    note=None,
    n=260,
):
    R.append(
        {
            "team_rule_id": rid,
            "jurisdiction": jur,
            "level": "state" if len(jur) == 2 else "city",
            "category": cat,
            "status": status,
            "title": title,
            "requirement": req,
            "key_value": key,
            "coverage_conditions": cov,
            "exemptions": exm,
            "overrides": list(overrides),
            "interaction": interaction,
            "effective_date": eff,
            "citation": cit,
            "source_doc_id": doc,
            "source_url": url(doc),
            "quoted_span": span(doc, needle, n),
            "confidence": conf,
            "conflict_flag": conflict,
            "conflict_note": note,
        }
    )


# ------------------------------------------------------------------ CA state
rule(
    "CA-RENT-01",
    "CA",
    "rent_increase_limits",
    "in_force",
    "Tenant Protection Act rent cap (AB 1482)",
    "Over any 12 months, rent can go up by at most 5% plus local inflation (CPI), and never more than 10%.",
    "5% + CPI, max 10%",
    "Buildings with a certificate of occupancy more than 15 years old",
    "Housing built in the last 15 years; single-family homes and condos owned by individuals (with notice); units covered by stricter local rent control",
    "2020-01-01",
    "Cal. Civ. Code § 1947.12",
    "D024",
    "ner of residential real property shall not, over the course",
    n=330,
)
rule(
    "CA-EVIC-01",
    "CA",
    "just_cause_eviction",
    "in_force",
    "Statewide just-cause eviction",
    "After a tenant has lived in the unit 12 months, the landlord may end the tenancy only for a reason listed in the law, stated in the written notice.",
    "Just cause after 12 months",
    "Tenancies of 12+ months",
    "Newer buildings (15 years), owner-occupied duplexes, some single-family homes",
    "2020-01-01",
    "Cal. Civ. Code § 1946.2",
    "D023",
    "sly and lawfully occupied a residential real property for 12 months",
)
rule(
    "CA-DEP-01",
    "CA",
    "security_deposits",
    "in_force",
    "Security deposit cap (AB 12)",
    "A landlord may not ask for a security deposit larger than one month's rent.",
    "1 month's rent",
    "All residential rentals",
    "Small landlords (natural person owning max 2 properties, max 4 units) may ask for two months",
    "2024-07-01",
    "Cal. Civ. Code § 1950.5",
    "D025",
    "a landlord shall not demand or receive security",
)
rule(
    "CA-FEE-01",
    "CA",
    "application_screening_fees",
    "in_force",
    "Application screening fee cap",
    "A screening fee may only cover the actual cost of the screening, up to a CPI-adjusted maximum, and no fee may be charged if no unit is available.",
    "CPI-adjusted cap (base $30, 1997)",
    "All residential rentals",
    None,
    None,
    "Cal. Civ. Code § 1950.6",
    "D026",
    "to rent a residential property from an applicant, the landlord or their agent may charge",
    conf=0.75,
    conflict=True,
    note="No single official 2026 dollar figure is published; the cap must be computed from CPI.",
)
rule(
    "CA-SCR-01",
    "CA",
    "screening_restrictions",
    "in_force",
    "Source-of-income discrimination ban (FEHA, SB 329)",
    "Landlords may not refuse or screen out applicants because they pay with a housing voucher or other lawful source of income.",
    None,
    "All housing accommodations",
    None,
    "2020-01-01",
    "Cal. Gov. Code § 12955",
    "D027",
    "It shall be unlawful",
    conf=0.85,
)
rule(
    "CA-ALG-01",
    "CA",
    "algorithmic_rent_setting",
    "in_force",
    "Common pricing algorithms (AB 325)",
    "It is unlawful to use or distribute a common pricing algorithm as part of a conspiracy to restrain trade, or to coerce others to adopt its recommended prices.",
    "Ban on coordinated pricing algorithms",
    "Statewide, all persons",
    None,
    "2026-01-01",
    "Cal. Bus. & Prof. Code § 16729 (AB 325, Stats. 2025)",
    "D022",
    "This bill would also make it unlawful for a person to use or distribute",
)
# ------------------------------------------------------------------ CA cities
rule(
    "SF-RENT-01",
    "San Francisco, CA",
    "rent_increase_limits",
    "in_force",
    "SF Rent Ordinance annual increase",
    "For rent-controlled units, the yearly increase is limited to the amount set by the Rent Board: 1.6% from March 1, 2026 to February 28, 2027.",
    "1.6% (3/1/2026 - 2/28/2027)",
    "Certificate of occupancy on or before 1979-06-13",
    "Newer buildings; single-family homes and condos (Costa-Hawkins)",
    "2026-03-01",
    "S.F. Admin. Code ch. 37",
    "D080",
    "For rent-controlled units, the annual allowable increase",
    overrides=["CA-RENT-01"],
    interaction="Stricter local rent control: the state cap (CA-RENT-01) yields to this rule.",
)
rule(
    "SF-ALG-01",
    "San Francisco, CA",
    "algorithmic_rent_setting",
    "in_force",
    "SF ban on algorithmic rent-setting devices",
    "Landlords may not sell or use algorithmic devices to set rents or manage occupancy for residential units in San Francisco.",
    "Ban on algorithmic devices",
    "All residential units in SF",
    None,
    "2024-10",
    "S.F. Admin. Code § 37.10C",
    "D081",
    "New law prohibits the sale or use of algorithmic devices",
)
rule(
    "LA-RENT-01",
    "Los Angeles, CA",
    "rent_increase_limits",
    "in_force",
    "LA Rent Stabilization Ordinance (RSO)",
    "Rent increases in RSO buildings are limited to the yearly percentage set by the Los Angeles Housing Department.",
    "Annual LAHD percentage (new formula)",
    "Built (certificate of occupancy) on or before 1978-10-01",
    "Single-family homes; newer buildings",
    "2026-02-02",
    "L.A. Mun. Code ch. XV (RSO)",
    "D041",
    "Generally, the RSO applies to rental properties that were first built on or before October 1, 1978",
    overrides=["CA-RENT-01"],
    interaction="Local rent control: the state cap yields where the RSO covers the unit.",
    conflict=True,
    note="Two published effective dates for the new formula: 2026-02-02 (LAHD) vs 2026-01-24 (landlord association).",
    conf=0.8,
)
rule(
    "SD-ALG-01",
    "San Diego, CA",
    "algorithmic_rent_setting",
    "in_force",
    "San Diego automated rent price-fixing ban",
    "Landlords may not use or sell algorithmic devices that set rents using nonpublic competitor data.",
    "Ban on algorithmic devices",
    "Citywide",
    None,
    "2025-06",
    "San Diego Mun. Code §§ 98.1101-98.1104",
    "D076",
    "Complex, AI-driven price-fixing software is used across San Diego",
    conf=0.8,
)
rule(
    "BER-ALG-01",
    "Berkeley, CA",
    "algorithmic_rent_setting",
    "in_force",
    "Berkeley coordinated pricing algorithm ban",
    "Landlords may not use coordinated pricing algorithms that rely on nonpublic competitor data to set rents.",
    "Ban on coordinated pricing algorithms",
    "Citywide",
    None,
    "2026-03-01",
    "Berkeley Mun. Code ch. 13.63",
    "D001",
    "In recent years, a number of new software programs",
    conflict=True,
    note="Ordinance text says March 1, 2026; an August 2026 law-firm alert says January 2026.",
    conf=0.7,
)
# ------------------------------------------------------------------ NJ
rule(
    "NJ-DEP-01",
    "NJ",
    "security_deposits",
    "in_force",
    "Rent Security Deposit Act",
    "A security deposit may not be more than one and a half months' rent.",
    "1.5 months' rent",
    "Residential rentals statewide",
    "Owner-occupied buildings with 2 or fewer units (unless tenant opts in); seasonal rentals",
    None,
    "N.J.S.A. 46:8-21.2",
    "D067",
    "The maximum-security deposit to be collected by the landlord",
)
rule(
    "NJ-EVIC-01",
    "NJ",
    "just_cause_eviction",
    "in_force",
    "Anti-Eviction Act",
    "A landlord may recover possession of a home only for one of the good causes listed in the Anti-Eviction Act.",
    "Good cause required",
    "Most residential tenancies",
    "Owner-occupied buildings with 2 or fewer units",
    None,
    "N.J.S.A. 2A:18-61.1",
    "D067",
    "The Anti-Eviction Act,  N.J.S.A. 2A:18-61.1",
)
rule(
    "NJ-FEE-01",
    "NJ",
    "application_screening_fees",
    "in_force",
    "Application fee cap",
    "A landlord may not charge an application fee above $50.",
    "$50",
    "Residential rental property",
    None,
    "2026-05-01",
    "N.J.S.A. 46:8-18.1 (P.L.2025, c.405)",
    "D066",
    "A landlord, or\nagent thereof, shall not require an application",
)
rule(
    "NJ-SCR-01",
    "NJ",
    "screening_restrictions",
    "in_force",
    "Fair Chance in Housing Act",
    "Landlords may not ask about criminal records on an application before making a conditional offer.",
    "No criminal-history questions before conditional offer",
    "Housing providers, most multifamily",
    "Owner-occupied 2-unit buildings; some federally assisted housing",
    "2022-01-01",
    "N.J.S.A. 46:8-52 et seq. (P.L.2021, c.110)",
    "D065",
    "shall not require an applicant to\ncomplete",
)
rule(
    "NJ-ALG-01",
    "NJ",
    "algorithmic_rent_setting",
    "not_yet_effective",
    "FAIR Act (algorithmic rent inflation)",
    "Landlords will be barred from using algorithmic systems that coordinate or inflate rents.",
    "Ban on algorithmic rent setting",
    "Statewide",
    None,
    "2027-07-01",
    "P.L.2026, c.43 (FAIR Act)",
    "D069",
    "This act shall take effect on the first day of",
    conflict=True,
    note="May preempt the Jersey City and Hoboken local bans once in force; human review needed.",
)
rule(
    "JC-ALG-01",
    "Jersey City, NJ",
    "algorithmic_rent_setting",
    "in_force",
    "Jersey City algorithmic rent coordination ban",
    "Landlords may not use algorithmic rent coordination services; fines up to $2,000 per day.",
    "Ban; up to $2,000/day",
    "Citywide",
    None,
    "2025-06",
    "Jersey City Code § 218-12",
    "D037",
    "Jersey City Code § 218-12",
    conf=0.7,
    conflict=True,
    note="Possible preemption by NJ FAIR Act (eff. 2027-07-01).",
)
rule(
    "HOB-ALG-01",
    "Hoboken, NJ",
    "algorithmic_rent_setting",
    "in_force",
    "Hoboken algorithmic rent-setting ban",
    "Landlords may not use software, algorithms or data-sharing platforms to coordinate or recommend rents.",
    "Ban on coordinated rent software",
    "Citywide",
    None,
    "2025-07",
    "Hoboken City Code ch. 158, Art. II",
    "D037",
    "Hoboken City Code, ch. 158-2",
    conf=0.7,
    conflict=True,
    note="Possible preemption by NJ FAIR Act (eff. 2027-07-01).",
)
# ------------------------------------------------------------------ MA
rule(
    "MA-DEP-01",
    "MA",
    "security_deposits",
    "in_force",
    "Security deposit limit",
    "A landlord may ask for a security deposit no larger than the first month's rent.",
    "1 month's rent",
    "All residential tenancies",
    None,
    None,
    "M.G.L. c.186 § 15B",
    "D052",
    "a security deposit equal to the first month's rent",
)
rule(
    "MA-FEE-01",
    "MA",
    "application_screening_fees",
    "in_force",
    "Upfront charges limited",
    "At the start of a tenancy a landlord may only collect first and last month's rent, a security deposit and the cost of a new lock.",
    "First + last month, deposit, lock",
    "All residential tenancies",
    None,
    None,
    "M.G.L. c.186 § 15B(1)(b)",
    "D052",
    "rent for the first full month of occupancy",
)
rule(
    "MA-RENT-01",
    "MA",
    "rent_increase_limits",
    "in_force",
    "State ban on local rent control",
    "Cities and towns in Massachusetts may not enact or enforce rent control, so there is no rent-increase cap in Boston or Cambridge.",
    "No rent cap (local rent control barred)",
    "Statewide",
    None,
    None,
    "M.G.L. c.40P § 4",
    "D048",
    "No city or town may enact, maintain or enforce rent control",
)
rule(
    "MA-ALG-P1",
    "MA",
    "algorithmic_rent_setting",
    "pending",
    "S.2983: An Act prohibiting algorithmic rent setting",
    "Pending bill that would prohibit algorithmic rent setting. It is not law.",
    None,
    "Statewide if enacted",
    None,
    None,
    "Mass. S.2983 (194th Gen. Ct.)",
    "D046",
    "An Act prohibiting algorithmic rent setting",
)
rule(
    "MA-ALG-P2",
    "MA",
    "algorithmic_rent_setting",
    "pending",
    "H.5222: preventing algorithmic rent fixing",
    "Pending bill on algorithmic rent fixing, referred to House Ways and Means. It is not law.",
    None,
    "Statewide if enacted",
    None,
    None,
    "Mass. H.5222 (194th Gen. Ct.)",
    "D045",
    "An Act relative to preventing algorithmic rent fixing",
)
rule(
    "MA-RENT-P1",
    "MA",
    "rent_increase_limits",
    "failed",
    "Rent-control ballot question (IP 25-21)",
    "A proposed statewide rent-control ballot question was struck by the Supreme Judicial Court on 2026-06-23. It will not be on the ballot and is not law.",
    None,
    None,
    None,
    None,
    "Initiative Petition 25-21",
    "D059",
    "High court derails rent control ballot question",
    conf=0.85,
)

RULES = {r["team_rule_id"]: r for r in R}


# ------------------------------------------------------------ fixture evaluator
def year(a):
    try:
        return int(a["year_built"])
    except ValueError:
        return None


def units(a):
    try:
        return int(a["units"])
    except ValueError:
        return None


def evaluate(a: dict, as_of: str) -> list[dict]:
    st, city = a["resolved_state"], a["resolved_city"]
    out = []
    for r in sorted(R, key=lambda r: r["level"] == "state"):  # city rules first (overrides)
        j = r["jurisdiction"]
        if not (j == st or j == f"{city}, {st}"):
            continue
        if r["status"] == "failed":
            continue
        rid = r["team_rule_id"]
        res, why, cf = "applies", "", r["conflict_flag"]
        if r["status"] == "pending":
            res, why = "pending", "Pending bill, not law. Listed so you can see what may change."
        elif r["effective_date"] and r["effective_date"] > as_of:
            res, why = "not_yet_effective", f"Enacted, takes effect {r['effective_date']}."
        y, u = year(a), units(a)
        if res == "applies":
            if rid == "SF-RENT-01" or rid == "LA-RENT-01":
                cutoff = 1979 if rid == "SF-RENT-01" else 1978
                if y is None:
                    res, why = (
                        "unknown",
                        "Coverage depends on the certificate-of-occupancy date; year built is missing.",
                    )
                elif y == cutoff:
                    res, why = (
                        "unknown",
                        f"Built in {y}, the cutoff year; the certificate-of-occupancy date decides.",
                    )
                elif y > cutoff:
                    continue
                else:
                    why = f"Built {y}, before the {cutoff} cutoff, multifamily ({a['units'] or 'unit count missing'} units)."
            elif rid == "CA-RENT-01":
                local = [x for x in out if x["team_rule_id"] in ("SF-RENT-01", "LA-RENT-01")]
                if y is None:
                    res, why = (
                        "unknown",
                        "Coverage depends on building age (15-year rule); year built is missing.",
                    )
                elif y > 2011:
                    continue
                elif local and local[0]["result"] == "applies":
                    res, why = (
                        "superseded",
                        f"Covered, but local rent control ({local[0]['team_rule_id']}) is stricter and governs.",
                    )
                else:
                    why = f"Built {y}, more than 15 years ago; multifamily building."
            elif rid == "CA-DEP-01":
                if u is not None and u > 4:
                    why = f"{u} units: the small-landlord exception (max 4 units) cannot apply."
                else:
                    res, why = (
                        "unknown",
                        "Small-landlord exception depends on owner type and unit count, which are not in the data.",
                    )
            elif rid == "NJ-DEP-01" or rid == "NJ-EVIC-01":
                why = "NJ class 4C (apartment) property: the owner-occupied 2-unit exemption cannot apply."
            else:
                why = f"{'Statewide' if r['level'] == 'state' else 'Citywide'} rule; the address is inside {j}."
        out.append({"team_rule_id": rid, "result": res, "explanation": why, "conflict_flag": cf})
    return out


def main():
    addrs = list(csv.DictReader((ROOT / "data/addresses_resolved.csv").open()))
    nr = [
        {
            "finding_id": f"NR-0{i}",
            "jurisdiction": j,
            "level": "city",
            "category": "rent_increase_limits",
            "status": "no_rule",
            "finding": f"{j.split(',')[0]} has no local rent control: state law bars cities and towns from enacting or enforcing it.",
            "citation": "M.G.L. c.40P § 4",
            "source_doc_id": "D048",
            "source_url": url("D048"),
            "quoted_span": span(
                "D048", "No city or town may enact, maintain or enforce rent control"
            ),
            "quoted_span_doc_id": "D048",
            "confidence": 0.9,
        }
        for i, j in enumerate(["Boston, MA", "Cambridge, MA"], 1)
    ]
    (OUT / "rules.json").write_text(
        json.dumps(
            {"as_of": "2026-10-01", "rules": R, "no_rule_findings": nr},
            indent=1,
            ensure_ascii=False,
        )
    )
    lookups = {a["address_id"]: evaluate(a, "2026-10-01") for a in addrs}
    (OUT / "lookups.json").write_text(
        json.dumps({"as_of": "2026-10-01", "lookups": lookups}, indent=1, ensure_ascii=False)
    )

    def by(f):
        return sorted(a["address_id"] for a in addrs if f(a))

    changes = {
        "T1": {
            "affected_address_ids": by(lambda a: a["resolved_state"] == "CA"),
            "notes": "CA-ALG-01 is not_yet_effective on 2025-12-31 and applies on 2026-01-02 for every CA address.",
        },
        "T2": {
            "affected_address_ids": by(lambda a: a["resolved_city"] in ("Hoboken", "Jersey City")),
            "notes": "HOB-ALG-01 only for Hoboken, JC-ALG-01 only for Jersey City; none for Newark.",
        },
        "T3": {
            "affected_address_ids": by(lambda a: a["resolved_state"] == "NJ"),
            "conflict_flag_address_ids": by(
                lambda a: a["resolved_city"] in ("Hoboken", "Jersey City")
            ),
            "notes": "NJ-ALG-01 not_yet_effective on 2026-10-01, applies on 2027-07-02. JC/HOB carry a conflict flag (possible preemption).",
        },
        "T4": {
            "affected_address_ids": by(lambda a: a["resolved_state"] == "MA"),
            "notes": "MA-ALG-P1 / MA-ALG-P2 are pending bills; listed addresses would be affected if enacted.",
        },
        "T5": {
            "affected_address_ids": [],
            "notes": "IP 25-21 recorded as failed (MA-RENT-P1). No rent cap reported for Boston or Cambridge.",
        },
    }
    (OUT / "changes.json").write_text(json.dumps(changes, indent=1))
    audit = [
        {
            "ts": "2026-10-03T18:02:11Z",
            "event": "extract",
            "doc_id": r["source_doc_id"],
            "model": "fixture",
            "rule_ids": [r["team_rule_id"]],
            "note": "fixture record (web UI development only)",
        }
        for r in R
    ]
    (OUT / "audit.jsonl").write_text("\n".join(json.dumps(x) for x in audit) + "\n")
    print(f"fixtures: {len(R)} rules, {len(lookups)} lookups")


if __name__ == "__main__":
    main()
