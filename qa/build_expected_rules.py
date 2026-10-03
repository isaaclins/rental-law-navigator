"""Build qa/expected_rules.json: the hand-reviewed QA answer key (test oracle, not product code).

Each record was written by reading the corpus text; the script only serialises the records and
verifies that every quoted_span occurs verbatim (whitespace-normalised) in its source document.
Run: python3 qa/build_expected_rules.py
"""
import json, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / 'starter/corpus/text'
SUPP = pathlib.Path('/home/steward/hacknation/realpage/navigator/supplementary/text')
def norm(s): return re.sub(r'\s+', ' ', s).strip()
def R(kid, jur, cat, status, title, citation, cpat, doc, span, eff=None, eff_accept=None, kv=None, kvpat=None,
      cov=None, tier='core', notes=None):
    level = 'state' if jur in ('CA', 'NJ', 'MA') else 'city'
    return dict(key_rule_id=kid, jurisdiction=jur, level=level, category=cat, status=status, title=title,
                citation=citation, citation_patterns=cpat, effective_date=eff,
                effective_date_accept=eff_accept if eff_accept is not None else ([eff] if eff else []),
                key_value=kv, key_value_patterns=kvpat or [], coverage_conditions=cov, tier=tier,
                source_doc_id=doc, quoted_span=span, notes=notes)
RI, JC, SD_, AF, SR, AL = ('rent_increase_limits', 'just_cause_eviction', 'security_deposits',
                          'application_screening_fees', 'screening_restrictions', 'algorithmic_rent_setting')
