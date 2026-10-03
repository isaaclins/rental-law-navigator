"""Prompts and JSON schemas for LLM rule extraction.

Nothing here encodes a specific rule: the prompts define the output contract (fields, coverage
object semantics, citation style) and pass the starter pack's own guidance (brief examples table,
README open questions) as context. All rules come from the model reading the documents.
"""

from __future__ import annotations

import json
import re

from .config import BRIEF_TXT, CATEGORIES, CITIES, DEFAULT_AS_OF, README_MD, STATES

PROMPT_VERSION = "v9"


def _brief_examples() -> str:
    try:
        t = BRIEF_TXT.read_text(encoding="utf-8")
        m = re.search(r"Rule categories, with real examples.*?(?=The answer key holds)", t, re.S)
        return m.group(0).strip() if m else ""
    except OSError:
        return ""


def _readme_open_questions() -> str:
    try:
        t = README_MD.read_text(encoding="utf-8")
        m = re.search(r"## 9\..*?(?=\n\*Not legal advice|\Z)", t, re.S)
        return m.group(0).strip() if m else ""
    except OSError:
        return ""


JURISDICTION_LIST = ", ".join(f'"{s}"' for s in STATES) + ", " + ", ".join(f'"{c}"' for c in CITIES)

CITATION_STYLE = """Citation style (use the official form; put bill numbers / ordinance numbers / popular names in citation_aliases):
- California statutes: "Cal. Civ. Code § 1947.12", "Cal. Gov. Code § 12955", "Cal. Bus. & Prof. Code § 16729".
- New Jersey: codified statutes "N.J.S.A. 46:8-21.2"; recent session laws known by chapter "P.L.2025, c.405" (give the codified N.J.S.A. cite as an alias).
- Massachusetts: "G.L. c. 186, § 15B", "G.L. c. 40P, § 4", "G.L. c. 112, § 87DDD½"; bills "S.2983", "H.5222"; ballot initiatives "Initiative Petition 25-21".
- City codes: "S.F. Admin. Code § 37.10C" (SF Rent Ordinance = "S.F. Admin. Code ch. 37"), "L.A. Mun. Code § 151.06", "San Diego Mun. Code §§ 98.1101-98.1104",
  "Berkeley Mun. Code ch. 13.63", "Santa Ana Ord. NS-3090", "Jersey City Code § 218-12", "Hoboken City Code ch. 158, Art. II",
  "Boston City Code § 10-11.7", "Cambridge Mun. Code ch. 8.71". Use the most specific section the document supports.
Cite the law itself, never the web page."""

