"""Plain-language layer: short renter answers per rule, generated and checked by code.  (Not legal advice.)

    python -m navigator plain [--rules ID ...] [--jurisdiction "Santa Monica, CA"]
    python -m navigator plain --compare ID ...      # generate for rules that have reviewed copy, compare, no write

For every rule without reviewed copy (web/headlines.py, the hand-checked tables) one model call writes the
English + Spanish plain copy from ONLY the rule's own fields (key_value, requirement, coverage_conditions,
exemptions, effective_date, status) and its verbatim quoted_span:
  answer   (<= 8 words, the number first), why (<= 20 words, 5th-8th grade), headline (the row title),
  short    (the Compare cell), period_end + after_* (the figure belongs to a period), removes_protection.
The question title comes from the category, not the model.

Code then checks every field (validate()): each number, money amount, percent and date must occur in the
rule's key_value / requirement / quoted_span (or be its effective date); length limits; a jargon list; the
answer must agree with the status (pending -> "not law yet", not yet effective -> "starts <date>"); Spanish
present with the same numbers. On failure the model gets one retry with the errors; if that fails too a
category template built from key_value is used and the record is marked needs_review.

Output: OUTPUT_DIR/plain_language.json (one record per rule id, source "generated" | "reviewed", model,
prompt hash, validation result, needs_review), one audit line per model call in OUTPUT_DIR/audit.jsonl.
Responses are cached in cache/llm/ like the extraction, so reruns are free and give the same text.
Reviewed copy always wins; web/headlines.py fills only the gaps from this file at startup.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import llm as L
from .config import AUDIT_LOG, BASE_OUTPUT_DIR, EXTENSION, OUTPUT_DIR, RULES_JSON

PLAIN_VERSION = "plain-v5"
PLAIN_JSON = OUTPUT_DIR / "plain_language.json"
COMPARE_JSON = BASE_OUTPUT_DIR / "plain_compare.json"

# the question each category answers (same wording as the web app's topic rows)
QUESTIONS = {
    "rent_increase_limits": ("How much can the rent go up?", "¿Cuánto puede subir la renta?"),
    "just_cause_eviction": (
        "Does the landlord need a reason to end the tenancy?",
        "¿Necesita el propietario una causa para terminar el contrato?",
    ),
    "security_deposits": ("How large can the deposit be?", "¿Qué tan alto puede ser el depósito?"),
    "application_screening_fees": (
        "What can be charged to apply or move in?",
        "¿Qué se puede cobrar por solicitar o al mudarse?",
    ),
    "screening_restrictions": (
        "What may a landlord ask about or consider?",
        "¿Qué puede preguntar o considerar el propietario?",
    ),
    "algorithmic_rent_setting": (
        "Can software be used to set the rent?",
        "¿Se puede usar software para fijar la renta?",
    ),
}
GENERIC_QUESTION = ("What does this rule say?", "¿Qué dice esta regla?")

RULE_FIELDS = (
    "jurisdiction",
    "level",
    "category",
    "status",
    "title",
    "key_value",
    "requirement",
    "coverage_conditions",
    "exemptions",
    "effective_date",
    "quoted_span",
)

# ------------------------------------------------------------------------------------------------ prompt --
SYSTEM = """You write the plain-language layer of a rental-law information site for renters (not legal advice).
You get ONE rule record extracted from an official law text. Write short answers a 12-year-old can read, in
English and in Spanish (neutral Latin American Spanish, "usted").

Fields:
- answer_en / answer_es: the renter's question (given above the record) answered directly in 8 words or fewer
  (Spanish: 11), in the style of the examples below. When the
  rule only covers a side duty (deposit interest, a notice the landlord must hand over, a relocation payment), say
  what it gives the renter ("Yes, landlords must pay you interest."): other rules on the page answer the main
  question, so never write "this rule", "not stated" or "sets no limit". Lead with the number
  when there is one ("Max 1 month's rent.", "Yes, but only 1.6% until Feb 2027."). End with a period.
- why_en / why_es: ONE short sentence, about 12 words (never over 20; Spanish 26), 5th-8th grade words: the most
  useful extra fact for a renter.
- headline_en / headline_es: a neutral row title, 8 words or fewer, no period ("Deposit capped at 1 month's rent").
- short_en / short_es: a table cell, 6 words or fewer and 40 characters or fewer ("Max 1 month's rent", "Max 3%/yr").
- period_end: ISO date (YYYY-MM-DD) when the figure in the answer only holds until a date (e.g. this year's
  allowed raise "until Feb 28, 2027"), else null. Then after_headline_* and after_short_* give the general wording
  without that figure ("Yearly increase set by the city"); else null.
  For a pending or failed proposal the headline names the proposal, never the rule as if it were law
  ("Measure RR: on the Nov 3, 2026 ballot").
- removes_protection: true only when the rule takes a renter protection away (e.g. a state ban on local rent
  control), else false.

