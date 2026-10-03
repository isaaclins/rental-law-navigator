# Adding a jurisdiction: Santa Monica, CA (added live, 2026-10-03)

Not legal advice. Automated reading of public law; check the cited source.

Adding a jurisdiction means adding documents and addresses, then rerunning. No code names Santa Monica: the
city lives in data files under `new_docs/santa-monica/`. The output goes to `output/extension/santa-monica/`.
The official deliverables `output/rules.json`, `lookups.json` and `changes.json` for the 500 sample addresses stay
byte-identical (checked with `cmp`, see "Verification").

## Why Santa Monica

- **Same address source as the starter.** The parcels come from the LA County eGIS parcel layer, the same
  `source_dataset` as the 80 Los Angeles rows, with the same columns and no owner fields.
- **Layered law.** Local rent control (City Charter Article XVIII, 1979) sits on top of California law (AB 1482
  rent cap and just cause, Civ. Code § 1950.5 deposits, § 1950.6 fees, FEHA screening, B&P § 16729 algorithmic
  pricing). This exercises the precedence logic: state rules yield where the local rule governs.
- **West Hollywood was the first choice but could not be fetched within the rules.** www.weho.org returns
  "Access Denied" to scripts. Its code publisher (library.qcode.us / ecode360) sits behind a Cloudflare challenge.
  We did not work around either block.
- **Santa Monica access.** santamonica.gov served its PDFs directly. After a few requests its HTML pages started
  showing an Imperva bot challenge, and we stopped there. The council's legislative system
  (santamonicacityca.iqm2.com) never answered, so the algorithmic-pricing ordinance (SMMC ch. 4.58) has no
  official text in this extension.

## Recipe

```bash
# 0. jurisdiction file: name, state, rule-id code, Census place (for geocoding), postal city
cat new_docs/santa-monica/jurisdiction.json

# 1. documents: a handful of official texts -> new_docs/<slug>/text/<doc_id>.txt + manifest.csv
#    (same columns as starter/corpus/corpus_manifest.csv; sha256 = of the downloaded file;
#     text files start with SOURCE / RETRIEVED headers like the corpus)

# 2. addresses: N evenly spaced 5+ unit apartment parcels (2 requests to the public LA County parcel layer)
python3 geo/lacounty_parcels.py "SANTA MONICA" new_docs/santa-monica/addresses.csv --n 40 --prefix SM

# 3. legal jurisdiction per address (Census geocoder, cached in cache/geo/)
python3 geo/resolve.py --extension new_docs/santa-monica

# 4. extraction + lookups + change tests (LLM responses cached in cache/llm/)
NAVIGATOR_EXTENSION=new_docs/santa-monica nice -n 19 uv run python -m navigator extend
```

For another LA County city, change the slug, the `TaxRateCity` value and `jurisdiction.json`. For a city
outside LA County, any parcel source that produces the columns of `sample_addresses.csv` works.

**What `extend` does.** It builds on the main extraction (`output/rules_reviewed.json`) rather than re-reading
the 68 corpus documents:

1. Stage 1 runs on the new documents only, with the same prompts and the same verbatim span verifier.
2. The new jurisdiction gets consolidation, the evidence-grounded coverage audit and the empty-cell probe. The
   state's reviewed rules are passed in as context for precedence, state exemptions and preemption.
3. Main and new rules are finalised together. Ids of existing rules do not change; new ones get the code from
   `jurisdiction.json` (`SMO-RENT-01`). The result is schema-validated.
4. Lookups are computed for the extension addresses, plus change tests for the new jurisdiction's pending or
   future rules.
5. `summary.json` records wall time, LLM calls, cost (taken from the `claude -p` envelope stored in the cache),
   the span pass rate and result counts.

**Outputs** (`output/extension/santa-monica/`): `rules.json` (all 62 main rules plus the 6 new ones, plus
no-rule findings), `lookups.json` (40 addresses), `changes.json`, `addresses_resolved.csv`, `audit.jsonl`,
`rules_raw.json`, `rules_reviewed.json`, `summary.json`.

**API and web.** `navigator.api.extensions()` and `navigator.api.extension_lookup("santa-monica", "SM002",
as_of=...)` are exposed in the web app as `GET /api/extensions` and
`GET /api/extension/santa-monica/address/SM002?as_of=2026-12-01`. Each extension is labelled
"extension: Santa Monica, CA, added live" and is kept apart from the main 500 addresses. Lookups for other
dates are computed live.