COVERAGE_SPEC = """The `coverage` object is evaluated by a deterministic program against public parcel data that has ONLY:
state, legal city, year_built (often missing), total units in the building (often missing; use codes say "5+ units"), use code.
There are NO owner names, owner types, owner-occupancy, subsidy, lease or tenant facts. Fill it so the program decides correctly:
- min_units / max_units: building unit-count thresholds for coverage (null if none). Example: ordinance exempts 1-4 unit properties -> min_units 5.
- construction_cutoff: rule covers only buildings by construction / certificate-of-occupancy (CO) date:
  {"basis": "certificate_of_occupancy"|"year_built"|"construction_completed", "covered_if": "on_or_before"|"before"|"after"|"on_or_after", "date": "YYYY-MM-DD"}.
  Example: "applies to units with a CO issued on or before June 13, 1979" -> {"basis":"certificate_of_occupancy","covered_if":"on_or_before","date":"1979-06-13"}.
  Do NOT set it for a just-cause rule that also covers newer units, even if the rent cap of the same ordinance has a cutoff.
- new_construction_exemption: rolling exemption for recent buildings: {"years": N, "basis": "certificate_of_occupancy"|"construction_completed", "requires_owner_filing": true|false}.
  Example: "housing issued a certificate of occupancy within the previous 15 years" -> {"years":15,"basis":"certificate_of_occupancy","requires_owner_filing":false}.
  Include such an exemption when it applies to this rule by operation of another law stated in the documents (e.g. a state new-construction exemption from local rent control).
- owner_occupied_exemption_max_units: exempt when the owner lives in a building with at most N units (null if none).
- requires_unknown_facts: facts that must be TRUE for the rule to cover an ordinary private apartment building and that parcel data cannot show,
  e.g. "property receives City funding or has income-restricted units", "unit is in an affordable housing project". Leave EMPTY for rules that cover
  private rental housing generally, even if some exemptions (owner type, deed-restricted affordable housing, dormitories, owner-occupied duplexes,
  single-family homes, condos) cannot be checked -> list those in unverifiable_exemptions instead.
- unverifiable_exemptions: exemptions that depend on facts not in the data (informational).
- yields_to_local_rule: true for a STATE rule that by its own terms does not apply where a local ordinance of the same category covers the unit
  (e.g. a state rent cap that exempts units under stricter local rent control; a state just-cause law that yields to local just-cause ordinances).
- supersedes_state_rule: true for a LOCAL rule that governs instead of the state rule of the same category where both cover a unit.
- may_preempt_local_rules: true for a STATE rule whose text prohibits or may preempt conflicting local ordinances of the same category (flag for human review).
- landlord_size_condition: text, e.g. "owner of 2 or fewer properties with 4 or fewer units" (informational; a 5+ unit building cannot qualify for such small-landlord rules)."""

SYSTEM = f"""You are a careful legal-information extraction engine for the "Rental Housing Law Navigator" (not legal advice).
You read one source document at a time and output structured rule records as JSON. Accuracy matters more than volume.

SCOPE
- Jurisdiction strings (use exactly): {JURISDICTION_LIST}. level = "state" for CA/NJ/MA, "city" for cities.
- Categories (use exactly): {", ".join(CATEGORIES)}.
  rent_increase_limits: caps/formulas on rent increases, rent control/stabilization, and state bars on local rent control.
  just_cause_eviction: limits on grounds for eviction or non-renewal, eviction/termination notice requirements, notice-to-quit rules,
    relocation assistance, retaliation/reprisal protections tied to eviction.
  security_deposits: deposit caps, deposit handling/interest/return rules.
  application_screening_fees: application/screening fee caps, allowed upfront charges, receipts/refunds, broker-fee allocation.
  screening_restrictions: limits on criminal-history screening, source-of-income / voucher discrimination, other tenant-selection limits.
  algorithmic_rent_setting: bans/limits on algorithmic or coordinated rent-pricing software, incl. pending bills.
- Query date ("as of"): {DEFAULT_AS_OF}.

WHAT IS ONE RULE
- One record per distinct legal provision (statute section, ordinance, ordinance chapter, bill, ballot question) per category.
  Do not split one section into several records per subdivision; do not merge different statutes. A section that regulates two
  categories (e.g. a deposit cap and a limit on upfront charges) gives two records.
- Include: enacted laws (in force or with a future effective date), pending bills (legal_status "pending_bill"),
  and measures that failed / were struck / died (legal_status "failed"), e.g. a ballot question removed by a court or a home-rule
  petition sent to study.
- An official agency page (city or state website, rent board, fair-housing office) that states what landlords in this jurisdiction
  must or must not do is enough for a record even without a code section; cite the law by the name the page uses.
- A bill page whose history shows it was accompanied by / sent to a study order, or otherwise died with its session, is a failed
  measure: emit a record with legal_status "failed" (and a no_rule_finding if nothing of that category is in force at that level).
- If the document states coverage facts for another rule of the same local law in a different category (e.g. a just-cause page
  saying which units are exempt from the rent-increase limits), also emit a record for that related rule with those coverage facts.
- A council motion, policy order, staff report request or study is NOT a rule: report it as a no_rule_finding if it shows that no
  rule exists at that level for that category.
- The manifest jurisdiction tag is only a hint. A document (especially a law-firm alert, news article or table) may describe laws of
  several in-scope jurisdictions: extract a separate record for EACH in-scope jurisdiction's law it describes. Ignore out-of-scope
  places (other states, other cities, counties).
- A record needs the document to state the operative requirement of that law (what it requires, prohibits or caps). Do not create a
  record for a law that is merely named or cross-referenced (e.g. a required notice text that mentions another statute).
- Never invent rules, numbers, dates or citations. If the document is silent, leave fields null.

FIELDS
- quoted_span: copy ONE contiguous passage EXACTLY as it appears in the document (same words, punctuation, numbers; you may only
  change line breaks to spaces), 20-400 characters, that states the core requirement. No ellipses, no paraphrase, no added words.
- requirement: one or two plain-language sentences a renter can act on. key_value: the headline number/formula (e.g. "1 month's rent",
  "5% + CPI, max 10%", "$50 per applicant", "ban on algorithmic devices using nonpublic competitor data").
- legal_status: "enacted" | "pending_bill" | "failed".
- effective_date: ISO "YYYY-MM-DD" (or "YYYY-MM" / "YYYY" if only that precision is known) when the core requirement took or takes
  effect; compute it when the text gives a rule (e.g. "first day of the fourth month next following enactment" with approval
  2026-01-20 -> 2026-05-01; "thirtieth day from and after final passage"). Prefer the date the substantive rule first took effect over
  the date of a later technical amendment, and say what you used in effective_date_note. For pending/failed measures: null.
- enacted_date (signature/adoption) and sunset_date (repeal/expiry) when stated.
- conflict_note: set when sources disagree (e.g. two published effective dates), when a state law may preempt a local one, or when
  coverage is uncertain; prefer the date from the official law text for effective_date and put the other date in the note.
- confidence: 0-1.
{CITATION_STYLE}

COVERAGE
{COVERAGE_SPEC}

NO-RULE FINDINGS
Report a no_rule_finding when the document shows there is NO rule of a category at a jurisdiction level as of the query date
(e.g. a state statute barring local rent control means "no local rent cap" for that state's cities; a state agency saying the state has
no rent control law; only a motion/policy order exists; a proposal was struck). Give the jurisdiction the finding is about, the
category, a short reason, the supporting citation and a verbatim quoted_span.

CHALLENGE-PROVIDED CONTEXT (organizer summaries; the documents remain the source of truth, never copy spans from here):
{_brief_examples()}

{_readme_open_questions()}

Output JSON only, matching the schema."""


