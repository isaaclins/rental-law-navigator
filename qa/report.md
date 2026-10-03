# QA score report (independent key)

Not the official `score.py` (not shipped in the starter pack). Oracle: `qa/expected_rules.json`, `qa/expected_lookups.json`. Not legal advice.

Inputs: `/home/steward/hacknation/realpage/navigator/output/rules.json`, `/home/steward/hacknation/realpage/navigator/output/lookups.json`, `/home/steward/hacknation/realpage/navigator/output/changes.json`

| Component | Score | Max |
|---|---:|---:|
| Extraction accuracy | 23.8 | 25 |
| Address coverage | 19.7 | 20 |
| Citations | 13.6 | 15 |
| Change tracking (T1-T5) | 15.0 | 15 |
| **Auto-scored total** | **72.1** | **75** |

## 1. Extraction

Weighted recall credit 94.2%, precision 100.0%; core rules matched 36/36.

### Missing / citation-mismatched key rules (by points at stake)

| Key rule | Tier | Jurisdiction | Category | Expected citation | Status | Team match |
|---|---|---|---|---|---|---|
| HOB-RENT-01 | probable | Hoboken, NJ | rent_increase_limits | Hoboken City Code ch. 155 | in_force | none |
| BOS-RENT-P1 | probable | Boston, MA | rent_increase_limits | Mass. H.3744 (193rd General Court) | failed | none |
| MA-SCR-02 | possible | MA | screening_restrictions | 803 CMR 5.00 | in_force | none |
| SF-JC-02 | possible | San Francisco, CA | just_cause_eviction | S.F. Admin. Code § 37.9C | in_force | none |

### Field errors on matched rules

| Key rule | Team rule | Field | Expected | Team |
|---|---|---|---|---|
| LA-JC-01 | LA-EVIC-01 | effective_date | 2023-01-27 or 2022-12-10 or 2020 | None |
| BRK-RENT-01 | BER-RENT-01 | effective_date | 2026-01-01 or 1980 or 2024-12 | None |
| BRK-SCR-01 | BER-SCR-01 | effective_date | 2020 | None |
| NJ-JC-01 | NJ-EVIC-01 | effective_date | 1974 | None |
| MA-FEE-01 | MA-FEE-01 | effective_date | 2025-08-01 | None |

### Team rules not in the key (possible false positives, or gaps in our key)


## 2. Address coverage

945.0 of 960.5 weighted points on 61 sampled addresses (team lookups cover 500 addresses). Counts: {'correct': 579, 'unknown_for_applies': 4, 'wrong_result': 5, 'false_positive': 3, 'missed_other': 3}.

### Errors grouped by key rule (weighted points lost)

| Key rule | Points lost | Errors |
|---|---:|---|
| LA-JC-01 | 4.0 | unknown (half credit): 4 |
| SF-RENT-01 | 4.0 | false positive (should be omitted): 3, wrong result: 1 |
| CA-RENT-01 | 4.0 | wrong result: 2 |
| CA-JC-01 | 2.0 | wrong result: 2 |
| HOB-RENT-01 | 1.5 | missing: 3 |

### Every address error

