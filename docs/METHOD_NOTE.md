# Clause & Effect: method note

RealPage Rental Housing Law Navigator · Hack-Nation 7 · <https://navigator.isaaclins.com> · **Not legal advice.**

**Problem.** Which housing rules apply to one building on one date, and what is about to change? Law is layered
(state, then city), the mailing city is often not the legal city, and enacted, pending and failed law look alike in
the text. Every answer must trace back to its source.

**Method.** The model reads, code decides.

1. **Extract.** Claude (`claude -p --model sonnet`) turns each document into schema-constrained rule records with a
   machine-readable `coverage` object. Prompts name no specific law. Responses are cached by
   `sha256(system + prompt + schema)`, so an offline rerun rebuilds `lookups.json` and `changes.json` byte for byte.
2. **Verify.** Code checks every `quoted_span` verbatim against its document. A failure gets one retry, then snaps to
   the closest exact passage or the record is dropped.
3. **Consolidate.** One pass per jurisdiction merges duplicates, audits coverage and turns empty cells into cited
   *no-rule findings*.
4. **Resolve.** The US Census Geocoder places each address in its incorporated place (486 batch, 7 single-line,
   7 via OpenStreetMap). 38 of 500 addresses have a mailing city that is not their legal city.
5. **Evaluate.** Deterministic code tests time, coverage (year built, units, use) and precedence, giving `applies`,
   `unknown`, `superseded`, `not_yet_effective` or `pending`. 500 addresses take 0.3 s for any date.
6. **Track change.** Change tests diff two dates and list affected addresses and conflict flags. `ingest-new` adds
   a new law in one command.
7. **Explain.** Rules without hand-checked copy get a generated one-line answer (EN + ES). Code checks that every
   number and date is in the rule, plus reading level and status wording; failures fall back to a template marked
   for review.

**Data and sources.** The starter corpus: 87 documents for 3 states and 10 cities, 54 full texts and 33 links only.
Each link was requested once, 2 s apart; 14 were readable. They keep URL and retrieval date and are flagged
`secondary_source` up to the UI; the organisers confirmed this is allowed. Sites refusing automated access were
skipped. No owner, resident, rent or pricing data.

**Validation.** `selfcheck` re-checks schema, verbatim spans, the jurisdiction × category matrix, all 25 examples in
the brief, the four known open questions and the change tests. CI runs it on every pull request with the model
binaries stubbed out. Output: 62 rules (57 in force, 1 not yet effective, 2 pending, 2 failed), 29 no-rule findings,
every span verbatim.

| Test | Result |
|---|---|
| T1 CA AB 325 / SB 763 | 250/250 CA addresses: `not_yet_effective` 2025-12-31, `applies` 2026-01-02 |
| T2 Hoboken, Jersey City bans | 40 + 50 addresses, each ban only in its city, none in Newark |
| T3 NJ FAIR Act | 140/140 NJ addresses flip on 2027-07-02; 90/90 in JC and Hoboken flagged |
| T4 MA S.2983 / H.5222 | both `pending`, never in force; 110/110 MA addresses |
| T5 MA ballot question | recorded as `failed`; affected set empty |

**Responsible design.** "Not legal advice" on every page and API response. `unknown` names the missing fact instead
of guessing (626 answers). Enacted, not-yet-effective, pending and failed law stay separate. 9 rules carry a
conflict flag for human review (721 answers). `audit.jsonl` logs every model call with prompt hash, model and raw
output. *Ask the law* is the one place a model writes at request time: Claude Haiku via the `claude` CLI with no
tools, fed only retrieved rules and the engine's verdicts. A validator keeps a sentence only if its citations come
from the retrieved set and every number is in a cited source. Questions about getting around a rule are refused
before any model call. Calls are budgeted, and each answer is logged with the question redacted.

**Limitations.** Jersey City and Hoboken algorithmic bans rest on secondary sources. Link-only law we could not read
evaluates as `unknown`. 212 addresses lack year built, 242 lack unit count; owner occupancy and subsidies are not in
the data. The corpus is frozen at 2026-10-01.

**Reproduce** (no API key, about 10 s):

```bash
git clone https://github.com/isaaclins/rental-law-navigator && cd rental-law-navigator && uv sync
uv run python -m navigator run-all   # from cache: extract, plain, evaluate, changes, selfcheck
uv run python -m navigator lookup A0016 --as-of 2027-07-02
```