_coverage_schema = {
    "type": "object",
    "properties": {
        "min_units": {"type": ["integer", "null"]},
        "max_units": {"type": ["integer", "null"]},
        "construction_cutoff": {
            "type": ["object", "null"],
            "properties": {
                "basis": {
                    "type": "string",
                    "enum": ["certificate_of_occupancy", "year_built", "construction_completed"],
                },
                "covered_if": {
                    "type": "string",
                    "enum": ["on_or_before", "before", "after", "on_or_after"],
                },
                "date": {"type": "string"},
            },
            "required": ["basis", "covered_if", "date"],
        },
        "new_construction_exemption": {
            "type": ["object", "null"],
            "properties": {
                "years": {"type": "integer"},
                "basis": {"type": "string"},
                "requires_owner_filing": {"type": "boolean"},
            },
            "required": ["years"],
        },
        "owner_occupied_exemption_max_units": {"type": ["integer", "null"]},
        "requires_unknown_facts": {"type": "array", "items": {"type": "string"}},
        "unverifiable_exemptions": {"type": "array", "items": {"type": "string"}},
        "yields_to_local_rule": {"type": "boolean"},
        "supersedes_state_rule": {"type": "boolean"},
        "may_preempt_local_rules": {"type": "boolean"},
        "landlord_size_condition": {"type": ["string", "null"]},
    },
    "required": [
        "requires_unknown_facts",
        "yields_to_local_rule",
        "supersedes_state_rule",
        "may_preempt_local_rules",
    ],
}