## Measured (first run, 2026-10-03, `claude -p --model sonnet`, at most 3 parallel calls, `nice -n 19`)

| step | number |
|---|---|
| documents fetched | 5 (4 official santamonica.gov, 1 secondary news). Requests that failed or were blocked, none worked around: weho.org (403), qcode/ecode360 (Cloudflare), santamonica.gov HTML (Imperva), iqm2 (timeout, 2 tries), 1 dead FAQ link (404) |
| addresses | 40 of 2,374 Santa Monica parcels with use code 05xx (2 requests); 39 Census batch matches, 1 postal-city fallback (`SM001`, a 2024 building not yet in the Census address file) |
| geocoding wall time | 14 s |
| `extend` wall time | **124 s** first run; 0.6 s rerun from cache (identical lookups) |
| LLM calls | **9** (6 extract (SM01 split into 2 chunks), 1 consolidation, 1 coverage audit, 1 probe; no span-fix call needed) |
| LLM time (sum over calls) | 177 s |
| LLM cost | **$1.62**: extract $0.44 total, consolidation $0.34, coverage audit $0.45, probe $0.41. Audit and probe cost the most because they include the CA state documents. |
| rules found | **6**: 4 in force, 2 pending; plus 2 no-rule findings |
| verbatim spans | **6/6** found verbatim in the source text on the first pass (no snapping, no retry); 5 primary sources, 1 secondary |
| schema errors | 0 |
| lookups (as of 2026-10-01) | 469 entries: 345 applies, 66 superseded, 43 pending, 15 unknown |

Rules extracted:

| id | status | citation | key value | coverage |
|---|---|---|---|---|
| SMO-RENT-01 | in_force | Santa Monica City Charter art. XVIII, § 1805 | 75% of CPI, min 0%, max 3% annual general adjustment | built on or before 1979-04-10; supersedes state cap |
| SMO-EVIC-01 | in_force | art. XVIII, § 1806 | eviction only for enumerated causes | controlled units (same cutoff) |
| SMO-DEP-01 | in_force | Rent Control Regulations § 14002 | 1 month's MAR (2 months for qualifying small landlords) | controlled units |
| SMO-ALG-01 | in_force | Santa Monica algorithmic rental pricing ordinance | ban on sale and use of algorithmic devices | secondary source only (news); verification `secondary_source` |
| SMO-EVIC-P1 | pending | art. XVIII, § 1806(a)(1) (Measure RR, 2026-11-03 ballot) | nonpayment eviction only above the average HUD Small Area FMR | controlled units |
| SMO-EVIC-P2 | pending | art. XXIII, § 2304(a)(1) (Measure RR) | same threshold | non-controlled units (built after 1979-04-10) |

No-rule findings: no local rule in the captured documents for application fees or for screening restrictions.
State rules CA-FEE-01 and CA-SCR-01/02 apply.

Change test X1 ("Pending local measures"): Measure RR would affect all 40 sampled addresses. That is 36 through
Article XVIII (33 pre-1979 buildings plus 3 with no year built) and 7 through Article XXIII (4 post-1979
buildings plus the same 3 with no year built).

## Answers checked against the law

- **SM002, 1211 Berkeley St (1948, 14 units).**
  - Local rent control applies: Charter § 1801(c) covers all rental units except, among others, (c)(5) units
    "constructed after the adoption of this Article" (adopted 4/10/79). The annual adjustment is 75% of CPI,
    capped at 0-3% (§ 1805(a)(1), (3)).
  - CA-RENT-01 is `superseded`: Civ. Code § 1947.12 exempts housing under local rent control that restricts
    increases below the state cap.
  - CA-EVIC-01 is `superseded`: § 1946.2 yields to a local just-cause ordinance adopted on or before 2019-09-01,
    and § 1806 is from 1979.
  - Deposits: Reg. § 14002(b) and the state § 1950.5 both apply. Both caps are one month, so there is no
    precedence question. **Correct.**
