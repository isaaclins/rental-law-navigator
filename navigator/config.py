"""Paths and fixed vocabulary for the navigator."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "starter"
CORPUS_DIR = STARTER / "corpus"
CORPUS_TEXT = CORPUS_DIR / "text"
MANIFEST_CSV = CORPUS_DIR / "corpus_manifest.csv"
LINKS_ONLY_CSV = CORPUS_DIR / "links_only.csv"
SCHEMA_JSON = STARTER / "schema" / "rule_record.schema.json"
CHANGE_TESTS_JSON = STARTER / "dev" / "change_tests.json"
SAMPLE_ADDRESSES = STARTER / "data" / "sample_addresses.csv"
BRIEF_TXT = ROOT / "docs" / "challenge-brief.txt"
README_MD = STARTER / "README.md"

SUPP_DIR = ROOT / "supplementary" / "text"  # link-only sources fetched once (secondary)
NEW_DOCS_DIR = ROOT / "new_docs"  # documents ingested later (e.g. the hour-16 ordinance)
DATA_DIR = ROOT / "data"
RESOLVED_CSV = DATA_DIR / "addresses_resolved.csv"
CACHE_DIR = ROOT / "cache" / "llm"
OUTPUT_DIR = ROOT / "output"
RULES_JSON = OUTPUT_DIR / "rules.json"
RAW_RULES_JSON = OUTPUT_DIR / "rules_raw.json"
LOOKUPS_JSON = OUTPUT_DIR / "lookups.json"
CHANGES_JSON = OUTPUT_DIR / "changes.json"
AUDIT_LOG = OUTPUT_DIR / "audit.jsonl"
SELFCHECK_TXT = OUTPUT_DIR / "selfcheck.txt"

DEFAULT_AS_OF = "2026-10-01"

CATEGORIES = [
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
    "screening_restrictions",
    "algorithmic_rent_setting",
]
CAT_CODE = {
    "rent_increase_limits": "RENT",
    "just_cause_eviction": "EVIC",
    "security_deposits": "DEP",
    "application_screening_fees": "FEE",
    "screening_restrictions": "SCR",
    "algorithmic_rent_setting": "ALG",
}

STATES = ["CA", "NJ", "MA"]
# jurisdiction string -> (state, short code used in rule ids)
CITIES = {
    "Los Angeles, CA": ("CA", "LA"),
    "San Francisco, CA": ("CA", "SF"),
    "San Diego, CA": ("CA", "SD"),
    "Berkeley, CA": ("CA", "BER"),
    "Santa Ana, CA": ("CA", "SA"),
    "Jersey City, NJ": ("NJ", "JC"),
    "Hoboken, NJ": ("NJ", "HOB"),
    "Newark, NJ": ("NJ", "NWK"),
    "Boston, MA": ("MA", "BOS"),
    "Cambridge, MA": ("MA", "CAM"),
}
JURISDICTIONS = STATES + list(CITIES)
JUR_CODE = {s: s for s in STATES} | {j: c for j, (_, c) in CITIES.items()}

STATUSES = ["in_force", "not_yet_effective", "pending", "failed"]
