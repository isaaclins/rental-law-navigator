# navigator: extraction, address lookup, change tracking

Not legal advice. Everything here is an automated reading of the supplied corpus.

## Commands

```bash
uv sync                                   # Python 3.14 venv with jsonschema + trafilatura
uv run python -m navigator run-all        # extract (cached) + evaluate + changes + selfcheck
uv run python -m navigator extract        # Module A -> output/rules.json (+ rules_raw.json, rules_reviewed.json, audit.jsonl)
uv run python -m navigator evaluate --as-of 2026-10-01   # Module B -> output/lookups.json (other dates -> lookups_<date>.json)
uv run python -m navigator changes        # Module C -> output/changes.json (T1-T5 + any ingested law)
uv run python -m navigator ingest-new path/to/new_ordinance.txt --jurisdiction "Cambridge, MA"   # hour-16 test (T6)
uv run python -m navigator lookup A0001 --as-of 2027-07-02
uv run python -m navigator selfcheck      # -> output/selfcheck.txt, exit 1 if a check fails
NAVIGATOR_EXTENSION=new_docs/santa-monica uv run python -m navigator extend   # new jurisdiction -> output/extension/santa-monica/ (docs/NEW_JURISDICTION.md)
```

LLM backend: `claude -p --model sonnet --output-format json --json-schema ...` (default), `codex exec` (fallback),
Anthropic API when `ANTHROPIC_API_KEY` is set (`NAVIGATOR_LLM=api`). Every response is cached in `cache/llm/` keyed by
sha256(system + prompt + schema), so reruns are free and reproducible; max 3 parallel calls, run under `nice -n 19`.

## Module A: extraction (`extract.py`, `prompts.py`)

1. **Per document** (53 corpus texts + 15 link-only secondary pages fetched once by `fetch-supplementary`; long docs chunked):
   the model returns rule records in the starter schema plus a machine-evaluable `coverage` object, and no-rule findings.
2. **Deterministic verification**: every `quoted_span` must occur in its document (whitespace/quote-insensitive match, then
   the exact original substring is stored). Failures go back to the model once ("copy it exactly"), then snap to the closest
   exact passage (similarity >= 0.55), else the record is dropped. Jurisdictions, categories, dates and citations are normalised
   (`normalize.py`, e.g. `Civil Code section 1947.12` -> `Cal. Civ. Code § 1947.12`, `M.G.L. c.186 §15B` -> `G.L. c. 186, § 15B`).
3. **Per-jurisdiction consolidation + completeness** (13 calls): the model sees all candidates and the full text of the
   jurisdiction's documents, merges duplicates, fixes coverage objects, re-reads documents for empty categories and records
   no-rule findings. Rules that exist only in link-only sources we could not read are allowed only as `unverified_link_only`
   (confidence <= 0.4, conflict flag, always evaluated as `unknown`).
4. **Finalisation**: ids (`CA-RENT-01`, `MA-ALG-P1` for proposals), status as of 2026-10-01 (`in_force`, `not_yet_effective`,
   `pending`, `failed`), `overrides`/`interaction` links (state rules that yield to local ones; state laws that may preempt local
   ones), conflict flags, JSON-schema validation.

Nothing in the code names a specific law; the prompts pass the brief's example table and the README open questions as
organiser context, and the documents remain the source of every rule and span.

### Coverage object (evaluated in `evaluate.py`)

| field | meaning |
|---|---|
| `min_units` / `max_units` | building unit thresholds |
| `construction_cutoff` | `{basis, covered_if, date}`, e.g. SF CO on or before 1979-06-13 |
| `new_construction_exemption` | rolling exemption, e.g. 15 years (CA), 30 years with owner filing (NJ) |
| `owner_occupied_exemption_max_units` | exemption for owner-occupied small buildings |
| `requires_unknown_facts` | coverage needs facts not in parcel data (funding, affordable housing) -> `unknown` |
| `yields_to_local_rule` / `supersedes_state_rule` | state cap / just cause yields to stricter local law -> `superseded` |
| `may_preempt_local_rules` | state law may preempt local ordinances -> conflict flag where both exist |

### No-rule findings: where they live and why

`rules.json` has two lists: `rules` (schema-valid records, including `pending` bills and `failed` measures such as
Initiative Petition 25-21) and `no_rule_findings` (`status: "no_rule"`, jurisdiction, category, finding, supporting
citation and verbatim span). We keep findings out of `rules` because the schema has no "no rule" status and a finding
recorded as an `in_force` record would claim a rule exists exactly where the key says it does not (the MA rows of the
brief test this). Findings are never evaluated against addresses.

## Module B: address lookup (`evaluate.py`)

Input `data/addresses_resolved.csv` (falls back to a postal-city map if absent). Units come from the assessor count, else
from use codes/descriptions (`6B-20U-G` -> 20 units, NJ class 4C -> 5+, `4-8-UNIT-APT` -> 4-8). Results:
`applies`, `unknown` (fact missing, cutoff year equals the building year, owner filing unknown, unverified source),
`superseded`, `not_yet_effective`, `pending`; non-applicable and failed rules are omitted. When unsure between omitting and
`unknown`, the evaluator answers `unknown`.

## Module C: change tracking (`changes.py`)

Test rule ids (`CA-ALG-01`, `HOB-ALG-01`, `MA-ALG-P1`, ...) resolve to extracted rules by jurisdiction code, category code
and enacted/proposal type. `as_of` tests diff results between the two dates; `boundary` lists addresses where the rules
apply; `pending` lists addresses the bills would cover; `negative` must be empty. `ingest-new` copies a new law into
`new_docs/`, runs the same extraction (stage 1 + consolidation against existing rules as context), re-evaluates all
addresses and writes the test (default `T6`) with before/after results using the extracted effective date.

## API for the web layer (`api.py`)

`load_rules()`, `get_rule(id)`, `no_rule_findings()`, `address_ids()`, `lookup(address_id_or_dict, as_of)`,
`changes(test_id)`, `run_change_test(test_dict)`, `extensions()`, `extension_lookup(slug, address_id, as_of)`
(jurisdictions added with `navigator extend`; the web app serves them at `/api/extensions` and
`/api/extension/{slug}/address/{id}`), `lookup_user(state, jurisdiction, facts, as_of)` (any geocoded address with
user-supplied year built / units / owner occupancy / certificate date; every `unknown` carries `needs_fact`, found by
re-running the evaluator with probe values per missing fact, `navigator/user_facts.py`; served by `web/any_address.py`
at `POST /api/resolve` and `POST /api/evaluate`, #39).