- **SM005, 1427 Berkeley St (1988, 7 units).** Built after 4/10/79, so local rent control and § 1806 are not
  listed. AB 1482 applies because the building is older than 15 years. **Correct** for the captured documents,
  with one caveat: under § 1801(c)(7) the post-1979 exemption "shall be granted by the Board upon application".
  The data cannot show whether that filing exists. The coverage audit did not turn this into an owner-filing
  condition.
- **SM001, 3223 Wilshire Blvd (2024, 53 units).** No rent cap at all: AB 1482's 15-year new-construction
  exemption applies and the building is post-1979. Measure RR would cover it through Article XXIII. **Correct.**
- **SM012, 2201 Oak St (no year built).** Every rule that depends on the 1979 cutoff, and both state rules with
  the 15-year exemption, are `unknown`, and the explanation names the missing fact. **Correct** under our
  "when in doubt, unknown" rule.

## What generalised and what needed care

Generic changes (none name Santa Monica; with `NAVIGATOR_EXTENSION` unset, main-mode behaviour is unchanged):

- `navigator/config.py`: an optional `NAVIGATOR_EXTENSION` adds the cities from `jurisdiction.json` to `CITIES`
  and points outputs, addresses and resolved CSV at `output/extension/<slug>/`.
- `navigator/corpus.py`: loads the extension's `manifest.csv` documents with the same `Doc` objects and the same
  span verifier.
- `navigator/normalize.py`: cities without a hand-written alias ("Santa Monica", "City of Santa Monica")
  normalise by name.
- `navigator/extend.py` and the `extend` CLI command: the incremental run described above.
- `navigator/llm.py`: new cache entries also store the CLI's `total_cost_usd`, token usage and prompt size, so
  cost is measurable.
- `navigator/api.py`: adds `extensions()` and `extension_lookup()`. `lookup()` was split into a reusable
  `_lookup()` with identical output.
- `geo/resolve.py --extension DIR`: adds the extension's Census place to the in-scope places.
- `geo/lacounty_parcels.py`: the LA County parcel sampler.
- `web/app.py`: two read-only endpoints.

What needed care:

1. **Access rules decided the city.** Check robots.txt and bot challenges first. The government PDFs were the
   reliable path.
2. **Document size.** The official "Charter Amendment Complete" PDF is 337 pages: Article XVIII plus every Rent
   Control Board regulation, about 1.2M characters. We kept pages 1-18 (Article XVIII). The manifest's sha256 is
   for the full PDF, and the text file header says which pages are included. The full PDF would have meant
   about 27 extraction calls and a review prompt too large to be useful.
3. **The state level is reused, not re-extracted.** State-law candidates found in the new documents are logged
   (`extend_scope` in the audit) and left to the main extraction, so CA rule ids and content stay stable.
4. **Unit counts.** The parcel layer stores units per building (`Units1`..`Units5`). We sum them and keep
   parcels with 5+ units, matching the starter's LA rows. Taking `Units1` alone gives "1 unit" for many 05xx
   parcels.
5. **Known gaps you can see in the output.**
   - Article XXIII (just cause for non-controlled units) is in force but appears only as amended text on the
     Measure RR page. For the 4 post-1979 buildings, CA-EVIC-01 therefore shows `applies` where Article XXIII
     probably governs.
   - The algorithmic ban rests on a news article: no official text was reachable, its effective date is
     "2025-06" from the article date, and it is marked `secondary_source`.
   - Santa Monica's own screening and source-of-income rules (SMMC) were not fetched, so the no-rule findings
     only cover the captured documents.

   Each gap is fixed the same way: add the document to `manifest.csv` and rerun `extend`. Only the changed
   calls hit the LLM.
6. **The prompt context file must exist.** Prompts include the brief's example table from
   `docs/challenge-brief.txt`. Without that file the prompts change and every cache key misses.

## Verification

- `cmp` of `output/rules.json`, `lookups.json`, `changes.json` (and `rules_reviewed.json`, `rules_raw.json`,
  `audit.jsonl`, `selfcheck.txt`) against copies taken before the run: identical, after both the first and the
  cached extension run.
- A main-mode `run-all` in a scratch copy with the new code:
  - all 273 LLM calls came from cache (0 new);
  - `lookups.json` and `changes.json` are byte-identical;
  - `rules.json` is identical apart from `generated_at`;
  - `SELFCHECK: OK`.