Hard rules (code checks every one; a failing answer is thrown away):
1. Use ONLY facts in the record. Every number, money amount, percent and date you write must appear in
   key_value, requirement or quoted_span (or be the effective_date). Never compute, round or add numbers.
   Write numbers as digits in both languages (1, 2, 30, $8,245, 1.5%), US number format also in Spanish.
2. Status: "pending" means a bill or ballot measure that is NOT law: the answer must say so ("Not law yet: ...",
   "Aún no es ley: ..."). "failed": say it is not law ("Not law: the proposal failed."). "not_yet_effective": the
   answer must name the start date ("From Jul 1, 2027: ...", "Desde el 1 jul 2027: ..."). "in_force": never say
   it is not law or not yet in effect.
3. No legal jargon: no section signs, no "CPI" (say "inflation"), no "exempt"/"exemption", no bill numbers, no
   acronyms like HUD, FMR, MAR, no "shall", "pursuant", "ordinance", "statute", "tenancy".
4. Dates as "Jan 1, 2027" / "Feb 2027" in English and "1 ene 2027" / "feb 2027" in Spanish.
5. Spanish says the same thing as English, with the same numbers and dates.

Examples (other rules):
- Security deposit, California, in force, key_value "1 month's rent (2 months for small landlords)":
  answer "Max 1 month's rent." why "Small landlords may ask for 2 months." short "Max 1 month's rent".
- Rent increases, San Francisco, in force, key_value "1.6% annual allowable increase (Mar 1, 2026 - Feb 28, 2027)":
  answer "Yes, but only 1.6% until Feb 2027." period_end "2027-02-28", after_headline "Yearly increase set by the city".
- Algorithmic rent-setting, Massachusetts, pending bill: answer "Not law yet. A bill is being discussed."
  why "Nothing changes unless it passes."
- Eviction, Los Angeles, in force, key_value "just cause required; relocation $11,000-$27,400":
  answer "Only for a good reason." why "If it's not your fault, they pay $11,000–$27,400 to move you."