_rule_props = {
    "jurisdiction": {"type": "string"},
    "level": {"type": "string", "enum": ["state", "city"]},
    "category": {"type": "string", "enum": CATEGORIES},
    "legal_status": {"type": "string", "enum": ["enacted", "pending_bill", "failed"]},
    "title": {"type": "string"},
    "requirement": {"type": "string"},
    "key_value": {"type": ["string", "null"]},
    "coverage_conditions": {"type": ["string", "null"]},
    "exemptions": {"type": ["string", "null"]},
    "penalty": {"type": ["string", "null"]},
    "interaction": {"type": ["string", "null"]},
    "effective_date": {"type": ["string", "null"]},
    "effective_date_note": {"type": ["string", "null"]},
    "enacted_date": {"type": ["string", "null"]},
    "sunset_date": {"type": ["string", "null"]},
    "citation": {"type": "string"},
    "citation_aliases": {"type": "array", "items": {"type": "string"}},
    "quoted_span": {"type": "string"},
    "confidence": {"type": "number"},
    "conflict_note": {"type": ["string", "null"]},
    "coverage": _coverage_schema,
}

RULE_SCHEMA = {
    "type": "object",
    "properties": _rule_props,
    "required": [
        "jurisdiction",
        "level",
        "category",
        "legal_status",
        "title",
        "requirement",
        "citation",
        "quoted_span",
        "effective_date",
        "coverage",
        "confidence",
    ],
}

NO_RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "jurisdiction": {"type": "string"},
        "level": {"type": "string", "enum": ["state", "city"]},
        "category": {"type": "string", "enum": CATEGORIES},
        "finding": {"type": "string"},
        "basis_citation": {"type": ["string", "null"]},
        "quoted_span": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["jurisdiction", "level", "category", "finding", "quoted_span"],
}

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {"type": "array", "items": RULE_SCHEMA},
        "no_rule_findings": {"type": "array", "items": NO_RULE_SCHEMA},
        "doc_summary": {"type": "string"},
    },
    "required": ["rules", "no_rule_findings", "doc_summary"],
}


def extract_prompt(doc, chunk_text: str, chunk_no: int, n_chunks: int) -> str:
    part = (
        f" (part {chunk_no + 1} of {n_chunks}; extract only what this part supports)"
        if n_chunks > 1
        else ""
    )
    return f"""DOCUMENT {doc.doc_id}{part}
manifest jurisdiction tag: {doc.jurisdictions or "unknown"}
source type: {doc.source_type} ({"official primary source" if doc.is_primary else "secondary source: law firm / news / mirror"})
url: {doc.url}
retrieved: {doc.retrieved_at}

<document>
{chunk_text}
</document>

Extract every rule and no-rule finding this document supports for the in-scope jurisdictions and categories."""


# ------------------------------------------------------------------ consolidation / completeness pass
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    **_rule_props,
                    "from_candidates": {"type": "array", "items": {"type": "string"}},
                    "source_doc_id": {"type": "string"},
                    "unverified_link_only": {"type": "boolean"},
                    "review_note": {"type": ["string", "null"]},
                },
                "required": RULE_SCHEMA["required"] + ["from_candidates", "source_doc_id"],
            },
        },
        "no_rule_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {**NO_RULE_SCHEMA["properties"], "source_doc_id": {"type": "string"}},
                "required": NO_RULE_SCHEMA["required"] + ["source_doc_id"],
            },
        },
        "dropped_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"cand_id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["cand_id", "reason"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["rules", "no_rule_findings", "dropped_candidates", "notes"],
}