| Address | City | Built | Units | Key rule | Expected | Team | Error | Why expected |
|---|---|---|---|---|---|---|---|---|
| A0040 | Hoboken | - | - | HOB-RENT-01 | unknown (also ok: applies) | omitted | missing | no year built: 30-year new-construction exemption untestable |
| A0049 | Hoboken | - | - | HOB-RENT-01 | unknown (also ok: applies) | omitted | missing | no year built: 30-year new-construction exemption untestable |
| A0050 | San Francisco | 1986 | 49 | CA-RENT-01 | applies | superseded | wrong result | built 1986: older than 15 years |
| A0050 | San Francisco | 1986 | 49 | SF-RENT-01 | omit | applies | false positive (should be omitted) | built 1986: after the SF rent-control cutoff (just cause still applies) |
| A0081 | San Francisco | 2005 | 69 | CA-RENT-01 | applies | superseded | wrong result | built 2005: older than 15 years |
| A0081 | San Francisco | 2005 | 69 | SF-RENT-01 | omit | applies | false positive (should be omitted) | built 2005: after the SF rent-control cutoff (just cause still applies) |
| A0105 | San Francisco | 2019 | 7 | SF-RENT-01 | omit | applies | false positive (should be omitted) | built 2019: after the SF rent-control cutoff (just cause still applies) |
| A0106 | San Francisco | - | 60 | SF-RENT-01 | unknown | applies | wrong result | SF rent limits depend on CO on/before 1979-06-13; no year built |
| A0107 | Los Angeles | 1978 | 20 | CA-JC-01 | superseded | unknown | wrong result | local just-cause ordinance governs (1946.2(i)) |
| A0107 | Los Angeles | 1978 | 20 | LA-JC-01 | applies | unknown | unknown (half credit) | local just cause covers every multifamily unit (RSO/JCO; SF 37.9 incl. post-1979 units) |
| A0119 | Hoboken | - | - | HOB-RENT-01 | unknown (also ok: applies) | omitted | missing | no year built: 30-year new-construction exemption untestable |
| A0200 | Los Angeles | - | 5 | LA-JC-01 | applies | unknown | unknown (half credit) | local just cause covers every multifamily unit (RSO/JCO; SF 37.9 incl. post-1979 units) |
| A0235 | Los Angeles | - | - | LA-JC-01 | applies | unknown | unknown (half credit) | local just cause covers every multifamily unit (RSO/JCO; SF 37.9 incl. post-1979 units) |
| A0432 | Los Angeles | 1978 | 23 | CA-JC-01 | superseded | unknown | wrong result | local just-cause ordinance governs (1946.2(i)) |
| A0432 | Los Angeles | 1978 | 23 | LA-JC-01 | applies | unknown | unknown (half credit) | local just cause covers every multifamily unit (RSO/JCO; SF 37.9 incl. post-1979 units) |

### Full-sample audit (unscored): oracle logic applied to all 500 addresses

61 disagreements. Grouped by key rule:

| Key rule | Disagreement | Count | Examples |
|---|---|---:|---|
| HOB-RENT-01 | expected unknown, team omitted | 36 | A0040 (Hoboken, built -, units -); A0049 (Hoboken, built -, units -); A0087 (Hoboken, built -, units -); A0089 (Hoboken, built -, units -) |
| SF-RENT-01 | expected omit, team applies | 7 | A0050 (San Francisco, built 1986, units 49); A0081 (San Francisco, built 2005, units 69); A0105 (San Francisco, built 2019, units 7); A0283 (San Francisco, built 1986, units 51) |
| SF-RENT-01 | expected unknown, team applies | 2 | A0106 (San Francisco, built -, units 60); A0257 (San Francisco, built -, units 6) |
| LA-JC-01 | expected applies, team unknown | 8 | A0107 (Los Angeles, built 1978, units 20); A0200 (Los Angeles, built -, units 5); A0235 (Los Angeles, built -, units -); A0267 (Los Angeles, built -, units -) |
| CA-RENT-01 | expected applies, team superseded | 6 | A0050 (San Francisco, built 1986, units 49); A0081 (San Francisco, built 2005, units 69); A0283 (San Francisco, built 1986, units 51); A0357 (San Francisco, built 1997, units 29) |
| CA-JC-01 | expected superseded, team unknown | 2 | A0107 (Los Angeles, built 1978, units 20); A0432 (Los Angeles, built 1978, units 23) |

## 3. Citations

3781/4168 'applies' answers backed by a source and a verbatim corpus span. Outcome counts: {'doc': 3781, 'supplementary_only': 387}.

Rule-level span check over all rules: {'doc': 51, 'supplementary_only': 6}

| Team rule | 'applies' answers | failing | span check |
|---|---:|---:|---|
| CA-SCR-01 | 250 | 250 | supplementary_only |
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
