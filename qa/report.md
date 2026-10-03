# QA score report (independent key)

Not the official `score.py` (not shipped in the starter pack). Oracle: `qa/expected_rules.json`, `qa/expected_lookups.json`. Not legal advice.

Inputs: `output/rules.json`, `output/lookups.json`, `output/changes.json`

| Component | Score | Max |
|---|---:|---:|
| Extraction accuracy | 24.7 | 25 |
| Address coverage | 20.0 | 20 |
| Citations | 14.7 | 15 |
| Change tracking (T1-T5) | 15.0 | 15 |
| **Auto-scored total** | **74.4** | **75** |

## 1. Extraction

Weighted recall credit 99.0%, precision 98.4%; core rules matched 36/36.

### Missing / citation-mismatched key rules (by points at stake)

| Key rule | Tier | Jurisdiction | Category | Expected citation | Status | Team match |
|---|---|---|---|---|---|---|
| MA-SCR-02 | possible | MA | screening_restrictions | 803 CMR 5.00 | in_force | none |

### Field errors on matched rules

| Key rule | Team rule | Field | Expected | Team |
|---|---|---|---|---|
| LA-JC-01 | LA-EVIC-01 | effective_date | 2023-01-27 or 2022-12-10 or 2020 | None |

### Team rules not in the key (possible false positives, or gaps in our key)

- `NJ-EVIC-02` NJ / just_cause_eviction / in_force: NJ Foreclosure Fairness Act tenant protections - `N.J.S.A. 2A:50-69 et seq`

## 2. Address coverage

967.5 of 967.5 weighted points on 61 sampled addresses (team lookups cover 500 addresses). Counts: {'correct': 591}.

### Errors grouped by key rule (weighted points lost)

| Key rule | Points lost | Errors |
|---|---:|---|

### Every address error

| Address | City | Built | Units | Key rule | Expected | Team | Error | Why expected |
|---|---|---|---|---|---|---|---|---|

Team rule ids in sampled lookups that map to no key rule: `NJ-EVIC-02` x17

### Full-sample audit (unscored): oracle logic applied to all 500 addresses

0 disagreements. Grouped by key rule:

| Key rule | Disagreement | Count | Examples |
|---|---|---:|---|

## 3. Citations

4455/4545 'applies' answers backed by a source and a verbatim corpus span. Outcome counts: {'doc': 4455, 'supplementary_only': 90}.

Rule-level span check over all rules: {'doc': 58, 'supplementary_only': 4}

| Team rule | 'applies' answers | failing | span check |
|---|---:|---:|---|
| JC-ALG-01 | 50 | 50 | supplementary_only |
| HOB-ALG-01 | 40 | 40 | supplementary_only |

## 4. Change tracking

| Test | Score | Team n | Expected n | Missing | Extra |
|---|---:|---:|---:|---|---|
| T1 | 1.00 | 250 | 250 | 0 [] | 0 [] |
| T2 | 1.00 | 90 | 90 | 0 [] | 0 [] |
| T3 | 1.00 | 140 | 140 | 0 [] | 0 [] |
| T4 | 1.00 | 110 | 110 | 0 [] | 0 [] |
| T5 | 1.00 | 0 | 0 | 0 [] | 0 [] |

T3 conflict flags: Jaccard 1.00 (team 90, expected 90); missing [], extra [].

T6 (hour-16 fictional Cambridge ordinance): not scored (data not in starter pack).
