# Clause & Effect: Rental Housing Law Navigator

**Which housing rules apply to this apartment today, and what is about to change?**

[![CI](https://github.com/isaaclins/rental-law-navigator/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/isaaclins/rental-law-navigator/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live demo](https://img.shields.io/badge/demo-navigator.isaaclins.com-002664)](https://navigator.isaaclins.com/)

Housing law in the US comes in layers: state statutes, then city ordinances, each with its own building tests and
dates. Clause & Effect reads the public law of 3 states and 10 cities (87 source documents) with an LLM. It turns
the text into rule records and checks every quote against the source in code. Each address is resolved to its
*legal* city, and a deterministic engine decides which rules apply on any date you pick. Renters and small landlords
get a one-line answer per topic, the law word for word one tap away, and a list of what changes next. They can also
check a rent increase, ask a question in plain English or Spanish, or draft a letter. **The model reads, code
decides:** every answer carries a citation, a retrieval date and an "as of" date. Built in 24 hours for the RealPage
challenge at the [Hack-Nation 7th Global AI Hackathon](https://hack-nation.ai/) (October 3-4, 2026).

**Live demo: <https://navigator.isaaclins.com/>** (a 60-second guided tour: <https://navigator.isaaclins.com/#/tour>) ·
[Method note](docs/METHOD_NOTE.md) ([PDF](docs/METHOD_NOTE.pdf)) · [Architecture](docs/ARCHITECTURE.md) ·
[Design notes](web/DESIGN.md)

> [!IMPORTANT]
> **Not legal advice.** This is a research prototype. It summarises public law from a fixed corpus (as of
> 2026-10-01) and is not a compliance check. Every answer links to its source; read the source before you rely on it.

| | | |
|---|---|---|
| [![Home: search an address, answers as of Oct 1, 2026](docs/img/home.png)](https://navigator.isaaclins.com/) | [![3515 Fillmore St, San Francisco: rent capped at 1.6% until Feb 2027, eviction only for 17 listed reasons, deposit max 1 month's rent](docs/img/lookup.png)](https://navigator.isaaclins.com/#/a/A0016) | [![Ask the law: a deposit question answered for a Los Angeles building, checked by the rules engine, every sentence cited](docs/img/ask.png)](https://navigator.isaaclins.com/#/ask) |
| **Home** | **Address lookup** | **Ask the law** |
| [![Check a rent increase: $2,400 to $2,600 in San Francisco is $161.60 too high, with the law behind it and a letter to the landlord](docs/img/check.png)](https://navigator.isaaclins.com/#/check/A0016) | [![What's changing: a timeline of laws taking effect, filtered by place](docs/img/changes.png)](https://navigator.isaaclins.com/#/changes) | [![Compare San Francisco and Boston: different in 6 of 6 topics](docs/img/compare.png)](https://navigator.isaaclins.com/#/compare/A0016,A0048) |
| **Check a rent increase** | **What's changing** | **Compare two addresses** |
| [![Rules where you live: pick a state or city, six topics answered](docs/img/rules.png)](https://navigator.isaaclins.com/#/rules) | [![My properties: example portfolio with upcoming changes and the next rent notice due](docs/img/properties.png)](https://navigator.isaaclins.com/#/properties) | [![Sources: 87 source texts, 62 of 62 quotes checked word for word](docs/img/sources.png)](https://navigator.isaaclins.com/#/audit) |
| **Rules by place** | **My properties** | **Sources and method** |

<p>
<img src="docs/img/phone-lookup.png" width="200" alt="Address lookup on a phone">
<img src="docs/img/phone-ask.png" width="200" alt="Ask the law on a phone">
<img src="docs/img/phone-check.png" width="200" alt="Rent check on a phone: $161.60 too high">
<img src="docs/img/phone-changes.png" width="200" alt="What's changing on a phone">
</p>

## Contents

[The brief, mapped](#the-brief-mapped) · [Results](#results) · [Run it](#run-it) ·
[Reproduce the outputs](#reproduce-the-outputs) · [How it works](#how-it-works) · [Ask the law](#ask-the-law-grounding-security-audit) ·
[Plain language](#plain-language-without-hand-writing) · [Adding a jurisdiction](#adding-a-jurisdiction) ·
[Features](#features) · [Output files](#output-files) · [Limitations](#limitations) · [Videos](#videos) ·
[Team](#team) · [Repository layout](#repository-layout) · [License](#license)

## The brief, mapped

### Required modules

| Brief | What we built | Where |
|---|---|---|
| **Module A: rule extraction**, automated, in the provided schema | Claude reads each document and returns schema-constrained rule records plus a machine-readable `coverage` object. The prompts name no specific law. Code checks every `quoted_span` verbatim against its document (one retry, then snap or drop). A per-jurisdiction pass merges duplicates, audits coverage and writes cited *no-rule findings*. Result: 62 rules, 29 no-rule findings, 0 schema errors. | [`navigator/extract.py`](navigator/extract.py), [`navigator/prompts.py`](navigator/prompts.py), [`output/rules.json`](output/rules.json) |
| **Module B: address lookup**: jurisdiction stack, every applicable rule, local overrides, `unknown` instead of guessing | The US Census Geocoder places each of the 500 addresses in its incorporated place (38 have a mailing city that is not their legal city). The evaluator tests time, coverage (year built, units, use) and precedence. A state rule that yields to a local one becomes `superseded`; a missing fact gives `unknown` and names the fact (626 answers). | [`geo/resolve.py`](geo/resolve.py), [`navigator/evaluate.py`](navigator/evaluate.py), [`output/lookups.json`](output/lookups.json), the address page |
| **Module C: change tracking**: test cases, affected addresses, before/after, "as of" queries | Each change test compares two dates and lists the affected addresses, conflict flags and per-address before/after results. Every page and API call takes an as-of date. `ingest-new` runs a new ordinance through the same extraction and re-evaluates all addresses. | [`navigator/changes.py`](navigator/changes.py), [`output/changes.json`](output/changes.json), *What's changing*, the as-of picker |
| **Explain**: plain-language summary and citation for every applicable rule | Every topic has four layers: a one-line answer, a why line, *Show me the law* (the verbatim quote, citation, source link, retrieval date) and *More details*. | the address page, [`web/headlines.py`](web/headlines.py), [`navigator/plain.py`](navigator/plain.py) |

### Stretch goals

| Brief | What we built | Where |
|---|---|---|
| Plain-language view in English and Spanish | The whole app, Ask, Listen, letters and notices work in EN and ES. Citations and quoted law stay in the original English. Plain answers for rules without hand-checked copy are generated and checked by code ([below](#plain-language-without-hand-writing)). | EN/ES toggle, [`web/translations/`](web/translations/), [`web/static/i18n/es.json`](web/static/i18n/es.json) |
| Confidence score and conflict flag for each answer | Each answer in `lookups.json` carries `confidence` and `conflict_flag`. In the app, an uncertain reading shows "double-check this one" and a conflict shows "these laws may conflict", with the reason one tap away. 9 rules carry a conflict note, which flags 721 address answers. | `lookups.json`, the status dots on each topic |
| Extend to one new jurisdiction during the event | Santa Monica, CA was added as data only: 5 documents, 40 parcels, 3 commands, 125 s from documents to live answers ([recipe](#adding-a-jurisdiction)). | [`new_docs/santa-monica/`](new_docs/santa-monica/), [`output/extension/santa-monica/`](output/extension/santa-monica/), [docs/NEW_JURISDICTION.md](docs/NEW_JURISDICTION.md) |

### Responsible AI

| The brief says the solution should / must not | How | Where to check |
|---|---|---|
| Cite the source text and retrieval date for every rule | Every rule has a citation, source URL, `retrieved_at` and a quote that code found in the source. Secondary sources (law-firm and news pages) are labelled as summaries. | *Show me the law* on every topic, `rules.json` |
| Show an "as of" date; keep enacted and pending law apart | The as-of date is on every answer, page and API response. `pending`, `not_yet_effective` and failed measures are their own results and never read as `applies`. | the as-of picker, T1, T3, T4, T5 |
| Say "unknown" when a fact is missing | Coverage tests run as code against parcel facts. A missing fact gives `unknown` and becomes one question to the user ("Was the building built before 1979?"); the answer re-runs the engine. | [`navigator/evaluate.py`](navigator/evaluate.py), the address page |
| Flag conflicts and low confidence for review | Conflict notes (NJ FAIR Act preemption, Berkeley's two dates, LA's two RSO dates, the CA screening-fee figure). Rules found only in sources we could not read are capped at confidence 0.4 and evaluate as `unknown`. | `conflict_note`, selfcheck section 6 |
| Plain language a renter can act on | One-line answers, a why line at grade 9 or below, a rent check with the deciding quote, a letter to the landlord, a spoken briefing. | the app |
| Keep an auditable log of sources, model outputs and changes | `output/audit.jsonl` logs every pipeline model call (prompt hash, model, raw output, cache hit, dropped candidates). `cache/llm/` stores every response. Ask writes its own redacted log ([below](#ask-the-law-grounding-security-audit)). | *Sources and method*, `/api/audit`, `/ask/audit` |
| Must not present output as legal advice or a compliance verdict | "Not legal advice" on every page, every API response (plus an `X-Not-Legal-Advice` header), every letter and in the JSON outputs. Ask removes sentences such as "you are compliant". | footer, API, [`web/ask.py`](web/ask.py) `COMPLIANCE` |
| Must not suggest ways around a rule | Ask refuses questions about getting around a rule before any model call, quotes the rule and points to help. Model sentences that suggest a way around are dropped. The letter and notice are fixed templates. | [`web/ask.py`](web/ask.py) `EVASION`, [`tests/test_ask.py`](tests/test_ask.py) |
| Must not invent rules or citations | No rule is hand-coded; a quote not found in the source drops the record. In Ask, cited ids must come from the retrieved set and every number must appear in a cited source. | selfcheck sections 1-2, Ask validator |
| Must not use non-public data or scrape against terms | Only the starter corpus, public assessor data, the Census Geocoder and OpenStreetMap Nominatim (1 request/s, cached). Each link-only page was requested once, 2 s apart; pages that refused automated access were skipped, not worked around. | [`navigator/supplementary.py`](navigator/supplementary.py), [docs/NEW_JURISDICTION.md](docs/NEW_JURISDICTION.md) |

**Submission files:** [`output/rules.json`](output/rules.json), [`output/lookups.json`](output/lookups.json),
[`output/changes.json`](output/changes.json). Live demo: <https://navigator.isaaclins.com/>.

## Results

### Self-test score

The official `score.py` and held-out key are not in the starter pack. We wrote **our own independent key** by
hand from the corpus, separately from the pipeline: 59 rules, 19 no-rule findings and 61 sampled addresses, each with
a verbatim quote ([`qa/`](qa/)). It follows the brief's weights. **This is our key, not the official score.py.** It
cannot catch blind spots that the key and the pipeline share, and its findings drove extraction fixes, so the score
is partly fit to it.

```bash
python3 qa/score.py   # "independent key, not the official score.py"
```

| Component | Score | Max | Detail |
|---|---:|---:|---|
| Extraction accuracy | 24.7 | 25 | core rules 36/36, all 58/59, precision 98% |
| Address coverage | 20.0 | 20 | 968/968 points, 0 missed `applies`, 0 false positives |
| Citations | 14.7 | 15 | 4455/4545 `applies` answers quote the starter corpus verbatim (the other 90 quote fetched secondary pages) |
| Change tracking T1-T5 | 15.0 | 15 | T1-T5 all 1.00 |
| **Auto-scored total** | **74.4** | **75** | judged parts (plain language, responsible design, scalability) not included |

Full report: [`qa/report.md`](qa/report.md).

### Change tests

| Test | What a correct system does | Our result |
|---|---|---|
| **T1** CA AB 325 / SB 763 | `not_yet_effective` on 2025-12-31, `applies` on 2026-01-02, every CA address | 250/250 CA addresses flip |
| **T2** Hoboken and Jersey City bans | each ban only inside its own city, neither in Newark | 40 Hoboken + 50 Jersey City addresses, 0 in Newark |
| **T3** NJ FAIR Act (eff. 2027-07-01) | `not_yet_effective` today, `applies` on 2027-07-02, conflict with the local bans | 140/140 NJ addresses flip; 90/90 Jersey City and Hoboken addresses flagged |
| **T4** MA S.2983 / H.5222 | pending, never in force; list the addresses they would affect | both `pending`; 110/110 Boston and Cambridge addresses |
| **T5** MA ballot question, struck | no rent cap for Boston or Cambridge; affected set empty | recorded as `failed`; affected set empty |
| **T6** fictional Cambridge ordinance (hour 16) | extracted unaided, affected addresses, future effective date right | *pending: the ordinance is released at hour 16; it goes through `ingest-new` and the result is added here* |

`uv run python -m navigator selfcheck` re-checks schema, verbatim spans, the jurisdiction × category matrix, all 25
examples in the brief, T1-T5 and the four known open questions ([`output/selfcheck.txt`](output/selfcheck.txt)).
CI runs it on every pull request with the model binaries stubbed out.

### Tests

**1,171 tests pass** (`pytest`, about a minute), covering the evaluator, rent check, letters, notices, Ask
(grounding, validator, evasion, budgets, redaction, dates), plain-language checks, sharing, Listen, accounts and
Spanish dates. Lint: `ruff check` and `ruff format --check` are clean.

## Run it

You need [uv](https://docs.astral.sh/uv/); it installs Python 3.12+ if needed. No API key is needed.

```bash
git clone https://github.com/isaaclins/rental-law-navigator && cd rental-law-navigator
uv sync
uv run uvicorn web.app:app --port 8765          # -> http://127.0.0.1:8765
```

From a fresh clone, `uv sync` takes about 3 s and the app answers in about 2 s. Everything except two features works
offline:

- **Ask** writes fresh answers with the `claude` CLI (or `ANTHROPIC_API_KEY`). Without either, it falls back to the
  quoted rules themselves.
- **Listen** uses ElevenLabs when a key is configured and the browser's own voice otherwise.

## Reproduce the outputs

```bash
uv run python -m navigator run-all     # extract (from cache) + plain + evaluate + changes + selfcheck -> "SELFCHECK: OK" (~8 s)
python3 qa/score.py                    # our independent key -> 74.4 / 75
uv run python -m navigator lookup A0016 --as-of 2027-07-02          # one address, any date
uv run --with pytest --with httpx python -m pytest tests -q         # the test suite
```

Every model response is stored in [`cache/llm/`](cache/llm/), keyed by `sha256(system prompt + prompt + schema)`;
geocoder responses are in [`cache/geo/`](cache/geo/). The offline rerun rebuilds `lookups.json` and `changes.json`
byte for byte. `rules.json` differs only in `generated_at`, `plain_language.json` only in its `cached` flags, and
`audit.jsonl` gets one more run appended.

**Rerun extraction with a live model:**

```bash
mv cache/llm cache/llm.recorded                      # force cache misses
uv run python -m navigator run-all                   # default: Claude Code CLI (claude -p --model sonnet)
NAVIGATOR_LLM=api ANTHROPIC_API_KEY=... uv run python -m navigator run-all   # or the Anthropic API
```

A cold run is about 106 model calls, about 10 minutes at 3 parallel calls. **A new law**, extracted unaided:

```bash
uv run python -m navigator ingest-new path/to/ordinance.txt --jurisdiction "Cambridge, MA" --url https://...
```

`ingest-new` extracts and consolidates the text (2 model calls) and adds the rules to `rules.json`. It then
re-evaluates all 500 addresses and adds a `new_law` change test with the affected addresses and before/after results
around the extracted effective date.

## How it works

```mermaid
flowchart TB
  subgraph A["Module A: extract (LLM)"]
    direction LR
    C[("starter corpus<br/>54 official texts")] --> X
    S2[("14 link-only pages<br/>fetched once, secondary")] --> X
    X["per-document extraction<br/>schema-constrained JSON"] --> V["verbatim span check<br/>(code, not model)"]
    V --> RV["per-jurisdiction consolidation,<br/>coverage audit, empty-cell probe"]
    RV --> F["finalise: ids, status,<br/>conflict flags, schema"]
    F --> PL["plain-language answers<br/>(LLM + code checks)"]
  end
  subgraph B["Module B: resolve + apply (code)"]
    direction LR
    AD[("500 sample addresses")] --> G["US Census Geocoder<br/>to incorporated place"]
    G --> J["jurisdiction stack<br/>state, county, city"]
    J --> E["deterministic evaluator<br/>time, coverage, precedence"]
  end
  subgraph CC["Module C: track change"]
    T[("change tests T1-T5<br/>+ ingest-new")] --> D["as-of diffs, affected sets,<br/>pending, conflict flags"]
  end
  F --> RJ[/"rules.json"/]
  RJ --> E
  E --> LJ[/"lookups.json"/]
  RJ --> D
  E --> D
  D --> CJ[/"changes.json"/]
  LJ --> W["web app EN / ES<br/>lookup, check, letters, Listen"]
  CJ --> W
  E --> ASK["Ask: retrieval + engine verdicts<br/>-> Haiku -> validator"]
  ASK --> W
  X -.-> AU[("audit.jsonl + cache/llm")]
```

1. **Extract (LLM).** Each document becomes rule records in the starter schema plus a `coverage` object: unit
   thresholds, construction cutoffs, exemptions, facts the data cannot show, and whether a state rule yields to local
   law.
2. **Verify (code).** Each `quoted_span` must occur in its document; the check ignores whitespace and quote style.
3. **Resolve (Census).** The mailing city is not the legal city: Dorchester is Boston, and a "Los Angeles" address
   can sit in West Hollywood. 486 batch matches, 7 single-line, 7 OpenStreetMap fallbacks.
4. **Apply (code).** Four tests per rule: time (pending, not yet effective, failed, sunset), coverage, precedence and
   conflicts. 500 addresses take 0.3 s for any date.
5. **Track change.** Change tests diff two dates; `ingest-new` adds a law in one command.

More depth: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Ask the law: grounding, security, audit

Ask ([`web/ask.py`](web/ask.py), [`web/ask_prompt.md`](web/ask_prompt.md)) answers a plain question in EN or ES,
across several turns. It is the one place where a model writes text at request time, so the model only gets to
phrase what our data already says.

| | |
|---|---|
| **Place** | One of our 500 addresses (fuzzy street match), else the cities or states named, else a short "which state?" choice. Places we do not cover are refused right away with the closest official source. Dates in the question ("in 2023", "el 1 de enero de 2027") set the as-of date. |
| **Applicability** | At an address, the deterministic engine decides what applies. The model explains those verdicts and never decides them. |
| **Retrieval** | BM25 over the extracted rules, the no-rule findings and passages of the source documents, filtered by place and topic. Every retrieved quote is checked against its source text. |
| **Model** | Claude **Haiku** through the `claude` CLI in headless mode: `--tools ""` (no tools), no session persistence, no MCP servers, no slash commands, a temporary working directory, strict JSON out. A 12 s hard timeout kills the process tree. |
| **Every claim cited** | The prompt allows only the SOURCES of this turn. The server-side validator then keeps a sentence only if its cited ids come from the retrieved set, a sentence about the law has a citation, and every number appears in a cited source or the question. It also drops sentences that contradict the engine at an address, claim a rule not yet in force applies, read as a compliance verdict, suggest a way around a rule, or contain markup, links, paths or e-mail addresses. Streamed partial answers pass through the same validator. If nothing survives, the reply is an honest "I don't have that in my sources" with the official source. |
| **Prompt injection** | The question and the conversation are passed as untrusted text. The prompt tells the model to ignore instructions inside them and never reveal its context. The model has no tools, so the worst case is a sentence the validator drops. |
| **No evasion help** | Questions about getting around a rule ("how do I raise the rent above the cap") are caught before any model call. They get a kind refusal, the rule itself quoted and where to get help. |
| **Urgent situations** | Lockouts, shut-off utilities, eviction papers with a date: help contacts come first. |
| **Budgets** | At most 3 model processes at once, and background checks of follow-up chips may use only 1 of them. Fresh calls are capped at 1,200 per hour and 8,000 per day, with the counter kept on disk across restarts. A question waits at most 5 s for a slot. Busy, over budget or timed out, the answer falls back to the quoted rules, with no model involved. Per-visitor limits can be set by environment variable and are off by default. |
| **Audit log** | One JSON line per model answer in `output/ask_audit.jsonl`: time, prompt hash, model, language, as-of date, the **redacted** question, place, topics, retrieved ids, engine verdicts, the answer, cited ids, and every sentence the validator dropped with the reason. Redaction removes e-mail addresses, phone numbers, street addresses and unit numbers. Reviewers read it at `/ask/audit` (linked from *Sources > For reviewers*). The log is not in git. |
| **Caching** | Answers are cached in memory. Only the suggested questions are pre-warmed to disk (`cache/ask/`, not in git). |

Tests: [`tests/test_ask.py`](tests/test_ask.py) covers retrieval, the validator, evasion and compliance phrasing,
budgets and slots, redaction and dates.

## Plain language without hand-writing

The short answers ("Max 1 month's rent.", "Not law yet: on the Nov 3, 2026 ballot.") have two sources. Hand-checked
copy in [`web/headlines.py`](web/headlines.py) always wins: 46 of the 62 rules have it. Every other rule gets one
model call ([`navigator/plain.py`](navigator/plain.py)) that sees **only that rule's own fields** and its verbatim
quote. Code then checks the copy:

- every number, amount, percent and date occurs in the rule's key value, requirement or quote;
- length limits, a why line at Flesch-Kincaid grade 9 or below, and no jargon (§, CPI, "exempt", "shall", bill
  numbers);
- the answer matches the status (pending: "Not law yet"; not yet effective: names the start date);
- the why line stays on the rule's topic;
- the Spanish copy carries the same numbers and dates.

A failure gets one retry with the list of failed checks. A second failure falls back to a category template marked
`needs_review` (3 rules today). Generated answers carry a small "Auto-summary" note in the app. In a blind comparison
against the hand-written copy, 11 of 12 generated answers carried the same facts ([`output/plain_compare.json`](output/plain_compare.json)).

## Adding a jurisdiction

A new city needs data, not code: a `jurisdiction.json` (name, state, rule-id code, Census place) and a few official
texts with a manifest in `new_docs/<slug>/`. Choosing the sources is the one human step
([docs/NEW_JURISDICTION.md](docs/NEW_JURISDICTION.md)). Then:

```bash
python3 geo/lacounty_parcels.py "SANTA MONICA" new_docs/santa-monica/addresses.csv --n 40 --prefix SM   # 1. addresses
python3 geo/resolve.py --extension new_docs/santa-monica                                                # 2. legal city per address
NAVIGATOR_EXTENSION=new_docs/santa-monica nice -n 19 uv run python -m navigator extend                  # 3. rules -> plain -> lookups
```

**Measured end to end** (Santa Monica, 2026-10-04, cold caches, `claude -p --model sonnet`, 3 parallel calls):

| Step | Wall time |
|---|---:|
| 1. 40 parcels from the LA County parcel layer (2 requests) | 1.8 s |
| 2. Census batch geocoding (39 matched, 1 postal-city fallback flagged) | 12.4 s |
| 3. `extend`: 5 documents -> rules -> plain answers -> 40 address lookups (15 model calls) | 109.4 s |
| 4. web app start + first Santa Monica answer | 1.7 s |
| **Documents -> live answers** | **125 s, $1.57 in model cost** |

The committed extension has 6 Santa Monica rules (rent control, just cause, two pending ballot measures, deposit
interest, algorithmic pricing). A rerun from cache takes under 1 s. Prompts and the evaluator name no specific law,
so adding a city never changes an existing answer. Model work grows with the number of documents. Evaluation is plain
code and grows with addresses × rules.

## Features

| Feature | What it does |
|---|---|
| **Address lookup** | Jurisdiction stack, building facts, one plain answer per topic, the law one tap away. Unknowns become one question. |
| **Any US address** | The live Census geocoder finds the legal city; you add the building facts the answer depends on. |
| **As-of date** | Every page re-evaluates for any date, from 2019 to 2027. |
| **Ask the law** | Conversational questions in EN/ES, grounded in our rules, every sentence cited ([above](#ask-the-law-grounding-security-audit)). |
| **Check a rent increase** | Deterministic verdicts for a rent increase, deposit, fee, notice or termination, each with the deciding quote. |
| **Letter to the landlord** | When a check finds an increase over the limit: a fixed EN/ES template filled only from the engine's numbers. Name and unit stay in the browser. Copy, print, PDF or share. |
| **Rent-increase notice** | For owners, the twin of the letter: the highest lawful rent, the earliest start date and the notice deadline, checked against our sources. |
| **What's changing** | A timeline of laws taking effect or ending, by place, with the addresses each affects. Also a chart of how many cities have each protection, 2019-2027. |
| **Rules by place** | Pick a state or city and its six topics answer with the same component as the address page. |
| **Compare** | Two addresses side by side, topic by topic. |
| **Listen** | A 35-50 s spoken briefing for renters or owners (EN/ES), with a time-synced transcript. Deterministic templates, no LLM. ElevenLabs voice, budgeted and cached, with a browser-voice fallback. |
| **Share an answer** | A frozen, cited permalink with a link-preview card, recomputed from the address, topic and date. No database. |
| **My properties** | Google sign-in, saved buildings, next lawful rent increase, open questions, an ICS calendar feed and e-mail alerts before a law change. A read-only example portfolio for visitors. |
| **Sources and method** | The pipeline audit log, every source text, how each address was geocoded, and the Ask audit log. |
| **Product tour** | A 60-second guided walk through the live app (`#/tour`). |
| **Installable app** | A PWA that keeps recent answers readable offline. |

## Output files

All in [`output/`](output/) and committed, so CI validates exactly what the demo shows.

| File | Contents |
|---|---|
| [`rules.json`](output/rules.json) | **Submission.** 62 schema-valid rules (57 in force, 1 not yet effective, 2 pending, 2 failed), each with citation, source URL, retrieval date, verbatim quote, confidence, conflict flag and `coverage`; plus 29 cited `no_rule_findings`. |
| [`lookups.json`](output/lookups.json) | **Submission.** For all 500 addresses, every rule's result (`applies` 4545, `unknown` 626, `superseded` 265, `pending` 220, `not_yet_effective` 140) with explanation, citation and conflict flag. |
| [`changes.json`](output/changes.json) | **Submission.** Per test: affected addresses, conflict-flag addresses, per-address before/after, and the mapping to our rule ids. |
| [`audit.jsonl`](output/audit.jsonl) | One line per model call and pipeline step: prompt version and hash, model, cache hit, raw output, dropped or restored candidates. |
| [`plain_language.json`](output/plain_language.json) | Plain answers per rule (EN + ES): reviewed or generated, with model, prompt hash, every check result and `needs_review`. |
| [`rules_raw.json`](output/rules_raw.json), [`rules_reviewed.json`](output/rules_reviewed.json) | Candidates before and after consolidation. |
| [`selfcheck.txt`](output/selfcheck.txt) | The selfcheck report. |
| [`extension/santa-monica/`](output/extension/santa-monica/) | The added jurisdiction: rules, lookups, changes, plain answers, `summary.json` with time and cost. |

**Why `no_rule_findings` is a separate list.** The brief tests whether systems avoid reporting rules that don't
exist, such as rent control in Massachusetts cities. The schema has no "no rule" status, and a finding stored as a
rule would read as `in_force`. So findings carry `status: "no_rule"`, a citation and a verbatim quote, and are never
evaluated against addresses.

## Limitations

- **Our score is our own.** The key was written by us, no lawyer reviewed it (nor the starter pack's), and it drove
  fixes. It is a regression test, not a grade.
- **Jersey City and Hoboken algorithmic bans rest on secondary sources.** The corpus links to the ordinances but has
  no text, so those rules quote law-firm or news pages (90 `applies` answers).
- **Unreadable link-only law evaluates as `unknown`.** Hoboken and Newark rent control and San Diego's
  source-of-income ordinance sit on code-publisher sites that refuse automated access.
- **Parcel data decides a lot.** 212 of 500 addresses have no year built and 242 no unit count. Owner type, owner
  occupancy and subsidies are not in the data, so exemptions that depend on them are listed but not tested.
- **Annual figures are dated by the current figure.** SF's 1.6% allowance starts 2026-03-01, so an earlier as-of
  date shows it as `not_yet_effective`, not last year's figure.
- **Some old statutes give no effective date** (for example N.J.S.A. 2A:18-61.1), so the field stays empty.
- **The corpus is frozen at 2026-10-01.** Change tracking covers documents you ingest; it does not watch
  legislatures.
- **Ask is guarded, not proven.** The validator checks citations, numbers and phrasing, not whether a paraphrase is
  a fair summary. Its redaction is pattern-based (e-mail, phone, street, unit); a name typed into a question is not
  removed. It needs the `claude` CLI or an API key for fresh answers.
- **Generated plain copy is marked for review** until a person checks it; 3 rules use a template today.
- **Santa Monica's algorithmic-pricing ordinance** has no official text in the extension (the city's legislative
  system never answered), so that rule quotes a news page.

## Videos

| Video | Link |
|---|---|
| Team introduction (≤ 60 s) | *link follows* |
| Product demo (≤ 60 s) | *link follows* |
| Technical walkthrough with scores (≤ 60 s) | *link follows* |

## Team

**Clause & Effect** is Isaac Lins and a fleet of AI agents. Isaac set the direction and the quality bar; the agents
built it in parallel. Each issue on the [project board](https://github.com/users/isaaclins/projects/6) went to its
own agent in its own branch and git worktree. Pull requests merged only with green
[CI](.github/workflows/ci.yml) (lint, schema and span validation, offline selfcheck with the model binaries stubbed,
web smoke test). A separate QA agent wrote the answer key by hand, and critic agents reviewed the design and the
brief's requirements before each merge.

## Repository layout

```
navigator/   pipeline: corpus, LLM extraction + span check, plain language, evaluator, change tracking, selfcheck, CLI
geo/         address -> legal jurisdiction (Census Geocoder, LA County parcels; cached)
web/         FastAPI app (lookup, check, Ask, letter, notice, share, Listen, accounts) + build-free single page (EN/ES)
qa/          independent answer key, scorer, report (test oracle, not product code)
tests/       pytest suite + Playwright screenshot scripts (shots_*.py)
scripts/     validate_outputs.py (schema, spans, coverage; runs in CI)
output/      rules.json, lookups.json, changes.json (+ audit log, plain language, selfcheck, extension)
cache/       recorded LLM and geocoder responses for offline, reproducible runs
data/        addresses_resolved.csv (sample addresses + legal city, county, method, confidence)
new_docs/    the added jurisdiction (Santa Monica): documents, manifest, addresses
supplementary/text/   link-only sources fetched once (secondary, flagged as such)
starter/     the organisers' starter pack, unmodified
docs/        method note, architecture, new-jurisdiction notes, challenge brief, screenshots
```

## License

Code: [MIT](LICENSE) © 2026 Isaac Lins. The [`starter/`](starter/) pack and
[`docs/challenge-brief.txt`](docs/challenge-brief.txt) belong to the challenge organisers and are included unmodified
for reproducibility. Law texts are public records. Fonts: Inter and Instrument Serif (SIL OFL). Street photos and
illustrations are AI-generated for this project.

## Acknowledgements

- [RealPage](https://www.realpage.com/), for the challenge, the corpus and the starter pack.
- [Hack-Nation](https://hack-nation.ai/), for the 7th Global AI Hackathon, and the ETH AI Club for co-hosting the
  [Zurich hub](https://luma.com/xi9z9ikg).
- US Census Bureau Geocoder; assessor open data from LA County, DataSF, NJOGIS and MassGIS; geocoding fallback
  © OpenStreetMap contributors (ODbL).
