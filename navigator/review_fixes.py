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
]