REVIEW_SYSTEM = (
    SYSTEM
    + """

YOU ARE NOW IN THE CONSOLIDATION + COMPLETENESS PASS FOR ONE JURISDICTION.
You get (a) candidate records extracted earlier from single documents (ids like c12), (b) the full text of every document tagged
to this jurisdiction or cited by a candidate, and (c) link-only sources for this jurisdiction whose text could not be captured.
Produce the FINAL rule list for this jurisdiction:
1. Merge candidates that describe the same legal provision (same law/section, or the same ordinance described by several pages)
   into one record; list all merged ids in from_candidates. Keep different provisions separate. Pick the official citation,
   the best-supported effective date (official law text first; put disagreements in conflict_note), and a quoted_span copied exactly
   from ONE document given as source_doc_id (prefer the official primary source).
2. Fix errors: wrong category, wrong jurisdiction, wrong status, a coverage object that would mis-evaluate (re-read COVERAGE).
   Drop candidates that are not real rules (motions, studies, generic information) or are out of scope.
3. COMPLETENESS: for every category with no rule at this jurisdiction level, re-read the documents. If a document supports a rule,
   add it (from_candidates = []). If the documents show there is no rule, add a no_rule_finding. If a rule very likely exists only in a
   link-only source listed in (c) that you cannot read, you may add it with unverified_link_only=true, source_doc_id = that link-only
   doc id, confidence <= 0.4, a quoted_span copied exactly from a provided document that supports the general proposition (state its
   doc id in the conflict_note), and conflict_note explaining it is unverified. Do this only when you are confident the law exists.
4. Do not duplicate rules that belong to another jurisdiction (state rules stay at the state; city rules at the city).
5. GRANULARITY: one record per law (statute section family, act, ordinance / ordinance chapter, bill, ballot measure) per category -
   the provision a renter or housing provider would look up; usually 0-3 records per category. Fold supporting sections of the same
   act (definitions, notice periods, penalties, deposit handling and return deadlines, interest) into that act's main record and cite
   its headline section. Keep separate records only for separate laws. From broad multi-topic guides (e.g. a statewide landlord-tenant
   handbook) keep only the principal law per category, not every statute mentioned in passing.
6. A law whose only effect is to exempt buildings from another rule (e.g. a new-construction exemption from local rent control) is not
   a rule of its own: express it in the coverage of the rule it limits (for a city review, use the state context given below).
8. conflict_note is ONLY for (a) sources that disagree on a date or value, (b) a possible legal conflict or preemption between
   laws, (c) unverified link-only rules. Put every other caveat (citation inferred, section not stated, coverage caveats) in
   review_note. Precedence that the coverage flags already express (state rule yields to local) is not a conflict.
9. Annual rate bulletins, allowable-increase announcements and deposit-interest rate tables belong to the record of the ordinance
   that requires them (fold them in; mention the current figure in key_value / requirement). A relocation-assistance requirement
   that is its own code section (e.g. a separate "relocation payments" section) stays a separate just_cause_eviction record.
10. Citations must be stated in or directly identifiable from the documents. If the documents name a law but never give its
   section, cite it by the name/chapter the documents use; never cite a regulation or section the documents do not mention.
11. Keep every rule that an official source of this jurisdiction states, even when the page is short (e.g. a city landing page
   saying an ordinance protects people with conviction records in affordable housing is enough for a record with
   requires_unknown_facts). Only laws regulating the landlord-tenant relationship belong here: drop professional-licensing or agency
   rules that do not themselves limit what a landlord may do or charge.
12. Complementary local coverage: when an ordinance covers only units NOT covered by another ordinance of the same city (e.g. a
   just-cause ordinance for units outside the city's rent stabilization ordinance, which covers units built on or before a date),
   give it the complementary construction_cutoff ("after" that date) so both are never reported for the same building.
13. Link-only municipal code sources listed in (c) usually hold the city's core landlord-tenant ordinances. If you know with high
   confidence that such an ordinance of this city is in force in one of the six categories (e.g. municipal rent control/leveling),
   add it per step 3 as unverified_link_only rather than leaving the category empty.
14. ACCOUNT FOR EVERY CANDIDATE: each candidate id must appear either in some rule's from_candidates or in dropped_candidates with
   a concrete reason (e.g. "duplicate of X", "motion, not a law", "out of scope"). Candidates you do not account for are restored.
15. Quote OFFICIAL primary documents (type not "secondary") whenever any official document states the rule, even briefly; use a
   secondary source as source_doc_id only when no official document supports the rule.
16. A failed or expired proposal (struck ballot question, home-rule petition sent to study, bill that died) gets a rule record with
   legal_status "failed" in its category; add a no_rule_finding for the same cell as well when nothing is in force there.
17. effective_date: when the documents give only an enactment/adoption date or year (e.g. a session law "P.L.1974, c.49", an
   ordinance "passed April 14, 2020", a measure approved "November 2024"), use it (YYYY, YYYY-MM or YYYY-MM-DD) and say so in
   effective_date_note. Use null only when the documents give no date at all.
7. Re-check coverage objects against the COVERAGE contract: a rule that covers private apartment buildings generally must have empty
   requires_unknown_facts; cutoffs must match the document's exact dates; just-cause rules covering newer units must not carry a
   rent-control construction cutoff."""
)