"""

_S = {"type": "string"}
_SN = {"type": ["string", "null"]}
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "answer_en",
        "answer_es",
        "why_en",
        "why_es",
        "headline_en",
        "headline_es",
        "short_en",
        "short_es",
        "period_end",
        "after_headline_en",
        "after_headline_es",
        "after_short_en",
        "after_short_es",
        "removes_protection",
    ],
    "properties": {
        **{
            k: _S
            for k in (
                "answer_en",
                "answer_es",
                "why_en",
                "why_es",
                "headline_en",
                "headline_es",
                "short_en",
                "short_es",
            )
        },
        **{
            k: _SN
            for k in (
                "period_end",
                "after_headline_en",
                "after_headline_es",
                "after_short_en",
                "after_short_es",
            )
        },
        "removes_protection": {"type": "boolean"},
    },
}


def rule_input(r: dict) -> dict:
    return {k: r.get(k) for k in RULE_FIELDS}


def question(r: dict) -> tuple[str, str]:
    return QUESTIONS.get(r.get("category"), GENERIC_QUESTION)


def prompt(r: dict, previous: dict | None = None, errors: list[str] | None = None) -> str:
    p = f"Renter's question: {question(r)[0]}\n\nRule record:\n" + json.dumps(
        rule_input(r), indent=1, ensure_ascii=False
    )
    if previous is not None:
        p += (
            "\n\nYour previous answer:\n"
            + json.dumps(previous, indent=1, ensure_ascii=False)
            + "\n\nIt failed these checks:\n- "
            + "\n- ".join(errors or [])
            + "\n\nReturn a corrected JSON object."
        )
    return p


# ------------------------------------------------------------------------------------------- validation --
_NUM_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}
_MONTHS = {
    m: i + 1
    for i, ms in enumerate(
        [
            ("jan", "january", "ene", "enero"),
            ("feb", "february", "febrero"),
            ("mar", "march", "marzo"),
            ("apr", "april", "abr", "abril"),
            ("may", "mayo"),
            ("jun", "june", "junio"),
            ("jul", "july", "julio"),
            ("aug", "august", "ago", "agosto"),
            ("sep", "sept", "september", "septiembre", "set", "setiembre"),
            ("oct", "october", "octubre"),
            ("nov", "november", "noviembre"),
            ("dec", "december", "dic", "diciembre"),
        ]
    )
    for m in ms
}
_MON_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DATE_PATTERNS = [
    # 9/1/2026 (US order)
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), lambda m: (int(m[3]), int(m[1]), int(m[2]))),
    # 2027-07-01
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    # Jul 1, 2027 / July 1 2027
    (
        re.compile(rf"\b({_MON_RE})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.I),
        lambda m: (int(m[3]), _MONTHS[m[1].lower()], int(m[2])),
    ),
    # 1 jul 2027 / 1 de julio de 2027
    (
        re.compile(rf"\b(\d{{1,2}})\s+(?:de\s+)?({_MON_RE})\.?\s+(?:de\s+)?(\d{{4}})\b", re.I),
        lambda m: (int(m[3]), _MONTHS[m[2].lower()], int(m[1])),
    ),
    # Feb 2027 / febrero de 2027
    (
        re.compile(rf"\b({_MON_RE})\.?\s+(?:de\s+)?(\d{{4}})\b", re.I),
        lambda m: (int(m[2]), _MONTHS[m[1].lower()], None),
    ),
]
_NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?")


def _dates(text: str) -> tuple[list[tuple], str]:
    """Dates in text as (year, month, day|None), and the text with them removed."""
    found = []
    for rx, conv in _DATE_PATTERNS:

        def sub(m, conv=conv):
            found.append(conv(m))
            return " "

        text = rx.sub(sub, text)
    return found, text


def _words_to_digits(text: str) -> str:
    t = re.sub(r"\bone and (?:one-|a )half\b", "1.5", text, flags=re.I)
    t = re.sub(r"\b(?:one-)?half\b", "0.5", t, flags=re.I)
    t = re.sub(r"\btwice\b", "2", t, flags=re.I)
    return re.sub(
        r"\b(" + "|".join(_NUM_WORDS) + r")\b",
        lambda m: str(_NUM_WORDS[m[1].lower()]),
        t,
        flags=re.I,
    )


def _num(tok: str) -> float:
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", tok):
        tok = tok.replace(",", "")
    return float(tok.replace(",", "."))


def numbers(text: str) -> tuple[set[float], list[tuple]]:
    """(numbers, dates) written in a text: $11,000 -> 11000, 2.87% -> 2.87, 'Feb 2027' -> (2027, 2, None)."""
    ds, rest = _dates(text or "")
    return {_num(t) for t in _NUM_RE.findall(rest)}, ds


def source_facts(r: dict) -> tuple[set[float], set[tuple]]:
    """Numbers and dates the generated text may use: key_value, requirement, quoted_span, effective_date."""
    src = " \n ".join(str(r.get(k) or "") for k in ("key_value", "requirement", "quoted_span"))
    src = _words_to_digits(src)
    ds, _ = _dates(src)
    nums = {_num(t) for t in _NUM_RE.findall(src)}  # digits inside dates count too (years, days)
    eff = str(r.get("effective_date") or "")
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", eff)
    if m:
        ds.append((int(m[1]), int(m[2]) if m[2] else None, int(m[3]) if m[3] else None))
        nums |= {float(x) for x in m.groups() if x}
    full = {d for d in ds}
    full |= {(y, mo, None) for y, mo, _ in ds}
    return nums, full


# phrases that tell the reader a rule is not law (pending, failed) or not in effect yet
NOT_LAW = {
    "en": re.compile(
        r"\b(not (?:a )?law|no law yet|isn't law|not yet law|failed|was rejected|withdrawn)\b", re.I
    ),
    "es": re.compile(
        r"\b(?:no es ley|aún no hay ley|no hay ley)\b|fracas[óo]|fue rechazad|fue retirad", re.I
    ),
}
STARTS = {
    "en": re.compile(r"\b(from|starts?|starting|begins?|beginning|takes effect|effective)\b", re.I),
    "es": re.compile(r"\b(desde|empieza|a partir|comienza|entra en vigor|rige)\b", re.I),
}
BANNED = re.compile(
    r"§|\bCPI\b|\bIPC\b|\bFMR\b|\bHUD\b|\bMAR\b|\bRSO\b|\b(?:AB|SB|HB) ?\d|\bexempt|\bexenci|\bexent[oa]s?\b"
    r"|\bpursuant\b|\bnotwithstanding\b|\bherein|\bthereof\b|\bshall\b|\bordinance\b|\bstatute\b|\btenancy\b"
    r"|\bCiv\. Code\b|\bG\.L\.|\bN\.J\.S\.A\.|\bU\.S\.C\."
    # talk about the extraction instead of the law
    r"|\bthe source\b|\brule record\b|\bthe record (?:says|gives)\b|\bno more facts\b|\bla fuente no\b"
    r"|\bnot stated\b|\bsets no (?:limit|cap)\b|\bno se indica\b",
    re.I,
)
# the answer speaks about the renter's situation, not about "this rule" (other rules may answer the question)
ANSWER_BANNED = re.compile(r"\bthis rule\b|\besta regla\b", re.I)
# (max words, max chars) per field; Spanish runs about a third longer
LIMITS = {
    "answer_en": (8, 70),
    "answer_es": (11, 90),
    "why_en": (20, 150),
    "why_es": (26, 190),
    "headline_en": (8, 60),
    "headline_es": (11, 80),
    "short_en": (6, 40),
    "short_es": (8, 46),
    "after_headline_en": (8, 60),
    "after_headline_es": (11, 80),
    "after_short_en": (6, 40),
    "after_short_es": (8, 46),
}
TEXT_FIELDS = tuple(LIMITS)
MAX_GRADE = 9.0  # Flesch-Kincaid grade of the English why line (names count as one syllable)

# The why line stays on the rule's topic. A fact phrased like another topic misleads: "Yearly increases can't go
# over 10%" under a deposit reads like a rent cap. TOPIC_PHRASES are the phrasings that belong to one category;
# a why line may not use another category's phrasing (OFF_TOPIC_OK lists the overlaps that are fine).
TOPIC_PHRASES = {
    "rent_increase_limits": re.compile(
        r"\brent (?:increase|raise|hike)s?\b|\b(?:raise|increase)s? (?:the |your )?rent\b"
        r"|\brent (?:can|may|could) (?:go up|rise)\b|\b(?:yearly|annual) (?:rent )?(?:increase|raise)s?\b"
        r"|\b(?:increase|raise)s? (?:can't|cannot|may not|can never) (?:go|pass|exceed)\b"
        r"|\brent (?:cap|limit)s?\b|\brent control(?! (?:board|office))\b"
        r"|\baumentos? (?:anual(?:es)? )?de (?:la )?(?:renta|alquiler)|\bsubir (?:la )?(?:renta|el alquiler)\b"
        r"|\btope de (?:la )?(?:renta|alquiler)|(?<!junta de )(?<!oficina de )\bcontrol de (?:rentas?|alquiler(?:es)?)\b",
        re.I,
    ),
    "just_cause_eviction": re.compile(
        r"\bevict|\bnotice to quit\b|\bjust cause\b|\bdesaloj|\bcausa justa\b", re.I
    ),
    "security_deposits": re.compile(r"\b(?:security )?deposits?\b|\bdepósitos?\b", re.I),
    "application_screening_fees": re.compile(
        r"\b(?:application|screening|broker) fees?\b|\bcuotas? de solicitud|\bcargos? por solicitud",
        re.I,
    ),
    "screening_restrictions": re.compile(
        r"\bcriminal (?:record|history)|\bconvictions?\b|\bcredit (?:score|check|report|history)s?\b|\bvouchers?\b"
        r"|\bantecedentes\b|\bcondenas?\b|\bhistorial de crédito\b|\bvales?\b",
        re.I,
    ),
    "algorithmic_rent_setting": re.compile(r"\bsoftware\b|\balgorithm|\balgoritm", re.I),
}
OFF_TOPIC_OK = {
    "application_screening_fees": {"security_deposits"},  # move-in costs: first, last, deposit
    "algorithmic_rent_setting": {"rent_increase_limits"},  # price-setting software raises rents
}
# ... and an English why line names its own topic (a deposit why talks about the deposit). Not required for
# pending / failed proposals, whose why line says what happens to the proposal.
TOPIC_WORDS = {
    "rent_increase_limits": re.compile(
        r"\brent|\braise|\bincrease|\blimit|\bcap\b|\binflation|%", re.I
    ),
    "just_cause_eviction": re.compile(
        r"\bevict|\bnotice|\breason|\bcause\b|\brelocation|\bmov(?:e|ing) (?:you|out)|\bstay\b|\byour home\b"
        r"|\bcourt|\bend(?:s|ing)? (?:your|the) (?:lease|rental|stay)|\bnot your fault\b|\bno-fault\b|\bcomplain"
        r"|\bpayback\b|\bretaliat|\bpunish|\byour rights\b",
        re.I,
    ),
    "security_deposits": re.compile(
        r"\bdeposit|\binterest\b|\bmove[sd]? out\b|\bmove-out\b|\brefund|\breturn|\bcome back\b|\bbank account"
        r"|\bmonths?'? rent\b|\bask for \d",
        re.I,
    ),
    "application_screening_fees": re.compile(
        r"\bfees?\b|\bcharge|\bapplication|\bappl(?:y|ies|icant)|\bbroker|\bmove-in|\bfirst month|\bdeposit|\bcap\b",
        re.I,
    ),
    "screening_restrictions": re.compile(
        r"\brecord|\bconviction|\barrest|\bcredit|\bvoucher|\bincome|\bbackground|\bscreen|\bapplicant"
        r"|\bturn(?:ing)? (?:you )?down|\breject",
        re.I,
    ),
    "algorithmic_rent_setting": re.compile(
        r"\bsoftware|\balgorithm|\bpric(?:e|ing)|\bdata\b|\brent-setting|\bset (?:the )?rents?\b|\bcompetitor|\brival",
        re.I,
    ),
}


# how a renter would name each topic (for the retry message)
TOPIC_NAME = {
    "rent_increase_limits": "rent increases",
    "just_cause_eviction": "evictions",
    "security_deposits": "the deposit",
    "application_screening_fees": "fees",
    "screening_restrictions": "how landlords screen applicants",
    "algorithmic_rent_setting": "rent-pricing software",
}


def topic_errors(g: dict, r: dict) -> list[str]:
    """The why line talks about the rule's own topic and not in another topic's words."""
    cat, errs = r.get("category"), []
    if cat not in TOPIC_PHRASES:
        return errs
    for lang in ("en", "es"):
        w = g.get(f"why_{lang}") or ""
        for other, rx in TOPIC_PHRASES.items():
            if other == cat or other in OFF_TOPIC_OK.get(cat, ()):
                continue
            m = rx.search(w)
            if m:
                errs.append(
                    f"why_{lang} uses {TOPIC_NAME[other]} wording ({m[0]!r}) on a rule about {TOPIC_NAME[cat]},"
                    f" so it reads like a different topic; keep the line about {TOPIC_NAME[cat]}: {w!r}"
                )
    w = g.get("why_en") or ""
    if (
        w
        and w != WHY_FALLBACK[0]
        and r.get("status") not in ("pending", "failed")
        and not TOPIC_WORDS[cat].search(w)
    ):
        errs.append(
            f"why_en does not say what it is about, so it can be read as another rule; work in a plain word for"
            f" {TOPIC_NAME[cat]} (keep it short and simple): {w!r}"
        )
    return errs


def _syllables(w: str) -> int:
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def grade(text: str) -> float:
    """Flesch-Kincaid grade level; capitalised words (names, places) count as one syllable."""
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", text or "")
    if not words:
        return 0.0
    sentences = max(1, len(re.findall(r"[.!?](?:\s|$)", text)))
    syl = sum(1 if w[0].isupper() else _syllables(w) for w in words)
    return round(0.39 * len(words) / sentences + 11.8 * syl / len(words) - 15.59, 1)


def _word_count(s: str) -> int:
    """Words as a reader sees them; a date ("Jul 1, 2027") counts as one."""
    ds, rest = _dates(s or "")
    return len(re.findall(r"\S+", rest)) + len(ds)


def validate(g: dict, r: dict) -> list[str]:
    """Every check that generated copy must pass; [] = valid. Messages go back to the model on retry."""
    errs: list[str] = []
    status = r.get("status")
    for k in ("answer_en", "answer_es", "why_en", "why_es", "headline_en", "headline_es"):
        if not str(g.get(k) or "").strip():
            errs.append(f"{k} is empty")
    if status in ("in_force", "not_yet_effective"):
        for k in ("short_en", "short_es"):
            if not str(g.get(k) or "").strip():
                errs.append(f"{k} is empty")
    nums, dates = source_facts(r)
    for k in TEXT_FIELDS:
        s = g.get(k)
        if not s:
            continue
        mw, mc = LIMITS[k]
        if _word_count(s) > mw:
            errs.append(f"{k} has {_word_count(s)} words (max {mw}): {s!r}")
        if len(s) > mc:
            errs.append(f"{k} has {len(s)} characters (max {mc}): {s!r}")
        b = BANNED.search(s) or (ANSWER_BANNED.search(s) if k.startswith("answer_") else None)
        if b:
            errs.append(f"{k} uses jargon {b[0]!r}: {s!r}")
        ns, ds = numbers(s)
        for n in sorted(ns - nums):
            errs.append(
                f"{k}: the number {n:g} is not in key_value, requirement or quoted_span: {s!r}"
            )
        for d in ds:
            if d not in dates:
                errs.append(
                    f"{k}: the date {_fmt(d)} is not in the rule's text or effective date: {s!r}"
                )
    # Spanish says the same numbers as English, field by field
    for k in TEXT_FIELDS:
        if not k.endswith("_en"):
            continue
        ke = k
        ks = k[:-3] + "_es"
        if bool(g.get(ke)) != bool(g.get(ks)):
            errs.append(f"{ks if g.get(ke) else ke} is missing")
            continue
        if not g.get(ke):
            continue
        (ne, de), (ns_, ds_) = numbers(g[ke]), numbers(g[ks])
        if ne != ns_ or set(de) != set(ds_):
            errs.append(
                f"{ks} must carry the same numbers and dates as {ke}: {g[ke]!r} vs {g[ks]!r}"
            )
    # the answer agrees with the status
    for lang in ("en", "es"):
        a = g.get(f"answer_{lang}") or ""
        if status in ("pending", "failed"):
            if not NOT_LAW[lang].search(a):
                errs.append(
                    f"answer_{lang} must say this is not law ({status}): {a!r}"
                    + (
                        " e.g. 'Not law yet: ...'"
                        if lang == "en"
                        else " p. ej. 'Aún no es ley: ...'"
                    )
                )
        elif NOT_LAW[lang].search(a):
            errs.append(f"answer_{lang} says 'not law' but the rule is {status}: {a!r}")
        if status == "not_yet_effective":
            eff = str(r.get("effective_date") or "")[:10]
            _, ds = numbers(a)
            want = _date_tuple(eff)
            if not want or not STARTS[lang].search(a) or not any(_same_day(d, want) for d in ds):
                errs.append(
                    f"answer_{lang} must name the start date {eff} ('From <date>: ...'), the rule is not yet in effect: {a!r}"
                )
    pe = g.get("period_end")
    if pe:
        t = _date_tuple(pe)
        if not t or t not in dates and (t[0], t[1], None) not in dates:
            errs.append(f"period_end {pe!r} is not a date in the rule's text")
        if not g.get("after_headline_en"):
            errs.append(
                "period_end is set, so after_headline_en/es (the wording after it) are needed"
            )
    if not isinstance(g.get("removes_protection"), bool):
        errs.append("removes_protection must be true or false")
    errs += topic_errors(g, r)
    if g.get("why_en") and grade(g["why_en"]) > MAX_GRADE:
        errs.append(
            f"why_en reads at grade {grade(g['why_en'])} (max {MAX_GRADE:g}); use shorter, everyday words: {g['why_en']!r}"
        )
    return errs


def _date_tuple(s: str | None):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(s or "")[:10])
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def _same_day(d: tuple, want: tuple) -> bool:
    return d[:2] == want[:2] and d[2] in (None, want[2])


def _fmt(d: tuple) -> str:
    return "-".join(f"{x:02d}" for x in d if x is not None)


# --------------------------------------------------------------------------------------------- fallback --
# category templates for when the model's copy fails twice: true without reading the law closely, plus the
# figure only when key_value states it as a maximum
TEMPLATES = {
    "rent_increase_limits": (
        "Rent increases are limited here",
        "Los aumentos de renta tienen límite aquí",
        "Raises limited",
        "Aumentos con límite",
    ),
    "just_cause_eviction": (
        "Rules limit evictions here",
        "Hay reglas que limitan los desalojos",
        "Eviction rules",
        "Reglas de desalojo",
    ),
    "security_deposits": (
        "Deposits are limited here",
        "Los depósitos tienen límite aquí",
        "Deposit limited",
        "Depósito con límite",
    ),
    "application_screening_fees": (
        "Application fees are limited here",
        "Los cargos por solicitud tienen límite",
        "Fees limited",
        "Cargos con límite",
    ),
    "screening_restrictions": (
        "Limits on what landlords may check",
        "Límites a lo que el dueño puede revisar",
        "Screening limited",
        "Revisión con límites",
    ),
    "algorithmic_rent_setting": (
        "Rules on rent-setting software apply",
        "Hay reglas sobre software de rentas",
        "Software rules",
        "Reglas de software",
    ),
}
GENERIC_TEMPLATE = (
    "A rule applies here",
    "Aquí aplica una regla",
    "Rule applies",
    "Aplica una regla",
)
WHY_FALLBACK = (
    "Open the law below for the exact rule and its source.",
    "Abra la ley abajo para ver la regla exacta y su fuente.",
)
_MAX_RE = re.compile(
    r"\b(?:max(?:imum)?|up to|cap(?:ped)?(?: at)?|not (?:to )?exceed|no more than|at most)\s+"
    r"(\$\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?\s+months?'?s?)",
    re.I,
)


def _template_figure(r: dict) -> tuple[str, str] | None:
    m = _MAX_RE.search(_words_to_digits(str(r.get("key_value") or "")))
    if not m:
        return None
    f = re.sub(r"\s+", " ", m[1]).strip()
    if re.search(r"months?", f, re.I):
        n = re.match(r"[\d.]+", f)[0]
        one = n in ("1", "1.0")
        return (
            f"{n} month's rent" if one else f"{n} months' rent",
            f"{n} mes de renta" if one else f"{n} meses de renta",
        )
    f = f.replace(" %", "%")
    return f, f


def fallback(r: dict) -> dict:
    """Safe copy from the category template (+ the maximum from key_value if it states one)."""
    he, hs, se, ss = TEMPLATES.get(r.get("category"), GENERIC_TEMPLATE)
    fig = _template_figure(r)
    if fig:
        he, hs = f"{he}: max {fig[0]}", f"{hs}: máx. {fig[1]}"
        se, ss = f"Max {fig[0]}", f"Máx. {fig[1]}"
    ae, as_ = he + ".", hs + "."
    status = r.get("status")
    if status == "pending":
        ae, as_ = "Not law yet: a proposal.", "Aún no es ley: es una propuesta."
        he, hs = "Proposal, not law yet", "Propuesta, aún no es ley"
        se = ss = None
    elif status == "failed":
        ae, as_ = "Not law: the proposal failed.", "No es ley: la propuesta fracasó."
        he, hs = "Failed proposal, not law", "Propuesta fracasada, no es ley"
        se = ss = None
    elif status == "not_yet_effective":
        t = _date_tuple(str(r.get("effective_date") or "")[:10])
        if t:
            from web.headlines import fmt_date  # noqa: PLC0415 - the app's own date wording

            d = f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}"
            ae = f"From {fmt_date(d, 'en')}: {he[0].lower()}{he[1:]}."
            as_ = f"Desde el {fmt_date(d, 'es')}: {hs[0].lower()}{hs[1:]}."
    out = {
        "answer_en": ae,
        "answer_es": as_,
        "why_en": WHY_FALLBACK[0],
        "why_es": WHY_FALLBACK[1],
        "headline_en": he,
        "headline_es": hs,
        "short_en": se,
        "short_es": ss,
        "period_end": None,
        "after_headline_en": None,
        "after_headline_es": None,
        "after_short_en": None,
        "after_short_es": None,
        "removes_protection": False,
    }
    # a figure the checks reject (or a too-long line) falls back to the bare template
    if fig and validate(out, r):
        return fallback({**r, "key_value": ""})
    return out


# ------------------------------------------------------------------------------------- tables for the app --
def priority(r: dict) -> int | None:
    """Compare cell order: the jurisdiction's first rule of a category leads, the rest are appended."""
    if r.get("status") not in ("in_force", "not_yet_effective"):
        return None
    return 1 if re.search(r"-0?1$", r["team_rule_id"]) else 2


