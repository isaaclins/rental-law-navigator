"""Reviewed field corrections, each backed by a verbatim quote that code checks against the source text.

The extraction leaves a field empty or incomplete when the model did not pick it up; a reviewer who finds the value
stated in the source adds it here with the exact sentence that states it. finalize() applies a fix only when that
sentence is found verbatim (whitespace- and quote-insensitive) in the named document, and logs every fix to
audit.jsonl (stage "review_fix"). Nothing here is applied without its evidence; a value no source states is never
added. Not legal advice.
"""

from __future__ import annotations

FIXES: list[dict] = [
    {
        # SB 763 is named in the corpus only by the secondary source D028 (fetched link-only page); the citation
        # aliases already list it, the title did not
        "rule": "CA-ALG-01",
        "citation": "Cal. Bus. & Prof. Code § 16729",
        "set": {
            "title": "AB 325 / SB 763 – Common pricing algorithm prohibition (Cartwright Act)",
            "penalty": "Cartwright Act as amended by AB 325 / SB 763: civil fines up to $1 million; criminal fines"
            " up to $6 million for businesses and $1 million for individuals (D028).",
        },
        "evidence": [
            {
                "doc_id": "D028",
                "quoted_span": "Last October, California Governor Newsom signed into law Assembly Bill 325 (AB 325)"
                " and Senate Bill 763 (SB 763), amending the Act.",
            },
            {
                "doc_id": "D028",
                "quoted_span": "Criminal fines rise to more than $6 million for businesses and $1 million for"
                " individuals, and businesses and individuals may now be subject to civil fines of up to $1"
                " million",
            },
        ],
    },
    {
        # the current text of the cap clause, § 15B(1)(b), took effect Aug 1, 2025 (St. 2025, c. 9); the cap itself
        # is older and its first date is not stated, so the rule stays in force on every earlier date
        "rule": "MA-DEP-01",
        "citation": "G.L. c. 186, § 15B",
        "set": {
            "effective_date": "2025-08-01",
            "current_version_effective": "2025-08-01",
            "amends_existing_law": True,
            "effective_date_note": "Current text of § 15B(1)(b) effective August 1, 2025 (St. 2025, c. 9, §§ 54-55);"
            " the original date of the one-month cap is not stated in the document.",
        },
        "evidence": [
            {
                "doc_id": "D052",
                "quoted_span": "Introductory paragraph of clause (b) of subsection (1) as amended by 2025, 9, Secs."
                " 54 and 55 effective August 1, 2025.",
            }
        ],
    },
    # ---- earlier versions (evaluate.version_gap): a rule that amends an older law states its requirement as of its
    # effective_date. Before that date the engine answers "unknown: an earlier version applied" unless the sources
    # show the earlier version said the same ("same"); "in_sources": the sources state the earlier figure, but our
    # data holds only the current one.
    {
        "rule": "CA-RENT-01",
        "citation": "Cal. Civ. Code § 1947.12",
        "set": {"earlier_version": "same"},
        "evidence": [
            {
                "doc_id": "D024",
                "quoted_span": "This section shall apply to all rent increases subject to subdivision (a) occurring"
                " on or after March 15, 2019",
            }
        ],
    },
    {
        "rule": "CA-FEE-01",
        "citation": "Cal. Civ. Code § 1950.6",
        "set": {"earlier_version": "same"},
        "evidence": [
            {
                "doc_id": "D026",
                "quoted_span": "The thirty dollar ($30) application screening fee may be adjusted annually by the"
                " landlord or their agent commensurate with an increase in the Consumer Price Index, beginning on"
                " January 1, 1998.",
            }
        ],
    },
    {
        # the statute shows the text "effective until August 1, 2025" too: the same first-month cap
        "rule": "MA-DEP-01",
        "citation": "G.L. c. 186, § 15B",
        "set": {"earlier_version": "same"},
        "evidence": [
            {
                "doc_id": "D052",
                "quoted_span": "effective until August 1, 2025.  For text effective August 1, 2025, see below.] (b)"
                " At or prior to the commencement of any tenancy, no lessor may require a tenant or prospective"
                " tenant to pay any amount in excess of the following:",
            }
        ],
    },
    {
        "rule": "MA-FEE-02",
        "citation": "G.L. c. 186, § 15B(1)(b)",
        "set": {"earlier_version": "same"},
        "evidence": [
            {
                "doc_id": "D052",
                "quoted_span": "effective until August 1, 2025.  For text effective August 1, 2025, see below.] (b)"
                " At or prior to the commencement of any tenancy, no lessor may require a tenant or prospective"
                " tenant to pay any amount in excess of the following:",
            }
        ],
    },
    {
        "rule": "CA-DEP-01",
        "citation": "Cal. Civ. Code § 1950.5",
        "set": {"earlier_version": "in_sources"},
        "evidence": [
            {
                "doc_id": "D025",
                "quoted_span": "This subdivision shall not apply to a security collected or demanded by the landlord"
                " before July 1, 2024.",
            },
            {
                "doc_id": "D007",
                "quoted_span": "Before July 1, 2024, landlords could charge up to two months' rent for unfurnished"
                " units, and up to three months' rent for furnished units.",
            },
        ],
    },
    {
        "rule": "SF-RENT-01",
        "citation": "S.F. Admin. Code ch. 37",
        "set": {"earlier_version": "in_sources"},
        "evidence": [
            {
                "doc_id": "D080",
                "quoted_span": "The annual allowable increase amount effective March 1, 2025 through February 28,"
                " 2026 is 1.4%.",
            }
        ],
    },
    {
        "rule": "SF-EVIC-02",
        "citation": "S.F. Admin. Code § 37.9C",
        "set": {"earlier_version": "in_sources"},
        "evidence": [
            {"doc_id": "D082", "quoted_span": "3/01/25 – 2/28/26 $8,062.00 $24,184.00 $5,375.00"}
        ],
    },
    {
        "rule": "SF-DEP-01",
        "citation": "S.F. Admin. Code ch. 37",
        "set": {"earlier_version": "in_sources"},
        "evidence": [{"doc_id": "D083", "quoted_span": "March 1, 2025 – February 28, 2026 5.0%"}],
    },
    # ---- legal-accuracy review 2026-10-04 (~/share/hacknation/qa/legal-review): wording of the data itself
    {
        # § 12: three months only when rent is paid every three months or less often; otherwise one rent period or
        # 30 days, whichever is longer (the "3 months" the Ask fallback and the any-address card read was wrong for
        # monthly rent); the section governs tenancies at will (no lease) only
        "rule": "MA-EVIC-02",
        "citation": "G.L. c. 186, § 12",
        "set": {
            "key_value": "One rent period or 30 days (whichever is longer); 3 months if rent is paid quarterly;"
            " 14 days for nonpayment",
            "requirement": "Without a lease (a tenancy at will), either party may end the tenancy with written"
            " notice of one rent period or 30 days, whichever is longer, or three months if rent is paid every three"
            " months or less often. For nonpayment, 14 days' notice to quit applies, with a 10-day right to cure for"
            " tenants without a similar notice in the prior 12 months.",
        },
        "evidence": [
            {
                "doc_id": "D051",
                "quoted_span": "if the rent reserved is payable at periods of less than three months, the time of"
                " such notice shall be sufficient if it is equal to the interval between the days of payment or"
                " thirty days, whichever is longer.",
            },
            {
                "doc_id": "D051",
                "quoted_span": "In case of neglect or refusal to pay the rent due from a tenant at will, fourteen"
                " days' notice to quit, given in writing by the landlord to the tenant, shall be sufficient to"
                " determine the tenancy",
            },
        ],
    },
    {
        # § 1d: the first CPI adjustment is on January 1 of the year after enactment (approved January 20, 2026),
        # and only when the CPI change is above zero
        "rule": "NJ-FEE-01",
        "citation": "P.L.2025, c.405",
        "set": {
            "key_value": "$50 per application (CPI-adjusted yearly from 2027)",
            "requirement": "Landlords or their agents cannot charge an application or similar fee above $50 to"
            " apply to lease or sublease a residential rental. From January 1, 2027 the cap is adjusted each year"
            " for CPI (only if CPI rises), and wrongly charged amounts are refunded to the applicant.",
        },
        "evidence": [
            {
                "doc_id": "D066",
                "quoted_span": "Beginning on January 1 of the year next following enactment of P.L.2025, c.405",
            },
            {
                "doc_id": "D066",
                "quoted_span": "An adjustment in the fee limitation shall be made only if the percent change in the"
                " Consumer Price Index for the period specified is greater than zero.",
            },
            {"doc_id": "D066", "quoted_span": "Approved January 20, 2026."},
        ],
    },
    {
        # the 3% is the last figure LAHD published (to June 30, 2026), not the current one
        "rule": "LA-RENT-01",
        "citation": "L.A. Mun. Code § 151.00 et seq",
        "set": {
            "key_value": "Once per 12 months, by LAHD's yearly percentage (last published: 3% for"
            " 7/1/2025–6/30/2026)",
            "requirement": "For RSO units, rent may be raised only once every 12 months by the annual allowable"
            " percentage set by LAHD (last published: 3% for 7/1/2025–6/30/2026). Since Feb 2, 2026 no extra"
            " percentage for utilities and no extra 10% for an added dependent; 10% for an added non-dependent"
            " tenant is still allowed.",
        },
        "evidence": [
            {
                "doc_id": "D042",
                "quoted_span": "Annual rent increases for rental units subject to the City of Los Angeles Rent"
                " Stabilization Ordinance (RSO), effective July 1, 2025, through June 30, 2026 is 3%",
            }
        ],
    },
    {
        # letter_quote: the sentence a letter or notice quotes because it states the figure (or rule) the letter
        # relies on; the rule's own quote here is the 5% cap, the 1.0% is D008's
        "rule": "BER-RENT-01",
        "citation": "Berkeley Mun. Code § 13.76.110",
        "set": {
            "letter_quote": {
                "doc_id": "D008",
                "quoted_span": "The 2026 AGA of 1.0% represents 65% of the increase in the Consumer Price Index"
                " (CPI) for All Urban Consumers in the Bay Area",
            }
        },
        "evidence": [
            {
                "doc_id": "D008",
                "quoted_span": "The 2026 AGA of 1.0% represents 65% of the increase in the Consumer Price Index"
                " (CPI) for All Urban Consumers in the Bay Area",
            }
        ],
    },
    {
        # the same for Santa Ana: the rule's own quote is the formula, the 2.87% is D084's
        "rule": "SA-RENT-01",
        "citation": "Santa Ana Rent Stabilization Ordinance",
        "set": {
            "letter_quote": {
                "doc_id": "D084",
                "quoted_span": "2.87 percent is the maximum allowable rent increase for the period of September 1,"
                " 2026 through August 31, 2027.",
            }
        },
        "evidence": [
            {
                "doc_id": "D084",
                "quoted_span": "2.87 percent is the maximum allowable rent increase for the period of September 1,"
                " 2026 through August 31, 2027.",
            }
        ],
    },
    {
        # the owner's notice quoted the exemption note "(Please Note: All 1-4 Unit Properties are exempt ...)";
        # the sentence that says the ordinance governs is the administering one
        "rule": "JC-RENT-01",
        "citation": "Jersey City Code ch. 260",
        "set": {
            "letter_quote": {
                "doc_id": "D036",
                "quoted_span": "The Office of Landlord Tenant Relations administers and enforces the Rent Control"
                " Ordinance, Chapter 260 of the Jersey City Municipal Code",
            }
        },
        "evidence": [
            {
                "doc_id": "D036",
                "quoted_span": "The Office of Landlord Tenant Relations administers and enforces the Rent Control"
                " Ordinance, Chapter 260 of the Jersey City Municipal Code",
            }
        ],
    },
]