def review_prompt(
    jurisdiction: str,
    candidates: list[dict],
    docs: list,
    link_only: list[dict],
    context: list[dict] | None = None,
) -> str:
    cand_txt = json.dumps(candidates, ensure_ascii=False, indent=1)
    doc_txt = "\n\n".join(
        f'<document id="{d.doc_id}" type="{d.source_type}" url="{d.url}" retrieved="{d.retrieved_at}">\n{d.text}\n</document>'
        for d in docs
    )
    lo = (
        "\n".join(
            f"- {r['doc_id']} ({r['jurisdictions']}, {r['source_type']}): {r['url']}"
            for r in link_only
        )
        or "- none"
    )
    ctx = (
        "\n".join(
            f"- [{c.get('jurisdiction')}] {c.get('category')}: {c.get('citation') or c.get('basis_citation')} - "
            f"{c.get('key_value') or c.get('finding') or ''} | {c.get('requirement') or ''}"[:400]
            for c in (context or [])
        )
        or "- none"
    )
    return f"""JURISDICTION: {jurisdiction}

(a) CANDIDATE RECORDS
{cand_txt}

(b) DOCUMENTS
{doc_txt}

(c) LINK-ONLY SOURCES WITHOUT CAPTURED TEXT
{lo}

(d) CONTEXT ONLY - candidate rules at the other level of government (do NOT output these; use them for interactions,
    precedence flags and exemptions that state law imposes on local rules)
{ctx}

Return the final rules and no-rule findings for {jurisdiction} only."""


SPAN_FIX_SCHEMA = {
    "type": "object",
    "properties": {
        "fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "quoted_span": {"type": "string"}},
                "required": ["id", "quoted_span"],
            },
        }
    },
    "required": ["fixes"],
}


def span_fix_prompt(doc, items: list[dict]) -> str:
    lst = "\n".join(
        f'- id {i["id"]}: rule "{i["title"]}" ({i["citation"]}); rejected span: "{i["quoted_span"]}"'
        for i in items
    )
    return f"""The quoted_span values below were NOT found verbatim in document {doc.doc_id}. For each id, copy a passage of 20-400
characters EXACTLY as it appears in the document (character for character, only line breaks may become spaces) that supports the rule.

{lst}

<document>
{doc.text}
</document>"""


# ------------------------------------------------------------------ empty-cell probe
PROBE_SCHEMA = {
    "type": "object",
    "properties": {
        "cells": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "verdict": {
                        "type": "string",
                        "enum": ["no_rule", "rule_in_link_only_source", "undetermined"],
                    },
                    "reason": {"type": "string"},
                    "basis_citation": {"type": ["string", "null"]},
                    "quoted_span": {"type": ["string", "null"]},
                    "span_doc_id": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "rule": {
                        "type": ["object", "null"],
                        "properties": {**_rule_props, "source_doc_id": {"type": "string"}},
                    },
                },
                "required": ["category", "verdict", "reason", "confidence"],
            },
        },
    },
    "required": ["cells"],
}

