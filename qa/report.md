# QA score report (independent key)

Not the official `score.py` (not shipped in the starter pack). Oracle: `qa/expected_rules.json`, `qa/expected_lookups.json`. Not legal advice.

Inputs: `/home/steward/hacknation/realpage/navigator/output/rules.json`, `/home/steward/hacknation/realpage/navigator/output/lookups.json`, `/home/steward/hacknation/realpage/navigator/output/changes.json`

| Component | Score | Max |
|---|---:|---:|
| Extraction accuracy | 23.1 | 25 |
| Address coverage | 19.7 | 20 |
| Citations | 13.6 | 15 |
| Change tracking (T1-T5) | 15.0 | 15 |
| **Auto-scored total** | **71.4** | **75** |

## 1. Extraction

Weighted recall credit 91.5%, precision 98.2%; core rules matched 36/36.

### Missing / citation-mismatched key rules (by points at stake)

| Key rule | Tier | Jurisdiction | Category | Expected citation | Status | Team match |
|---|---|---|---|---|---|---|
| SF-SCR-01 | probable | San Francisco, CA | screening_restrictions | S.F. Police Code art. 49 (Fair Chance Ordinance) | in_force | none |
| HOB-RENT-01 | probable | Hoboken, NJ | rent_increase_limits | Hoboken City Code ch. 155 | in_force | none |
| BOS-RENT-P1 | probable | Boston, MA | rent_increase_limits | Mass. H.3744 (193rd General Court) | failed | none |
| BOS-SCR-02 | probable | Boston, MA | screening_restrictions | Boston City Code ch. 10-3 (Fair Housing) | in_force | none |
| MA-SCR-02 | possible | MA | screening_restrictions | 803 CMR 5.00 | in_force | none |
| SF-JC-02 | possible | San Francisco, CA | just_cause_eviction | S.F. Admin. Code § 37.9C | in_force | none |

### Field errors on matched rules

| Key rule | Team rule | Field | Expected | Team |
|---|---|---|---|---|
| LA-JC-01 | LA-EVIC-01 | effective_date | 2023-01-27 or 2022-12-10 or 2020 | None |
| BRK-RENT-01 | BER-RENT-01 | effective_date | 2026-01-01 or 1980 or 2024-12 | None |
| BRK-SCR-01 | BER-SCR-01 | effective_date | 2020 | None |
| NJ-JC-01 | NJ-EVIC-01 | effective_date | 1974 | None |

### Team rules not in the key (possible false positives, or gaps in our key)

- `MA-FEE-01` MA / application_screening_fees / in_force: Licensed broker fee disclosure regulation - `254 C.M.R. 7`

## 2. Address coverage

943.0 of 957.5 weighted points on 61 sampled addresses (team lookups cover 500 addresses). Counts: {'correct': 570, 'missed_other': 13, 'missed_applies': 8}.

### Errors grouped by key rule (weighted points lost)

| Key rule | Points lost | Errors |
|---|---:|---|
| BOS-SCR-02 | 8.0 | MISSED: 8 |
| SF-SCR-01 | 5.0 | missing: 10 |
| HOB-RENT-01 | 1.5 | missing: 3 |

### Every address error

| Address | City | Built | Units | Key rule | Expected | Team | Error | Why expected |
|---|---|---|---|---|---|---|---|---|
| A0006 | Boston | 1900 | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0016 | San Francisco | 1926 | 21 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0036 | Boston | 2019 | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0040 | Hoboken | - | - | HOB-RENT-01 | unknown (also ok: applies) | omitted | missing | no year built: 30-year new-construction exemption untestable |
| A0048 | Boston | 1899 | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0049 | Hoboken | - | - | HOB-RENT-01 | unknown (also ok: applies) | omitted | missing | no year built: 30-year new-construction exemption untestable |
| A0050 | San Francisco | 1986 | 49 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0065 | Boston | - | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0072 | San Francisco | 1973 | 6 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0081 | San Francisco | 2005 | 69 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0093 | Boston | 2004 | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0098 | Boston | - | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0105 | San Francisco | 2019 | 7 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0106 | San Francisco | - | 60 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0119 | Hoboken | - | - | HOB-RENT-01 | unknown (also ok: applies) | omitted | missing | no year built: 30-year new-construction exemption untestable |
| A0123 | Boston | 2013 | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0156 | San Francisco | 1927 | 9 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0362 | Boston | 1920 | - | BOS-SCR-02 | applies | omitted | MISSED | Boston fair housing |
| A0384 | San Francisco | 1925 | 7 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0398 | San Francisco | 1908 | 5 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |
| A0477 | San Francisco | 1975 | 19 | SF-SCR-01 | unknown | omitted | missing | Fair Chance Ordinance covers affordable housing only; not in data |

Team rule ids in sampled lookups that map to no key rule: `MA-FEE-01` x13

### Full-sample audit (unscored): oracle logic applied to all 500 addresses

176 disagreements. Grouped by key rule:

| Key rule | Disagreement | Count | Examples |
|---|---|---:|---|
| SF-SCR-01 | expected unknown, team omitted | 80 | A0016 (San Francisco, built 1926, units 21); A0021 (San Francisco, built 1963, units 6); A0027 (San Francisco, built 1923, units 6); A0030 (San Francisco, built 1908, units 5) |
| BOS-SCR-02 | expected applies, team omitted | 60 | A0006 (Boston, built 1900, units -); A0036 (Boston, built 2019, units -); A0048 (Boston, built 1899, units -); A0052 (Boston, built 1965, units -) |
| HOB-RENT-01 | expected unknown, team omitted | 36 | A0040 (Hoboken, built -, units -); A0049 (Hoboken, built -, units -); A0087 (Hoboken, built -, units -); A0089 (Hoboken, built -, units -) |

## 3. Citations

3774/4161 'applies' answers backed by a source and a verbatim corpus span. Outcome counts: {'doc': 3774, 'supplementary_only': 387}.

Rule-level span check over all rules: {'doc': 49, 'supplementary_only': 7}

| Team rule | 'applies' answers | failing | span check |
|---|---:|---:|---|
| CA-SCR-02 | 250 | 250 | supplementary_only |
| JC-ALG-01 | 50 | 50 | supplementary_only |
| LA-DEP-01 | 47 | 47 | supplementary_only |
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
