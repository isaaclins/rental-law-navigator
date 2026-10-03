# Rental Housing Law Navigator — Participant Guide

MIT AI Hackathon · 24 hours · public data only · Realpage discussion draft, October 2026

> This guide and the starter pack are everything you need to build. Read sections 1–4 before you start coding.

---

## 1. The task in one paragraph

For any apartment address in the sample, your system must answer: **which housing rules apply here on the query date, and how do the supplied change cases affect the answer?** It reads a corpus of real state and city law, turns each rule into a structured record (Module A), resolves each address to its state and city and tests each rule's coverage conditions (Module B), and reports which addresses each supplied law-change case affects (Module C). Every answer must cite the source text.

**Default query date: 2026-10-01.** Some tests ask for other dates.

## 2. Minimum viable submission

If you run short on time, this is what counts:

1. **Modules A and B** on the supplied sample addresses. If you run short on time, prioritize accurate extraction, jurisdiction resolution and citations.
2. Module C (change tracking) and the plain-language view come next.
3. Stretch goals (Spanish view, confidence indicators, a new jurisdiction) only after that.

## 3. Rules of the event

- **Extraction must be automated.** Rules must come from your system reading the supplied corpus, not hand-coded. You should show the extraction pipeline in the demo.
- **Use the starter pack.** You may consult the public sources in section 6, but do not bulk-scrape sites whose terms forbid it.
- **No non-public data.** No customer, resident or pricing data.
- **"Unknown" is a valid answer** when coverage depends on a fact the data doesn't have. Say unknown rather than guessing when the supplied data is insufficient.
- **Not legal advice.** Every interface you build must say so.
- **Logistics (TBD by organizers):** event dates and location · team size · model / API access and credits · submission method and deadline · code and data licensing · contact. These will be confirmed at registration.

## 4. What's in the starter pack

| Path | What it is |
|---|---|
| `corpus/corpus_manifest.csv` | 87 source documents: `doc_id`, jurisdiction, URL, source type, capture status |
| `corpus/text/` | Plain-text copies of official documents, each headed with its source URL and retrieval date |
| `corpus/links_only.csv` | Sources without supplied text, including publisher pages awaiting terms review and official pages that blocked capture |
| `data/sample_addresses.csv` | ~500 multifamily properties from public assessor data (see 4.1) |
| `schema/rule_record.schema.json` | Required format for every rule record |
| `schema/sample_rule_record.json` | One worked example |
| `dev/change_tests.json` | The five deterministic change-tracking tests (T1-T5) |
| `submission_templates/` | Example `rules.json`, `lookups.json`, `changes.json` |

### 4.1 Sample addresses

Columns: `address_id, street_address, postal_city, state, zip, year_built, units, use_code, use_description, source_dataset, retrieved_at`.

- **The jurisdiction is not given.** `postal_city` is the mailing city, which is not always the legal city. In Los Angeles, "Van Nuys" is inside the City of Los Angeles, and Boston rows may say "Dorchester". Resolving the real jurisdiction (e.g. with the Census Geocoder) is part of Module B.
- **Coverage by city:** Los Angeles 80 · San Francisco 80 · San Diego 50 · Berkeley 40 · Jersey City 50 · Hoboken 40 · Newark 50 · Boston 60 · Cambridge 50.
- **Known gaps in the public records (handle them explicitly):**
  - San Diego and Berkeley have no year built; Berkeley also has no unit count.
  - Boston apartment rows (`use_code` starting `A/`) have no unit count in this sample.
  - Jersey City and Newark have no unit counts in this sample; 39 of 40 Hoboken rows also lack them. New Jersey construction years are often missing.