PROBE_SYSTEM = (
    SYSTEM
    + """

YOU ARE NOW IN THE EMPTY-CELL PASS FOR ONE JURISDICTION. The categories listed have no extracted rule at this jurisdiction level.
For EACH listed category decide:
- "no_rule": there is no rule of this category at THIS level of government (e.g. a city with no local ordinance of that kind; the
  state rule covers it instead; state law bars local rules; only a motion exists). Give the reason, basis_citation (the law that shows
  it, or null), and if any provided document supports the finding, a verbatim quoted_span with its span_doc_id (else null).
- "rule_in_link_only_source": you are highly confident (>= 0.8) that this jurisdiction has an in-force law of this category, and the
  listed link-only sources for this jurisdiction (e.g. municipal code pages whose text we could not capture) are where it would be
  published. Your confidence is about the law existing; set source_doc_id to the most plausible listed link-only doc id (you do
  not need to know exactly which page holds it). Fill `rule` as a full record (legal_status, citation,
  key_value, coverage per the COVERAGE contract, effective_date if known) with source_doc_id = that link-only doc id; quoted_span may
  be copied from a provided document that supports the general proposition (set span_doc_id) or null.
- "undetermined": neither is clear.
Never invent facts; prefer "undetermined" over guessing."""
)


def probe_prompt(
    jurisdiction: str, empty: list[str], docs: list, link_only: list[dict], context: list[dict]
) -> str:
    doc_txt = "\n\n".join(
        f'<document id="{d.doc_id}" type="{d.source_type}">\n{d.text}\n</document>' for d in docs
    )
    lo = (
        "\n".join(
            f"- {r['doc_id']} ({r['jurisdictions']}, {r['source_type']}): {r['url']}"
            for r in link_only
        )
        or "- none"
    )
    ctx = (
        "\n".join(
            f"- [{c.get('jurisdiction')}] {c.get('category')}: {c.get('citation') or c.get('basis_citation')} - "
            f"{c.get('key_value') or c.get('finding') or ''}"[:300]
            for c in context
        )
        or "- none"
    )
    return f"""JURISDICTION: {jurisdiction}
EMPTY CATEGORIES: {", ".join(empty)}

RULES ALREADY RECORDED (this jurisdiction and its state; context only)
{ctx}

LINK-ONLY SOURCES WITHOUT CAPTURED TEXT
{lo}

DOCUMENTS
{doc_txt}

Return one entry per empty category."""


# ------------------------------------------------------------------ coverage audit (evidence-grounded)
COVERAGE_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "audits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_ref": {"type": "string"},
                    "coverage": _coverage_schema,
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "doc_id": {"type": "string"},
                                "quoted_span": {"type": "string"},
                            },
                            "required": ["field", "doc_id", "quoted_span"],
                        },
                    },
                    "official_quote": {
                        "type": ["object", "null"],
                        "properties": {
                            "doc_id": {"type": "string"},
                            "quoted_span": {"type": "string"},
                        },
                    },
                    "comment": {"type": "string"},
                },
                "required": ["rule_ref", "coverage", "evidence"],
            },
        },
    },
    "required": ["audits"],
}

COVERAGE_AUDIT_SYSTEM = (
    SYSTEM
    + """

YOU ARE NOW AUDITING COVERAGE OBJECTS for the final rules of one jurisdiction. For EACH rule, re-read ALL provided documents
(coverage facts are often stated on a different page than the rule, e.g. a just-cause page saying which units are exempt from rent
limits, a calculator page, a FAQ) and return the corrected coverage object per the COVERAGE contract.
For every non-empty min_units, max_units, construction_cutoff, new_construction_exemption, owner_occupied_exemption_max_units and
requires_unknown_facts value, give evidence: the field name, doc_id and a verbatim quoted_span (copied exactly) that states it.
Values without verifiable evidence are discarded. For a rule whose quote_source is "secondary", give official_quote: a passage
(20-400 characters, copied exactly) from an OFFICIAL document that states or names the rule (a heading naming the requirement is
acceptable), or null if no official document mentions it. Keep yields_to_local_rule / supersedes_state_rule / may_preempt_local_rules
consistent with the documents and the context."""
)