def tables(g: dict, r: dict) -> tuple[dict, dict]:
    """The generated fields in the shape of web/headlines.py's HEADLINES and PLAIN entries."""
    h = {"en": g["headline_en"], "es": g["headline_es"]}
    if g.get("short_en"):
        h |= {"short_en": g["short_en"], "short_es": g["short_es"]}
        if priority(r):
            h["priority"] = priority(r)
    if g.get("period_end"):
        h |= {
            "until": g["period_end"],
            "after_en": g["after_headline_en"],
            "after_es": g["after_headline_es"],
        }
        if g.get("short_en") and g.get("after_short_en"):
            h |= {
                "short_until": g["period_end"],
                "short_after_en": g["after_short_en"],
                "short_after_es": g["after_short_es"],
            }
    if g.get("removes_protection"):
        h["removes_protection"] = True
    p = {"en": [g["answer_en"], g["why_en"]], "es": [g["answer_es"], g["why_es"]]}
    if g.get("period_end"):
        p["until"] = g["period_end"]
    return h, p


# ----------------------------------------------------------------------------------------------- runner --
_audit_lock = threading.Lock()


def _audit(entry: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "prompt_version": PLAIN_VERSION,
        **entry,
    }
    with _audit_lock, open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def generate(r: dict, llm=None) -> dict:
    """One rule -> a plain_language record (model call, checks, one retry, template fallback)."""
    llm = llm or L.call_llm
    rid = r["team_rule_id"]
    attempts, g, prev, errs = [], None, None, None
    for attempt in (1, 2):
        try:
            g, meta = llm(
                SYSTEM, prompt(r, prev, errs), SCHEMA, tag=f"plain:{rid}:{attempt}", timeout=300
            )
        except L.LLMError as e:
            attempts.append({"attempt": attempt, "error": str(e)[:500]})
            _audit({"stage": "plain", "rule_id": rid, "attempt": attempt, "error": str(e)[:500]})
            g = None
            break
        errs = validate(g, r)
        attempts.append(
            {
                "attempt": attempt,
                "model": meta["model"],
                "prompt_hash": meta["prompt_hash"],
                "cached": meta["cached"],
                "errors": errs,
            }
        )
        _audit(
            {
                "stage": "plain",
                "rule_id": rid,
                "attempt": attempt,
                "model": meta["model"],
                "prompt_hash": meta["prompt_hash"],
                "cached": meta["cached"],
                "raw_output": meta["raw"],
                "validation": errs,
            }
        )
        if not errs:
            break
        prev = g
    ok = bool(g) and not errs
    fields = g if ok else fallback(r)
    reasons = [] if ok else ["checks_failed: template used"]
    if r.get("verification") == "unverified_link_only" or (r.get("confidence") or 1) < 0.5:
        reasons.append(f"low_confidence: {r.get('confidence')} ({r.get('verification')})")
    h, p = tables(fields, r)
    q = question(r)
    last = next((a for a in reversed(attempts) if "prompt_hash" in a), {})
    return {
        "rule_id": rid,
        "source": "generated",
        "method": "model" if ok else "template",
        "needs_review": bool(reasons),
        "review_reasons": reasons,
        "question_en": q[0],
        "question_es": q[1],
        "fields": fields,
        "headline": h,
        "plain": p,
        "model": last.get("model"),
        "prompt_hash": last.get("prompt_hash"),
        "prompt_version": PLAIN_VERSION,
        "validation": {
            "passed": ok,
            "attempts": attempts,
            "grade_why_en": grade(fields["why_en"]),
        },
        "input": rule_input(r),
    }