- **Santa Ana** laws are in the corpus but there are **no Santa Ana addresses**: no open parcel data with addresses was found. Santa Ana rules count for extraction only.
- **No owner names.** They are deliberately excluded, so owner-type tests (e.g. California's small-landlord deposit exception) can't be resolved from the data. Answer "unknown" or explain why the exception can't apply.
- **Year built ≠ certificate of occupancy.** Several cutoffs use the certificate date (San Francisco: on or before 1979-06-13; Los Angeles: on or before 1978-10-01). A building in the cutoff year should be "unknown".

## 5. Submission format

Submit three JSON files (templates in `submission_templates/`):

1. **`rules.json`**: a list of rule records matching `schema/rule_record.schema.json`.
2. **`lookups.json`**: `{"as_of": "2026-10-01", "lookups": {address_id: [{team_rule_id, result, explanation, conflict_flag}]}}`, covering **all 500 addresses**.
3. **`changes.json`**: `{test_id: {affected_address_ids: [...], conflict_flag_address_ids: [...], notes}}`, covering all 500 addresses.

Use the supplied schemas and templates, keep every answer tied to a source document and retrieval date, and make the system reproducible for the live demo. Organizers will provide submission logistics separately.

**`result` values**

| Value | Meaning |
|---|---|
| `applies` | The rule is in force and covers this address |
| `unknown` | Coverage depends on facts not in the data |
| `superseded` | Covered, but a stricter rule at another level governs (e.g. California's statewide cap where local rent control applies) |
| `not_yet_effective` | Enacted, but its effective date is after the query date |
| `pending` | A bill or proposal, not law |

Leave out rules that don't apply.

## 6. Public sources you may use

| Source | Use it for | Access |
|---|---|---|
| Census Geocoder (`geocoding.geo.census.gov`) | Address → state, county, incorporated place | No key; batch up to 10,000 rows |
| Census TIGER/Line | City boundaries | Free download |
| LegiScan API | Bill status and text | Free key; 10,000 queries/month; CC BY 4.0 |
| Open States API v3 | Bill status | Free key |
| State code sites (CA, NJ, MA legislatures) | Statute text | Free; California's site blocks scripts, so use the corpus copy |
| City code sites and publishers (ecode360, American Legal, Municode) | Ordinance text | Read freely; respect terms, no bulk scraping |
| LSC Eviction Laws Database | Methods reference only | Laws as of 1/1/2021, out of date |

## 7. Change-tracking tests

| Test | What it checks |
|---|---|
| **T1** | California AB 325 / SB 763: as of 2025-12-31 vs 2026-01-02 |
| **T2** | Hoboken vs Jersey City local algorithmic bans: get the boundary right |
| **T3** | New Jersey FAIR Act: enacted 2026-07-20, effective 2027-07-01. Report `not_yet_effective` now, `applies` on 2027-07-02. Flag a possible conflict with the Jersey City and Hoboken ordinances. |
| **T4** | Massachusetts S.2983 and H.5222: pending bills. Which addresses would be affected if they passed? |
| **T5** | Massachusetts rent-control ballot question (struck 2026-06-23): affected set must be empty. Never report a rent cap in Boston or Cambridge. |

## 8. Responsible design

**Do**

- Cite the source text and retrieval date for every rule.
- Show an "as of" date on every answer.
- Separate enacted law from pending law.
- Say "unknown" instead of guessing.
- Flag conflicts for human review.
- Keep an audit log.

**Don't**

- Present output as legal advice or a compliance certification.
- Suggest ways to avoid a rule.
- Invent rules or citations.
- Use non-public data.

## 9. Known open questions in the law (bonus if your system surfaces them)

- **Berkeley's algorithmic ban** (ch. 13.63) has two published effective dates: March 1, 2026 in the ordinance text, January 2026 per an August 2026 law-firm alert.
- **New Jersey's FAIR Act** may preempt the Jersey City and Hoboken ordinances once it takes effect.
- **Los Angeles's new RSO formula** has two published effective dates: 2026-02-02 per LAHD, 2026-01-24 per a landlord association.
- **California's screening-fee cap** has no single official 2026 dollar figure.

*Not legal advice. Summaries of law in this pack are for building a prototype.*