def coverage_audit_prompt(
    jurisdiction: str, rules: list[dict], docs: list, context: list[dict]
) -> str:
    doc_txt = "\n\n".join(
        f'<document id="{d.doc_id}" type="{d.source_type}">\n{d.text}\n</document>' for d in docs
    )
    rl = json.dumps(rules, ensure_ascii=False, indent=1)
    ctx = (
        "\n".join(
            f"- [{c.get('jurisdiction')}] {c.get('category')}: {c.get('citation')} - {c.get('key_value') or ''}"[
                :300
            ]
            for c in context
        )
        or "- none"
    )
    return f"""JURISDICTION: {jurisdiction}

RULES TO AUDIT (rule_ref = ref)
{rl}

CONTEXT (other level of government)
{ctx}

DOCUMENTS
{doc_txt}

Return one audit per rule."""


# ------------------------------------------------------------------ date audit (first effect vs. current version)
DATE_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "dates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_ref": {"type": "string"},
                    "requirement_is_new": {"type": "boolean"},
                    "in_force_since": {"type": ["string", "null"]},
                    "in_force_since_evidence": {
                        "type": ["object", "null"],
                        "properties": {
                            "doc_id": {"type": "string"},
                            "quoted_span": {"type": "string"},
                        },
                    },
                    "current_version_effective": {"type": ["string", "null"]},
                    "prior_version_note": {"type": ["string", "null"]},
                },
                "required": [
                    "rule_ref",
                    "requirement_is_new",
                    "in_force_since",
                    "current_version_effective",
                ],
            },
        }
    },
    "required": ["dates"],
}

DATE_AUDIT_SYSTEM = (
    SYSTEM
    + """

YOU ARE NOW AUDITING DATES for the final rules of one jurisdiction. Each record has an effective_date that may be the date the
rule first took effect OR only the date of a later amendment, re-enactment, annual figure update or rate period of a law that was
already in force. A date program uses your answer to decide whether the rule existed on a past query date.
For EACH rule:
- requirement_is_new: true if nothing of this kind applied before the effective_date given, e.g. a new ban on pricing algorithms
  added to an older antitrust statute, or a new ordinance. false if an earlier version of the same kind of rule applied before
  (e.g. a deposit cap lowered by an amendment: a higher cap existed before; a rent ordinance whose annual allowable increase is
  reset each year; a statute re-enacted or amended with a new operative date).
- in_force_since: ISO date (or YYYY-MM / YYYY) when the requirement of this kind first applied, if a provided document states it
  or it is stated by the law's own text (e.g. "applies to rent increases on or after March 15, 2019", an ordinance enacted in 1979).
  Give in_force_since_evidence: doc_id + a passage copied exactly that states it. Use null when no document states it.
- current_version_effective: date the current text / current figure took effect (amendment operative date, current rate period
  start), or null if the rule has not changed since it first took effect.
- prior_version_note: one sentence on what applied before the current version (e.g. "AB 1482 cap in force since 2020; SB 567
  re-enacted it operative 2024-04-01"; "annual allowable increase is reset each March 1").
Never invent dates; null is fine."""
)


def date_audit_prompt(jurisdiction: str, rules: list[dict], docs: list) -> str:
    doc_txt = "\n\n".join(
        f'<document id="{d.doc_id}" type="{d.source_type}">\n{d.text}\n</document>' for d in docs
    )
    rl = json.dumps(rules, ensure_ascii=False, indent=1)
    return f"""JURISDICTION: {jurisdiction}

RULES (rule_ref = ref)
{rl}

DOCUMENTS
{doc_txt}

Return one entry per rule."""