def reviewed_ids() -> tuple[set[str], set[str]]:
    """Rule ids with reviewed (hand-checked) copy: (HEADLINES ids, PLAIN ids) of web/headlines.py."""
    try:
        from web import headlines as H  # noqa: PLC0415
    except ImportError:
        return set(), set()
    return set(H.REVIEWED_HEADLINES), set(H.REVIEWED_PLAIN)


def _load_rules() -> list[dict]:
    return json.loads(RULES_JSON.read_text(encoding="utf-8"))["rules"]


def run(
    rule_ids: list[str] | None = None,
    jurisdiction: str | None = None,
    *,
    rules: list[dict] | None = None,
    llm=None,
    out: Path | None = None,
    log=print,
) -> dict:
    """Generate plain copy for every selected rule without reviewed copy; rewrite plain_language.json."""
    out = out or PLAIN_JSON
    rules = rules if rules is not None else _load_rules()
    # an extension run covers its own jurisdictions; the main rules' copy lives in output/plain_language.json
    ext = {j["name"] for j in EXTENSION.get("jurisdictions", [])}
    if ext:
        rules = [r for r in rules if r["jurisdiction"] in ext]
    sel = [
        r
        for r in rules
        if (not rule_ids or r["team_rule_id"] in rule_ids)
        and (not jurisdiction or r["jurisdiction"] == jurisdiction)
    ]
    rh, rp = reviewed_ids()
    old = json.loads(out.read_text(encoding="utf-8")).get("records", {}) if out.exists() else {}
    partial = bool(rule_ids or jurisdiction)
    records = {k: v for k, v in old.items() if partial} if partial else {}
    todo = []
    for r in sel:
        rid = r["team_rule_id"]
        if rid in rh and rid in rp:
            records[rid] = {"rule_id": rid, "source": "reviewed", "reviewed_in": "web/headlines.py"}
        else:
            todo.append(r)
    with ThreadPoolExecutor(max_workers=max(1, L.MAX_PARALLEL)) as ex:
        for rec in ex.map(lambda r: generate(r, llm), todo):
            rid = rec["rule_id"]
            # which tables this record fills; a template answer never replaces a reviewed headline as the answer
            rec["fills"] = [
                k
                for k, ids in (("headline", rh), ("plain", rp))
                if rid not in ids and not (k == "plain" and rec["needs_review"] and rid in rh)
            ]
            records[rid] = rec
            log(
                f"[plain] {rid:12} {rec['method']:8} {'REVIEW ' if rec['needs_review'] else ''}"
                f"{rec['fields']['answer_en']} | {rec['fields']['why_en']}"
            )
    doc = {
        "about": "Plain-language answers per rule. source=reviewed: hand-checked copy in web/headlines.py wins; "
        "source=generated: written by navigator/plain.py from the rule's own fields and checked by code "
        "(numbers, dates, length, jargon, status, Spanish). Not legal advice.",
        "prompt_version": PLAIN_VERSION,
        "counts": {
            "rules": len(records),
            "reviewed": sum(1 for v in records.values() if v["source"] == "reviewed"),
            "generated": sum(1 for v in records.values() if v["source"] == "generated"),
            "needs_review": sum(1 for v in records.values() if v.get("needs_review")),
        },
        "records": dict(sorted(records.items())),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"[plain] {json.dumps(doc['counts'])} -> {out}")
    return doc