rules = [
 # ---------------- California (state) ----------------
 R('CA-RENT-01','CA',RI,'in_force','Tenant Protection Act rent cap (AB 1482)','Cal. Civ. Code § 1947.12',[r'1947\.12'],'D024',
   'an owner of residential real property shall not, over the course of any 12-month period, increase the gross rental rate for a dwelling or a unit more than 5 percent plus the percentage change in the cost of living, or 10 percent, whichever is lower',
   eff='2020-01-01', eff_accept=['2020-01-01','2019-03-15','2024-04-01'], kv='5% + CPI, max 10%', kvpat=[r'5\s*(%|percent)', r'10\s*(%|percent)'],
   cov='CO more than 15 years old (rolling); not single-family/condo with notice; not units under stricter local rent control (d)(3); owner-occupied duplex exempt; sunsets 2030-01-01'),
 R('CA-JC-01','CA',JC,'in_force','Tenant Protection Act just cause (AB 1482)','Cal. Civ. Code § 1946.2',[r'1946\.2'],'D023',
   'after a tenant has continuously and lawfully occupied a residential real property for 12 months, the owner of the residential real property shall not terminate a tenancy without just cause, which shall be stated in the written notice to terminate tenancy.',
   eff='2020-01-01', eff_accept=['2020-01-01','2024-04-01','2026-01-01'], kv='Just cause after 12 months; one month relocation for no-fault', kvpat=[r'just cause|12|month|relocation'],
   cov='Same 15-year CO exemption as 1947.12; yields to local just-cause ordinances (subd. (i))'),
 R('CA-DEP-01','CA',SD_,'in_force','Security deposit cap (AB 12)','Cal. Civ. Code § 1950.5',[r'1950\.5'],'D025',
   'a landlord shall not demand or receive security, however denominated, in an amount or value in excess of an amount equal to one month’s rent, in addition to any rent for the first month paid on or before initial occupancy.',
   eff='2024-07-01', kv="One month's rent (two months for qualifying small landlords)", kvpat=[r'(one|1)[\s-]*month'],
   cov='All residential; small-landlord exception (natural person/family LLC owning <=2 properties with <=4 units) cannot apply at 5+ units'),
 R('CA-FEE-01','CA',AF,'in_force','Application screening fee cap','Cal. Civ. Code § 1950.6',[r'1950\.6'],'D026',
   'In no case shall the amount of the application screening fee charged by the landlord or their agent be greater than thirty dollars ($30) per applicant.',
   eff=None, eff_accept=[], kv='$30 per applicant, CPI-adjusted since 1998; no fee if no unit available', kvpat=[r'30|CPI|consumer price|adjust'],
   notes='No single official 2026 dollar figure (README sec. 9); Berkeley publishes $68.96 for 2026 (D005).'),
 R('CA-SCR-01','CA',SR,'in_force','FEHA source-of-income protection (SB 329)','Cal. Gov. Code § 12955',[r'12955'],'D027',
   'For the owner of any housing accommodation to discriminate against or harass any person because of the race, color, religion, sex, gender, gender identity, gender expression, sexual orientation, marital status, national origin, ancestry, familial status, source of income, disability, veteran or military status, or genetic information of that person.',
   eff='2020-01-01', eff_accept=['2020-01-01','2024-01-01'], kv='No source-of-income discrimination (incl. Section 8 vouchers)', kvpat=[r'source of income|voucher|section 8'] ),
 R('CA-ALG-01','CA',AL,'in_force','Cartwright Act: common pricing algorithms (AB 325 / SB 763)','Cal. Bus. & Prof. Code § 16729 (AB 325)',[r'16729|AB\s*-?\s*325|SB\s*-?\s*763'],'D022',
   'It shall be unlawful for a person to use or distribute a common pricing algorithm as part of a contract, combination in the form of a trust, or conspiracy to restrain trade or commerce in violation of this chapter.',
   eff='2026-01-01', kv='Ban on using/distributing a common pricing algorithm in a conspiracy or with coercion', kvpat=[r'algorithm|pricing|coerc']),
 R('CA-SCR-02','CA',SR,'in_force','FEHA regulations: criminal history in housing','Cal. Code Regs. tit. 2, § 12264 et seq. (FEHA)',[r'1226[4-9]|1227[01]|Reg|C\.?C\.?R|Civil Rights Council'],'D016',
   'Housing providers cannot consider some types of criminal history including arrests that did not lead to a conviction, records that are sealed or expunged, or records or matters processed in the juvenile justice system.',
   eff='2020-01-01', kvpat=[], tier='probable'),
 # ---------------- Los Angeles ----------------
 R('LA-RENT-01','Los Angeles, CA',RI,'in_force','Rent Stabilization Ordinance (RSO)','L.A. Mun. Code ch. XV, § 151.00 et seq. (RSO)',[r'151|RSO|Rent Stabilization'],'D041',
   'Generally, the RSO applies to rental properties that were first built on or before October 1, 1978',
   eff=None, eff_accept=['2026-02-02','2026-01-24','1979'], kv='3% (7/1/2025-6/30/2026); no utility add-on from 2/2/2026', kvpat=[r'%|CPI|percent'],
   cov='Certificate of occupancy on or before 1978-10-01 (year 1978 = unknown); RSO units take the stricter local cap'),
 R('LA-JC-01','Los Angeles, CA',JC,'in_force','Just Cause Ordinance (JCO) / RSO eviction protections','L.A. Mun. Code § 165.00 et seq. (JCO); § 151.09 (RSO)',[r'165|151\.09|Just Cause|JCO'],'D040',
   'It prohibits terminations of tenancies without just cause and requires relocation assistance for no-fault evictions.',
   eff=None, eff_accept=['2023-01-27','2022-12-10','2020'], kv='Just cause required; relocation $11,000-$27,400 for no-fault (7/1/2026)', kvpat=[r'just cause|relocation|\$'],
   cov='JCO covers non-RSO units (incl. post-1978 and new construction); RSO units covered by LAMC 151.09 -> every LA multifamily unit has local just cause'),
 R('LA-DEP-01','Los Angeles, CA',SD_,'in_force','RSO security deposit interest','L.A. Mun. Code § 151.06.02',[r'151\.06'],'D044',
   None, tier='possible', notes='Source is link-only (D044, AAGLA); no quoted span in supplied corpus text.'),
 # ---------------- San Francisco ----------------
 R('SF-RENT-01','San Francisco, CA',RI,'in_force','SF Rent Ordinance annual allowable increase','S.F. Admin. Code ch. 37 (§ 37.3)',[r'\b37\b|37\.3|Rent Ordinance|Admin'],'D080',
   'For rent-controlled units, the annual allowable increase amount effective March 1, 2026 through February 28, 2027 is 1.6%.',
   eff=None, eff_accept=['2026-03-01','1979-06-13','1979'], kv='1.6% (3/1/2026-2/28/2027)', kvpat=[r'1\.6'],
   cov='Rent increase limits: certificate of occupancy on or before 1979-06-13 (year 1979 = unknown)'),
 R('SF-JC-01','San Francisco, CA',JC,'in_force','SF Rent Ordinance just cause','S.F. Admin. Code § 37.9',[r'37\.9'],'D079',
   'In order to evict a tenant from a rental unit covered by the Rent Ordinance, a landlord must have a "just cause" reason that is the dominant motive for pursuing the eviction.',
   eff=None, eff_accept=[], kv='17 just causes (37.9(a)); relocation $8,245/tenant (3/1/26)', kvpat=[r'just cause|17|caus|relocation'],
   cov='Applies also to post-1979 units exempt from rent limits (D079)'),
 R('SF-ALG-01','San Francisco, CA',AL,'in_force','Algorithmic rent-setting device ban','S.F. Admin. Code § 37.10C',[r'37\.10\s*C'],'D081',
   'Legislation adding Section 37.10C to the Rent Ordinance went into effect on October 14, 2024.',
   eff='2024-10-14', eff_accept=['2024-10-14','2024-10'], kv='Ban on sale/use of algorithmic devices using nonpublic competitor data', kvpat=[r'algorithm|nonpublic|device']),
 R('SF-SCR-01','San Francisco, CA',SR,'in_force','Fair Chance Ordinance (affordable housing)','S.F. Police Code art. 49 (Fair Chance Ordinance)',[r'Fair Chance|Police Code|Art(icle)?\.?\s*49|\b49\b|4903'],'D078',
   "San Francisco's Fair Chance Ordinance protects residents with arrest or conviction history in affordable housing decisions.",
   tier='probable', cov='Affordable housing only -> coverage unknown from assessor data'),
 R('SF-DEP-01','San Francisco, CA',SD_,'in_force','Security deposit interest rate','S.F. Admin. Code ch. 49',[r'\b49\b|49\.2|deposit'],'D083',
   'Security Deposit Interest: 4.2% for March 1, 2026 – February 28, 2027', kv='4.2% interest (3/1/26-2/28/27)', kvpat=[r'4\.2'], tier='probable'),
 # ---------------- San Diego ----------------
 R('SD-JC-01','San Diego, CA',JC,'in_force','Residential Tenant Protections (just cause)','San Diego Mun. Code §§ 98.0701-98.0710',[r'98\.07'],'D073',
   'A landlord shall not terminate a tenancy without just cause. For purposes of this Division, just cause includes at-fault just cause and no-fault just cause.',
   eff='2023-06-24', kv='Just cause from day one; two months relocation for no-fault', kvpat=[r'just cause|relocation|month'],
   cov='Same exemptions as state law incl. CO within previous 15 years -> unknown (no year built for San Diego)'),
 R('SD-ALG-01','San Diego, CA',AL,'in_force','Prohibition of anti-competitive automated rent price-fixing','San Diego Mun. Code §§ 98.1101-98.1104',[r'98\.110[1-4]|98\.11'],'D076',
   '(b) It is unlawful for a landlord to use an algorithmic device to set rental rates or occupancy levels for residential rental property.',
   eff='2025-06', eff_accept=['2025-06','2025-05'], kv='Ban on algorithmic devices; up to $1,000 per violation', kvpat=[r'algorithm|1,?000']),
 R('SD-SCR-01','San Diego, CA',SR,'in_force','Source of income discrimination ordinance','San Diego Mun. Code § 98.0801 et seq.',[r'98\.08|div(ision)?\.?\s*8\b'],'D075',
   None, tier='possible', notes='Link-only source (D075).'),
 # ---------------- Berkeley ----------------
 R('BRK-RENT-01','Berkeley, CA',RI,'in_force','Rent Stabilization Ordinance: Annual General Adjustment','Berkeley Mun. Code ch. 13.76 (§ 13.76.110)',[r'13\.76'],'D008',
   'allow eligible landlords to increase the 2025 permanent rent ceilings by 1.0% no earlier than January 1, 2026.',
   eff=None, eff_accept=['2026-01-01','1980','2024-12'], kv='AGA 1.0% for 2026 (65% of CPI, max 5%)', kvpat=[r'1(\.0)?\s*%|65'],
   cov='Fully covered: multifamily built before 1980; new construction (CO after June 1980) exempt -> unknown (no year built in Berkeley data)'),
 R('BRK-JC-01','Berkeley, CA',JC,'in_force','Rent Stabilization and Eviction for Good Cause Ordinance: just cause','Berkeley Mun. Code § 13.76.130',[r'13\.76'],'D006',
   'tenants in units that are fully or partially covered by the Rent Ordinance cannot be evicted unless there is',
   eff=None, eff_accept=[], kv='Just cause; relocation $19,413 (+$6,471) from 1/1/2026', kvpat=[r'just cause|good cause|relocation|19,?413'],
   cov='Fully and partially covered units (incl. post-1980 new construction)'),
 R('BRK-ALG-01','Berkeley, CA',AL,'in_force','Ban on coordinated pricing algorithms','Berkeley Mun. Code ch. 13.63 (Ord. 7,992-N.S.)',[r'13\.63|7,?992'],'D001',
   'It shall be unlawful for a landlord to use a coordinated pricing algorithm described in subsection A when setting rents or occupancy levels for residential dwelling units in the City of Berkeley.',
   eff='2026-03-01', eff_accept=['2026-03-01','2026-01','2025-12'], kv='Ban; civil penalties up to $1,000 per violation', kvpat=[r'algorithm|1,?000|coordinat'],
   notes='Two published effective dates: 2026-03-01 (ordinance) vs January 2026 (Aug 2026 law-firm alert, D002). Either accepted; a conflict flag is ideal.'),
 R('BRK-SCR-01','Berkeley, CA',SR,'in_force','Fair Chance Access to Housing Ordinance','Berkeley Mun. Code ch. 13.106',[r'13\.106'],'D003',
   'The Fair Chance Access to Housing Ordinance prohibits rental housing providers in Berkeley from asking about and using criminal history and/or criminal background checks in their rental housing advertising, applications, tenant selection process, or decision-making.',
   eff=None, eff_accept=['2020'], kv='No criminal-history inquiries or use', kvpat=[r'criminal']),
 R('BRK-FEE-01','Berkeley, CA',AF,'in_force','Tenant screening fee disclosure and limits','Berkeley Mun. Code ch. 13.78',[r'13\.78'],'D005',
   'The maximum tenant screening fee for 2026 is $68.96', kv='$68.96 max (2026); no non-refundable renewal/roommate fees', kvpat=[r'68\.96|refund'], tier='probable'),
 R('BRK-DEP-01','Berkeley, CA',SD_,'in_force','Security deposit interest (Rent Ordinance)','Berkeley Mun. Code ch. 13.76',[r'13\.76|deposit'],'D007',
   'landlords must pay tenants interest on their security deposit at the end of each year', tier='probable'),
 # ---------------- Santa Ana (extraction only) ----------------
 R('SA-RENT-01','Santa Ana, CA',RI,'in_force','Rent Stabilization Ordinance','Santa Ana Mun. Code ch. 8, art. XIX (Rent Stabilization Ordinance)',[r'Rent Stabilization|8-\d|NS-?30\d\d|Santa Ana'],'D085',
   'Increase in residential rents are limited to the lower of 3% per year, or 80% of the percent change in the Consumer Price Index over the most recent 12-month period.',
   eff='2021-11-19', kv='Lower of 3% or 80% of CPI (2.87% for 9/1/2026-8/31/2027)', kvpat=[r'3\s*%|80\s*%|2\.87'],
   cov='Not buildings constructed after 1995-02-01'),
 R('SA-JC-01','Santa Ana, CA',JC,'in_force','Just Cause Eviction Ordinance','Santa Ana Mun. Code ch. 8, art. XX (Just Cause Eviction Ordinance)',[r'Just Cause|8-\d|NS-?30\d\d|Santa Ana'],'D085',
   'After 30 days, an owner shall not terminate a tenancy without just cause, which shall be stated in a written notice.',
   eff='2021-11-19', kv='Just cause after 30 days; 3 months relocation for no-fault', kvpat=[r'just cause|30 days|3 months|three months|relocation']),
 R('SA-ALG-01','Santa Ana, CA',AL,'in_force','Ban on algorithmic rent-setting devices','Santa Ana Ord. No. NS-3090',[r'NS-?\s*3090'],'D086',
   None, eff='2026-04-02', eff_accept=['2026-04-02','2026-04','2026-03-03'], kv='Ban; up to $1,000 per violation', kvpat=[r'algorithm|1,?000'],
   notes='Text only in link-only sources (D086/D087, D002 table).'),
 # ---------------- New Jersey (state) ----------------
 R('NJ-JC-01','NJ',JC,'in_force','Anti-Eviction Act','N.J.S.A. 2A:18-61.1',[r'2A:18-61'],'D067',
   'The Anti-Eviction Act, N.J.S.A. 2A:18-61.1 to 61.12, was created to protect blameless tenants from eviction',
   eff=None, eff_accept=['1974'], kv='Eviction only for statutory good causes', kvpat=[r'cause|good|statutory|ground'],
   cov='Most residential rentals; not owner-occupied premises with <=2 rental units'),
 R('NJ-DEP-01','NJ',SD_,'in_force','Rent Security Deposit Act','N.J.S.A. 46:8-21.2',[r'46:8-21\.2|46:8-19|46:8-26'],'D067',
   'The maximum-security deposit to be collected by the landlord cannot be more than one and one-half times one month’s rent',
   eff=None, eff_accept=[], kv="1.5 months' rent", kvpat=[r'1\.5|one and one-half|1 1/2|one-and-one-half'],
   cov='Not owner-occupied 2- or 3-family dwellings (unless tenant opts in)'),
 R('NJ-FEE-01','NJ',AF,'in_force','Residential rental application fee cap','N.J.S.A. 46:8-18.1 (P.L.2025, c.405)',[r'46:8-18\.1|c\.?\s*405'],'D066',
   'A landlord, or agent thereof, shall not require an application or other similar fee to apply to lease or sublease a residential rental property for dwelling purposes, which exceeds $50.',
   eff='2026-05-01', kv='$50 cap (CPI-adjusted from 2027)', kvpat=[r'\$?\s*50\b'],
   cov='Not units in one- or two-family dwellings'),
 R('NJ-SCR-01','NJ',SR,'in_force','Fair Chance in Housing Act','N.J.S.A. 46:8-52 et seq. (P.L.2021, c.110)',[r'46:8-5\d|46:8-6\d|c\.?\s*110|Fair Chance'],'D065',
   'A housing provider shall not require an applicant to complete any housing application that includes any inquiries regarding an applicant’s criminal record prior to the provision of a conditional offer',
   eff='2022-01-01', kv='No criminal-history inquiry before a conditional offer; lookback limits', kvpat=[r'criminal|conditional offer'],
   cov='Not owner-occupied premises of <=4 dwelling units'),
 R('NJ-SCR-02','NJ',SR,'in_force','LAD: source of lawful income','N.J.S.A. 10:5-12 (Law Against Discrimination)',[r'10:5-12|Law Against Discrimination|\bLAD\b'],'D068',
   'The LAD also prohibits housing discrimination based on the source of lawful income or source of lawful rent or mortgage payment a tenant or purchaser uses.',
   tier='probable', kv='No source-of-income discrimination (Section 8)', kvpat=[r'source of (lawful )?income|section 8|voucher']),
 R('NJ-ALG-01','NJ',AL,'not_yet_effective','FAIR Act (algorithmic rent-setting ban)','P.L.2026, c.43 (N.J.S.A. 56:9-20 et seq.)',[r'c\.?\s*0?43|56:9-2\d|FAIR'],'D069',
   'a rental property owner, or any agent, representative, or subcontractor thereof, to receive, subscribe to, contract for, or otherwise exchange any form of consideration in return for the use of, the services of a coordinator;',
   eff='2027-07-01', kv='Ban on coordinators/algorithmic rent setting; may preempt local bans (sec. 6b)', kvpat=[r'algorithm|coordinat|antitrust']),
 # ---------------- Jersey City / Hoboken / Newark ----------------
 R('JC-RENT-01','Jersey City, NJ',RI,'in_force','Rent Control Ordinance','Jersey City Mun. Code ch. 260',[r'260'],'D036',
   'The Office of Landlord Tenant Relations administers and enforces the Rent Control Ordinance, Chapter 260 of the Jersey City Municipal Code',
   kv='CPI-based annual increase', kvpat=[], cov='1-4 unit properties exempt; new construction exempt 30 years (N.J.S.A. 2A:42-84.5)'),
 R('JC-ALG-01','Jersey City, NJ',AL,'in_force','Ban on algorithmic rent coordination','Jersey City Mun. Code § 218-12',[r'218-12'],'D035',
   None, eff='2025-06', eff_accept=['2025-06'], kv='Ban; fines up to $2,000 per day', kvpat=[r'algorithm|2,?000|coordinat'],
   notes='Ordinance text not supplied (D035/D037 link-only).'),
 R('HOB-RENT-01','Hoboken, NJ',RI,'in_force','Rent Leveling and Stabilization','Hoboken City Code ch. 155',[r'155|Rent (Leveling|Control)'],'D032',
   None, tier='probable', cov='New construction exempt 30 years', notes='Code text link-only (ecode360, check-terms).'),
 R('HOB-ALG-01','Hoboken, NJ',AL,'in_force','Ban on algorithmic rent-setting','Hoboken City Code ch. 158, Art. II',[r'158'],'D032',
   None, eff='2025-07', eff_accept=['2025-07'], kv='Ban on software/algorithms coordinating rents', kvpat=[r'algorithm|software|coordinat'],
   notes='Code text link-only.'),
 R('NWK-RENT-01','Newark, NJ',RI,'in_force','Rent Control Ordinance','Newark Mun. Code ch. 19:2',[r'19[:\-]2|Rent (Control|Regulation)'],'D070',
   None, tier='probable', notes='Code text link-only (ecode360, check-terms).'),
 # ---------------- Massachusetts (state) ----------------
 R('MA-RENT-01','MA',RI,'in_force','Rent Control Prohibition Act (state bar on local rent control)','G.L. c. 40P, § 4',[r'40P'],'D048',
   'No city or town may enact, maintain or enforce rent control of any kind',
   kv='No local rent control (narrow voluntary exception)', kvpat=[r'no|bar|prohibit'],
   notes='A bar, not a cap: lookups must never report a rent cap for Boston/Cambridge.'),
 R('MA-RENT-P1','MA',RI,'failed','Initiative Petition 25-21 (statewide rent control) struck by SJC','Initiative Petition 25-21 (Cella v. Attorney General, SJC-13893)',[r'25-21|Cella|ballot|Initiative'],'D059',
   None, eff=None, kv='Would have capped increases at lesser of CPI or 5% - never in force', kvpat=[],
   notes='Struck 2026-06-23; must be status failed and never applied (T5).'),
 R('MA-DEP-01','MA',SD_,'in_force','Security deposit limit','G.L. c. 186, § 15B',[r'186.{0,12}15B|15B'],'D052',
   "a security deposit equal to the first month's rent provided that such security deposit is deposited as required by subsection (3)",
   kv="First month's rent", kvpat=[r'first month|one month|1 month']),
 R('MA-FEE-01','MA',AF,'in_force','Upfront charges limited (no application fees)','G.L. c. 186, § 15B(1)(b)',[r'186.{0,12}15B|15B'],'D052',
   'At or prior to the commencement of any tenancy, no lessor or agent of the lessor may require a tenant or prospective tenant to pay, to the lessor or to an agent of the lessor, any amount in excess of the following:',
   eff=None, eff_accept=['2025-08-01'], kv="Only first and last month's rent, security deposit, lock and key", kvpat=[r'first|last|lock|deposit']),
 R('MA-FEE-02','MA',AF,'in_force','Broker fee paid by the party who hired the broker','G.L. c. 112, § 87DDD½',[r'87\s*DDD'],'D057',
   'Any fee shall only be paid by the party, lessor or tenant who originally engaged and entered into a contract with the licensed broker or salesperson.',
   eff='2025-08-01', kv='Broker fee only payable by the party that engaged the broker', kvpat=[r'broker|engag|hired']),
 R('MA-SCR-01','MA',SR,'in_force','No discrimination against recipients of public assistance / housing subsidies','G.L. c. 151B, § 4(10)',[r'151B'],'D049',
   'For any person furnishing credit, services or rental accommodations to discriminate against any individual who is a recipient of federal, state, or local public assistance',
   kv='Source of income / Section 8 protected', kvpat=[r'assistance|subsid|voucher|section 8|source']),
 R('MA-SCR-02','MA',SR,'in_force','CORI use in housing','803 CMR 5.00',[r'803\s*CMR|CORI'],'D056',
   None, tier='possible', notes='Official source blocked (403); no text supplied.'),
 R('MA-JC-01','MA',JC,'in_force','Notice to quit / termination of tenancy at will','G.L. c. 186, §§ 11-12',[r'186.{0,14}\b1[12]\b'],'D051',
   "Estates at will may be determined by either party by three months' notice in writing for that purpose given to the other party",
   kv="3 months' (or one rental period, min. 30 days) notice; 14 days for nonpayment", kvpat=[r'notice|14|30|month'],
   tier='probable', notes='Notice rules, not just-cause; MA has no statewide just-cause requirement. D050 (sec. 11) and D051 (sec. 12).'),
 R('MA-JC-02','MA',JC,'in_force','Reprisal / retaliation protection','G.L. c. 186, § 18',[r'186.{0,14}\b18\b'],'D053',
   "shall be liable for damages which shall not be less than one month's rent or more than three month's rent",
   kv="1-3 months' rent damages; 6-month presumption", kvpat=[r'month|reprisal|retaliat'], tier='probable'),
 R('MA-JC-03','MA',JC,'in_force','Notice to quit for nonpayment must include state form','G.L. c. 186, § 31',[r'186.{0,14}\b31\b'],'D058',
   'A notice to quit for nonpayment of rent given in writing by a landlord to a residential tenant pursuant to this chapter shall be accompanied by a form',
   tier='possible'),
 R('MA-ALG-P1','MA',AL,'pending','S.2983: An Act prohibiting algorithmic rent setting','Mass. S.2983 (194th General Court)',[r'S\.?\s*2983'],'D046',
   'An Act prohibiting algorithmic rent setting', kv='Pending in Senate Ways and Means', kvpat=[]),
 R('MA-ALG-P2','MA',AL,'pending','H.5222: An Act relative to preventing algorithmic rent fixing','Mass. H.5222 (194th General Court)',[r'H\.?\s*5222'],'D045',
   'An Act relative to preventing algorithmic rent fixing in the rental housing market', kv='Pending in House Ways and Means', kvpat=[]),
 # ---------------- Boston / Cambridge ----------------
 R('BOS-RENT-P1','Boston, MA',RI,'failed','H.3744 home-rule petition (rent stabilization) - not enacted','Mass. H.3744 (193rd General Court)',[r'H\.?\s*3744'],'D011',
   'An Act petition for a special law authorizing the city of Boston to implement rent stabilization and tenant eviction protections',
   tier='probable', notes='Sent to study order 9/9/2024; never enacted. Must never be applied.'),
 R('BOS-JC-01','Boston, MA',JC,'in_force','Housing Stability Notification Act','Boston City Code § 10-11.7',[r'10-11|Housing Stability'],'D013',
   'The Housing Stability Notification Act requires any landlord to provide renters with a Notice of Tenant’s Rights and Resources when planning to end a tenancy agreement.',
   tier='probable', notes='Notice duty, not just cause.'),
 R('BOS-SCR-01','Boston, MA',SR,'in_force','Boston Fair Chance Tenant Selection Policy','Boston DND Fair Chance Tenant Selection Policy (2017)',[r'Fair Chance|DND|Tenant Selection'],'D010',
   'will not impose a blanket policy that denies housing to anyone with arrests and or convictions.',
   tier='probable', cov='Only DND-funded / IDP income-restricted housing'),
 R('BOS-SCR-02','Boston, MA',SR,'in_force','Boston Fair Housing ordinance: rental assistance','Boston City Code ch. 10-3 (Fair Housing)',[r'10-3|Fair Housing'],'D012',
   "In the City of Boston, it’s illegal to discriminate when renting, buying, selling, or securing financing for any housing.", tier='probable'),
 R('CAM-JC-01','Cambridge, MA',JC,'in_force','Tenants Rights and Resources Notification Ordinance','Cambridge Mun. Code ch. 8.71',[r'8\.71'],'D031',
   'The City of Cambridge Tenants Rights and Resources Ordinance, Chapter 8.71 of the Cambridge Municipal Code',
   tier='probable', notes='Notice duty, not just cause.'),
 R('CAM-SCR-01','Cambridge, MA',SR,'in_force','Cambridge Fair Housing Ordinance: source of income','Cambridge Mun. Code ch. 14.04',[r'14\.04|2\.76'],'D029',
   'Source of Income, includes Section 8 and public benefits', tier='probable'),
 R('NJ-JC-02','NJ',JC,'in_force','Reprisal / retaliatory eviction protection','N.J.S.A. 2A:42-10.10',[r'2A:42-10\.1\d'],'D067',
   None, tier='possible'),
 R('LA-JC-02','Los Angeles, CA',JC,'in_force','Resident Protections Ordinance (demolition for new construction)','L.A. Ord. Nos. 188481-188482 (Resident Protections Ordinance)',[r'18848|Resident Protection'],'D043',
   None, tier='possible'),
 R('SF-JC-02','San Francisco, CA',JC,'in_force','Relocation payments for no-fault evictions','S.F. Admin. Code § 37.9C',[r'37\.9\s*C'],'D083',
   None, kv='$8,245 per tenant, max $24,733 per unit (3/1/26)', kvpat=[r'8,?245'], tier='possible'),
]
NR = lambda fid, jur, cat, finding, cite, doc, span, tier='core': dict(finding_id=fid, jurisdiction=jur, level='state' if jur in ('CA','NJ','MA') else 'city', category=cat, finding=finding, basis_citation=cite, source_doc_id=doc, quoted_span=span, tier=tier)
no_rule = [
 NR('NR-01','Boston, MA',RI,'No rent cap: local rent control barred by G.L. c.40P; H.3744 never enacted; ballot question IP 25-21 struck.','G.L. c. 40P, § 4','D048','No city or town may enact, maintain or enforce rent control of any kind'),
 NR('NR-02','Cambridge, MA',RI,'No rent cap: local rent control barred by G.L. c.40P; ballot question struck.','G.L. c. 40P, § 4','D048','No city or town may enact, maintain or enforce rent control of any kind'),
 NR('NR-03','MA',JC,'No statewide just-cause eviction requirement (only notice-to-quit rules, c.186 §§11-12).','G.L. c. 186, § 12','D051',"Estates at will may be determined by either party by three months' notice in writing for that purpose given to the other party",'possible'),
 NR('NR-04','Boston, MA',JC,'No local just-cause ordinance in force (H.3744 home-rule petition not enacted; HSNA is notice-only).','Mass. H.3744','D011','Accompanied a study order','possible'),
 NR('NR-05','Cambridge, MA',JC,'No local just-cause ordinance (ch. 8.71 is a notice requirement only).','Cambridge Mun. Code ch. 8.71','D031','This Ordinance does not prevent a landlord from initiating an eviction action if otherwise allowed by law.','possible'),
 NR('NR-06','MA',AL,'No enacted state algorithmic rent-setting law; S.2983 and H.5222 are pending.','Mass. S.2983 / H.5222','D046','Referred to Senate Committee on Ways and Means'),
 NR('NR-07','Boston, MA',AL,'No local algorithmic rent-setting ban.','-',None,None),
 NR('NR-08','Cambridge, MA',AL,'No local algorithmic rent-setting ban in force (policy order only; hour-16 fictional ordinance is a separate test).','-','D030',None),
 NR('NR-09','NJ',RI,'No state rent-control law; rent control is set city by city.','NJ DCA Truth in Renting','D067','The State of New Jersey has no laws that establish, govern or control rents.'),
 NR('NR-10','Newark, NJ',AL,'No Newark algorithmic rent-setting ban (T2).','-',None,None),
 NR('NR-11','Los Angeles, CA',AL,'No LA algorithmic ban: only a 2024 Council motion asking for a report.','Council File 24-1031','D039','report on the number of ownership and management entities that are using algorithm-based software to establish rents and the feasibility of instituting a ban'),
 NR('NR-12','San Diego, CA',RI,'No local rent control in San Diego; only the state cap.','-',None,None),
 NR('NR-13','MA',AF,'No application-fee permission: landlords may not charge application fees (c.186 §15B) - recorded as rule MA-FEE-01, listed here for completeness.','G.L. c. 186, § 15B','D052',None,'possible'),
 NR('NR-14','Jersey City, NJ',JC,'No local just-cause ordinance; state Anti-Eviction Act governs.','N.J.S.A. 2A:18-61.1','D067',None,'possible'),
 NR('NR-15','Hoboken, NJ',JC,'No local just-cause ordinance; state Anti-Eviction Act governs.','N.J.S.A. 2A:18-61.1','D067',None,'possible'),
 NR('NR-16','Newark, NJ',JC,'No local just-cause ordinance; state Anti-Eviction Act governs.','N.J.S.A. 2A:18-61.1','D067',None,'possible'),
 NR('NR-17','MA',RI,'No statewide rent cap (IP 25-21 struck 2026-06-23).','Initiative Petition 25-21','D059',None,'possible'),
 NR('NR-18','Los Angeles, CA',SD_,'No LA local deposit cap (state 1950.5 governs; RSO only requires interest).','-',None,None,'possible'),
 NR('NR-19','Newark, NJ',SR,'No Newark local screening ordinance found in the corpus.','-',None,None,'possible'),
]
# verify spans
bad = 0
def find(doc, span):
    for base in (CORPUS, SUPP):
        p = base / f'{doc}.txt'
        if p.exists() and norm(span) in norm(p.read_text(encoding='utf-8')):
            return 'corpus' if base == CORPUS else 'supplementary'
    return None
for r in rules + no_rule:
    if r.get('quoted_span'):
        loc = find(r['source_doc_id'], r['quoted_span'])
        r['span_location'] = loc
        if not loc:
            bad += 1; print('SPAN NOT FOUND', r.get('key_rule_id') or r.get('finding_id'), r['source_doc_id'], r['quoted_span'][:80])
    else:
        r['span_location'] = None
from collections import Counter
print('rules', len(rules), Counter(r['tier'] for r in rules), 'no_rule', len(no_rule), 'bad spans', bad)
out = {
 'about': 'Independent QA answer key (test oracle), hand-built from the starter corpus by reading the legal texts. Not legal advice. '
          'Tiers: core = almost certainly in the hidden key; probable; possible = plausible extra records (scored with lower weight). '
          'citation_patterns / key_value_patterns are regexes used by qa/score.py for matching; effective_date_accept lists accepted values (prefix match).',
 'as_of': '2026-10-01', 'built': '2026-10-03', 'rules': rules, 'no_rule_findings': no_rule}
json.dump(out, open(ROOT / 'qa/expected_rules.json', 'w'), indent=1, ensure_ascii=False)