# ----------------------------------------------------------------------------------- compare to reviewed --
def compare(rule_ids: list[str], *, llm=None, log=print) -> list[dict]:
    """Generate copy for rules that already have reviewed copy (ignoring it) and put both side by side."""
    from web import headlines as H  # noqa: PLC0415

    by = {r["team_rule_id"]: r for r in _load_rules()}
    rows = []
    todo = [by[i] for i in rule_ids if i in by]
    with ThreadPoolExecutor(max_workers=max(1, L.MAX_PARALLEL)) as ex:
        for r, rec in zip(todo, ex.map(lambda r: generate(r, llm), todo), strict=True):
            rid = r["team_rule_id"]
            ra, rw = (H.PLAIN.get(rid) or {}).get("en") or (None, None)
            rows.append(
                {
                    "rule_id": rid,
                    "status": r["status"],
                    "key_value": r.get("key_value"),
                    "reviewed_answer": ra,
                    "generated_answer": rec["fields"]["answer_en"],
                    "reviewed_why": rw,
                    "generated_why": rec["fields"]["why_en"],
                    "reviewed_headline": (H.HEADLINES.get(rid) or {}).get("en"),
                    "generated_headline": rec["fields"]["headline_en"],
                    "generated_answer_es": rec["fields"]["answer_es"],
                    "method": rec["method"],
                    "attempts": len(rec["validation"]["attempts"]),
                    "reviewed_passes_checks": validate(
                        {
                            **rec["fields"],
                            "answer_en": ra or "",
                            "why_en": rw or "",
                            "answer_es": ((H.PLAIN.get(rid) or {}).get("es") or ("", ""))[0],
                            "why_es": ((H.PLAIN.get(rid) or {}).get("es") or ("", ""))[1],
                        },
                        r,
                    ),
                }
            )
            log(f"[compare] {rid}: {ra!r} vs {rec['fields']['answer_en']!r}")
    COMPARE_JSON.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return rows
