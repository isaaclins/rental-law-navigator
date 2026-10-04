"""Ask the law (#101): a plain-language question in, a short answer out, every sentence quoted from our own data.

POST /api/ask   {"q": "...", "lang": "en"|"es" (UI language, a fallback), "as_of": "YYYY-MM-DD"}
    -> JSON answer (below). With `Accept: text/event-stream` the same work streams as server-sent events:
       `step` events (rules found -> quotes checked -> [address checked] -> writing) and one final `answer` event.
GET  /api/ask/suggest?lang=en  -> the suggested questions (pre-warmed, so the first click is instant).

How an answer is made (nothing outside our corpus, no external service except the LLM):
1. Place: one of our 500 addresses (fuzzy street match or the address id), else the cities / states named. A place
   we do not cover (another state, a foreign country) is refused right away with the closest official source.
2. Address named: the deterministic engine (web.app.build_address -> navigator.evaluate) decides what applies at that
   building. The LLM only explains those verdicts; it never decides applicability.
3. Retrieval: BM25 over the extracted rules (title, requirement, key value, verbatim quote, exemptions, in EN and ES),
   the "no rule" findings and passages of the source documents (a passage hit lifts the rules quoted from that
   document), filtered by jurisdiction and topic.
4. Every retrieved quote is checked against its source text (the same verbatim check as the answer cards).
5. The LLM (navigator.llm, claude CLI headless, Haiku) writes strict JSON {status, answer, body, citations, ...}.
   Server-side validation: cited ids must come from the retrieved set, every body sentence must carry a valid marker,
   every number in the answer must appear in the cited sources (or the question); anything else is dropped. Nothing
   relevant left -> an honest "we don't cover that" with the closest official source.

Not legal advice. What is kept: every model answer is appended to output/ask_audit.jsonl on the server (not served)
with the question redacted (e-mail, phone, street address and unit removed), the rules retrieved, the engine verdicts,
the answer and what the checks removed. The public /ask/audit view shows none of the free text: only topic, place,
date, rule ids, verdicts, counts and reasons. Answers also live in a small in-memory cache keyed by (normalised
question, as-of, language, place, conversation); pre-warmed suggested questions are cached in cache/ask/.
"""

from __future__ import annotations

import calendar
import hashlib
import ipaddress
import json
import logging
import math
import os
import re
import sys
import threading
import time
import unicodedata
from collections import Counter, OrderedDict, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from web.any_address import RateLimit
from web.ask_dates import MAX_DATE, MIN_DATE, find_date, strip_date
from web.ask_dates import fmt as fmt_date
from web.ask_ext import ask_store, places, zip_city

router = APIRouter()
# per-visitor limits are off by default (Isaac 2026-10-04); the global slots + hourly/daily budget still protect the box
ASK_LIMIT = RateLimit(
    int(os.environ.get("NAVIGATOR_ASK_PER_IP", "1000000")), 60.0
)  # all questions per connection and minute
LLM_LIMIT = RateLimit(
    int(os.environ.get("NAVIGATOR_ASK_FRESH_PER_IP", "1000000")), 60.0
)  # fresh model answers
MODEL = os.environ.get("NAVIGATOR_ASK_MODEL", "haiku")
LLM_TIMEOUT = min(
    12, int(os.environ.get("NAVIGATOR_ASK_TIMEOUT", "12"))
)  # hard cap, the process tree is killed
REWRITE_TIMEOUT = 8
MAX_PARALLEL = int(
    os.environ.get("NAVIGATOR_ASK_MAX_PARALLEL", "3")
)  # claude CLI processes at once
SLOT_WAIT = 5.0  # seconds a question waits for a free slot before the deterministic fallback
# each answer also checks its follow-up chips (up to 4 more calls), so the caps leave room for that
BUDGET_HOUR = int(os.environ.get("NAVIGATOR_ASK_BUDGET_HOUR", "1200"))
BUDGET_DAY = int(os.environ.get("NAVIGATOR_ASK_BUDGET_DAY", "8000"))
BUDGET_FILE = Path(
    os.environ.get(
        "NAVIGATOR_ASK_BUDGET_FILE", Path(__file__).resolve().parent.parent / ".ask-budget.json"
    )
)
log = logging.getLogger("navigator.ask")
ASK_CACHE = (
    Path(__file__).resolve().parent.parent / "cache" / "ask"
)  # pre-warmed answers, not in git
TOP_K = 7
DISCLAIMER = {
    "en": "Not legal advice. Information about public law from a fixed set of quoted sources.",
    "es": "No es asesoría legal. Información sobre leyes públicas de un conjunto fijo de fuentes citadas.",
}

# ------------------------------------------------------------------ suggested questions (pre-warmed)
DEMO_QS = {
    "Can my SF landlord keep my deposit?",
    "How long do they have?",
}  # videos/tools/demo_scenes*.py
SUGGEST = {
    "en": [
        "How much deposit can my landlord ask for at 6238 De Longpre Ave?",
        "Can they raise my rent 8% in Hoboken?",
        "Can I be evicted without a reason in Berkeley?",
        "¿Cuánto me pueden cobrar por la solicitud?",
    ],
    "es": [
        "¿Cuánto depósito me pueden pedir en 6238 De Longpre Ave?",
        "¿Me pueden subir la renta un 8% en Hoboken?",
        "¿Me pueden desalojar sin motivo en Berkeley?",
        "¿Cuánto me pueden cobrar por la solicitud?",
    ],
}

# ------------------------------------------------------------------ places
CITY_ALIASES = {
    "Los Angeles, CA": [
        "los angeles",
        "city of los angeles",
        "hollywood",
        "north hollywood",
        "van nuys",
        "echo park",
    ],
    "San Francisco, CA": ["san francisco", "san fran", "sf", "frisco"],
    "San Diego, CA": ["san diego"],
    "Berkeley, CA": ["berkeley"],
    "Santa Ana, CA": ["santa ana"],
    "Jersey City, NJ": ["jersey city"],
    "Hoboken, NJ": ["hoboken"],
    "Newark, NJ": ["newark"],
    "Boston, MA": [
        "boston",
        "dorchester",
        "roxbury",
        "mattapan",
        "brighton",
        "allston",
        "jamaica plain",
        "hyde park",
        "east boston",
        "south boston",
        "charlestown",
        "roslindale",
        "west roxbury",
    ],
    "Cambridge, MA": ["cambridge"],
}
CASE_ALIASES = {
    "LA": "Los Angeles, CA",
    "L.A.": "Los Angeles, CA",
    "SF": "San Francisco, CA",
    "JC": "Jersey City, NJ",
}
STATE_ALIASES = {
    "CA": ["california", "calif", "cali"],
    "NJ": ["new jersey", "nueva jersey"],
    "MA": ["massachusetts", "mass"],
}
STATE_CODES = {"CA", "NJ", "MA"}
STATE_NAME = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}
# cities in our three states that we do not cover locally (state law still applies there)
OTHER_LOCAL = {
    "CA": [
        "west hollywood",
        "santa monica",
        "oakland",
        "sacramento",
        "san jose",
        "pasadena",
        "long beach",
        "fresno",
        "irvine",
        "anaheim",
        "palo alto",
        "mountain view",
        "richmond",
        "alameda",
        "glendale",
        "burbank",
        "inglewood",
        "culver city",
        "beverly hills",
        "riverside",
        "bakersfield",
        "stockton",
        "chula vista",
        "oceanside",
    ],
    "NJ": [
        "trenton",
        "paterson",
        "princeton",
        "camden",
        "elizabeth nj",
        "edison",
        "montclair",
        "bayonne",
        "union city",
        "west new york",
        "weehawken",
        "atlantic city",
        "new brunswick",
        "passaic",
    ],
    "MA": [
        "worcester",
        "springfield",
        "somerville",
        "lowell",
        "quincy",
        "brookline",
        "newton",
        "medford",
        "malden",
        "salem",
        "lynn",
        "framingham",
        "amherst",
        "chelsea",
        "everett ma",
        "revere",
    ],
}
OUT_US = [
    "new york",
    "nyc",
    "nueva york",
    "manhattan",
    "brooklyn",
    "chicago",
    "seattle",
    "portland",
    "oregon",
    "washington state",
    "washington dc",
    "district of columbia",
    "texas",
    "houston",
    "austin",
    "dallas",
    "florida",
    "miami",
    "illinois",
    "colorado",
    "denver",
    "arizona",
    "phoenix",
    "nevada",
    "las vegas",
    "georgia",
    "atlanta",
    "pennsylvania",
    "philadelphia",
    "ohio",
    "michigan",
    "detroit",
    "minnesota",
    "minneapolis",
    "maryland",
    "baltimore",
    "virginia",
    "north carolina",
    "south carolina",
    "tennessee",
    "nashville",
    "utah",
    "connecticut",
    "rhode island",
    "vermont",
    "new hampshire",
    "maine",
    "delaware",
    "hawaii",
    "honolulu",
    "alaska",
    "new mexico",
    "nuevo mexico",
    "louisiana",
    "new orleans",
    "missouri",
    "kansas",
    "iowa",
    "wisconsin",
    "indiana",
    "kentucky",
    "alabama",
    "mississippi",
    "oklahoma",
    "arkansas",
    "nebraska",
    "idaho",
    "montana",
    "wyoming",
    "north dakota",
    "south dakota",
    "puerto rico",
]
OUT_WORLD = [
    "london",
    "england",
    "united kingdom",
    "uk",
    "britain",
    "scotland",
    "ireland",
    "dublin",
    "paris",
    "france",
    "germany",
    "berlin",
    "alemania",
    "zurich",
    "switzerland",
    "suiza",
    "schweiz",
    "geneva",
    "canada",
    "toronto",
    "vancouver",
    "montreal",
    "mexico city",
    "ciudad de mexico",
    "cdmx",
    "spain",
    "espana",
    "madrid",
    "barcelona",
    "italy",
    "rome",
    "amsterdam",
    "netherlands",
    "australia",
    "sydney",
    "india",
    "japan",
    "tokyo",
    "china",
    "brazil",
    "argentina",
    "colombia",
    "bogota",
    "peru",
    "chile",
    "europe",
    "europa",
]
OFFICIAL = {  # closest official source per jurisdiction (checked 2026-10-04); others fall back to our manifest
    "Los Angeles, CA": ("Los Angeles Housing Department", "https://housing.lacity.gov/residents"),
    "San Francisco, CA": ("San Francisco Rent Board", "https://sf.gov/departments/rent-board"),
    "Berkeley, CA": ("Berkeley Rent Board", "https://rentboard.berkeleyca.gov"),
    "Jersey City, NJ": (
        "Jersey City Office of Landlord/Tenant Relations",
        "https://www.jerseycitynj.gov/landlordtenant",
    ),
    "Boston, MA": (
        "Boston Office of Housing Stability",
        "https://www.boston.gov/departments/housing/office-housing-stability",
    ),
    "Cambridge, MA": ("Cambridge tenant rights", "https://www.cambridgema.gov/tenantrights"),
    "NJ": (
        "NJ DCA: Truth in Renting",
        "https://www.nj.gov/dca/codes/publications/pdf_lti/t_i_r.pdf",
    ),
    "US": ("USA.gov: Tenant rights and protections", "https://www.usa.gov/tenant-rights"),
    "WORLD": ("USA.gov: Tenant rights (U.S. only)", "https://www.usa.gov/tenant-rights"),
}

# ------------------------------------------------------------------ topics
CATEGORIES = [
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
    "screening_restrictions",
    "algorithmic_rent_setting",
]
CAT_NAME = {
    "en": {
        "rent_increase_limits": "rent increases",
        "just_cause_eviction": "evictions",
        "security_deposits": "security deposits",
        "application_screening_fees": "application and move-in fees",
        "screening_restrictions": "tenant screening",
        "algorithmic_rent_setting": "rent-pricing software",
    },
    "es": {
        "rent_increase_limits": "aumentos de renta",
        "just_cause_eviction": "desalojos",
        "security_deposits": "depósitos de garantía",
        "application_screening_fees": "cargos de solicitud y mudanza",
        "screening_restrictions": "selección de inquilinos",
        "algorithmic_rent_setting": "software para fijar la renta",
    },
}
# accent-folded, lower-case phrases; a word boundary is required on both sides
CAT_TERMS = {
    "rent_increase_limits": [
        "raise",
        "raising",
        "raised",
        "increase",
        "increases",
        "increased",
        "go up",
        "goes up",
        "rent cap",
        "rent caps",
        "rent control",
        "rent controlled",
        "rent stabilization",
        "rent stabilized",
        "stabilized",
        "how much more",
        "hike",
        "subir",
        "suben",
        "sube",
        "aumento",
        "aumentos",
        "aumentar",
        "control de renta",
        "control de rentas",
        "control de alquiler",
        "tope",
        "limite de renta",
        "rent leveling",
        "allowable increase",
        "cpi",
    ],
    "just_cause_eviction": [
        "evict",
        "evicted",
        "eviction",
        "evictions",
        "kick me out",
        "kick out",
        "kicked out",
        "throw me out",
        "make me leave",
        "move out",
        "notice to quit",
        "notice to vacate",
        "terminate",
        "termination",
        "end my lease",
        "end the tenancy",
        "just cause",
        "good cause",
        "no fault",
        "no-fault",
        "relocation",
        "owner move in",
        "owner move-in",
        "retaliat",
        "reprisal",
        "not renew",
        "nonrenewal",
        "non-renewal",
        "desalojo",
        "desalojar",
        "desalojan",
        "desalojen",
        "echar",
        "echarme",
        "desahucio",
        "causa justa",
        "reubicacion",
        "represalia",
        "sin motivo",
        "sin razon",
        "without a reason",
        "without reason",
        "for no reason",
        "foreclos",
    ],
    "security_deposits": [
        "deposit",
        "deposits",
        "security",
        "deposito",
        "depositos",
        "fianza",
        "garantia",
        "interest on",
        "last month",
        "first and last",
    ],
    "application_screening_fees": [
        "last month",
        "last month's rent",
        "first month",
        "first and last",
        "first, last",
        "move-in costs",
        "move-in cost",
        "move in costs",
        "upfront",
        "up front",
        "application fee",
        "application fees",
        "screening fee",
        "screening fees",
        "fee",
        "fees",
        "apply",
        "application",
        "applying",
        "broker",
        "solicitud",
        "cuota",
        "tarifa",
        "cargo",
        "cobrar",
        "cobran",
        "comision",
        "move in cost",
        "move-in cost",
        "upfront",
    ],
    "screening_restrictions": [
        "criminal",
        "background check",
        "background",
        "record",
        "conviction",
        "convictions",
        "arrest",
        "felony",
        "voucher",
        "vouchers",
        "section 8",
        "source of income",
        "housing assistance",
        "public assistance",
        "credit",
        "discriminat",
        "fair chance",
        "refuse to rent",
        "turn me down",
        "reject",
        "rejected",
        "antecedentes",
        "penales",
        "vale",
        "vales",
        "seccion 8",
        "ingresos",
        "discrimin",
        "rechaz",
        "credito",
    ],
    "algorithmic_rent_setting": [
        "algorithm",
        "algorithms",
        "algorithmic",
        "software",
        "realpage",
        "yieldstar",
        "pricing tool",
        "pricing tools",
        "revenue management",
        "ai pricing",
        "price fixing",
        "price-fixing",
        "algoritmo",
        "algoritmos",
        "programa",
    ],
}
RENTAL_WORDS = [
    "rent",
    "renting",
    "renter",
    "landlord",
    "tenant",
    "tenants",
    "lease",
    "apartment",
    "unit",
    "housing",
    "building",
    "evict",
    "deposit",
    "move in",
    "move out",
    "notice",  # short renter questions without a topic word (eval: 'How much notice do I get?' was refused as off-topic)
    "eviction",
    "evicted",
    "sublet",
    "sublease",
    "roommate",
    "roommates",
    "repair",
    "repairs",
    "landlady",
    "property manager",
    "desalojo",
    "subarrendar",
    "reparaciones",
    "aviso",
    "heat",
    "heating",
    "mold",
    "alquiler",
    "renta",
    "inquilino",
    "inquilinos",
    "casero",
    "arrendador",
    "propietario",
    "dueno",
    "apartamento",
    "departamento",
    "vivienda",
    "contrato",
]
ES_WORDS = {
    "que",
    "qué",
    "cuanto",
    "cuánto",
    "cuanta",
    "puede",
    "pueden",
    "puedo",
    "mi",
    "me",
    "mis",
    "el",
    "los",
    "las",
    "una",
    "un",
    "en",
    "por",
    "para",
    "sin",
    "con",
    "es",
    "son",
    "hay",
    "como",
    "cómo",
    "casero",
    "alquiler",
    "renta",
    "inquilino",
    "desalojar",
    "desalojo",
    "deposito",
    "depósito",
    "solicitud",
    "cobrar",
    "subir",
    "ley",
    "leyes",
    "dueño",
    "si",
    "sí",
    "tengo",
    "derecho",
    "derechos",
}
# Spanish query words -> English index terms (the index holds both, this widens recall)
ES_EN = {
    "deposito": "deposit security",
    "fianza": "deposit security",
    "garantia": "deposit security",
    "alquiler": "rent",
    "renta": "rent",
    "subir": "increase raise",
    "aumento": "increase",
    "aumentar": "increase",
    "desalojo": "eviction evict",
    "desalojar": "eviction evict",
    "desahucio": "eviction",
    "causa": "cause",
    "justa": "just",
    "motivo": "cause reason",
    "solicitud": "application",
    "cobrar": "fee charge",
    "cuota": "fee",
    "tarifa": "fee",
    "cargo": "fee",
    "antecedentes": "criminal history background",
    "penales": "criminal conviction",
    "vale": "voucher",
    "vales": "voucher",
    "ingresos": "income source",
    "credito": "credit",
    "algoritmo": "algorithm algorithmic",
    "software": "software",
    "interes": "interest",
    "aviso": "notice",
    "casero": "landlord",
    "inquilino": "tenant",
    "reubicacion": "relocation",
    "represalia": "retaliation reprisal",
    "mes": "month",
    "meses": "months",
}
STOP = set(
    """a an the and or of to in on at for by with from is are be can could may might my me i you your they them their
    it its this that what how much many do does did if as about any there here we our us will would should was were
    has have had not no yes than then so up down out into just also please tell know want get el la los las de del y o
    un una en por para con que mi me se es""".split()
)


# Short names people use for the laws in our rules (the brief audit, T3): matched as phrases in the question, the
# rule is then retrieved whatever the place filter says, and its topic wins over weak topic words ("apply").
ALIASES = {
    "NJ-ALG-01": [
        "fair act",
        "nj fair act",
        "new jersey fair act",
        "forbidding the algorithmic inflation of rent",
        "p.l.2026, c.43",
        "pl 2026 c 43",
        "p.l. 2026 c.43",
        "c.43",
    ],
    "CA-RENT-01": [
        "ab 1482",
        "ab1482",
        "tenant protection act",
        "tpa",
        "civil code 1947.12",
        "1947.12",
    ],
    "CA-EVIC-01": ["ab 1482", "ab1482", "tenant protection act", "tpa", "1946.2"],
    "CA-DEP-01": ["ab 12", "ab12", "1950.5"],
    "CA-FEE-01": ["1950.6"],
    "CA-ALG-01": ["ab 325", "ab325", "sb 763", "sb763", "cartwright act", "16729"],
    "CA-SCR-01": ["feha", "fair employment and housing act", "12955"],
    "CA-SCR-02": ["feha", "fair employment and housing act"],
    "LA-RENT-01": ["rso", "rent stabilization ordinance", "la rso", "151.00"],
    "LA-EVIC-01": ["rso", "151.09"],
    "LA-DEP-01": ["rso", "151.06.02"],
    "LA-EVIC-02": ["jco", "just cause ordinance", "just cause for eviction ordinance"],
    "LA-EVIC-03": ["rpo", "resident protections ordinance"],
    "SF-RENT-01": ["rent ordinance", "sf rent ordinance", "chapter 37", "rent board"],
    "SF-EVIC-01": ["rent ordinance", "37.9"],
    "SF-EVIC-02": ["37.9c", "relocation payments"],
    "SF-ALG-01": ["37.10c"],
    "BER-RENT-01": [
        "rent stabilization ordinance",
        "measure bb",
        "aga",
        "annual general adjustment",
        "13.76",
    ],
    "BER-EVIC-01": ["measure bb", "good cause ordinance", "13.76"],
    "BER-SCR-01": ["fair chance access to housing", "dellums"],
    "SA-RENT-01": ["rent stabilization ordinance"],
    "SA-EVIC-01": ["just cause eviction ordinance"],
    "NJ-EVIC-03": ["anti-eviction act", "anti eviction act", "2a:18-61.1"],
    "NJ-EVIC-02": ["foreclosure fairness act"],
    "NJ-DEP-01": ["security deposit law", "rent security deposit act", "46:8-21.2"],
    "NJ-SCR-01": ["law against discrimination", "nj lad", "lad"],
    "NJ-SCR-02": ["fair chance in housing", "fair chance in housing act", "fcha"],
    "JC-RENT-01": ["jersey city rent control ordinance", "chapter 260"],
    "HOB-RENT-01": ["hoboken rent control ordinance", "rent leveling", "chapter 155"],
    "MA-RENT-01": ["c.40p", "40p", "chapter 40p", "rent control ban", "1994 ballot"],
    "MA-RENT-P1": ["ballot question", "initiative petition", "25-21", "ballot initiative"],
    "MA-DEP-01": ["186 15b", "15b", "security deposit law"],
    "MA-ALG-P1": ["h.5222", "h 5222"],
    "MA-ALG-P2": ["s.2983", "s 2983"],
    "BOS-RENT-P1": ["h.3744", "h 3744", "home rule petition"],
    "BOS-EVIC-01": ["housing stability notification act"],
    "BOS-SCR-02": ["fair chance tenant selection"],
}
_ALIAS_RX = sorted({a for v in ALIASES.values() for a in v}, key=len, reverse=True)


def named_rules(q: str) -> list[str]:
    """Rules the question names by a short name (FAIR Act, AB 1482, RSO, c.40P, ...), most specific first."""
    qf = " " + fold(q) + " "
    out: list[str] = []
    for a in _ALIAS_RX:
        if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", qf):
            if a in ("rso", "lad", "aga", "tpa", "jco", "rpo") and not re.search(
                r"(?<![A-Za-z])" + a.upper() + r"(?![A-Za-z])", q
            ):
                continue  # short acronyms only in capitals
            out += [r for r, al in ALIASES.items() if a in al and r not in out]
    return out


PREEMPT = re.compile(
    r"\b(?:preempt\w*|pre-empt\w*|conflict\w*|override\w*|supersed\w*|overrul\w*|state law beats|deroga\w*|anula\w*|prevalec\w*)\b",
    re.I,
)


# ------------------------------------------------------------------ text helpers
def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace("’", "'").replace("‘", "'")


def norm_q(q: str) -> str:
    return re.sub(r"[\s?¿!¡.\"']+$", "", re.sub(r"\s+", " ", fold(q)).strip()).lstrip("¿¡ ")


def _stem(w: str) -> str:
    for suf in ("ations", "ation", "ings", "ing", "ies", "ions", "ion", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(s: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", fold(s)) if w not in STOP and len(w) > 1]


def has_phrase(text_f: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text_f) is not None


EN_MARKERS = {
    "the",
    "and",
    "is",
    "are",
    "law",
    "landlord",
    "landlords",
    "cannot",
    "may",
    "not",
    "of",
    "to",
    "for",
    "your",
}


def _english(text: str) -> bool:
    words = re.findall(r"[a-záéíóúñü]+", (text or "").lower())
    en = sum(1 for w in words if w in EN_MARKERS)
    es = sum(1 for w in words if w in ES_WORDS)
    return en >= 3 and en > 2 * es


def detect_lang(q: str, fallback: str = "en") -> str:
    if re.search(r"[¿¡ñ]", q):
        return "es"
    words = re.findall(r"[a-záéíóúñü]+", q.lower())
    es = sum(1 for w in words if w in ES_WORDS and w not in {"me", "en", "si", "un", "el"})
    en = sum(
        1
        for w in words
        if w in {"the", "my", "can", "how", "what", "is", "are", "does", "landlord", "rent", "to"}
    )
    if es >= 2 and es > en:
        return "es"
    if en >= 1:
        return "en"
    return fallback if fallback in ("en", "es") else "en"


# ------------------------------------------------------------------ BM25
class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.4, b: float = 0.72) -> None:
        self.docs = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 1.0
        df = Counter(t for d in self.docs for t in d)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, q: list[str]) -> list[float]:
        out = []
        for d, ln in zip(self.docs, self.len, strict=True):
            s = 0.0
            for t in set(q):
                f = d.get(t)
                if f:
                    s += (
                        self.idf[t]
                        * f
                        * (self.k1 + 1)
                        / (f + self.k1 * (1 - self.b + self.b * ln / self.avg))
                    )
            out.append(s)
        return out


class Index:
    """Rules + no-rule findings + source passages, rebuilt when the rule store reloads."""

    def __init__(self, store) -> None:
        self.sig = store._sig
        self.items: list[dict] = []  # rules and findings
        docs = []
        for r in store.rules.values():
            text = " ".join(
                str(x or "")
                for x in (
                    r.get("title"),
                    r.get("requirement"),
                    r.get("key_value"),
                    r.get("quoted_span"),
                    r.get("citation"),
                    r.get("coverage_conditions"),
                    r.get("exemptions"),
                    r.get("interaction"),
                    store.t(r.get("title"), "es"),
                    store.t(r.get("requirement"), "es"),
                    " ".join(CAT_TERMS.get(r.get("category"), [])[:12]),
                    " ".join(ALIASES.get(r["team_rule_id"], [])),
                )
            )
            self.items.append(
                {
                    "kind": "rule",
                    "id": r["team_rule_id"],
                    "jur": r["jurisdiction"],
                    "cat": r["category"],
                    "doc": r.get("quoted_span_doc_id") or r.get("source_doc_id"),
                }
            )
            docs.append(tokens(text))
        for f in store.no_rule:
            text = " ".join(
                str(x or "")
                for x in (
                    f.get("finding"),
                    store.t(f.get("finding"), "es"),
                    f.get("quoted_span"),
                    " ".join(CAT_TERMS.get(f.get("category"), [])[:12]),
                )
            )
            self.items.append(
                {
                    "kind": "finding",
                    "id": f["finding_id"],
                    "jur": f["jurisdiction"],
                    "cat": f["category"],
                    "doc": f.get("quoted_span_doc_id") or f.get("source_doc_id"),
                }
            )
            docs.append(tokens(text))
        self.bm = BM25(docs)
        # passages of the source documents: a hit lifts every item quoted from that document
        by_doc = defaultdict(list)
        for i, it in enumerate(self.items):
            if it["doc"]:
                by_doc[it["doc"]].append(i)
        self.p_doc, pdocs = [], []
        for doc_id in by_doc:
            words = (store.doc_text(doc_id) or "").split()
            for s in range(0, max(len(words) - 20, 1), 60):
                self.p_doc.append(doc_id)
                pdocs.append(tokens(" ".join(words[s : s + 120])))
        self.by_doc = by_doc
        self.pbm = BM25(pdocs) if pdocs else None

    def search(
        self, q: str, jurs: dict[str, float] | None, cats: list[str]
    ) -> list[tuple[float, dict]]:
        qt = tokens(q)
        for w in re.findall(r"[a-z]+", fold(q)):
            if w in ES_EN:
                qt += tokens(ES_EN[w])
        base = self.bm.scores(qt) if qt else [0.0] * len(self.items)
        lift = [0.0] * len(self.items)
        if self.pbm and qt:
            best: dict[str, float] = {}
            for doc_id, s in zip(self.p_doc, self.pbm.scores(qt), strict=True):
                best[doc_id] = max(best.get(doc_id, 0.0), s)
            for doc_id, s in best.items():
                for i in self.by_doc[doc_id]:
                    lift[i] = 0.35 * s
        out = []
        for i, it in enumerate(self.items):
            w = 1.0 if jurs is None else jurs.get(it["jur"], 0.0)
            if w <= 0 or (cats and it["cat"] not in cats):
                continue
            s = (base[i] + lift[i]) * w + (2.5 if cats and it["cat"] in cats else 0.0)
            out.append((s, it))
        out.sort(key=lambda x: -x[0])
        return out


_INDEX: Index | None = None
_INDEX_LOCK = threading.Lock()


def index() -> Index:
    global _INDEX
    STORE = ask_store()
    if _INDEX is None or _INDEX.sig != STORE._sig:
        with _INDEX_LOCK:
            if _INDEX is None or _INDEX.sig != STORE._sig:
                sync_places(STORE)
                _INDEX = Index(STORE)
    return _INDEX


_STATIC_CITIES = None
_STATIC_OTHER: dict[str, list] = {}
ZIP_CITY: dict[str, str] = {}


def sync_places(store) -> None:
    """Every city in the data becomes a place Ask knows: its names (from jurisdiction.json or the rules), its ZIPs,
    the chooser, the scope message. Cities that were 'other local' (state law only) leave that list once covered."""
    global _STATIC_CITIES, PLACE_PHRASES, ZIP_CITY
    if _STATIC_CITIES is None:
        _STATIC_CITIES = {k: list(v) for k, v in CITY_ALIASES.items()}
        _STATIC_OTHER.update({k: list(v) for k, v in OTHER_LOCAL.items()})
    found = places(store)
    merged = {k: list(v) for k, v in _STATIC_CITIES.items()}
    for jur, info in found.items():
        if info["state"] not in STATE_CODES:
            continue  # a new state needs its state rules first; its cities stay out of scope until then
        names = [n for n in info["aliases"] if len(n) > 2]
        merged[jur] = list(dict.fromkeys([*merged.get(jur, []), *names]))
    CITY_ALIASES.clear()
    CITY_ALIASES.update(merged)
    covered = {n for v in merged.values() for n in v}
    for st, lst in OTHER_LOCAL.items():
        lst[:] = [
            n for n in _STATIC_OTHER[st] if n.removesuffix(" nj").removesuffix(" ma") not in covered
        ]
    PLACE_PHRASES = sorted(
        {n for v in CITY_ALIASES.values() for n in v}
        | {n for v in STATE_ALIASES.values() for n in v}
        | {n for v in OTHER_LOCAL.values() for n in v}
        | set(OUT_US)
        | set(OUT_WORLD)
        | {"ca", "nj", "ma", "la"},
        key=len,
        reverse=True,
    )
    ZIP_CITY = zip_city(store, set(CITY_ALIASES))


# ------------------------------------------------------------------ place detection
SUFFIX = {
    "avenue": "ave",
    "av": "ave",
    "street": "st",
    "boulevard": "blvd",
    "bl": "blvd",
    "drive": "dr",
    "road": "rd",
    "place": "pl",
    "court": "ct",
    "lane": "ln",
    "terrace": "ter",
    "parkway": "pkwy",
    "highway": "hwy",
    "way": "way",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "mount": "mt",
    "saint": "st",
    "square": "sq",
}
STREET_SUFFIXES = {
    "ave",
    "st",
    "blvd",
    "dr",
    "rd",
    "pl",
    "ct",
    "ln",
    "ter",
    "pkwy",
    "hwy",
    "way",
    "sq",
    "cir",
    "aly",
}


def _street_tokens(s: str) -> list[str]:
    return [SUFFIX.get(w, w) for w in re.findall(r"[a-z0-9]+", fold(s))]


_ADDR_CACHE: tuple | None = None


def _addr_index(store) -> list[tuple[str, set[str], set[str]]]:
    """(address_id, house numbers, core street words) per address."""
    global _ADDR_CACHE
    if _ADDR_CACHE and _ADDR_CACHE[0] == store._sig:
        return _ADDR_CACHE[1]
    rows = []
    for aid, a in store.addresses.items():
        street = a.get("street_address") or ""
        m = re.match(r"\s*(\d+[a-z]?)(?:\s*-\s*(\d+[a-z]?))?\s+(.*)", fold(street))
        if not m:
            continue
        nums = {m.group(1)} | ({m.group(2)} if m.group(2) else set())
        if m.group(2) and m.group(1).isdigit() and m.group(2).isdigit():
            lo, hi = sorted((int(m.group(1)), int(m.group(2))))
            if hi - lo <= 12:
                nums |= {str(n) for n in range(lo, hi + 1)}
        words = [
            w
            for w in _street_tokens(m.group(3))
            if w not in STREET_SUFFIXES and w not in {"n", "s", "e", "w"}
        ]
        rows.append((aid, nums, set(words) or set(_street_tokens(m.group(3)))))
    _ADDR_CACHE = (store._sig, rows)
    return rows


def find_address(q: str, store) -> str | None:
    m = re.search(r"\b(A\d{4})\b", q, re.I)
    if m and m.group(1).upper() in store.addresses:
        return m.group(1).upper()
    qf = fold(q)
    qnums = set(re.findall(r"(?<![\d.$%])(\d{1,6}[a-z]?)(?![\d%])", qf))
    if not qnums:
        return None
    qwords = set(_street_tokens(qf))
    best, best_s = None, 0.0
    for aid, nums, words in _addr_index(store):
        if not (nums & qnums):
            continue
        hit = len(words & qwords)
        if not hit or hit < max(1, math.ceil(len(words) * 0.6)):
            continue
        s = hit / len(words)
        a = store.addresses[aid]
        city = fold(a.get("resolved_city") or a.get("postal_city") or "")
        if city and has_phrase(qf, city):
            s += 0.5
        if s > best_s:
            best, best_s = aid, s
    return best


def find_places(q: str) -> dict:
    """Cities / states named in the question, plus places we do not cover."""
    qf = " " + fold(q) + " "
    cities, states, other_local, outside = [], [], [], []
    street = r"(?:st|street|ave|avenue|av|blvd|boulevard|rd|road|dr|drive|way|pl|place|ct|court|ln|lane|ter|terrace)\b"
    for jur, names in CITY_ALIASES.items():  # "Berkeley St" is a street, not the city
        if any(
            re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])(?!\.?\s+" + street + ")", qf)
            for n in names
            if len(n) > 2
        ):
            cities.append(jur)
    for z in re.findall(r"(?<![\d$.,])(\d{5})(?![\d%])", q):
        jur = ZIP_CITY.get(z)
        if jur and jur not in cities:
            cities.append(jur)
    for code, jur in CASE_ALIASES.items():
        if re.search(r"(?<![A-Za-z])" + re.escape(code) + r"(?![A-Za-z])", q) and jur not in cities:
            cities.append(jur)
    for code, names in STATE_ALIASES.items():
        if any(has_phrase(qf, n) for n in names) or re.search(
            r"(?<![A-Za-z])" + code + r"(?![A-Za-z])", q
        ):
            states.append(code)
    for code, names in OTHER_LOCAL.items():
        for n in names:
            if has_phrase(qf, n) and not any(
                has_phrase(qf, c) for c in ("west new york",) if n != c
            ):
                other_local.append((code, n.removesuffix(" nj").removesuffix(" ma").title()))
    if has_phrase(qf, "west hollywood") and "Los Angeles, CA" in cities:
        if not has_phrase(qf.replace("west hollywood", ""), "hollywood") and not has_phrase(
            qf, "los angeles"
        ):
            cities.remove("Los Angeles, CA")
    for n in OUT_US:
        if has_phrase(qf, n):
            if n in ("new york", "nueva york") and has_phrase(qf, "west new york"):
                continue
            outside.append(("US", n.title()))
    for n in OUT_WORLD:
        if has_phrase(qf, n) and not (n == "uk" and "UK" not in q):
            outside.append(("WORLD", n.upper() if n == "uk" else n.title()))
    if any(has_phrase(qf, n) for n in ("cambridge, england", "cambridge uk")):
        cities = [c for c in cities if c != "Cambridge, MA"]
    return {"cities": cities, "states": states, "other_local": other_local, "outside": outside}


def categories_for(q: str) -> list[str]:
    qf = fold(q)
    hits = Counter()
    for cat, terms in CAT_TERMS.items():
        for t in terms:
            if has_phrase(qf, t) or (
                t.endswith(("discriminat", "discrimin", "retaliat", "rechaz", "foreclos"))
                and t in qf
            ):
                hits[cat] += 2 if " " in t else 1
    # "security deposit" is about deposits, not screening; a fee to apply is not about screening
    if hits.get("security_deposits") and "security" in qf:
        hits["screening_restrictions"] = max(0, hits["screening_restrictions"] - 1)
    if not hits:
        from web import ask_increase as INC

        m = INC.parse_money(q)  # "my rent is $2,000 and they want $300 more"
        return ["rent_increase_limits"] if m.get("rent") and (m.get("inc") or m.get("new")) else []
    top = max(hits.values())
    return [c for c, n in hits.most_common() if n >= max(1, top - 1)][:2]


def is_rental(q: str) -> bool:
    qf = fold(q)
    return any(has_phrase(qf, w) for w in RENTAL_WORDS) or bool(categories_for(q))


# ------------------------------------------------------------------ evidence
def _status_at(r: dict, as_of: str) -> str:
    from web.app import _norm_date, rule_status_at

    sunset = _norm_date(r.get("sunset_date"))
    if sunset and as_of >= sunset and r.get("status") != "failed":
        from navigator.evaluate import _sunset_is_repeal

        if _sunset_is_repeal(r):  # e.g. AB 1482's cap and just cause end on Jan 1, 2030
            return "repealed"
    return rule_status_at(r, as_of) or r.get("status") or "in_force"


STATUS_LABEL = {
    "en": {
        "in_force": "in force",
        "not_yet_effective": "not yet in force",
        "pending": "pending bill, not law",
        "failed": "failed proposal, not law",
        "no_rule": "no rule",
        "older_version": "this version not in force yet",
        "repealed": "no longer in force (ended {sunset})",
    },
    "es": {
        "in_force": "vigente",
        "not_yet_effective": "aún no vigente",
        "pending": "proyecto pendiente, no es ley",
        "failed": "propuesta fallida, no es ley",
        "no_rule": "sin norma",
        "older_version": "esta versión aún no vigente",
        "repealed": "ya no vigente (terminó el {sunset})",
    },
}
ENGINE_LABEL = {
    "en": {
        "applies": "Applies here",
        "unknown": "Can't tell yet",
        "superseded": "Overridden here",
        "not_yet_effective": "Starts later",
        "pending": "Not law yet",
        "failed": "Not law",
        "excluded": "Doesn't cover this building",
        "no_rule": "No rule here",
    },
    "es": {
        "applies": "Aplica aquí",
        "unknown": "Aún no se sabe",
        "superseded": "Reemplazada aquí",
        "not_yet_effective": "Empieza después",
        "pending": "Aún no es ley",
        "failed": "No es ley",
        "excluded": "No cubre este edificio",
        "no_rule": "Sin norma aquí",
    },
}


def _source_note(rule_id: str, lang: str) -> dict | None:
    from web.source_notes import note

    return note(rule_id, lang)


def _jur_label(j: str) -> str:
    return STATE_NAME.get(j, j.split(",")[0] if j else "")


def evidence_item(
    store, item_id: str, as_of: str, lang: str, engine: dict | None = None
) -> dict | None:
    r = store.rules.get(item_id)
    finding = None
    if r is None:
        finding = next((f for f in store.no_rule if f.get("finding_id") == item_id), None)
        if finding is None:
            return None
        r = finding
    v = store.verify(r)
    doc = r.get("quoted_span_doc_id") or r.get("source_doc_id")
    meta = store.doc_meta(doc)
    status = "no_rule" if finding else _status_at(r, as_of)
    version_from = None
    if not finding and status == "in_force" and r.get("amends_existing_law"):
        from web.app import _norm_date

        eff = _norm_date(r.get("effective_date"))
        if (
            eff and as_of < eff
        ):  # the law existed, but the text we hold is a later version (e.g. AB 12's one month)
            status, version_from = "older_version", eff
    out = {
        "id": item_id,
        "kind": "finding" if finding else "rule",
        "title": store.t(r.get("title") or "", lang)
        if not finding
        else store.t(r.get("finding"), lang),
        "title_en": r.get("title") or r.get("finding"),
        "jurisdiction": r.get("jurisdiction"),
        "jurisdiction_label": _jur_label(r.get("jurisdiction") or ""),
        "level": r.get("level"),
        "category": r.get("category"),
        "citation": r.get("citation") or "",
        "status": status,
        "version_from": version_from,
        "status_label": STATUS_LABEL[lang]
        .get(status, status)
        .replace("{sunset}", str(r.get("sunset_date") or "")[:10]),
        "quoted_span": r.get("quoted_span") or "",
        "verbatim": v.get("status") in ("exact", "normalized"),
        "quote_check": v.get("status"),
        # the quote is from another document than the cited law (web/source_notes.py)
        "source_note": None if finding else _source_note(item_id, lang),
        "doc_id": doc if meta.get("has_text") else None,
        "source_url": r.get("source_url") or meta.get("url"),
        # a law-firm or news page: a summary, never "Official site" (brief audit X4)
        "secondary": r.get("verification") == "secondary_source"
        or str(r.get("source_type") or "").startswith("secondary"),
        "requirement": store.t(r.get("requirement"), lang)
        if not finding
        else store.t(r.get("finding"), lang),
        "requirement_en": r.get("requirement") or r.get("finding"),
        "key_value": r.get("key_value") if not finding else None,
        "exemptions": r.get("exemptions") if not finding else None,
        "effective_date": r.get("effective_date"),
        "sunset_date": str(r.get("sunset_date") or "")[:10] or None,
        "enacted_date": str(r.get("enacted_date") or "")[:10] or None,
        "conflict_note": r.get("conflict_note") if not finding else None,
        "effective_date_note": r.get("effective_date_note") if not finding else None,
        "penalty": r.get("penalty") if not finding else None,
        "current_version_effective": r.get("current_version_effective") if not finding else None,
        "overrides": list(r.get("overrides") or []) if not finding else [],
        # which side wins where both cover a unit: a state rule that yields to local rules, a local one that supersedes
        "yields_to_local": bool((r.get("coverage") or {}).get("yields_to_local_rule"))
        if not finding
        else False,
        "supersedes_state": bool((r.get("coverage") or {}).get("supersedes_state_rule"))
        if not finding
        else False,
        "interaction": r.get("interaction") if not finding else None,
        "coverage_conditions": r.get("coverage_conditions") if not finding else None,
    }
    if engine:
        out["engine"] = {
            **engine,
            "label": ENGINE_LABEL[lang].get(engine.get("result"), engine.get("result")),
        }
    return out


NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ten": 10}
PAT_SMALL = r"small|natural[- ]person|two months|2 months|qualifying"
PAT_OWNER = r"owner[- ]occupied|duplex|single[- ]family|owner lives|owner shares"
PAT_NEW = r"new(ly)?[- ]construct|newer construction|\bCO\b[^.;]*within|certificate of occupancy[^.;]*within|less than \d+ years old|built (in|within) the (last|previous)"


def _maxunits(text: str) -> int | None:
    t = fold(text)
    m = (
        re.search(r"no more than (\w+) (?:\w+ )?(?:dwelling |rental )?units", t)
        or re.search(r"not more than (\w+) (?:\w+ )?(?:dwelling |rental )?units", t)
        or re.search(r"(\w+) (?:or fewer|units or fewer)", t)
    )
    if m:
        w = m.group(1)
        return int(w) if w.isdigit() else NUMW.get(w)
    m = re.search(r"(\d)\s*-\s*(\d) unit", t)
    if m:
        return int(m.group(2))
    if "duplex" in t:
        return 2
    if "single-family" in t or "single family" in t:
        return 1
    return None


def exception_checks(r: dict, place: dict, as_of: str) -> list[dict]:
    """Exceptions of a rule checked against the building's public facts. 'cannot': the facts rule it out (it is
    dropped from what the model sees); 'might': a needed fact is unknown (the model may say "unless ...")."""
    cov = r.get("coverage") or {}
    try:
        units = int(str(place.get("units") or "").strip())
    except ValueError:
        units = None
    lower = units or place.get("units_min")
    try:
        built = int(str(place.get("year_built") or "")[:4])
    except ValueError:
        built = None
    out = []

    def add(kind, pat, limit, why_cannot):
        if limit is None:
            return
        if lower and lower > limit:
            out.append(
                {
                    "kind": kind,
                    "verdict": "cannot",
                    "pattern": pat,
                    "why": why_cannot.format(n=lower, m=limit),
                }
            )
        elif not units:
            out.append(
                {"kind": kind, "verdict": "might", "pattern": pat, "why": "number of units unknown"}
            )

    if cov.get("landlord_size_condition"):
        add(
            "small_landlord",
            PAT_SMALL,
            _maxunits(cov["landlord_size_condition"]),
            "this building alone has {n} units; the exception needs {m} units or fewer in total",
        )
    if cov.get("owner_occupied_exemption_max_units"):
        add(
            "owner_occupied",
            PAT_OWNER,
            int(cov["owner_occupied_exemption_max_units"]),
            "this building has {n} units; the owner-occupied exception needs {m} or fewer",
        )
    else:
        for x in cov.get("unverifiable_exemptions") or []:
            if re.search(PAT_OWNER, x, re.I) and not re.search(r"condo", x, re.I):
                add(
                    "owner_occupied",
                    PAT_OWNER,
                    _maxunits(x),
                    "this building has {n} units; the exception needs {m} or fewer",
                )
                break
    nce = cov.get("new_construction_exemption") or {}
    if nce.get("years"):
        age_limit = int(nce["years"])
        if built:
            if int(as_of[:4]) - built > age_limit + 1:
                out.append(
                    {
                        "kind": "new_construction",
                        "verdict": "cannot",
                        "pattern": PAT_NEW,
                        "why": f"built {built}; the new-construction exception covers buildings under {age_limit} years old",
                    }
                )
        else:
            out.append(
                {
                    "kind": "new_construction",
                    "verdict": "might",
                    "pattern": PAT_NEW,
                    "why": "year built unknown",
                }
            )
    return out


def _strip(text: str | None, pattern: str) -> str | None:
    """Remove the parentheses, clauses and sentences of a text that talk about an excluded exception."""
    if not text:
        return text
    t = re.sub(
        r"\s*\([^()]*\)", lambda m: "" if re.search(pattern, m.group(0), re.I) else m.group(0), text
    )
    parts = re.split(r"(?<=[.;])\s+", t)
    t = " ".join(p for p in parts if not re.search(pattern, p, re.I))
    return t.strip() or None


def _until(expl: str) -> str:
    """'built 2001: exempt as new construction (... within 30 years)': give the end year, so the model never does
    the date math itself (eval AD12: '2001 + 30 is past')."""
    m = re.search(r"\bbuilt (\d{4})\b.*?\bwithin (\d+) years\b", expl)
    if m and "until" not in expl:
        expl += f"; the exemption runs until about {int(m.group(1)) + int(m.group(2))}"
    return expl


STATED_YEAR = re.compile(
    r"\b(?:built|constructed|erected|completed|construid[oa]|edificad[oa])\s+(?:back\s+)?(?:in\s+|en\s+|el\s+a[nñ]o\s+|around\s+|about\s+)?"
    r"((?:18|19|20)\d{2})\b|\byear built:?\s*((?:18|19|20)\d{2})\b",
    re.I,
)
STATED_UNITS = re.compile(
    r"\b(\d{1,4})[- ](?:units?|apartments?|unidades|apartamentos|departamentos|viviendas)\b", re.I
)


def stated_facts(q: str) -> dict | None:
    """'built in 1962 and has 20 units': building facts the person gives, for the engine (brief example)."""
    y = STATED_YEAR.search(q or "")
    if not y:
        return None
    u = STATED_UNITS.search(q or "")
    return {"year_built": int(y[1] or y[2]), "units": int(u[1]) if u else None}


def stated_engine(items: list[dict], place: dict, facts: dict, as_of: str) -> bool:
    """The deterministic engine on the stated facts: every rule of the place gets its verdict (never the model's)."""
    import datetime as _dt

    from navigator import evaluate as E
    from navigator import user_facts as U

    st = place.get("state")
    jur = place.get("jurisdiction") if place.get("kind") == "city" else None
    try:
        d = U.evaluate_user(st, jur, facts, as_of)
        f = U.make_facts(st, jur, facts)
    except Exception:  # noqa: BLE001 - a place the engine does not cover: no verdicts, as before
        return False
    res = {e["team_rule_id"]: e for e in d["results"]}
    done = False
    for e in items:
        r = d["rules"].get(e["id"])
        if e["kind"] != "rule" or not r:
            continue
        if e["id"] in res:
            x = res[e["id"]]
            e["engine"] = {
                "result": x["result"],
                "explanation": x.get("explanation_en") or x.get("explanation") or "",
            }
        else:
            v, why = E.coverage(r, f, _dt.date.fromisoformat(as_of))
            if v != E.NO:
                continue
            e["engine"] = {"result": "excluded", "explanation": "; ".join(map(str, why))}
        done = True
    return done


def address_evidence(
    store, address_id: str, as_of: str, lang: str, cats: list[str]
) -> tuple[dict, list[dict]]:
    """Run the deterministic engine for the address; every verdict comes from it, never from the LLM."""
    from web.app import build_address

    slug = getattr(store, "address_slug", {}).get(address_id)
    if slug:
        return ext_address_evidence(store, slug, address_id, as_of, lang, cats)
    a = build_address(address_id, as_of, "en")
    items: list[dict] = []
    for c in a["categories"]:
        if cats and c["id"] not in cats:
            continue
        for it in c["enacted"] + c["pending"] + c["not_law"]:
            eng = {
                "result": it["result"],
                "explanation": it.get("explanation_en") or it.get("explanation") or "",
            }
            if it.get("missing_fact"):
                eng["missing_fact"] = it["missing_fact"]
            if it.get("superseded_by"):
                eng["superseded_by"] = [b["id"] for b in it["superseded_by"]]
            e = evidence_item(store, it["rule"]["team_rule_id"], as_of, lang, eng)
            if e:
                items.append(e)
        for x in c.get("excluded") or []:
            e = evidence_item(
                store,
                x["id"],
                as_of,
                lang,
                {
                    "result": "excluded",
                    "explanation": _until("; ".join(map(str, x.get("reasons") or []))),
                },
            )
            if e:
                items.append(e)
        for f in c.get("no_rule_findings") or []:
            e = evidence_item(
                store, f["finding_id"], as_of, lang, {"result": "no_rule", "explanation": ""}
            )
            if e:
                items.append(e)
    fa = a["address"]
    jur = a["jurisdiction"]
    place = {
        "kind": "address",
        "address_id": address_id,
        "label": f"{_title(fa['street_address'])}, {jur.get('city') or fa['postal_city']}",
        "city": jur.get("city"),
        "state": jur.get("state"),
        "jurisdiction": f"{jur['city']}, {jur['state']}" if jur.get("city") else None,
        "year_built": fa.get("year_built"),
        "units": fa.get("units"),
        "units_min": fa.get("units_min"),
        "missing": fa.get("missing") or [],
    }
    for e in items:
        r = store.rules.get(e["id"])
        if r and e["kind"] == "rule":
            e["exceptions"] = exception_checks(r, place, as_of)
    return place, items


def ext_address_evidence(store, slug: str, address_id: str, as_of: str, lang: str, cats: list[str]):
    """An address of a jurisdiction added with `navigator extend`: the same engine over that extension's rules
    (navigator.api.extension_lookup)."""
    from navigator import api as NA

    lk = NA.extension_lookup(slug, address_id, as_of)
    items: list[dict] = []
    for e in lk["results"]:
        r = store.rules.get(e["team_rule_id"])
        if not r or (cats and r.get("category") not in cats):
            continue
        it = evidence_item(
            store,
            e["team_rule_id"],
            as_of,
            lang,
            {"result": e["result"], "explanation": e.get("explanation") or ""},
        )
        if it:
            items.append(it)
    for f in lk.get("no_rule_findings") or []:
        if cats and f.get("category") not in cats:
            continue
        it = evidence_item(
            store, f["finding_id"], as_of, lang, {"result": "no_rule", "explanation": ""}
        )
        if it:
            items.append(it)
    a = store.addresses[address_id]
    st = a.get("resolved_state") or a["state"]
    city = a.get("resolved_city") or ""
    units = (a.get("units") or "").strip() or None
    place = {
        "kind": "address",
        "address_id": address_id,
        "label": f"{_title(a['street_address'])}, {city or a['postal_city']}",
        "city": city or None,
        "state": st,
        "jurisdiction": f"{city}, {st}" if city else None,
        "year_built": (a.get("year_built") or "").strip() or None,
        "units": units,
        "units_min": None,
        "missing": [k for k in ("year_built", "units") if not (a.get(k) or "").strip()],
    }
    for e in items:
        r = store.rules.get(e["id"])
        if r and e["kind"] == "rule":
            e["exceptions"] = exception_checks(r, place, as_of)
    return place, items


def _title(s: str) -> str:
    return " ".join(w if re.match(r"^\d", w) else w.capitalize() for w in (s or "").lower().split())


def _official(jurs: list[str], store) -> dict:
    jurs = list(dict.fromkeys([*jurs, *(j.split(", ")[1] for j in jurs if ", " in j)]))
    for j in jurs:
        if j in OFFICIAL:
            n, u = OFFICIAL[j]
            return {"label": n, "url": u}
    for j in jurs:  # the official source most of that jurisdiction's rules are quoted from
        docs = Counter(
            r.get("source_doc_id") for r in store.rules.values() if r.get("jurisdiction") == j
        )
        for doc_id, _n in docs.most_common():
            m = store.manifest.get(doc_id or "", {})
            if m.get("source_type") in ("official", "code publisher") and m.get("url"):
                return {"label": f"{_jur_label(j)}: {m['url'].split('/')[2]}", "url": m["url"]}
    n, u = OFFICIAL["US"]
    return {"label": n, "url": u}


# ------------------------------------------------------------------ the model
PROMPT_FILE = (
    Path(__file__).resolve().parent / "ask_prompt.md"
)  # the system prompt, reviewable (DESIGN.md)
_PROMPT_CACHE: dict = {}


def system_prompt(lang: str, as_of: str) -> str:
    m = PROMPT_FILE.stat().st_mtime
    if _PROMPT_CACHE.get("m") != m:
        _PROMPT_CACHE.update(m=m, text=PROMPT_FILE.read_text(encoding="utf-8").strip())
    return (
        _PROMPT_CACHE["text"]
        .replace("{LANG}", "Spanish" if lang == "es" else "English")
        .replace("{AS_OF}", as_of)
    )


# Where to get help (shown as links; the model only picks ids). Checked 2026-10-04.
HELP = {
    "CA-COURTS": (
        "California Courts Self-Help: eviction",
        "https://selfhelp.courts.ca.gov/eviction",
        "CA",
    ),
    "NJ-LSNJ": ("Legal Services of New Jersey", "https://www.lsnj.org", "NJ"),
    "NJ-COURTS": (
        "New Jersey Courts: landlord/tenant self-help",
        "https://www.njcourts.gov/self-help/landlord-tenant",
        "NJ",
    ),
    "MA-LEGALHELP": ("MassLegalHelp: housing", "https://www.masslegalhelp.org/housing", "MA"),
    "LA-LAHD": (*OFFICIAL["Los Angeles, CA"], "Los Angeles, CA"),
    "SF-RENTBOARD": (*OFFICIAL["San Francisco, CA"], "San Francisco, CA"),
    "BER-RENTBOARD": (*OFFICIAL["Berkeley, CA"], "Berkeley, CA"),
    "JC-OLTR": (*OFFICIAL["Jersey City, NJ"], "Jersey City, NJ"),
    "BOS-OHS": (*OFFICIAL["Boston, MA"], "Boston, MA"),
    "CAM-TENANT": (*OFFICIAL["Cambridge, MA"], "Cambridge, MA"),
    "US-USAGOV": (*OFFICIAL["US"], "US"),
}


def _help_for(place: dict | None, address_id: str | None, store) -> list[str]:
    st, jur = None, None
    if address_id:
        a = store.addresses[address_id]
        st = a.get("resolved_state") or a["state"]
        jur = f"{a.get('resolved_city')}, {st}" if a.get("resolved_city") else None
    elif place:
        st, jur = place.get("state"), place.get("jurisdiction")
    out = [h for h, (_n, _u, w) in HELP.items() if w == jur]
    out += [h for h, (_n, _u, w) in HELP.items() if (w == st if st else w in STATE_CODES)]
    return out + ["US-USAGOV"]


def _for_model(e: dict) -> dict:
    """The evidence the model sees: exceptions the building facts rule out are removed."""
    e = dict(e)
    for x in e.get("exceptions") or []:
        if x["verdict"] == "cannot":
            for k in ("requirement_en", "key_value", "exemptions"):
                e[k] = _strip(e.get(k), x["pattern"])
    return e


def _fmt_sources(items: list[dict], as_of: str = "") -> str:
    from web import headlines as H

    # which retrieved rule governs instead of which (from the rules' own "overrides" links), in plain words
    by = {e["id"]: e for e in items}
    relations: dict[str, list[str]] = {}
    done = set()
    for e in items:
        for o in e.get("overrides") or []:
            if o not in by or frozenset((e["id"], o)) in done:
                continue
            done.add(frozenset((e["id"], o)))
            local, state = (e, by[o]) if e.get("level") == "city" else (by[o], e)
            if local.get("level") != "city" or state.get("level") != "state":
                continue
            if not (state.get("yields_to_local") or local.get("supersedes_state")):
                continue  # e.g. a state law that may preempt local rules: its conflict note says so
            city = local["jurisdiction_label"]
            relations.setdefault(local["id"], []).append(
                f"in {city}, for the units it covers, this rule governs instead of [{state['id']}]; do not give"
                f" [{state['id']}]'s figure for those units."
            )
            relations.setdefault(state["id"], []).append(
                f"where [{local['id']}] covers a unit in {city}, [{local['id']}] governs instead. For units"
                f" [{local['id']}] does not cover, this state rule still applies unless one of its own exemptions"
                " holds: never say there is no limit or no protection."
            )

    out = []
    for e in map(_for_model, items):
        lines = [
            f"[{e['id']}] {e['title_en']} ({e['jurisdiction_label']}, {e['level'] or 'state'} level)"
        ]
        if e.get("secondary"):  # 33 of 87 sources are law-firm or news pages (brief audit X3/X4)
            lines.append(
                "  Source type: a published summary (law firm or news), not the official text"
            )
        if e["kind"] == "finding":
            lines.append(f"  Finding: {e['requirement_en']}")
        else:
            lines.append(
                f"  Status on the as-of date: {STATUS_LABEL['en'].get(e['status'], e['status']).replace('{sunset}', str(e.get('sunset_date') or ''))}"
                + (
                    f" (enacted law; it takes effect {e.get('effective_date')}; never call it proposed or being passed)"
                    if e["status"] == "not_yet_effective" and e.get("effective_date")
                    else ""
                )
                + (
                    f" (the text below is the version in force from {e['version_from']}; an older version applied on the"
                    " as-of date and our sources do not include it, so its figures are unknown)"
                    if e.get("version_from")
                    else ""
                )
            )
            lines.append(f"  Requirement: {e['requirement_en']}")
            if e.get("key_value"):
                lines.append(f"  Key value: {e['key_value']}")
            if e.get("exemptions") and e["exemptions"] != "None":
                lines.append(f"  Exemptions: {e['exemptions']}")
            if e.get("citation"):
                lines.append(f"  Citation: {e['citation']}")
            known = [
                x
                for x in ALIASES.get(e["id"], [])
                if re.search(r"[a-z]", x) and not re.fullmatch(r"[\d.:-]+[a-z]?", x)
            ]
            if known:  # so "AB 1482" or "the FAIR Act" in a question is recognised as this rule
                lines.append(f"  Also known as: {', '.join(known[:5])}")
            if e.get("effective_date"):
                lines.append(f"  Effective date: {e['effective_date']}")
            cve = e.get("current_version_effective")
            if cve and as_of and as_of < str(cve) and e.get("status") == "in_force":
                lines.append(
                    f"  Version note: this text is the version in force from {cve}; the version in force on"
                    f" the as-of date may say something different."
                )
            if e.get("penalty"):
                lines.append(f"  Penalty: {str(e['penalty'])[:240]}")
            plain = (FALLBACK_PLAIN.get(e["id"]) or {}).get("en")
            if plain:
                lines.append(f"  Reviewed plain reading (use it): {plain}")
            if e.get("effective_date_note"):
                lines.append(f"  What changed when: {str(e['effective_date_note'])[:300]}")
            if e.get("interaction") and e["interaction"] != "None":
                lines.append(f"  How it relates to other rules: {e['interaction'][:260]}")
            for rel in relations.get(e["id"], []):
                lines.append(f"  Relationship: {rel}")
            if e.get("conflict_note"):
                lines.append(f"  Conflict note: {e['conflict_note'][:300]}")
        hd = H.HEADLINES.get(e["id"]) or {}
        per = H.period_of(hd, as_of) if hasattr(H, "period_of") else "in"
        if per == "after":
            lines.append(
                f"  NOTE: the figure above is for a period that ended {hd.get('until')}. It is NOT the current figure,"
                " and the current figure is not in the sources: never call it current."
            )
        elif per == "before":
            lines.append(
                f"  NOTE: the figure above applies only from {hd.get('from')}; on the as-of date it did not apply yet,"
                " and the figure for that date is not in the sources. Say so first."
            )
        if e.get("quoted_span"):
            quote = re.sub(r"\s+", " ", e["quoted_span"])[:420]
            lines.append(f'  Verbatim quote: "{quote}"')
        if e.get("engine"):
            g = e["engine"]
            verdict = {
                "applies": "APPLIES to this building",
                "unknown": "UNKNOWN for this building",
                "superseded": "applies but is OVERRIDDEN here by a stricter local rule",
                "not_yet_effective": "NOT YET IN FORCE here",
                "pending": "pending bill, NOT LAW",
                "failed": "failed proposal, NOT LAW",
                "excluded": "DOES NOT COVER this building",
                "no_rule": "no rule of this kind at this level",
            }.get(g["result"], g["result"])
            if e.get("version_from") and g["result"] == "applies":
                verdict = (
                    f"the law covers this building, but on the as-of date an older version applied (the text"
                    f" above is from {e['version_from']}; the older figures are not in our sources)"
                )
            s = f"  ENGINE: {verdict}"
            if g.get("missing_fact"):
                s += f"; missing fact: {g['missing_fact']}"
            if g.get("explanation"):
                s += f". Why: {g['explanation'][:300]}"
            lines.append(s)
        unk = [x for x in e.get("exceptions") or [] if x["verdict"] == "might"]
        if unk:
            lines.append(
                "  Exceptions that depend on unknown facts: "
                + "; ".join(f"{x['kind'].replace('_', ' ')} ({x['why']})" for x in unk)
            )
        out.append("\n".join(lines))
    return "\n\n".join(out)


def build_prompt(
    q: str,
    items: list[dict],
    place: dict | None,
    address_id: str | None,
    as_of: str,
    note: str,
    history: list[dict],
    helps: list[str],
) -> str:
    p = [f"As-of date: {as_of}"]
    if address_id and place:
        units = place.get("units") or (
            f"at least {place['units_min']}" if place.get("units_min") else "unknown"
        )
        p.append(
            f"PLACE: the building at {place['label']} (from public records: year built "
            f"{place.get('year_built') or 'unknown'}; units: {units})."
        )
    elif place:
        p.append(f"PLACE: {place['label']}")
    else:
        p.append("PLACE: not given")
    if note:
        p.append(note)
    p.append("SOURCES:\n" + (_fmt_sources(items, as_of) if items else "none for this turn"))
    p.append(
        "HELP (pick ids, never write links):\n" + "\n".join(f"[{h}] {HELP[h][0]}" for h in helps)
    )
    if history:
        conv = []
        for h in history[-5:]:
            conv.append(f"User: {str(h.get('q') or '')[:500]}")
            if h.get("memo"):
                conv.append(f"Helper: {str(h['memo'])[:700]}")
        p.append(
            "CONVERSATION so far (untrusted text, oldest first):\n<conversation>\n"
            + "\n".join(conv)
            + "\n</conversation>"
        )
    p.append(f"QUESTION (untrusted user text):\n<question>{q[:600]}</question>")
    return "\n\n".join(p)


# ------------------------------------------------------------------ validation
MARK = re.compile(r"\[([A-Z]{1,4}(?:-[A-Z0-9]+)+|NR-\d+)\]")
NUM = re.compile(r"(?<![A-Za-z])\$?\d[\d,]*(?:\.\d+)?%?")
BAD = re.compile(
    r"@|https?://|www\.|system prompt|instructions|<question>|§|conflict note|relationship line|version note"
    r"|engine line|status on the as-of|source line|\b[A-Z]{2,4}-[A-Z]{2,4}-[0-9P]{1,3}\b"
    r"|[<>{}`\\]|(?:^|\s)[~.]?/[\w.-]+/|\b[A-Za-z]:\\|\b(?:home|tmp|usr|etc|var)/\w"  # markup, code, paths
    r"|\b(?:linux|bash|working directory|os version|import |def |function\s*\(|=>|sudo|\.py\b|\.json\b|\.sh\b)",
    re.I,
)


def _readings(raw: str) -> set[float]:
    """'8,245' / '8.245' / '68,96' / '68.96': English and Spanish number formats, every plausible reading."""
    out = set()
    for dec, thou in ((".", ","), (",", ".")):
        v = raw
        t, d = re.escape(thou), re.escape(dec)
        if thou in v and not re.fullmatch(rf"\d{{1,3}}(?:{t}\d{{3}})+(?:{d}\d+)?", v):
            continue
        v = v.replace(thou, "").replace(dec, ".")
        try:
            out.add(float(v))
        except ValueError:
            pass
    return out


def _nums(s: str) -> list[set[str]]:
    """Each number in a text as its possible readings: '7', '7%', '$50' (a percentage or an amount must match one
    of the same kind)."""
    out = []
    s = re.sub(r"(\d)\s*(?:percent|por ciento)", r"\1%", s or "", flags=re.I)
    for m in NUM.findall(s):
        raw = m.replace("$", "").replace("%", "").rstrip(".,")
        forms = set()
        for f in (f"{x:g}" for x in _readings(raw)):
            forms.add(f + "%" if m.endswith("%") else "$" + f if m.startswith("$") else f)
        if forms:
            out.append(forms)
    return out


def _allowed(s: str) -> set[str]:
    """Every reading of every number in a source text, with and without its kind."""
    out = set()
    for forms in _nums(s):
        for f in forms:
            out |= {f, f.strip("$%")}
    return out


def _grounded_nums(text: str, allowed: set[str]) -> bool:
    return all(forms & allowed for forms in _nums(text))


def _split_sentences(s: str) -> list[str]:
    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-Z¿¡ÁÉÍÓÚÑ\"“])|(?<=\])\s+(?=[A-Z¿¡ÁÉÍÓÚÑ])", (s or "").strip()
    )
    return [p.strip() for p in parts if p.strip()]


LEGAL_CLAIM = re.compile(
    r"\b(?:must|may not|can't|cannot|can not|illegal|not allowed|is allowed|are allowed|required|entitled|has to"
    r"|have to|prohibit\w*|banned|bans|caps?|limits?|allows?|allowed|permit\w*|no puede|no pueden|debe|deben|prohíb\w*|prohib\w*"
    r"|tiene derecho|tienen derecho|tiene que|tienen que|límite|tope)\b",
    re.I,
)
_ID = r"(?:[A-Z]{1,4}(?:-[A-Z0-9]+)+|NR-\d+)"
CITE_WORDS = re.compile(r",?\s*\(?\bcites?:?\s*" + _ID + r"(?:\s*(?:,|and)\s*" + _ID + r")*\)?")
# The brief: the solution must not suggest ways to avoid, structure around or evade a rule.
EVASION = re.compile(
    r"\b(?:get(?:ting)? around|work(?:ing)? around|loopholes?|evade|evading|bypass\w*|circumvent\w*|sidestep\w*"
    r"|skirt(?:ing)? (?:the )?(?:law|rules?)|exploit\w*|trick\w*"
    r"|\bavoid\w*\b.{0,40}\b(?:rent control|rent cap|cap|limit|rules?|law|just cause|ordinance|registration"
    r"|relocation|paying (?:the )?interest|returning (?:the )?deposit)"
    r"|(?:how (?:do|can|could|should|would) (?:i|we)|(?:a |any |is there a )?ways? (?:to|for me to|i can))\b.{0,25}"
    r"\b(?:raise|increase|hike|charge|set|get)\w*\b.{0,30}\b(?:above|over|beyond|past|higher than|more than|around)"
    r" (?:the )?(?:cap|limit|maximum|max|allowed|allowable|legal|ordinance|rent control)"
    r"|(?:get|make|qualify)\w* (?:my |the |our )?(?:building|unit|units|property|apartment|place)s? (?:to be )?exempt"
    r"|(?:out of|outside(?: of)?|escape) (?:the )?(?:rent control|rent cap|rent ordinance|cap|just cause)"
    r"|without (?:having to )?pay(?:ing)? (?:the )?(?:relocation|interest)"
    r"|convert\w*\b.{0,40}\bcondo\w*\b.{0,40}\b(?:get out|avoid|escape|out of|around)|get out of\b.{0,30}\b(?:rent control|rent cap|ordinance|just cause)"
    r"|keep\w*\b.{0,30}\bdeposit\b.{0,60}\bwithout\b.{0,40}\b(?:fight|challenge|sue|contest|complain)"
    r"|without (?:them|the tenant|my tenant|tenants) (?:being able to )?(?:fight|challenge|sue|contest)"
    r"|how (?:do|can|could|should) (?:i|we) evict\b.*\bwithout\b"
    r"|evict\w* (?:someone|a tenant|my tenant|tenants|them|him|her) without (?:a )?(?:just |good )?(?:cause|reason)"
    r"|keep (?:the|their|his|her|a) (?:security )?deposit\b.*\b(?:anyway|regardless|even (?:if|though)|no matter)"
    r"|screen(?:ing)? out\b|weed(?:ing)? out\b|refuse (?:vouchers|section 8)\b.*\bwithout\b"
    r"|esquivar|eludir|evadir|c[oó]mo (?:puedo |podemos |se puede )?evitar\b|saltar(?:me|se|nos)? (?:la ley|las reglas|el control)|resquicio|truco"
    r"|(?:para|y) evitar (?:el|la|los|las) (?:control|tope|límite|limite|ley|reglas?)"
    r"|c[oó]mo (?:puedo|podemos|se puede)\b.{0,15}\b(?:subir|aumentar|cobrar)\w*\b.{0,30}\b(?:por encima|más (?:alto )?(?:que|del)|sobre) (?:el |del )?(?:tope|límite|limite|máximo))",
    re.I,
)
COMPLIANCE = re.compile(
    r"\b(?:you(?:'re| are) (?:fully |legally )?(?:compliant|in compliance|safe|covered legally)|this is legal for you"
    r"|you(?:'re| are) (?:legally )?in the clear|usted cumple|est[aá] en regla)\b",
    re.I,
)
CHAT_LEGAL = re.compile(  # with no sources, the helper may say what it can help with, but state no law
    r"\b(?:sue|suing|court|judge|lawsuit|small claims|damages|penalt\w*|fine[sd]?|landlord must|tenant must"
    r"|you have the right|you have a right|demand\w*|tribunal|corte|juez|demanda\w*|multa\w*)\b",
    re.I,
)
RECALL_Q = re.compile(
    r"\bwhat (?:did|was it) (?:i|that i) (?:just )?(?:ask|asked|say|said)\b|\bwhat (?:was|were) my (?:first|last|previous|earlier|original) questions?\b"
    r"|\b(?:repeat|remind me (?:of|what)) (?:my )?(?:first |last |previous )?question\b|\bqu[eé] (?:te |le )?pregunt[eé]\b"
    r"|\bcu[aá]l (?:fue|era) mi (?:primera|[uú]ltima|anterior) pregunta\b",
    re.I,
)
HISTORY = re.compile(  # eval T13: "Before Measure BB, increases had no upper limit"
    r"^\W*(?:before|prior to|antes de)\s+(?:the |this |that |la |el )?(?:\w+\s+){0,4}?"
    r"(?:law|laws|measure|ordinance|act|bill|ley|ordenanza|medida)\b(?!\s+(?:takes|took) effect)"
    r"|^\W*(?:previously|anteriormente)\b|\bused to (?:be|have|allow|cap|limit)\b|\bno upper limit\b"
    r"|\bthere was no (?:cap|limit)\b"
    r"|(?:^|[.!?]\s+)\W*(?:before|previously|until then|antes)\s*,|\bno (?:hard |upper |fixed )?(?:ceiling|cap|limit) before\b"
    r"|(?:^|[.!?]\s+)\W*previously\b",  # 'Before, there was no hard ceiling' (eval T13, round 16)
    re.I,
)
_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
EN_RANGE = re.compile(  # "October 1, 2026 through August 31, 2027"
    rf"\b({_MONTHS})\.? (\d{{1,2}}),? (\d{{4}}) (?:through|to|until|[-–])\s*({_MONTHS})\.? (\d{{1,2}}),? (\d{{4}})\b",
    re.I,
)
SRC_RANGE = re.compile(  # "9/1/2026 through 8/31/2027", "3/1/2026–2/28/2027" in the rule texts
    r"\b(\d{1,2})/(\d{1,2})/(\d{4})\s*(?:through|to|-|–)\s*(\d{1,2})/(\d{1,2})/(\d{4})\b"
)


def _src_ranges(src: str) -> list[tuple[str, str]]:
    out = [
        (f"{m[2]}-{int(m[0]):02d}-{int(m[1]):02d}", f"{m[5]}-{int(m[3]):02d}-{int(m[4]):02d}")
        for m in SRC_RANGE.findall(src)
    ]
    for m in EN_RANGE.findall(src):
        a = _MONTHS.split("|").index(m[0].lower()) + 1
        b = _MONTHS.split("|").index(m[3].lower()) + 1
        out.append((f"{m[2]}-{a:02d}-{int(m[1]):02d}", f"{m[5]}-{b:02d}-{int(m[4]):02d}"))
    return out


def fix_ranges(text: str, src: str) -> str:
    """A date range the rule doesn't give, but one end matches the rule's period: the rule's period (eval DM4:
    'starting October 2026' leaked into Santa Ana's 9/1/2026-8/31/2027)."""
    ranges = list(dict.fromkeys(_src_ranges(src)))
    if not ranges:
        return text

    def full(iso: str) -> str:
        y, m, d = iso.split("-")
        return f"{calendar.month_name[int(m)]} {int(d)}, {y}"

    def sub(m):
        a = _MONTHS.split("|").index(m[1].lower()) + 1
        b = _MONTHS.split("|").index(m[4].lower()) + 1
        got = (f"{m[3]}-{a:02d}-{int(m[2]):02d}", f"{m[6]}-{b:02d}-{int(m[5]):02d}")
        if got in ranges:
            return m[0]
        near = [r for r in ranges if r[0] == got[0] or r[1] == got[1]]
        return f"{full(near[0][0])} through {full(near[0][1])}" if len(near) == 1 else m[0]

    return EN_RANGE.sub(sub, text)


DATE_WORDS = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?"
    r"|\b\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?: de \d{4})?",
    re.I,
)
ES_PROCESS = {  # Spanish words for what the English source says (eval ES08: "multas" for "fines")
    "multa": ("fine", "penalt"),
    "deman": ("sue", "lawsu", "suit"),
    "corte": ("court",),
    "tribu": ("court",),
    "juez": ("judge", "court"),
}
REPAIRABLE = {
    "frequency not in the source (e.g. 'once a year' for a 12-month total)",
    "per-increase cap not in the source (the cap is on the total)",
}
THRESH = re.compile(
    r"\b(?:(\d+) or more units|(\d+)\+ units|at least (\d+) units|(\d+) units or more|(\d+) o m[aá]s unidades)\b",
    re.I,
)
FREQ = re.compile(
    r"\bonce (?:a|per|every|each) (?:year|12[- ]months?|twelve months)|\bfor two years\b|\bone (?:increase|raise) (?:a|per|each) year|\buna vez al a[nñ]o",
    re.I,
)
EACH_INC = re.compile(r"\b(?:each|every|per) (?:increase|raise)\b|\bcada aumento\b", re.I)
NO_LIMIT = re.compile(
    r"\bno (?:rent )?(?:limit|cap|ceiling|rent control|protections?)\b|\bunlimited\b|\bsin (?:l[ií]mite|tope)\b",
    re.I,
)
STATE_WORD = re.compile(
    r"\b(?:state|statewide|california|new jersey|massachusetts|estatal|estado)\b", re.I
)
QUALIFIER = re.compile(
    r"\b(?:unless|outside|not covered|isn't covered|aren't covered|not under|doesn't cover|does not cover|doesn't apply"
    r"|does not apply|salvo|fuera|no cubiert\w*|no cubre)\b",
    re.I,
)
CONDITION = re.compile(
    r"\b(still owes?|even if|only if|as long as|provided that|unless|aun si|a menos que|solo si|siempre que)\b(.{0,90})",
    re.I,
)
NOT_COVERED = re.compile(
    r"\b(?:not be covered|wouldn't be covered|would be allowed|would not apply|wouldn't apply|does not ban|doesn't ban"
    r"|do not ban|don't ban|does not prohibit|doesn't prohibit|not covered|does not apply|doesn't apply|do not apply|don't apply|is exempt|are exempt|exempt from|is allowed|are allowed|not banned|isn't banned|no cubre|no aplica|exent[oa])\b",
    re.I,
)
SCOPE_OUT = re.compile(
    r"\b(?:not be covered|wouldn't be covered|not covered|does not ban|doesn't ban|do not ban|don't ban"
    r"|does not prohibit|doesn't prohibit|would not apply|wouldn't apply|does not apply|doesn't apply|do not apply"
    r"|don't apply|no cubre|no aplica|no prohíbe|no prohibe)\b",
    re.I,
)
FREQ_FIX = re.compile(
    r"\bonce (?:a|per|every|each) (?:year|12[- ]months?|twelve months)\b|\buna vez al a[nñ]o\b",
    re.I,
)
TWICE_YEAR = re.compile(
    r"\b(?:once or twice|up to twice|at most twice|twice|two times) (?:a|per|each|every|in a) (?:year|calendar year)\b"
    r"|\b(?:una o dos veces|hasta dos veces|dos veces) al a[nñ]o\b",
    re.I,
)
FUTURE_Q = re.compile(r"\b(?:will|going to|gonna)\b|\b(?:aplicar[aá]|estar[aá]|ser[aá])\b", re.I)
LOCKOUT = re.compile(r"\b(?:locks?|lockouts?|locked out|cerraduras?|cerrojos?)\b")  # folded text
UTILITY = re.compile(  # folded text
    r"\b(?:water|heat|heating|electricity|electric|gas|utilit(?:y|ies)|essential services|agua|luz|calefaccion"
    r"|electricidad|servicios (?:basicos|esenciales|publicos))\b"
)
CANT_CHANGE = re.compile(
    r"\b(?:cannot|can't|can not|may not|must not|no puede|no se puede) (?:be|ser) (rais\w*|increas\w*|chang\w*|aument\w*|cambi\w*)\b",
    re.I,
)
NO_REASON = re.compile(
    r"\b(?:no (?:stated |given )?reason (?:is |being )?(?:required|needed|necessary)|(?<!not )without (?:a |any |giving a )?(?:reason|cause)"
    r"|for any reason|sin (?:dar )?(?:una |ninguna )?(?:raz[oó]n|causa))\b",
    re.I,
)
SETS_FIGURE = re.compile(  # a board's page lists the CPI-adjusted figure; the statute sets it (CA-FEE-01 conflict note)
    r"\b(Rent Board|Rent Stabilization Board)\s+(?:sets|has set|set|establishes|determines)\b"
)
SETTLED = re.compile(  # a preemption the sources leave open ("may preempt ... flagged for review"), stated as decided
    r"\b(?:now sets the rules|now governs|now controls|replaces?|replaced|overrides?|overrode|preempts?|preempted"
    r"|supersedes?|superseded|takes precedence|reemplaza|anula|prevalece)\b",
    re.I,
)
OPEN_Q = re.compile(
    r"\bwhether\b|\bnot (?:yet )?(?:been )?(?:decided|settled|resolved|clear)\b|\bundecided\b|\bunclear\b|\bopen question\b"
    r"|\bno (?:est[aá]|se ha) (?:decidido|resuelto)\b|\bsi\b.{0,40}\b(?:reemplaza|anula|prevalece)",
    re.I,
)
HEDGE = re.compile(r"\b(?:may|might|could|can|podr[ií]a|puede)\b(?:\s+\w+){0,2}\s*$", re.I)
NEW_TENANCY = re.compile(  # 1947.12(d): only the first rent of a new tenancy is free, the cap still covers it later
    r"\b(?:(?:the )?(?:initial|first|starting) rent (?:on|of|for|in|under) (?:a |the )?)?(?:new tenanc(?:y|ies)|new leases?)\b",
    re.I,
)
BECOMES = re.compile(
    r"\b(?:will become law|becomes law|will become a law|se convertir[aá] en ley|se convierte en ley|ser[aá] ley)\b",
    re.I,
)
TAKES = {
    "will become law": "will take effect",
    "becomes law": "takes effect",
    "will become a law": "will take effect",
    "se convertirá en ley": "entrará en vigor",
    "se convertira en ley": "entrará en vigor",
    "se convierte en ley": "entra en vigor",
    "será ley": "entrará en vigor",
    "sera ley": "entrará en vigor",
}
BECAME_ON = re.compile(  # "became law on July 1, 2027": that is the start date, not the enactment
    r"\b(?:became|becomes|will become|was passed|was enacted|was signed(?: into law)?)(?: a)?(?: law)? (on|in|from) ",
    re.I,
)
NONPAY_SCOPE = re.compile(
    r"\b(notices? to quit)\b(?![^.]{0,40}\b(?:nonpayment|non-payment|unpaid|not paying))", re.I
)
REDUCED = re.compile(r"\breduced (?:amounts?|relocation|payments?)\b", re.I)
PASSING = re.compile(
    r"\b(?:is (?:being )?passing|being passed|being considered|is proposed|proposed law|is coming|will pass|en tr[aá]mite|propuesta de ley)\b",
    re.I,
)
NOW_WORD = re.compile(
    r"\b(?:current|currently|now|this year|today|right now|actual|actualmente|ahora|este a[nñ]o|hoy)\b",
    re.I,
)
PAST_WORD = re.compile(
    r"\b(?:was|were|until|ended|through|previous|last period|that period|fue|era|hasta|termin\w*)\b",
    re.I,
)
OFFICE = re.compile(
    r"\b(?:housing authority|court clerk|clerk|city hall|website|web site|tribunal|police|911|sheriff|marshal"
    r"|autoridad de vivienda|sitio web|ayuntamiento|polic[ií]a)\b",
    re.I,
)
POLICE = re.compile(r"\b(?:police|polic[ií]a|911|sheriff)\b", re.I)
CONTEXT_GENERIC = set(
    tokens(
        "month months rent rents deposit deposits security max maximum cap caps capped limit limits up to per times time "
        "percent landlord landlords tenant tenants may not can cannot must the a an of for and or more than less no at most "
        "least amount equal one two renta mes meses depósito deposito máximo maximo"
    )
)
DOMAIN = set(
    tokens(
        "rent rents landlord landlords tenant tenants law laws rule rules unit units building buildings ban bans banned "
        "california jersey massachusetts city state local covered cover apply applies allowed exempt software device devices "
        "francisco angeles diego berkeley boston cambridge hoboken newark santa jersey ordinance pay owe money notice "
        "renta inquilino casero ley norma unidad edificio"
    )
)
NOT_THEN = ("not_yet_effective", "pending", "failed", "older_version", "repealed")
TIME_WORDS = re.compile(
    r"\b(?:not|n't|no longer|yet|until|from|starts?|started|begins?|began|took effect|takes effect|will|later|after"
    r"|before|since|didn't|wasn't|pending|proposal|bill|failed|aún|todavía|desde|a partir|hasta|entra|entró|no)\b",
    re.I,
)
ENGINE_NEG = {"excluded", "superseded", "failed", "pending", "not_yet_effective", "no_rule"}
APPLIES_WORD = re.compile(
    r"\b(?:applies|apply|covers|covered|protects|protected|aplica|aplican|cubre|protege)\b", re.I
)
NEGATION = re.compile(r"\b(?:not|doesn't|does not|don't|isn't|won't|no|never|nunca)\b", re.I)


def validate(
    out: dict,
    items: list[dict],
    q: str,
    as_of: str,
    lang: str,
    extra: str = "",
    *,
    address: bool = False,
    partial: bool = False,
    chat: bool = False,
    city: str | None = None,
    scope_local: bool = False,
) -> dict:
    """Keep only what the retrieved sources support (Isaac 2026-10-04: the model talks, the guardrails stay):
    - cited ids must be in the retrieved set; a sentence stating the law needs a valid citation;
    - every number in a sentence must appear in the sources (or the question), else the sentence goes;
    - at an address, no sentence may say a rule applies that the engine ruled out;
    - no markup, code, paths, links or e-mail addresses anywhere."""
    by_id = {e["id"]: e for e in items}
    allowed = (
        _allowed(q)
        | _allowed(as_of.replace("-", " "))
        | _allowed(extra)
        | _allowed(fmt_date(as_of, lang))
        | _allowed(
            f"{calendar.month_name[int(as_of[5:7])]} {int(as_of[8:10])}, {as_of[:4]}"
        )  # "the figure for July 1, 2026" (eval DT04)
    )
    for e in items:
        allowed |= _allowed(
            " ".join(
                str(e.get(k) or "")
                for k in (
                    "requirement_en",
                    "requirement",
                    "key_value",
                    "quoted_span",
                    "exemptions",
                    "citation",
                    "title_en",
                    "effective_date",
                    "penalty",
                    "interaction",
                    "coverage_conditions",
                )
            )
        )
        for k in ("effective_date", "sunset_date", "version_from"):
            d = str(e.get(k) or "")[:10]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                allowed |= _allowed(fmt_date(d, lang))
        if e.get("engine"):
            allowed |= _allowed(e["engine"].get("explanation", ""))
    order: list[str] = []

    def use(ids):
        for i in ids:
            if i not in order:
                order.append(i)

    def ruled_out(
        text: str, ids: list[str]
    ) -> bool:  # mentions an exception the building facts exclude
        return any(
            re.search(x["pattern"], text, re.I)
            for i in ids
            for x in by_id[i].get("exceptions") or []
            if x["verdict"] == "cannot"
        )

    dropped: list[dict] = []  # for the audit log: what the validator removed and why

    def why_not(
        text: str, ids: list[str], question_ok: bool = False, strict: bool = False
    ) -> str | None:
        if not text:
            return "empty"
        if BAD.search(text):
            return "unsafe text (markup, code, path, link, e-mail, internal names)"
        if len(text) > 600:
            return "too long"
        if COMPLIANCE.search(text):
            return "reads as a compliance verdict"
        if EVASION.search(text):
            return "suggests a way around a rule"
        if not _grounded_nums(text, allowed):
            return "number not in the sources"
        if ids and not context_ok(text, ids):
            return "number used outside the context the source gives it"
        if ids and ruled_out(text, ids):
            return "exception the building facts rule out"
        if (
            not ids
        ):  # no citation: only talk, questions and practical advice, never the law or a figure
            if question_ok and text.rstrip().endswith("?"):
                return None
            if [
                f
                for f in _nums(text)
                if not (f & allowed and any(re.fullmatch(r"(?:19|20)\d\d", x) for x in f))
            ]:
                return "uncited figure"
            if POLICE.search(
                text
            ):  # 'habla con la policía' (eval ES06): no source names the police
                return "office or place not named in the cited source"
            if OFFICE.search(text) and not re.search(
                r"legal aid|ayuda legal|asistencia legal", fold(text)
            ):
                return "office or place not named in the cited source"
            if chat and (LEGAL_CLAIM.search(text) or CHAT_LEGAL.search(text)):
                return "legal content without sources"
            if chat:  # no sources this turn: talk is fine, statements of law are not
                return (
                    "uncited legal claim"
                    if re.search(r"\b(?:illegal|legal|the law|ley)\b", text, re.I)
                    else None
                )
            return "uncited legal claim" if LEGAL_CLAIM.search(text) else None
        if ids and all(by_id[i].get("status") in NOT_THEN for i in ids):
            if not TIME_WORDS.search(text) and (
                strict
                or not (set(ids) & qualified)
                or (
                    re.search(r"\b(?:capped|limited|was|were|had|allowed|required)\b", text)
                    and not NEGATION.search(text)
                )
            ):  # "California law capped deposits at one month's rent" for 2023 (eval DT05)
                return "rule not in force on the as-of date stated as applying"
        if address and all((by_id[i].get("engine") or {}).get("result") in ENGINE_NEG for i in ids):
            if any(  # per sentence: "it would normally be covered. However ... does not qualify" is not a no
                APPLIES_WORD.search(x)
                and not NEGATION.search(x)
                and not re.search(
                    r"\b(?:only|solo|s[oó]lamente)\b", x, re.I
                )  # "covers only buildings before 1979"
                for x in _split_sentences(text)
            ):
                return "contradicts the rules engine"
        return drift(text, ids)

    def full_src(ids: list[str]) -> str:
        return " ".join(
            str(by_id[i].get(k) or "")
            for i in ids
            for k in (
                "requirement_en",
                "key_value",
                "quoted_span",
                "exemptions",
                "coverage_conditions",
                "interaction",
                "penalty",
                "title_en",
                "conflict_note",
            )
        )

    def overlap(words: str, ids: list[str], skip: set, keys: tuple | None = None) -> float:
        w = [t for t in tokens(words) if len(t) > 3 and t not in skip]
        if not w:
            return 1.0
        src = set(
            tokens(
                full_src(ids)
                if keys is None
                else " ".join(str(by_id[i].get(k) or "") for i in ids for k in keys)
            )
        )
        return sum(1 for t in w if t in src) / len(w)

    def freq_unsupported(text: str, ids: list[str]) -> bool:
        if not FREQ.search(text):
            return False
        pct_forms = [f for f in _nums(text) if any("%" in x for x in f)]
        fig = [  # the rules the sentence's figures come from: "once" in another city's rule doesn't support it
            i
            for i in ids
            if pct_forms
            and all({x for x in f if "%" in x} & _allowed(full_src([i])) for f in pct_forms)
        ]
        return not any(w in fold(full_src(fig or ids)) for w in ("once", "una vez"))

    def fix_freq(text: str, ids: list[str]) -> str:
        """'5% plus inflation or 10% ... once per 12 months': the cap is a 12-month total, say so."""
        if re.search(
            r"\btwo increases\b", full_src(ids)
        ):  # 'not ... more than once a year' (eval R02, round 22)
            text = " ".join(
                x
                for x in _split_sentences(text)
                if not re.search(
                    r"\bmore than once (?:a|per|every|each) (?:year|12[- ]months?|twelve months)\b",
                    x,
                    re.I,
                )
            )
        if TWICE_YEAR.search(text) and re.search(r"\b12[- ]month", full_src(ids)):
            text = TWICE_YEAR.sub(  # "once or twice per year": the source counts over any 12 months (eval R01)
                "in up to two increases over any 12 months"
                if lang == "en"
                else "en hasta dos aumentos en cualquier periodo de 12 meses",
                text,
            )
        if FREQ_FIX.search(text) and freq_unsupported(text, ids):
            if re.search(r"\b12[- ]month|\b12 months|\b12 meses", full_src(ids)):
                text = FREQ_FIX.sub(
                    "in total over any 12 months" if lang == "en" else "en total en 12 meses", text
                )
            else:  # the rule gives a period, not a 12-month count: no frequency at all (eval MT5)
                text = re.sub(r",?\s*(?:" + FREQ_FIX.pattern + ")", "", text, flags=re.I)
        return text

    def drift(text: str, ids: list[str]) -> str | None:
        for m in THRESH.finditer(
            text
        ):  # "covers buildings with 5 or more units": the rule's threshold, not the building's count
            n = next(g for g in m.groups() if g)
            if f"{float(n):g}" not in src_forms:
                return "coverage threshold not in the rule or the engine"
        """Wording the eval found drifting from the sources: frequency, per-increase caps, 'no limit' where a state
        rule still applies, a state figure for a city whose own rule governs, invented conditions or exemptions,
        'proposed' for enacted law, an expired figure called current, offices the source doesn't name."""
        src = fold(full_src(ids))
        tenure = re.search(r"\b(?:12|twelve)\+? months\b|\b(?:one|a) year\b", text, re.I)
        if tenure and city:
            for e in [by_id[i] for i in ids]:
                if (
                    e.get("jurisdiction") == city
                    and not re.search(
                        r"\b(?:12|twelve)[- ]months?\b|\bone year\b", full_src([e["id"]]), re.I
                    )
                    and any(  # the state rule it overrides, cited or not (AD11, round 17)
                        (by_id.get(j) or {}).get("level") == "state"
                        for j in (e.get("overrides") or [])
                    )
                ):  # 'after 12 months' is the state's condition; the city's own rule governs (eval MT3)
                    return "a state rule's tenure condition given for a city whose own rule governs"
        units = re.search(
            r"\b(?:your|this|the) building\b[^.]{0,60}?\b(?:fewer|less|more) than (\d+) units",
            text,
            re.I,
        )
        if (
            address
            and units
            and f"{units[1]} units"
            not in " ".join(str((e.get("engine") or {}).get("explanation") or "") for e in items)
        ):
            return "a unit count for the building that the records don't give"  # eval AD05
        if (
            ids
            and "%" in text
            and re.search(
                r"\brent increases?\b|\baumentos? (?:de|del) (?:alquiler|renta)\b", text, re.I
            )
            and all(by_id[i].get("category") == "security_deposits" for i in ids)
        ):  # the deposit's 10% yearly increase limit is not a rent cap (eval MT6, round 23)
            return "a rent cap taken from a deposit rule"
        if LOCKOUT.search(fold(text)) and not (LOCKOUT.search(src) or "self-help" in src):
            return "lockout claim the cited rule doesn't make"  # eval ES06, round 22
        if UTILITY.search(fold(text)) and not (UTILITY.search(src) or "self-help" in src):
            return "service (water, heat ...) the cited rule doesn't mention"  # eval SA03
        cant = CANT_CHANGE.search(text)
        stem = cant.group(1)[:4].lower() if cant else ""
        if cant and not any(
            x in src for x in {"aume": ("increas", "rais"), "camb": ("chang",)}.get(stem, (stem,))
        ):
            return "'cannot be raised/changed' not in the cited source"  # eval IN04
        if freq_unsupported(text, ids):
            return "frequency not in the source (e.g. 'once a year' for a 12-month total)"
        if EACH_INC.search(text) and not re.search(r"\b(?:each|per|every) (?:increase|raise)", src):
            return "per-increase cap not in the source (the cap is on the total)"
        if NO_LIMIT.search(text) and not STATE_WORD.search(text):
            cats_here = {by_id[i].get("category") for i in ids} or {
                e.get("category") for e in items
            }
            if any(
                e.get("level") == "state"
                and e.get("status") == "in_force"
                and not re.search(r"\bbar on\b", str(e.get("key_value") or ""), re.I)
                and e.get("category") in cats_here
                and (e.get("engine") or {}).get("result") not in ("excluded", "superseded")
                for e in items
            ):
                return "'no limit' where a state rule may still apply"
        if (
            city
            and ids
            and all(by_id[i].get("level") == "state" for i in ids)
            and not QUALIFIER.search(text)
        ):
            for i in ids:
                for e in items:
                    if (
                        e.get("jurisdiction") == city
                        and e.get("status") == "in_force"
                        and e.get("category") == by_id[i].get("category")
                        and (
                            i in (e.get("overrides") or [])
                            or e["id"] in (by_id[i].get("overrides") or [])
                        )
                        and (by_id[i].get("yields_to_local") or e.get("supersedes_state"))
                        and (e.get("engine") or {}).get("result")
                        != "excluded"  # built after the city's cutoff
                    ):
                        return "state figure given for a city whose own rule governs"
        for m in CONDITION.finditer(text):
            if overlap(m.group(2), ids, DOMAIN) < 0.5:
                return "condition not in the cited source"
        nc = NOT_COVERED.search(text)
        sc = SCOPE_OUT.search(text)
        scoped = [
            i for i in ids if by_id[i].get("exemptions") or by_id[i].get("coverage_conditions")
        ]
        claim = (
            next((x for x in re.split(r"(?<=[.;!?])\s+", text) if NOT_COVERED.search(x)), text)
            if nc
            else text
        )
        related = any(
            by_id[a].get("level") == "state"
            and by_id[b].get("level") != "state"
            and (a in (by_id[b].get("overrides") or []) or b in (by_id[a].get("overrides") or []))
            for a in ids
            for b in ids
        )  # "the state cap does not apply to RSO units": the rules' own relationship says so (eval T09)
        if (
            nc
            and not (related and STATE_WORD.search(claim))
            and (
                overlap(claim, ids, DOMAIN) < 0.5
                or (  # what it says is outside the rule must be in the rule's own exemptions or coverage
                    sc
                    and scoped
                    and overlap(
                        re.split(r"(?<=[.;])\s", text[sc.end() :])[0],
                        scoped,
                        DOMAIN,
                        ("exemptions", "coverage_conditions", "requirement_en"),
                    )
                    < 0.34
                )
            )
        ):
            return "exemption or 'not covered' claim not in the cited source"
        red = REDUCED.search(text)
        if red:  # "Reduced amounts apply for: X, Y, Z" must list what the source lists with "reduced" (eval E03)
            segs = [
                g
                for i in ids
                for k in ("requirement_en", "exemptions", "key_value")
                for g in re.split(r"[;.]\s", str(by_id[i].get(k) or ""))
                if re.search(r"\breduc", g, re.I)
            ]
            w = [t for t in tokens(text[red.start() :]) if len(t) > 3 and t not in DOMAIN]
            have = set(tokens(" ".join(segs)))
            if w and sum(t in have for t in w) / len(w) < 0.7:
                return "list of reduced cases not in the cited source"
        for m in re.finditer(
            r"\b(felon\w*|misdemeanou?r\w*|delito grave|delito menor)\b", text, re.I
        ):
            if m.group(1).lower()[:5] not in src:  # NJ grades crimes by degree (eval S04)
                return "crime class not in the cited source"
        if HISTORY.search(text) and overlap(text, ids, DOMAIN, ("effective_date_note",)) < 0.5:
            return "claim about the law before this rule that no cited source makes"
        if NO_REASON.search(text) and not re.search(r"\b(?:reason|cause|causa|raz[oó]n)", src):
            return "'no reason needed' not in the cited source"
        if any(by_id[i].get("conflict_note") for i in ids):
            for m in SETTLED.finditer(text):
                sent = next(
                    (x for x in _split_sentences(text) if m.group(0) in x), text
                )  # "Whether one overrides the other is not decided." leaves it open (eval T06)
                if not HEDGE.search(text[: m.start()]) and not OPEN_Q.search(sent):
                    return "decides a conflict the sources leave open"
        if PASSING.search(text) and all(
            by_id[i].get("status") in ("in_force", "not_yet_effective", "older_version")
            for i in ids
        ):
            return "enacted law described as proposed"
        exp = set()
        for i in ids:
            if i in expired:
                exp |= expired[i]
        if (
            exp
            and any(forms & exp for forms in _nums(text))
            and not PAST_WORD.search(text)
            and not any(int(y) < int(as_of[:4]) for y in re.findall(r"\b((?:19|20)\d\d)\b", text))
        ):
            return "figure of a period that has ended called current"
        if POLICE.search(text) and not POLICE.search(src):
            return "office or place not named in the cited source"
        for m in OFFICE.finditer(text):
            term = fold(m.group(0))
            if term not in src and not re.search(r"legal aid|ayuda legal", fold(text)):
                return "office or place not named in the cited source"
        return None

    q_forms = _allowed(q)

    def _counts(t: str) -> set:  # plain counts only: not %, not $
        return {
            f for forms in _nums(t) for f in forms if not any(("%" in x or "$" in x) for x in forms)
        }

    src_forms = (
        set()
    )  # counts in the rules and the engine's explanations (not the building's own unit count)
    for e in items:
        src_forms |= _counts(
            " ".join(
                str(e.get(k) or "")
                for k in (
                    "requirement_en",
                    "key_value",
                    "quoted_span",
                    "exemptions",
                    "coverage_conditions",
                )
            )
        )
        if e.get("engine"):
            src_forms |= _counts(
                re.sub(
                    r"\b(?:has|building has) (?:at least )?\d+(?: or more)? units\b(?: \([^)]*\))?"
                    r"|\b\d+(?: or more)? units \((?:assessor|use code)[^)]*\)",
                    "",
                    e["engine"].get("explanation", ""),
                )
            )

    def context_ok(text: str, ids: list[str]) -> bool:
        """A figure must come with the words the source gives it: '2.5 months' is the NJ total at lease start
        (deposit plus first month), not the deposit cap."""
        segs = []
        for i in ids:
            for k in (
                "requirement_en",
                "requirement",
                "key_value",
                "quoted_span",
                "exemptions",
                "coverage_conditions",
                "penalty",
            ):
                segs += [
                    x for x in re.split(r"[.;]\s|[()]", str(by_id[i].get(k) or "")) if x.strip()
                ]
        words = set(tokens(text))
        for forms in _nums(
            DATE_WORDS.sub(" ", text)
        ):  # "June 30, 2026" is a date, not a figure (eval T20)
            core = {f.strip("$%") for f in forms}
            if forms & q_forms or any(
                re.fullmatch(r"(?:1[89]|20)\d\d", c) or (c.isdigit() and int(c) <= 12) for c in core
            ):
                continue
            hits = [
                seg for seg in segs if any(core & {x.strip("$%") for x in f2} for f2 in _nums(seg))
            ]
            if not hits:
                continue
            ok = False
            for seg in hits:
                ctx = {
                    t for t in tokens(seg) if t not in CONTEXT_GENERIC and not re.match(r"^\d", t)
                }
                if len(ctx) < 2 or ctx & words:
                    ok = True
                    break
            if not ok:
                return False
        return True

    def base_rent(text: str, src_all: str) -> str:
        """'of the rent you were paying on Feb 28' / 'of your current rent': the source says base rent (AD03, R04)"""
        if "base rent" not in src_all:
            return text
        return re.sub(
            r"\bof (?:the rent you (?:were |are )?pa(?:ying|id|y)(?: on [A-Z][a-z]+\.? \d{1,2}, \d{4})?"
            r"|your (?:current|existing|present|monthly) rent|the current rent"
            r"|what you (?:were )?pa(?:id|y|ying)(?: before the increase| now)?)\b",  # eval MT5
            "of base rent",
            text,
        )

    def src_text(ids: list[str]) -> str:
        t = fold(
            " ".join(
                str(by_id[i].get(k) or "")
                for i in ids
                for k in ("requirement_en", "penalty", "key_value", "quoted_span", "title_en")
            )
        )
        return t + (" court" if re.search(r"\bsjc\b|\bsupreme\b", t) else "")

    def process_ok(text: str, ids: list[str]) -> bool:
        """court, sue, penalties, damages ...: only when the cited rules themselves say so"""
        said = (
            re.sub(  # "I don't have information about court decisions" states no process (eval T18)
                r"\b(?:no|any) (?:information|info|mention|record)s? (?:about|of|on)\b[^.]{0,60}"
                r"|\b(?:don't|do not|doesn't|does not) (?:have|mention|show|include)\b[^.]{0,60}",
                " ",
                text,
                flags=re.I,
            )
        )
        terms = {  # English "demand" is the source's own word ("may not demand or receive"), not "demanda" (eval D01)
            ES_PROCESS.get(t, t) if not (t == "deman" and not w.startswith("demanda")) else t
            for w in (fold(m.group(0)) for m in CHAT_LEGAL.finditer(said))
            for t in (w[:5],)
        }
        src = src_text(ids)
        return not terms or (
            bool(ids)
            and all(any(x in src for x in (t if isinstance(t, tuple) else (t,))) for t in terms)
        )

    def keep(text: str, ids: list[str], question_ok: bool = False, strict: bool = False) -> bool:
        reason = why_not(text, ids, question_ok, strict)
        if reason and text:
            dropped.append({"text": text[:200], "cites": ids, "why": reason})
        return reason is None

    def clean_list(lst, limit):
        res = []
        for x in (lst or [])[: limit + 2]:
            if isinstance(x, str):
                x = {"text": x, "cites": []}
            if not isinstance(x, dict):
                continue
            raw = str(x.get("text") or "")
            ids_in_text = re.findall(r"\b([A-Z]{1,4}(?:-[A-Z0-9]+)+|NR-\d+)\b", raw)
            text = re.sub(CITE_WORDS, "", raw)
            text = re.sub(r"\s*\([^()]*\)", "", MARK.sub("", text)).strip()
            text = re.sub(r",?\s*(?:per|see|under)?\s*\b" + _ID + r"\b", "", text).strip()
            if re.search(
                r"\b(?:a|al|to|con|call|llama|contact)\s+(?:hoy|today|ahora|now)\b|\b(?:or|o)\s+(?:hoy|today)\b"
                r"|\b(?:Call|Llama|Contact) (?:or|and|o|y)\b",
                text,
                re.I,
            ):
                dropped.append(
                    {"text": text[:200], "cites": [], "why": "a name was removed mid-sentence"}
                )
                continue  # 'Llama a hoy.' after an id was taken out (eval ES06)
            text = re.sub(r"\s+([.,;:!?])", r"\1", text)
            ids = list(
                dict.fromkeys(
                    i for i in (x.get("cites") or []) if isinstance(i, str) and i in by_id
                )
            )
            bad_ids = [i for i in (x.get("cites") or []) if isinstance(i, str) and i not in by_id]
            if bad_ids:
                dropped.append(
                    {"text": "", "cites": bad_ids, "why": "cited id not in the retrieved set"}
                )
            ids += [i for i in ids_in_text if i in by_id and i not in ids]
            text = fix_freq(_iso_dates(text, lang), ids)
            text = SETS_FIGURE.sub(r"\1 lists", text)
            src_all = full_src(ids)
            if (
                "at least" not in src_all.lower()
            ):  # "at least 5% interest": the source gives 5% or less (eval D04)
                text = re.sub(r"\bat least (?=\d[\d.,]*\s*%)", "", text)
            if "capital improvement or hardship increases" in src_all:  # JC-RENT-01 (eval R10)
                text = re.sub(
                    r"\bapply to the city for (?:any |all |a |rent )*increases?\b(?: (?:above|over|beyond|higher than) [^.;,]*)?",
                    "apply to the city for capital improvement or hardship increases",
                    text,
                )
            text = base_rent(text, src_all)
            if lang == "en":
                text = fix_ranges(text, src_all)
            here = {i for r in res for i in r["cites"]} | set(ids)
            for i in ids:  # "For those units, state law allows 5% + CPI" after a city rule the state rule yields to (R06)
                ov = [
                    o
                    for o in (by_id[i].get("overrides") or [])
                    if o != i
                    and (by_id.get(o) or {}).get("level") != "state"
                    and (o in here or (city and (by_id.get(o) or {}).get("jurisdiction") == city))
                ]  # the city's rule may sit in a part added later (the moved headline, eval R04 round 18)
                if by_id[i].get("level") == "state" and ov:
                    lbl = by_id[ov[0]].get("jurisdiction_label") or ""
                    text = re.sub(
                        r"^(?:For|In) (?:these|those|such|the covered|covered) (?:units|homes|apartments|buildings),\s*",
                        f"For units {lbl}'s law does not cover, ",
                        text,
                    )
                    text = re.sub(
                        r"^Para (?:esas|estas|dichas) (?:unidades|viviendas),\s*",
                        f"Para las unidades que no cubre la ley de {lbl}, ",
                        text,
                    )
            if (
                lang == "en" and "withdrawal needs written reasons" in src_all
            ):  # written reasons go with withdrawing an offer, not with asking early (eval S03)
                text = re.sub(
                    r"\bIf\b[^.,]*\bbefore\b[^.,]*,\s*(they must (?:give|provide) (?:you )?written reasons)",
                    r"If they withdraw an offer after the check, \1",
                    text,
                )
            for i in ids:  # the as-of date is past the start: 'has applied since', no 'once it starts' (eval DT10)
                eff = str(by_id[i].get("effective_date") or "")[:10]
                if (
                    lang == "en"
                    and re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff)
                    and as_of >= eff
                    and by_id[i].get("status") == "in_force"
                    and not FUTURE_Q.search(
                        q
                    )  # "Will it apply in August 2027?" is asked today (eval DT01)
                ):
                    mo = int(eff[5:7])
                    text = re.sub(
                        r"\b(?:starts|will start|begins|will begin|takes effect|will take effect)(?: on)? "
                        + rf"(?=(?:{calendar.month_name[mo]}|{calendar.month_abbr[mo]})\.? 0?{int(eff[8:10])},? {eff[:4]})",
                        "has applied since ",
                        text,
                        flags=re.I,
                    )
                    text = re.sub(  # "... before the state law. Once it starts, it may ..." (eval DT10, round 11)
                        r"(^|[.!?]\s+)(?:Once|When|After) (?:it|the (?:state )?law) (?:starts|takes effect|begins|goes into effect),\s*",
                        r"\1Now that it is in force, ",
                        text,
                    )
                    text = re.sub(
                        r",?\s*\b(?:once|when|after) (?:it|the (?:state )?law)? ?(?:is |it's )?(?:fully )?(?:starts|takes effect|begins|goes into effect|in effect)\b",
                        "",
                        text,
                        flags=re.I,
                    )
            if (
                lang == "en"
                and not FUTURE_Q.search(q)
                and any(
                    e.get("level") == "state"
                    and e.get("status") == "in_force"
                    and "2026-10-01" < str(e.get("effective_date") or "")[:10] <= as_of
                    for e in items
                )
            ):  # on a later as-of date the state law has started (eval DT10, round 9)
                text = re.sub(
                    r"\b(?:When|Once|After) (?:it|the (?:state )?law) (?:starts|takes effect|begins|goes into effect),\s*",
                    "Now that the state law is in force, ",
                    text,
                )
                text = re.sub(
                    r",?\s*\b(?:once|when|after) (?:it|the (?:state )?law)? ?(?:is |it's )?(?:fully )?(?:starts|takes effect|begins|goes into effect|in effect)\b",
                    "",
                    text,
                )
                text = re.sub(  # (eval DT10, round 22)
                    r",? but (?:it |the timing )?depends on where you rent(?: and when (?:the ban|the law|it) (?:takes effect|starts))?",
                    "",
                    text,
                )
            text = re.sub(  # "San Diego has no local cap higher than this": the finding says no local cap (eval DM2)
                r"\bno local (?:rent )?cap (?:(?:that is|that's|which is|that would be|which would be) )?(?:higher|lower|stricter|tighter)"
                r"(?: than (?:this|that|the state(?:'s)? (?:cap|limit)))?",
                "no local rent cap",
                text,
            )
            text = re.sub(
                r"\bno local rent cap than (?:state law|the state(?:'s)? (?:cap|law))",
                "no local rent cap",
                text,
            )
            if "owner-occupied duplex" in src_all and "owner-occupied" not in text:
                text = re.sub(r"\band duplexes\b", "and owner-occupied duplexes", text)  # eval MT4
            if re.search(r"\b12-month period\b", src_all) and re.search(r"%|\bpercent\b", text):
                text = re.sub(  # "10% per year": the cap counts over any 12 months (eval T10)
                    r"((?:%|\bpercent)[^.;]{0,30}?)\b(?:per|a) year\b",
                    r"\1over any 12 months",
                    text,
                )
                text = re.sub(r"\bcaps rent at\b", "caps rent increases at", text)
                text = re.sub(  # eval R05
                    r"\b(two|2) increases (?:per|a|each|every) year\b",
                    r"\1 increases in that period",
                    text,
                )
            if (
                "bank rate if lower" in src_all
                and re.search(r"\b5\s?%", text)
                and not re.search(r"\bbank|\bbanco", text, re.I)
            ):  # MA-DEP-01: 5% or the bank's rate if lower, in Spanish too (eval D04, MT6)
                text = re.sub(
                    r"(\b5\s?% (?:de intereses anuales|de inter[eé]s anual|annual interest|interest a year|interest))",
                    r"\1, o la tasa del banco si es menor"
                    if lang == "es"
                    else r"\1, or the bank's rate if lower",
                    text,
                    count=1,
                )
            for i in (
                ids
            ):  # Berkeley 'allows up to 5%': 5% is the formula's ceiling, 2026 is 1.0% (eval R01)
                one = full_src([i])
                cap = re.search(r"can never exceed (\d+(?:\.\d+)?)%", one)
                cur = re.search(
                    r"\bThe (\d{4}) (?:AGA|annual general adjustment|allowable increase) is (\d+(?:\.\d+)?%)",
                    one,
                )
                lbl = by_id[i].get("jurisdiction_label") or ""
                if lang == "en" and cap and cur and lbl and cur[2] not in text:
                    text = re.sub(
                        rf"(\b{re.escape(lbl)}\b[^.;]{{0,40}}?)\bup to {re.escape(cap[1])}%(?!\s*(?:plus|\+))",
                        rf"\g<1>{cur[2]} for {cur[1]} (never above {cap[1]}%)",
                        text,
                        count=1,
                    )
            text = re.sub(  # a rolling 'within the previous 15 years' anchored to the law's start date (eval AD11)
                r"\bwithin (?:the )?(?:previous |past |last )?(\d+) years before (?:[A-Z][a-z]+ \d{1,2}, \d{4}"
                r"|(?:the|this|that) (?:rule|law|ordinance) (?:started|took effect|began|was adopted|passed)|it (?:started|took effect))"
                r"|\bwithin (\d+) years of (?:the|this|that) (?:rule|law|ordinance)\b",
                lambda m: (
                    f"within the previous {m[1] or m[2]} years"
                ),  # also "within 30 years of the rule" (AD12)
                text,
            )
            if _src_ranges(
                src_all
            ):  # a period rule: an increase may start any day inside it (eval DM4, round 15)
                text = re.sub(
                    r"\b(?:must|can only|may only) take effect on\b", "can take effect from", text
                )
                text = re.sub(r"\bis only allowed (?:starting|from|on)\b", "is allowed from", text)
            for mon in [m for m in calendar.month_name[1:] if m not in src_all]:
                text = re.sub(  # "..., not October 1": never 'correct' the person's own date (eval DM4, round 10)
                    rf"(?:,|\s*[—–-])?\s*not (?:on |in )?{mon}(?: \d{{1,2}})?(?:,? \d{{4}})?(?=[.,;]|$)",
                    "",
                    text,
                )
            if (
                FUTURE_Q.search(q) and lang == "en"
            ):  # "Will it apply in August 2027?", asked today (DT01)
                from web.app import DEFAULT_AS_OF as _today

                for i in ids:
                    eff = str(by_id[i].get("effective_date") or "")[:10]
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff) and eff > _today:
                        text = re.sub(r"\btook effect\b", "takes effect", text)
                        text = re.sub(r"\bnow applies\b", "will apply", text)
                        text = re.sub(r"\bhas applied since\b", "applies from", text)
                        text = re.sub(
                            r"\b(?:started|began) on\b", "starts on", text
                        )  # eval DT01, round 14
                        text = re.sub(r"\bit was in effect\b", "it will be in effect", text)
                        text = re.sub(
                            r"\b(?:started|began)\b", "starts", text
                        )  # eval DT01, round 17
                        text = re.sub(
                            r"\bit is in (?:force|effect) on\b", "it will be in force on", text
                        )
            if (
                len(ids) > 1
                and re.search(
                    r"\b(?:California|New Jersey|Massachusetts),? and (?:California|New Jersey|Massachusetts)\b[^.]*\bsmall(?:er)? landlords?\b",
                    text,
                    re.I,
                )
            ):  # the merged form only; a per-state picture ("California: ...; New Jersey: ...") is fine
                if not all(
                    "small" in full_src([i]).lower() for i in ids
                ):  # CA's rule, not NJ's (eval MT1)
                    dropped.append(
                        {
                            "text": text[:200],
                            "cites": ids,
                            "why": "exception one of the cited rules doesn't have",
                        }
                    )
                    continue
            if re.search(r"\bno exceptions?\b", text, re.I) and re.search(
                r"\bexempt|\bexcept|\bsmall\b|two months", src_all, re.I
            ):  # "There are no exceptions for 2026" while the rule has some (eval IN04)
                text = " ".join(
                    x
                    for x in _split_sentences(text)
                    if not re.search(r"\bno exceptions?\b", x, re.I)
                )
                if not text:
                    continue
            if (
                "whichever is lower" in src_all and "5%" not in text
            ):  # "caps increases at 10%" (eval DM2)
                text = re.sub(
                    r"\b(caps? (?:rent )?(?:increases? )?(?:at|to)) 10%",
                    r"\1 5% plus inflation or 10%, whichever is lower,",
                    text,
                )
            if (
                "owners of 10 or more units" in src_all
            ):  # MA-RENT-01: the owner's 10 units, not the city's (eval T02)
                text = re.sub(
                    r"\b(?:only )?if it has 10 or more units\b",
                    "only for owners of 10 or more units",
                    text,
                )
                text = re.sub(  # 'buildings with 10 or more units' (eval AD05, round 20)
                    r"\b(?:of |for )?buildings (?:with|of) 10 or more units\b",
                    "for owners of 10 or more units",
                    text,
                )
            for i in ids:  # 'units after June 13, 1979 do not have a limit': not SF's limit (eval R04, round 20)
                if by_id[i].get("level") == "city" and "no limit" not in src_all.lower():
                    lbl = by_id[i].get("jurisdiction_label") or ""
                    text = re.sub(
                        r"\b(do|does) not have (?:a|any) (?:rent )?limit\b",
                        lambda m, lbl=lbl: (
                            f"{'are' if m[1] == 'do' else 'is'} not covered by {lbl}'s limit"
                        ),
                        text,
                    )
            text = re.sub(  # a rewrite never leaves '., ' (eval DT10, round 11)
                r"\.\s*,\s*(\w)", lambda m: ". " + m[1].upper(), text
            )
            for w in ("greater of", "set amount", "minimum increase"):
                if (
                    w in text.lower() and w not in src_all.lower()
                ):  # 'greater of 65% or a set amount' (R06)
                    text = " ".join(x for x in _split_sentences(text) if w not in x.lower())
            if (
                "no-fault" in src_all.lower()
            ):  # no-fault just cause is a listed reason, never 'no reason' (AD11)
                text = re.sub(r"\b(?:With|For) no reason,", "For a no-fault eviction,", text)
                text = re.sub(r"\bwith no reason\b", "for a no-fault reason", text)
                if re.search(r"reubicaci|mudar", text, re.I):  # Spanish too (eval ES04, round 19)
                    text = re.sub(
                        r"\bsin (?:una )?(?:raz[oó]n|causa)(?: v[aá]lida)?\b",
                        "sin culpa del inquilino",
                        text,
                    )
            dep = re.search(r",?\s*depending on ([^.;]+)", text)
            if (
                dep
                and any(  # 'depending on the size of the unit': factors the rule doesn't give (eval E03)
                    t not in set(tokens(src_all)) for t in tokens(dep[1]) if len(t) > 3
                )
            ):
                text = text[: dep.start()] + text[dep.end() :]
            text = " ".join(  # 'The amount depends on your household size and income.' (eval E03, rounds 16-19)
                x
                for x in _split_sentences(text)
                if not (
                    (d := re.search(r"\bdepends? on ([^.;]+)", x))
                    and any(  # invented factors only: household size, income, unit size, bedrooms
                        t not in set(tokens(src_all))
                        for t in tokens(d[1])
                        if t in ("household", "income", "size", "bedrooms", "family", "incomes")
                    )
                )
            )
            if "size" not in src_all.lower():  # 'sets amounts by bedroom size' (eval E02, round 22)
                text = re.sub(
                    r",?\s*(?:by|based on) (?:bedroom|unit|household|family) size\b", "", text
                )
            text = " ".join(  # 'is not covered by these rules' beyond the named exemptions (eval A02, round 22)
                x
                for x in _split_sentences(text)
                if not re.search(
                    r"\bnot covered by (?:these|the|those) rules\b|\bthese rules don't cover\b",
                    x,
                    re.I,
                )
            )
            text = " ".join(  # no 'would not violate' verdicts on a product (eval A01)
                x
                for x in _split_sentences(text)
                if not re.search(
                    r"\b(?:would|will|does) not violate\b|\b(?:wouldn't|won't|doesn't) violate\b",
                    x,
                    re.I,
                )
            )
            if not text:
                continue
            text = re.sub(  # steps name offices, they don't promise outcomes (eval SA02, ES06)
                r"\s*(?:They|It|Ellos|Ellas) (?:can|will|may|pueden|podr[aá]n) (?:help you |ayudarte a |ayudarle a )?"
                r"(?:get (?:you )?back in|regain access|let you back in|entrar|volver a entrar)[^.]*\.",
                "",
                text,
            ).strip()
            if not text:
                continue
            if limit == 3 and re.match(
                r"(?:They|It|Ellos|Ellas)\b", text
            ):  # a step whose office name went (T10)
                continue
            if (
                limit == 3 and len(text.split()) < 4
            ):  # a step cut to a fragment: 'Keep a copy.' (eval AD03)
                continue
            if (
                text.count('"') % 2
            ):  # a step cut mid-quote: 'A $50 raise exceeds that limit."' (eval DM1)
                text = text.replace('"', "").strip()
            text = re.sub(  # "..., the same as all other tenants": a comparison no source makes (eval T16)
                r",?\s*(?:the same as|just like|like) (?:all|any|every|other) (?:other )?(?:tenants?|renters?)\b",
                "",
                text,
            )
            cure = re.search(r"\b(\d+)-day right to cure\b", src_all)
            if (
                cure and lang == "en"
            ):  # "right to cure by paying within that time" is the source's 10 days (eval E14)
                text = re.sub(
                    r"(\bcure\b[^.]{0,60}?)\bwithin (?:that time|the notice period|those \d+ days)",
                    rf"\1within {cure.group(1)} days",
                    text,
                )
                text = re.sub(  # '14 days to pay' is the notice; the cure right is the source's 10 days (E14, round 17)
                    r"\b(?!" + cure.group(1) + r"\b)\d+ days to pay\b",
                    f"{cure.group(1)} days to pay",
                    text,
                )
            if (
                "answer day" not in src_all.lower()
            ):  # MA-EVIC-01's written-lease cure, not every rule's (E14)
                text = re.sub(r",?\s*by the answer day\b", "", text)
            if (
                "waive" in src_all.lower()
            ):  # the landlord waives the rent; the tenant never 'agrees to waive' (MT3)
                text = re.sub(
                    r",? unless you (?:agree to )?waive (?:it|that|the payment|this)\b",
                    " or waive that rent",
                    text,
                )
            if (
                "new tenanc" not in src_all.lower()
            ):  # CA-RENT-01's clause on a city rule (eval R08, round 21)
                text = re.sub(
                    r";?,?\s*(?:the )?(?:initial|first) rent (?:on|of|for) (?:a )?new tenanc(?:y|ies) (?:is|are) not (?:capped|covered)\b",
                    "",
                    text,
                    flags=re.I,
                )
            if re.search(
                r"\bgenerally (?:permitted|allowed|legal|ok)\b", text, re.I
            ) and not re.search(
                r"\bgenerally\b", src_all
            ):  # 'generally permitted' over-reads an exemption (eval A01)
                text = " ".join(
                    x
                    for x in _split_sentences(text)
                    if not re.search(r"\bgenerally (?:permitted|allowed|legal|ok)\b", x, re.I)
                )
                if not text:
                    continue
            if (
                "anniversary" not in src_all.lower()
            ):  # 'only on the anniversary of your tenancy' (MT5, round 17)
                text = re.sub(
                    r",?\s*only on the anniversary of (?:your|the) (?:tenancy|lease)\b,?", "", text
                )
            if not any(
                "job" in full_src([i]).lower() for i in ids
            ):  # NJ Fair Chance: an offer to rent (eval S04)
                text = re.sub(
                    r"\bconditional (?:job|employment) offer\b", "conditional offer to rent", text
                )
            if (
                NOT_COVERED.search(text)
                and any(i == "CA-RENT-01" for i in ids)
                and not re.search(  # "the first rent you pay on a new tenancy" already says it (eval MT4)
                    r"\b(?:first|initial) rent (?!(?:on|of|for|in|under)\b)[^.]{0,30}\bnew tenanc|\bprimera renta\b[^.]{0,30}\bnuevo contrato",
                    text,
                    re.I,
                )
            ):
                text = NEW_TENANCY.sub(
                    lambda m, t=text: (
                        (
                            "the first rent of a new tenancy"
                            if lang == "en"
                            else "la primera renta de un nuevo contrato"
                        )
                        if m.start() and not re.search(r"[.!?]\s*$", t[: m.start()])
                        else (
                            "The first rent of a new tenancy"
                            if lang == "en"
                            else "La primera renta de un nuevo contrato"
                        )
                    ),
                    text,
                )
            if ids and any(by_id[i].get("status") == "not_yet_effective" for i in ids):
                text = BECOMES.sub(lambda m: TAKES.get(m.group(0).lower(), m.group(0)), text)
            for (
                i
            ) in ids:  # "became law on <its start date>": it takes (took) effect then (eval DT01)
                eff = str(by_id[i].get("effective_date") or "")[:10]
                if lang == "en" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff):
                    text = re.sub(
                        BECAME_ON.pattern
                        + rf"(?=(?:{calendar.month_name[int(eff[5:7])]}|{calendar.month_abbr[int(eff[5:7])]})"
                        + rf"\.? 0?{int(eff[8:10])},? {eff[:4]}|{eff})",
                        (
                            "took effect"
                            if as_of >= eff and not FUTURE_Q.search(q)
                            else "takes effect"
                        )
                        + r" \1 ",
                        text,
                        flags=re.I,
                    )
            if (
                lang == "en"
                and any(
                    "for nonpayment"
                    in str(by_id[i].get("title") or by_id[i].get("title_en") or "").lower()
                    for i in ids
                )
                and not re.search(r"nonpayment|non-payment|unpaid|not pa(?:y|id)", q, re.I)
            ):  # MA-EVIC-04: the form goes with a notice to quit for nonpayment, not with every notice (eval E18)
                text = NONPAY_SCOPE.sub(r"\1 for nonpayment of rent", text, count=1)
            miss = [x for x in re.findall(r"\d+(?:\.\d+)?%", text) if x not in src_all]
            if (
                ids and miss
            ):  # the state cap's 5%/10% cited only to LA-RENT-01: cite the rule they come from (R03)
                extra_id = next(
                    (
                        e["id"]
                        for e in items
                        if e["kind"] == "rule"
                        and e["id"] not in ids
                        and all(x in full_src([e["id"]]) for x in miss)
                    ),
                    None,
                )
                if extra_id:
                    ids = ids + [extra_id]
            if limit != 3 and not process_ok(
                text, ids
            ):  # statements (not next steps) about courts and penalties
                dropped.append(
                    {
                        "text": text[:200],
                        "cites": ids,
                        "why": "legal process not in the cited sources",
                    }
                )
                continue
            if keep(text, ids, question_ok=True):
                res.append({"text": text, "cites": ids})
            elif dropped and dropped[-1]["why"] in REPAIRABLE and len(ids) == 1:
                plain = (FALLBACK_PLAIN.get(ids[0]) or {}).get(lang)
                if plain and not any(r["text"] == plain for r in res):
                    res.append({"text": plain, "cites": ids})
            elif (
                len(sents := _split_sentences(text)) > 1
            ):  # one bad sentence: keep the others that pass
                ok = [
                    x
                    for x in sents
                    if why_not(x, ids, True) is None and (limit == 3 or process_ok(x, ids))
                ]
                gone = [x for x in sents if x not in ok]
                if (
                    ok
                    and not re.match(
                        r"(?:However|But|So|That|This|Sin embargo|Pero|Eso|Esto)\b", ok[0]
                    )
                    and not any(  # a dropped qualifier would leave the rest overstated
                        re.match(
                            r"(?:Unless|Except|Only|But|However|If|Salvo|Excepto|Solo|Pero|Si)\b", g
                        )
                        for g in gone
                    )
                ):
                    res.append({"text": " ".join(ok), "cites": ids})
            if len(res) == limit:
                break
        return res

    from web import headlines as H

    expired = {}  # rule id -> number forms of figures whose period ended before the as-of date
    for e in items:
        hd = H.HEADLINES.get(e["id"]) or {}
        if (H.period_of(hd, as_of) if hasattr(H, "period_of") else "in") != "in":
            forms = set()
            for f in _nums(str(e.get("key_value") or "")):
                forms |= {x for x in f if "%" in x or "$" in x}
            expired[e["id"]] = forms
    qualified = (
        set()
    )  # rules whose timing ("not in force yet", "from July 1, 2024") the answer states somewhere
    for x in (
        list(out.get("parts") or [])
        + list(out.get("steps") or [])
        + [{"text": out.get("answer"), "cites": []}]
    ):
        if isinstance(x, dict) and TIME_WORDS.search(str(x.get("text") or "")):
            qualified |= {i for i in (x.get("cites") or []) if isinstance(i, str)}
    parts = clean_list(out.get("parts"), 6)
    steps = clean_list(out.get("steps"), 3)
    said = {x["text"].rstrip(". ") for x in parts}
    steps = [
        x for x in steps if x["text"].rstrip(". ") not in said
    ]  # a step repeating a part (eval DM1)
    answer = MARK.sub("", str(out.get("answer") or "")).strip()
    if (
        answer
    ):  # the headline: short, agreeing with itself, checked against everything the parts cite
        raw_answer, answer = answer, _short_answer(answer)
        union = list(dict.fromkeys(i for x in parts for i in x["cites"]))
        answer = SETS_FIGURE.sub(r"\1 lists", fix_freq(_iso_dates(answer, lang), union))
        answer = base_rent(answer, full_src(union))
        if union and all(by_id[i].get("status") == "in_force" for i in union):
            answer = re.sub(  # every cited rule is in force on the date (eval DT10)
                r",? but (?:it |the timing )?depends on where you rent(?: and when (?:the ban|the law|it) (?:takes effect|starts))?",
                "",
                answer,
                flags=re.I,
            )
        why = "answer line too long" if not answer else why_not(answer, union, strict=True)
        if (
            not why and answer
        ):  # 'No, it ended January 1, 2031': a date no source gives (eval DT08, round 21)
            known = set()
            for e in items:
                for k in ("effective_date", "sunset_date", "version_from", "enacted_date"):
                    d = str(e.get(k) or "")[:10]
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                        known.add(d)
            src_items = full_src(list(by_id))
            for mo, dd, yy in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", src_items):
                known.add(f"{yy}-{int(mo):02d}-{int(dd):02d}")
            for mn, dd, yy in re.findall(
                rf"\b({_MONTHS})\.? (\d{{1,2}}),? (\d{{4}})\b", src_items, re.I
            ):
                known.add(f"{yy}-{_MONTHS.split('|').index(mn.lower()) + 1:02d}-{int(dd):02d}")
            known |= set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", src_items))
            for m in re.finditer(rf"\b({_MONTHS})\.? (\d{{1,2}}),? (\d{{4}})\b", answer, re.I):
                iso = f"{m[3]}-{_MONTHS.split('|').index(m[1].lower()) + 1:02d}-{int(m[2]):02d}"
                if (
                    iso not in known
                    and m[0] not in src_items
                    and iso not in src_items
                    and iso != as_of
                ):
                    why = "date in the answer line that no source gives"
        if not why and _contradicts(answer):
            why = "answer line contradicts itself (Yes/No and the rest disagree)"
        if (
            not why
            and scope_local
            and not STATE_WORD.search(answer)
            and not re.search(r"\blocal\b", answer, re.I)
        ):
            why = "state rule given as the answer for a city whose local rules we don't have"
        if why:
            dropped.append({"text": raw_answer, "cites": union, "why": why})
            answer = ""
            if (
                why == "answer line too long"
                and union
                and keep(raw_answer, union)
                and not any(
                    p["text"] == raw_answer or raw_answer.rstrip(".") in p["text"] for p in parts
                )
            ):
                moved = base_rent(fix_freq(raw_answer, union), full_src(union))
                if re.search(r"\b12-month period\b", full_src(union)):  # eval R01, round 14
                    moved = re.sub(
                        r"((?:%|\bpercent)[^.;]{0,30}?)\b(?:per|a) year\b",
                        r"\1over any 12 months",
                        moved,
                    )
                parts.insert(
                    0, {"text": moved, "cites": union[:1]}
                )  # the same rewrites as any part
    cited_all = [i for x in parts for i in x["cites"]]
    state_cited = [i for i in cited_all if by_id[i].get("level") == "state"]
    if (
        answer
        and not city  # "Does Jersey City ban it?": yes; "not statewide yet" only answers a state question
        and state_cited
        and all(by_id[i].get("status") in NOT_THEN for i in state_cited)
        and any(by_id[i].get("status") not in NOT_THEN for i in cited_all)
    ):  # "Yes, but the ban starts 2027" for a state: only some cities have it now
        answer = re.sub(r"^\W*yes\b[,.]?\s*(?:but\s+)?", "Not statewide yet: ", answer, flags=re.I)
        answer = re.sub(
            r"^\W*s[ií]\b[,.]?\s*(?:pero\s+)?", "Aún no en todo el estado: ", answer, flags=re.I
        )
    if answer and cited_all and all(by_id[i].get("status") in NOT_THEN for i in cited_all):
        fixed = re.sub(r"^\W*yes\b[,.]?\s*(?:but\s+)?", "Not yet: ", answer, flags=re.I)
        fixed = re.sub(r"^\W*s[ií]\b[,.]?\s*(?:pero\s+)?", "Aún no: ", fixed, flags=re.I)
        answer = fixed
    if (
        answer
        and cited_all
        and all(by_id[i].get("status") in NOT_THEN for i in cited_all)
        and not TIME_WORDS.search(answer)
    ):
        dropped.append(
            {
                "text": answer,
                "cites": cited_all,
                "why": "rule not in force on the as-of date stated as applying",
            }
        )
        answer = ""
    if answer and not process_ok(answer, [i for x in parts for i in x["cites"]]):
        dropped.append(
            {"text": answer, "cites": [], "why": "legal process not in the cited sources"}
        )
        answer = ""
    ask_q = str(out.get("ask") or "").strip()
    if ask_q and (
        BAD.search(ask_q)
        or len(ask_q) > 200
        or not _grounded_nums(ask_q, allowed)
        or not ask_q.rstrip().endswith("?")  # "To find the 2026 rate, contact ...": not a question
    ):
        ask_q = ""
    if re.search(r"\bthose (?:cities|places|areas)\b|\besas ciudades\b", ask_q, re.I) and not any(
        by_id[i].get("level") == "city" for x in parts for i in x["cites"]
    ):
        ask_q = ""  # it pointed at a dropped part (eval MT4, round 16)
    if re.search(
        r"\bthose (?:categories|situations|exemptions|types)\b(?!\s*[—–:(,-])|\besas (?:categor[ií]as|situaciones|excepciones)\b(?!\s*[—–:(,-])",
        ask_q,
        re.I,
    ) and not any(
        re.search(r"exempt|cover|categor|such as|like|exent|cubr|como", x["text"], re.I)
        for x in parts
    ):
        ask_q = ""  # 'one of those categories' after the part naming them went (eval R06, round 23)
    if (
        city
        and re.search(r"\b(?:12|twelve) months\b|\ba year\b", ask_q)
        and any(
            by_id[i].get("jurisdiction") == city
            and not re.search(r"\b(?:12|twelve)[- ]months?\b", full_src([i]))
            and any(
                (by_id.get(j) or {}).get("level") == "state"
                for j in (by_id[i].get("overrides") or [])
            )
            for x in parts
            for i in x["cites"]
        )
    ):
        ask_q = ""  # the state's tenure condition for a city rule (eval MT3, round 22)
    all_src = full_src(list(by_id))
    if any(
        y not in all_src and y not in q for y in re.findall(r"\b(?:19|20)\d\d\b", ask_q)
    ):  # 'a unit built after 2022': a year no source gives (eval R08, round 19)
        ask_q = ""
    if chat and re.search(
        r"\b(?:state|city|where|live|rent in|ciudad|estado|d[oó]nde)\b", ask_q, re.I
    ):
        ask_q = ""  # off-topic or injection: no "Which state and city?" (persona Jamal); the topic reply instead
    for x in parts + steps:
        use(x["cites"])
    helps = [h for h in (out.get("help") or []) if isinstance(h, str) and h in HELP][:3]
    fups = []
    for f in out.get("followups") or []:
        f = str(f).strip()
        if (
            6 <= len(f) <= 90
            and not BAD.search(f)
            and not MARK.search(f)
            and chip_ok(f)
            and f not in fups
        ):
            fups.append(f)
    return {
        "answer": answer[:160],
        "parts": parts,
        "steps": [] if partial else steps,
        "ask": ask_q,
        "help": helps,
        "cites": order,
        "followups": fups[:6],
        "dropped": dropped,
    }


def _iso_dates(t: str, lang: str) -> str:
    """'it ended 2030-01-01' -> 'it ended Jan 1, 2030'."""
    return re.sub(r"\b(\d{4}-\d{2}-\d{2})\b", lambda m: fmt_date(m.group(1), lang), t)


def _short_answer(a: str, limit: int = 12) -> str:
    """At most `limit` words: the first clause when the line is longer, else nothing."""
    a = a.strip()
    if len(a.split()) <= limit:
        return a
    first = re.split(r"(?<=[.!?])\s+|\s+[—–-]\s+", a)[0].strip()
    if first.endswith((":", ";", ",")) or ";" in first:
        return ""
    return first if 1 < len(first.split()) <= limit else ""


ALLOW = re.compile(
    r"\b(?:allows?|allowed|can|may|up to|permits?|at most|is legal|puede|pueden|permite|hasta)\b",
    re.I,
)
DENY = re.compile(
    r"\b(?:cannot|can't|may not|not allowed|illegal|prohibit\w*|banned|no puede|no pueden|prohib\w*)\b",
    re.I,
)


def _contradicts(a: str) -> bool:
    m = re.match(r"^\W*(no|yes|s[ií])\b[\s.,;:!-]*(.*)$", a, re.I)
    if not m or not m.group(2):
        return False
    rest = m.group(2)
    if m.group(1).lower() == "no":
        return bool(ALLOW.search(rest)) and not re.search(
            r"\b(?:only|not|n't|never|no|solo)\b", rest, re.I
        )
    return bool(DENY.search(rest))


# Chips are things the renter asks us, never questions about the renter's own situation (Isaac 2026-10-04).
FACT_Q = re.compile(
    r"^\W*(?:am i|are you|do you|did you|have you|is your|are your|what(?: is|'s) your|is (?:my|the) landlord"
    r"|(?:does|did) (?:my|the|your) (?:landlord|owner) (?:own|have|live|rent|qualify)|do i (?:have|own|live|rent)|did i|was my|were my|when was my|how (?:many|old)\b.*\bmy\b"
    r"|what is my|soy|eres|tengo|tienes|es mi|está mi|mi casero (?:tiene|es|vive)|cuántos\b.*\btengo)\b",
    re.I,
)
LEGAL_CUE = re.compile(
    r"\b(?:can|could|must|have to|has to|need|allowed|legal|illegal|owe|required|limit|cap|how much|how long|what if"
    r"|what counts|protect|rights?|puede|pueden|debe|deben|tiene que|tienen que|límite|cuánto|qué pasa|derechos?)\b",
    re.I,
)


def chip_ok(f: str) -> bool:
    return not (FACT_Q.search(f) and not LEGAL_CUE.search(f))


# Meta and small talk (Isaac 2026-10-04: "who are you" got a cold refusal): a warm, short reply, no model call.
INTENT_META = re.compile(
    r"^\W*(?:who are you|what are you|what is this|what can you do|what do you do|how do you work|how does this work"
    r"|what can i ask|is this (?:an? )?(?:ai|bot|robot|chatbot)|are you (?:an? )?(?:ai|bot|robot|human|real person|chatbot|chatgpt)"
    r"|help|help me|hi|hello|hey|hiya|good (?:morning|afternoon|evening)|yo"
    r"|qui[eé]n eres|qu[eé] eres|qu[eé] es esto|qu[eé] puedes hacer|c[oó]mo funcionas|eres (?:una? )?(?:ia|robot|bot|humano|persona)"
    r"|ayuda|ay[uú]dame|hola|buen[oa]s (?:d[ií]as|tardes|noches))\W*$",
    re.I,
)
INTENT_THANKS = re.compile(
    r"^\W*(?:thanks?(?: you)?(?: so much)?|thx|ty|great|cool|ok(?:ay)?|perfect|got it|gracias|muchas gracias|vale"
    r"|perfecto|genial)\W*$",
    re.I,
)
INTENT_LAWYER = re.compile(
    r"\b(?:are you a (?:lawyer|attorney)|are you an attorney|is (?:this|that|it) (?:a )?legal advice"
    r"|can you be my (?:lawyer|attorney)|eres (?:un |una )?abogad[oa]|es (?:esto )?asesor[ií]a legal|es consejo legal)\b",
    re.I,
)


def intent_reply(
    q: str, lang: str, place: dict | None, address_id: str | None, store
) -> dict | None:
    T = TXT[lang]
    if INTENT_LAWYER.search(q) and len(q.split()) <= 10:
        helps = _help_for(place, address_id, store)[:3]
        return {
            "kind": "answer",
            "intent": "lawyer",
            "quiet": True,
            "answer": T["lawyer"],
            "answer_cites": [],
            "parts": [{"text": T["lawyer_b"], "cites": []}],
            "body": [],
            "citations": [],
            "help": [{"id": h, "label": HELP[h][0], "url": HELP[h][1]} for h in helps],
            "followups": SUGGEST[lang][:3],
            "_verified": True,
        }
    for rx, a, b, name in (
        (INTENT_META, "intro", "intro_b", "intro"),
        (INTENT_THANKS, "thanks", "thanks_b", "thanks"),
    ):
        if rx.search(q):
            return {
                "kind": "answer",
                "intent": name,
                "quiet": True,
                "answer": T[a],
                "answer_cites": [],
                "parts": [{"text": T[b], "cites": []}],
                "body": [],
                "citations": [],
                "followups": SUGGEST[lang][:3],
                "_verified": True,
            }
    return None


# ------------------------------------------------------------------ answer assembly
TXT = {
    "en": {
        "nc_place": "I can't help with {place}, sorry.",
        "nc_place_b": "I only know the rental laws of California, New Jersey and Massachusetts, plus the local rules of {cities}. The link below is a good place to start.",
        "ev": "I can't help find a way around the law.",
        "urgent": "This sounds urgent. Please contact one of the help offices below today, and keep every paper and message you got.",
        "urgent_a": "Get help today.",
        "horizon": "Our sources describe the law only up to {d}, and rules can change, so check again closer to the date.",
        "court": "Don't miss the date on your court papers: go, or get help before that date.",
        "no_law": "I don't have a law called \u201c{n}\u201d in my sources.",
        "no_federal": "Our sources have no federal rent law; they cover California, New Jersey and Massachusetts state rules and the local rules of {n} cities.",
        "place_ack": "Got it: {p}.",
        "place_ack_b": "What would you like to know about renting there?",
        "topic_qs": [
            "How much can the rent go up?",
            "Can they evict me without a reason?",
            "How much deposit can they ask for?",
        ],
        "ev_b": "What I can do is show what the law here requires, quoted from its source, and where to ask for help.",
        "nc_topic": "I can only help with renting questions in California, New Jersey and Massachusetts.",
        "intro": "I'm the Clause & Effect housing helper.",
        "intro_b": "I answer questions about renting in California, New Jersey and Massachusetts, using only the sources I quote, and I show you the exact sentence. I'm not a lawyer.",
        "thanks": "You're welcome.",
        "thanks_b": "Ask me anything else about renting in California, New Jersey or Massachusetts.",
        "lawyer": "No, I'm not a lawyer, and this isn't legal advice.",
        "lawyer_b": "I show what the public law says, with the exact sentence from its source. For your own situation, a legal aid office can help.",
        "nc_source": "I don't have that in my sources.",
        "not_here": "No rule on this covers this building.",
        "nc_source_b": "I only answer from the sources I hold, and none of them covers this. I'd rather say so than guess.",
        "local_note": "Our sources have no local rules for {city}; only {state} state law is covered there.",
        "busy": "Too many questions from this connection. Please wait a minute.",
        "depends": "It depends on {f}.",
        "when_built": "when your building was built",
        "closest": "Closest official source",
    },
    "es": {
        "nc_place": "Lo siento, no puedo ayudar con {place}.",
        "nc_place_b": "Solo conozco las leyes de alquiler de California, Nueva Jersey y Massachusetts, y las normas locales de {cities}. El enlace de abajo es un buen punto de partida.",
        "ev": "No puedo ayudar a buscar una forma de evitar la ley.",
        "urgent": "Esto parece urgente. Contacte hoy una de las oficinas de ayuda de abajo y guarde todos los papeles y mensajes que recibió.",
        "urgent_a": "Pida ayuda hoy.",
        "horizon": "Nuestras fuentes describen la ley solo hasta el {d}, y las normas pueden cambiar, así que vuelva a consultar más cerca de esa fecha.",
        "court": "No falte a la fecha de sus papeles de la corte: vaya, o pida ayuda antes de esa fecha.",
        "no_law": "No tengo una ley llamada \u201c{n}\u201d en mis fuentes.",
        "no_federal": "Nuestras fuentes no tienen una ley federal de renta; cubren las normas estatales de California, Nueva Jersey y Massachusetts y las normas locales de {n} ciudades.",
        "place_ack": "Entendido: {p}.",
        "place_ack_b": "¿Qué quiere saber sobre el alquiler allí?",
        "topic_qs": [
            "¿Cuánto pueden subir la renta?",
            "¿Me pueden desalojar sin motivo?",
            "¿Cuánto depósito me pueden pedir?",
        ],
        "ev_b": "Lo que sí puedo hacer es mostrar lo que exige la ley aquí, citado de su fuente, y dónde pedir ayuda.",
        "nc_topic": "Solo puedo ayudar con preguntas de alquiler en California, Nueva Jersey y Massachusetts.",
        "intro": "Soy el asistente de vivienda de Clause & Effect.",
        "intro_b": "Respondo preguntas sobre alquiler en California, Nueva Jersey y Massachusetts, solo con las fuentes que cito, y le muestro la frase exacta. No soy abogado.",
        "thanks": "De nada.",
        "thanks_b": "Pregúnteme lo que quiera sobre alquiler en California, Nueva Jersey o Massachusetts.",
        "lawyer": "No, no soy abogado, y esto no es asesoría legal.",
        "lawyer_b": "Muestro lo que dice la ley pública, con la frase exacta de su fuente. Para su caso, una oficina de ayuda legal puede orientarle.",
        "nc_source": "Eso no está en mis fuentes.",
        "not_here": "Ninguna norma sobre esto cubre este edificio.",
        "nc_source_b": "Solo respondo con las fuentes que tengo, y ninguna cubre esto. Prefiero decirlo antes que adivinar.",
        "local_note": "Nuestras fuentes no tienen normas locales de {city}; allí solo cubrimos la ley estatal de {state}.",
        "busy": "Demasiadas preguntas desde esta conexión. Espere un minuto.",
        "depends": "Depende de: {f}.",
        "when_built": "cuándo se construyó su edificio",
        "closest": "Fuente oficial más cercana",
    },
}


def city_list(lang: str) -> str:
    """The cities we have local rules for, from the data (a city added later is listed too)."""
    es = {"Los Angeles": "Los Ángeles"}
    names = [j.split(",")[0] for j in CITY_ALIASES]
    names = [es.get(n, n) for n in names] if lang == "es" else names
    return (
        ", ".join(names[:-1]) + (" y " if lang == "es" else " and ") + names[-1]
        if len(names) > 1
        else "".join(names)
    )


def _refusal(
    kind: str, lang: str, official: dict, place_name: str = "", q: str = "", as_of: str = ""
) -> dict:
    T = TXT[lang]
    if kind == "place":
        answer, body = (
            T["nc_place"].format(place=place_name),
            T["nc_place_b"].format(cities=city_list(lang)),
        )
    elif (
        kind == "topic"
    ):  # short and kind: one line and the starter chips, a link only for a known place
        return {
            "kind": "refusal",
            "reason": "topic",
            "quiet": True,
            "answer": T["nc_topic"],
            "answer_cites": [],
            "body": [],
            "citations": [],
            "official": official if place_name else None,
            "followups": SUGGEST[lang][:3],
            "_verified": True,
        }
    else:
        answer, body = T["nc_source"], T["nc_source_b"]
    return {
        "kind": "refusal",
        "reason": kind,
        "quiet": kind == "place",
        "answer": answer,
        "answer_cites": [],
        "body": [{"text": body, "cites": []}],
        "citations": [],
        "official": official,
        "followups": SUGGEST[lang][:3],
        "_verified": True,
    }


def _slug(city: str | None) -> str | None:
    if not city:
        return None
    s = re.sub(r"[^a-z]+", "-", fold(city.split(",")[0])).strip("-")
    return (
        s
        if s
        in {
            "los-angeles",
            "san-francisco",
            "san-diego",
            "berkeley",
            "jersey-city",
            "hoboken",
            "newark",
            "boston",
            "cambridge",
        }
        else None
    )


_CACHE: OrderedDict[tuple, dict] = OrderedDict()
_CACHE_LOCK = threading.Lock()
_INFLIGHT: dict[tuple, threading.Lock] = {}
CACHE_MAX = 400


def _cache_get(key):
    with _CACHE_LOCK:
        v = _CACHE.get(key)
        if v is not None:
            _CACHE.move_to_end(key)
        return v


def _cache_put(key, v):
    with _CACHE_LOCK:
        _CACHE[key] = v
        _CACHE.move_to_end(key)
        while len(_CACHE) > CACHE_MAX:
            _CACHE.popitem(last=False)


class ModelUnavailable(RuntimeError):
    """No slot within SLOT_WAIT or the hourly/daily budget is used up: answer deterministically instead."""


class Budget:
    """Fresh model calls per hour and per day, in memory and in a small counter file (survives restarts)."""

    def __init__(self, path: Path, per_hour: int, per_day: int) -> None:
        self.path, self.per_hour, self.per_day = path, per_hour, per_day
        self.lock = threading.Lock()
        self.hour: deque[float] = deque()
        self.day, self.day_n, self.logged = time.strftime("%Y-%m-%d"), 0, ""
        try:
            d = json.loads(path.read_text())
            if d.get("day") == self.day:
                self.day_n = int(d.get("n", 0))
            self.hour.extend(t for t in d.get("hour", []) if time.time() - t < 3600)
        except (OSError, ValueError):
            pass

    def take(self, reserve: int = 0) -> bool:
        """reserve: keep that many calls of the hour (and 4x of the day) for people asking (chip checks pass it)."""
        with self.lock:
            now, today = time.time(), time.strftime("%Y-%m-%d")
            if today != self.day:
                self.day, self.day_n = today, 0
            while self.hour and now - self.hour[0] >= 3600:
                self.hour.popleft()
            if reserve and (
                len(self.hour) >= self.per_hour - reserve
                or self.day_n >= self.per_day - 4 * reserve
            ):
                return False
            if len(self.hour) >= self.per_hour or self.day_n >= self.per_day:
                window = "day" if self.day_n >= self.per_day else "hour"
                if self.logged != f"{today}:{window}:{int(now // 3600)}":
                    self.logged = f"{today}:{window}:{int(now // 3600)}"
                    log.warning(
                        "ask: model budget per %s used up, deterministic answers only", window
                    )
                return False
            self.hour.append(now)
            self.day_n += 1
            try:
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(
                    json.dumps({"day": self.day, "n": self.day_n, "hour": list(self.hour)})
                )
                tmp.replace(self.path)
            except OSError:
                pass
            return True


MODEL_SLOTS = threading.BoundedSemaphore(MAX_PARALLEL)
BG_PARALLEL = max(
    1, MAX_PARALLEL - 2
)  # chip checks: at most this many slots, so two stay free for questions
BG_SLOTS = threading.BoundedSemaphore(BG_PARALLEL)
BG_RESERVE = max(
    20, BUDGET_HOUR // 4
)  # chip checks stop before the last quarter of the hourly budget
BUDGET = Budget(BUDGET_FILE, BUDGET_HOUR, BUDGET_DAY)


def _run_model(system: str, prompt: str, persist: bool, on_text=None, timeout: int = LLM_TIMEOUT):
    """The raw call: navigator.llm via the claude CLI (headless, no tools, isolated, streamed)."""
    from navigator import llm

    parsed, _meta = llm.stream_llm(
        system,
        prompt,
        on_text,
        model=MODEL,
        timeout=timeout,
        tag="ask",
        use_cache=persist,
        store=persist,
        cache_dir=ASK_CACHE,
    )
    return parsed


def call_model(
    system: str,
    prompt: str,
    persist: bool,
    on_text=None,
    wait: float = SLOT_WAIT,
    timeout: int = LLM_TIMEOUT,
    background: bool = False,
) -> dict:
    """Gated model call: answers kept on disk are free; fresh calls need one of MAX_PARALLEL slots (waiting at most
    `wait` seconds) and budget. Background work (checking follow-up chips) may hold only BG_PARALLEL of the slots and
    never the last part of the budget, so a person asking always finds a free slot (the brief audit: a question got
    "the answer writer is not available" while chip checks held all three). Raises ModelUnavailable otherwise.
    Indirection so tests can mock it."""
    from navigator import llm

    if persist and llm.stream_cached(system, prompt, ASK_CACHE):
        return _run_model(system, prompt, True, on_text, timeout)
    if background and not BG_SLOTS.acquire(timeout=wait):
        raise ModelUnavailable("busy")
    try:
        if not MODEL_SLOTS.acquire(timeout=wait):
            log.warning(
                "ask: no model slot within %.1fs (%s)",
                wait,
                "background" if background else "question",
            )
            raise ModelUnavailable("busy")
        try:
            if not BUDGET.take(reserve=BG_RESERVE if background else 0):
                raise ModelUnavailable("budget")
            try:
                return _run_model(system, prompt, persist, on_text, timeout)
            except Exception as e:
                log.warning(
                    "ask: model call failed (%s): %s",
                    "background" if background else "question",
                    str(e)[:200],
                )
                raise
        finally:
            MODEL_SLOTS.release()
    finally:
        if background:
            BG_SLOTS.release()


def _complete_objects(text: str, key: str) -> list[dict]:
    """The complete {...} items of the JSON array `key` in a JSON object that is still streaming."""
    m = re.search(r'"' + key + r'"\s*:\s*\[', text)
    if not m:
        return []
    out, depth, start, in_str, esc_ = [], 0, None, False, False
    for i in range(m.end(), len(text)):
        c = text[i]
        if in_str:
            if esc_:
                esc_ = False
            elif c == "\\":
                esc_ = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    out.append(json.loads(text[start : i + 1]))
                except ValueError:
                    pass
        elif c == "]" and depth == 0:
            break
    return out


def partial_json(text: str) -> dict:
    """The fields of a reply that is still streaming: the finished answer line and the finished parts."""
    out: dict = {}
    m = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        try:
            out["answer"] = json.loads('"' + m.group(1) + '"')
        except ValueError:
            pass
    out["parts"] = _complete_objects(text, "parts")
    return out


# ------------------------------------------------------------------ conversation (follow-ups)
FOLLOW_WORDS = set(
    """what about and how in for at also there then same whats what's if or so ok okay too case it its it's is
    this that he she they them we you i me my your our their be was were do does did can could would will
    when where why who which much many long soon never ever not no doesn't don't won't isn't still just only even
    y en que qué tal para el la los las de del o también tambien ahí alli allí entonces caso es si sí cuándo cuando
    cuánto cuanto dónde donde por""".split()
)
SMALLTALK = re.compile(
    r"^\W*(?:hi|hello|hey|thanks?|thank you|ok(?:ay)?|cool|great|bye|good (?:morning|night)|who are you|what are you"
    r"|gracias|hola|adi[oó]s|vale|perfecto)\b|\b(?:weather|joke|poem|recipe|football|soccer|movie|song|clima|chiste)\b",
    re.I,
)
FOLLOW_VERBS = set(
    """must return returned back get got pay paid owe owed keep kept give notice charge charged ask asked raise raised
    refund interest time days weeks months rule rules law laws apply applies covered cover allowed legal illegal limit
    cap more less extra fee fees money amount enough required need needed tell say write letter call do happens happen
    devolver devuelven pagar cobrar cobran aviso días dias ley leyes aplica permitido límite tope dinero decir hacer""".split()
)
FACT_WORD = re.compile(
    r"^(?:\d+\w*|units?|unidades?|unit|house|home|homes|casa|casas|building|buildings|edificio|apartment|apartamento"
    r"|condo|condos|duplex|single|family|built|construido|owner|owners|dueño|dueno|landlord|casero|small|pequeño|pequeno"
    r"|big|large|corporate|corporation|company|empresa|lives|live|vive|year|years|año|años|anos|old|new|nuevo|month"
    r"|months|mes|meses|lease|contrato|section|voucher|vale|properties|property|propiedades|two|three|four|one|dos|tres"
    r"|cuatro|una|uno|before|after|antes|despues|después|since|desde|i|my|mi|mis|he|she|it|they|is|are|has|have|es"
    r"|son|tiene|tienen|only|just|solo|sólo|a|an|the|un|una|with|con|of|de)$",
    re.I,
)
BUILDING_FACT = re.compile(
    r"^(?:\d+\w*|units?|unidades?|house|casa|duplex|condo|condos|single|family|built|construido|year|years|old|new"
    r"|nuevo|two|three|four|one|dos|tres|cuatro|uno|una)$",
    re.I,
)
# "what is a voucher?", "what does just cause mean?": a definition, not a question about the place
DEFINITION = re.compile(
    r"^\W*(?:what(?:'s| is| are)\s+(?:an?\s+|\w+\s+)?[\w\s'-]{1,40}?(?:\s+in this context|\s+mean)?\W*$"
    r"|what does\s+[\w\s'\"-]{1,40}\s+mean\b|define\b|definition of\b|meaning of\b|what do you mean by\b"
    r"|qu[eé]\s+(?:es|son)\s+(?:un|una|el|la|los|las)\s+[\w\s-]{1,40}\W*$|qu[eé] significa\b|qu[eé] quiere decir\b)",
    re.I,
)
NOT_DEFINITION = re.compile(
    r"\d|\b(?:limit|cap|maximum|max|allowed|can|could|may|must|how much|how many|how long|my|here|there|rule|rules|law"
    r"|laws|l[ií]mite|tope|m[aá]ximo|puede|pueden|cu[aá]nto|mi)\b",
    re.I,
)


def is_definition(q: str) -> bool:
    t = q.strip()
    if not DEFINITION.search(t):
        return False
    core = re.sub(r"\b(?:in this context|en este contexto)\b", "", t, flags=re.I)
    return not NOT_DEFINITION.search(core) and len(t.split()) <= 12


ADDRESSY = re.compile(r"\b\d{1,6}[a-z]?\s+[a-z0-9 .'-]{3,}", re.I)
PLACE_PHRASES = sorted(
    {n for v in CITY_ALIASES.values() for n in v}
    | {n for v in STATE_ALIASES.values() for n in v}
    | {n for v in OTHER_LOCAL.values() for n in v}
    | set(OUT_US)
    | set(OUT_WORLD)
    | {"ca", "nj", "ma", "la"},
    key=len,
    reverse=True,
)


class HistTurn(BaseModel):
    q: str = Field("", max_length=500)
    resolved_q: str | None = Field(None, max_length=700)
    memo: str | None = Field(None, max_length=800)
    lang: str | None = None
    context: dict | None = None


class AskIn(BaseModel):
    q: str = Field(..., min_length=2, max_length=500)
    lang: str = "en"
    as_of: str | None = None
    history: list[HistTurn] = Field(default_factory=list, max_length=6)
    place: dict | None = (
        None  # {"kind": "address", "address_id": ...}: the last looked-up address, untrusted
    )


def _clean_context(ctx: dict | None, store) -> dict | None:
    """A context the client sends back is untrusted: keep only ids and places we know."""
    if not isinstance(ctx, dict):
        return None
    cats = [c for c in (ctx.get("cats") or []) if c in CATEGORIES][:2]
    p = ctx.get("place") if isinstance(ctx.get("place"), dict) else None
    place = None
    if p:
        if p.get("kind") == "address" and p.get("address_id") in store.addresses:
            place = {"kind": "address", "address_id": p["address_id"]}
        elif p.get("kind") == "city" and p.get("jurisdiction") in CITY_ALIASES:
            place = {"kind": "city", "jurisdiction": p["jurisdiction"]}
        elif p.get("kind") == "state" and p.get("state") in STATE_CODES:
            local = re.sub(r"[^A-Za-z .'-]", "", str(p.get("local") or ""))[:40].strip() or None
            place = {"kind": "state", "state": p["state"], "local": local}
    asked = ctx.get("asked_as_of")
    asked = (
        asked
        if isinstance(asked, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", asked)
        and MIN_DATE <= asked <= MAX_DATE
        else None
    )
    if not cats and not place and not asked:
        return None
    return {
        "cats": cats,
        "place": place,
        "awaiting": bool(ctx.get("awaiting")),
        "asked_as_of": asked,
    }


def _residual(q: str, address_id: str | None) -> list[str]:
    """The words of a follow-up that are neither place names nor filler."""
    t = " " + fold(q) + " "
    for n in PLACE_PHRASES:
        t = re.sub(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", " ", t)
    words = [w.removesuffix("'s") for w in re.findall(r"[a-z0-9áéíóúñü']+", t)]
    if address_id:
        words = [
            w
            for w in words
            if not re.match(r"^\d", w) and w not in SUFFIX and w not in STREET_SUFFIXES
        ]
    return [w for w in words if w not in FOLLOW_WORDS and w not in STOP]


def _place_label(place: dict, store, lang: str) -> str:
    if place["kind"] == "address":
        a = store.addresses[place["address_id"]]
        return f"{_title(a['street_address'])}, {a.get('resolved_city') or a['postal_city']}"
    if place["kind"] == "city":
        return place["jurisdiction"].split(",")[0]
    if place.get("local"):
        return f"{place['local']}, {place['state']}"
    return STATE_NAME_L[lang].get(place["state"], place["state"])


STATE_NAME_L = {
    "en": STATE_NAME,
    "es": {"CA": "California", "NJ": "Nueva Jersey", "MA": "Massachusetts"},
}


def geocode_place(q: str) -> dict | None:
    """'Type your address' for an address outside our 500: the live Census geocoder (web/any_address.py) gives its
    state and city. Returns a context place or {'outside': name} or None."""
    from web.any_address import geocode, interpret

    try:
        m = geocode(re.sub(r"\s+", " ", q).strip()[:200])
    except Exception:  # noqa: BLE001
        return None
    if not m:
        return None
    g = interpret(m)
    if g.get("jurisdiction") in CITY_ALIASES:
        return {"kind": "city", "jurisdiction": g["jurisdiction"]}
    if g.get("state") in STATE_CODES:
        return {"kind": "state", "state": g["state"], "local": g.get("place")}
    return {"outside": g.get("place") or g.get("state") or "that address"}


def _with_place(base: str, place_label: str, lang: str, old_labels: list[str]) -> str:
    b = base.strip().rstrip("?").strip()
    for old in old_labels:
        b = re.sub(
            r"\s*(?:,\s*)?\b(?:in|at|en|para)\s+" + re.escape(old) + r"\b", "", b, flags=re.I
        )
    b = b.lstrip("¿").strip()
    return f"{'¿' if lang == 'es' else ''}{b} {'en' if lang == 'es' else 'in'} {place_label}?"


def resolve(
    q: str,
    history: list,
    store,
    lang: str,
    *,
    persist: bool = False,
    wait: float = SLOT_WAIT,
    default_place: dict | None = None,
) -> dict:
    """What the question is about, carrying topic, place and address forward from the conversation. The words of
    the question are the source of truth; the model only rewords a follow-up that adds new facts."""
    cats, places, address_id = categories_for(q), find_places(q), find_address(q, store)
    named = [r for r in named_rules(q) if r in store.rules]
    if named:  # a law named by its short name sets the topic
        cats = list(dict.fromkeys(store.rules[r]["category"] for r in named))[:2]
    own_place = bool(
        address_id or any(places[k] for k in ("cities", "states", "other_local", "outside"))
    )
    R = {
        "named": named,
        "cats": cats,
        "places": places,
        "address_id": address_id,
        "standalone": q,
        "followup": False,
        "carried": [],
        "awaiting": False,
        "geo_failed": False,
        "history": list(history or [])[-5:],
        "q": q,
    }
    prev = None
    for h in reversed(history or []):
        c = _clean_context(h.get("context") if isinstance(h, dict) else None, store)
        if c:
            prev = {**c, "q": (h.get("resolved_q") or h.get("q") or "")[:500]}
            break
    if (
        not prev and default_place
    ):  # the address the person looked up last, until they clear it (persona Keisha)
        c = _clean_context({"place": default_place}, store)
        if c and c["place"]:
            prev = {**c, "q": "", "default": True}
    if not prev:
        return R
    residual = _residual(q, address_id)
    facts = [  # "$1,450" or "10%" is not a fact about the building
        w
        for w in _residual(
            re.sub(r"\$\s?[\d,.]+|\d+(?:\.\d+)?\s*(?:%|percent|por ciento)", " ", q), address_id
        )
        if FACT_WORD.match(w)
    ]
    short = len(q.split()) <= 12
    R["awaiting"] = prev["awaiting"]
    off_q = (  # "What is 2+2?" after "Where do you rent?": a new question, not an address (persona Jamal)
        prev["awaiting"]
        and (
            "?" in q or len(q.split()) > 5
        )  # a typed place is short: "Oakland", "123 Main St, Springfield"
        and not own_place
        and not ADDRESSY.search(q)
        and not is_rental(q)
        and not cats
    )
    if off_q:
        return R
    if (
        prev["awaiting"]
        and not own_place
        and not cats
        and not off_q
        and (ADDRESSY.search(q) or residual)
    ):
        g = geocode_place(q)  # the renter typed an address after "Where do you rent?"
        if g and "outside" in g:
            places["outside"] = [("US", g["outside"])]
            own_place = True
        elif g:
            prev["place"], R["geocoded"] = g, True
        else:
            R["geo_failed"] = True
    if (
        not cats
        and prev["cats"]
        and (
            own_place
            or (
                short and not SMALLTALK.search(q) and not off_q
            )  # a short follow-up keeps the topic unless it is small talk
            or R.get("geocoded")
        )
    ):
        R["cats"] = list(prev["cats"])
        R["carried"].append("topic")
    if R["cats"] and not own_place and prev["place"]:
        pl = prev["place"]
        if (
            pl["kind"] == "address"
            and not prev.get(
                "default"
            )  # "10%" in a fresh question is not a fact about the building
            and any(BUILDING_FACT.match(w) for w in facts)
        ):  # new facts about the building itself (units, year, type): the address's place, not its records
            a = store.addresses[pl["address_id"]]
            st, city = a.get("resolved_state") or a["state"], a.get("resolved_city")
            pl = (
                {"kind": "city", "jurisdiction": f"{city}, {st}"}
                if f"{city}, {st}" in CITY_ALIASES
                else {"kind": "state", "state": st}
            )
        if pl["kind"] == "address":
            R["address_id"] = pl["address_id"]
        elif pl["kind"] == "city":
            R["places"] = {**places, "cities": [pl["jurisdiction"]]}
        elif pl.get("local"):
            R["places"] = {**places, "other_local": [(pl["state"], pl["local"])]}
        else:
            R["places"] = {**places, "states": [pl["state"]]}
        R["carried"].append("place")
        R["carried_place"] = pl
    if not R["carried"]:
        return R
    R["followup"] = True
    # the standalone question the model sees and the renter is shown ("Understood as ...")
    new_place = R.get("carried_place") or _own_place(R, store)
    label = _place_label(new_place, store, lang) if new_place else ""
    old = [_place_label(prev["place"], store, lang)] if prev.get("place") else []
    # (the conversation model sees the whole conversation; this wording is for retrieval and the cache)
    if "topic" in R["carried"] and residual:
        R["standalone"] = (
            (_with_place(prev["q"], label, lang, old) if label else prev["q"]) + " " + q
        )
    elif "topic" in R["carried"]:
        R["standalone"] = _with_place(prev["q"], label, lang, old) if label else prev["q"]
    else:  # own topic, place carried
        R["standalone"] = _with_place(q, label, lang, [])
    return R


def _own_place(R: dict, store) -> dict | None:
    if R["address_id"]:
        return {"kind": "address", "address_id": R["address_id"]}
    p = R["places"]
    if p["cities"]:
        return {"kind": "city", "jurisdiction": p["cities"][0]}
    if p["other_local"]:
        return {"kind": "state", "state": p["other_local"][0][0], "local": p["other_local"][0][1]}
    if p["states"]:
        return {"kind": "state", "state": p["states"][0]}
    return None


def _place_key(R: dict, store) -> str:
    p = _own_place(R, store)
    if not p:
        return ""
    return p.get("address_id") or p.get("jurisdiction") or f"{p['state']}:{p.get('local') or ''}"


# ------------------------------------------------------------------ "Where do you rent?"
WHERE = {
    "en": {
        "title": "Where do you rent?",
        "addr": "Type your address",
        "no_state": "No state limit",
        "geo_failed": "We couldn't find that address. Pick your state or city.",
    },
    "es": {
        "title": "¿Dónde alquila?",
        "addr": "Escriba su dirección",
        "no_state": "Sin límite estatal",
        "geo_failed": "No encontramos esa dirección. Elija su estado o ciudad.",
    },
}


def _state_rule(store, cat: str, st: str, as_of: str) -> str | None:
    from web import headlines as H

    cand = [
        r
        for r in store.rules.values()
        if r.get("jurisdiction") == st
        and r.get("category") == cat
        and r.get("level") == "state"
        and _status_at(r, as_of) == "in_force"
    ]
    cand.sort(
        key=lambda r: (
            H.HEADLINES.get(r["team_rule_id"], {}).get("priority") or 9,
            r["team_rule_id"],
        )
    )
    return cand[0]["team_rule_id"] if cand else None


def chooser(cats: list[str], lang: str, as_of: str, store, note: str | None = None) -> dict:
    """No place given: ask where, with a compact per-state summary when every state's line is short."""
    from web import headlines as H

    W = WHERE[lang]
    cat = cats[0]
    summary, cites = [], []
    for st in ("CA", "NJ", "MA"):
        rid = _state_rule(store, cat, st, as_of)
        if rid:
            text = (H.HEADLINES.get(rid) or {}).get(f"unknown_{lang}") or H.headline(
                rid, lang, as_of
            )
            e = evidence_item(store, rid, as_of, lang)
            if e and text:
                cites.append({**e, "n": len(cites) + 1})
                summary.append(
                    {"state": st, "label": STATE_NAME_L[lang][st], "text": text, "cite": len(cites)}
                )
                continue
        if any(f["jurisdiction"] == st and f["category"] == cat for f in store.no_rule):
            summary.append(
                {"state": st, "label": STATE_NAME_L[lang][st], "text": W["no_state"], "cite": None}
            )
        else:
            summary = []
            break
    if any(len(x["text"].split()) > 8 for x in summary):
        summary = []
    options = [
        {"label": STATE_NAME_L[lang][st], "q": STATE_NAME_L[lang][st], "group": "state"}
        for st in ("CA", "NJ", "MA")
    ]
    options += [
        {"label": j.split(",")[0], "q": j.split(",")[0], "group": "city"} for j in CITY_ALIASES
    ]
    return {
        "kind": "choose",
        "answer": W["title"],
        "answer_cites": [],
        "body": [],
        "note": note,
        "summary": summary,
        "citations": cites if summary else [],
        "options": options,
        "address_label": W["addr"],
        "followups": [],
        "_verified": True,
        "context": {"cats": cats, "place": None, "awaiting": True},
    }


def _public(res: dict) -> dict:
    return {k: v for k, v in res.items() if not k.startswith("_")}


def answer(
    q: str,
    ui_lang: str = "en",
    as_of: str | None = None,
    *,
    history: list | None = None,
    emit=None,
    ip: str | None = None,
    persist: bool = False,
    background: bool = False,
    place: dict | None = None,
) -> dict:
    """The whole pipeline. emit(step_id, info) reports real progress; ip is only used for the model rate limit;
    background: a chip check (waits for a model slot only briefly, never counts against the renter's limit)."""
    from web.app import DEFAULT_AS_OF

    STORE = ask_store()
    index()  # places and ZIPs of every jurisdiction in the data
    emit = emit or (lambda *_: None)
    t0 = time.time()
    as_of = as_of or DEFAULT_AS_OF
    q = re.sub(r"\s+", " ", q).strip()
    persist = (
        persist or q in DEMO_QS
    )  # the demo video's questions: one checked answer, kept on disk
    history = [h.model_dump() if isinstance(h, BaseModel) else h for h in (history or [])][-5:]
    prev_lang = next(
        (h.get("lang") for h in reversed(history) if h.get("lang") in ("en", "es")), None
    )
    lang = detect_lang(q, prev_lang or ui_lang)
    wait = 0.3 if background else SLOT_WAIT
    # a date in the question ("as of Aug 12, 2023", "in 2027", "el 1 de enero de 2027") answers for that day;
    # a follow-up without one keeps the date the conversation asked about
    found = find_date(q, as_of)
    if found and found["out_of_range"]:
        return {
            **_out_of_range(found, lang),
            "q": q,
            "lang": lang,
            "as_of": as_of,
            "cached": False,
            "ms": 0,
        }
    asked_before = [str(h.get("q") or "").strip() for h in history if str(h.get("q") or "").strip()]
    if asked_before and RECALL_Q.search(
        q
    ):  # "what did I ask you first?": from the conversation, not a law answer
        first = bool(
            re.search(
                r"\bfirst\b|\bprimer\w*|\bat the (?:start|beginning)\b|\bal principio\b", q, re.I
            )
        )
        prev_q = asked_before[0] if first else asked_before[-1]
        lead = {
            ("en", True): "You first asked:",
            ("en", False): "You last asked:",
            ("es", True): "Su primera pregunta fue:",
            ("es", False): "Su última pregunta fue:",
        }[(lang, first)]
        return {
            "kind": "answer",
            "intent": "recall",
            "quiet": True,
            "answer": f"{lead} “{prev_q[:300]}”",
            "answer_cites": [],
            "parts": [],
            "body": [],
            "citations": [],
            "help": [],
            "followups": [],
            "_verified": True,
            "q": q,
            "lang": lang,
            "as_of": as_of,
            "cached": False,
            "ms": 0,
        }
    carried = None
    if not found:
        for h in reversed(history):
            c = _clean_context(h.get("context") if isinstance(h, dict) else None, STORE)
            if c:
                carried = c.get("asked_as_of")
                break
    asked = found["iso"] if found else carried
    if asked:
        as_of = asked
    R = resolve(
        strip_date(q, found) if found else q,
        history,
        STORE,
        lang,
        persist=persist,
        wait=wait,
        default_place=place,
    )
    R["q"] = q  # the model and the audit log see the question as asked, date included
    R["background"] = background
    named_place = (
        R["address_id"] or any(R["places"][k] for k in ("cities", "states", "other_local"))
    ) and "place" not in R["carried"]
    R["definition"] = is_definition(strip_date(q, found) if found else q) and not named_place
    R["asked"] = (
        {
            "iso": asked,
            "grain": found["grain"] if found else "day",
            "span": found["span"] if found else None,
        }
        if asked
        else None
    )
    if R["followup"]:
        emit("context", {"q": R["standalone"]})
    conv = hashlib.sha1(
        json.dumps([(h.get("q"), h.get("memo")) for h in history], ensure_ascii=False).encode()
    )
    key = (
        norm_q(R["standalone"]),
        as_of,
        lang,
        _place_key(R, STORE),
        tuple(R["cats"]),
        R["geo_failed"],
        conv.hexdigest()[:16] if R["followup"] else "",
    )

    def replay(
        hit: dict,
    ) -> None:  # a cached answer replays the steps it was made with, with the real counts
        for step, info in hit.get("_steps") or []:
            emit(step, {**info, "cached": True})

    hit = _cache_get(key)
    if hit is not None:
        replay(hit)
        return {**hit, "q": q, "cached": True, "ms": int((time.time() - t0) * 1000)}
    steps: list = []
    outer = emit

    def emit(step, info=None):  # noqa: F811 - remember the progress steps for cache replays
        if step in ("engine", "quotes", "writing") or (step == "rules" and "n" in (info or {})):
            steps.append((step, dict(info or {})))
        outer(step, info)

    lock = _INFLIGHT.setdefault(key, threading.Lock())
    with lock:
        hit = _cache_get(key)
        if hit is not None:
            replay(hit)
            return {**hit, "q": q, "cached": True, "ms": int((time.time() - t0) * 1000)}
        urgent = bool(URGENT.search(q))
        res = _answer(
            R["standalone"],
            lang,
            as_of,
            emit,
            None if background else ip,
            persist,
            STORE,
            R,
            max(wait, 12.0) if urgent and not background else wait,
        )
        res = _safety(res, R, q, lang, STORE, as_of)
        if R["definition"] and res.get("kind") == "answer" and not res.get("urgent"):
            # a definition doesn't depend on a place: no place line, no photo (the conversation keeps its place)
            res = {**res, "place": None, "engine_checked": False, "general": True}
        res.update(
            {
                "lang": lang,
                "as_of": as_of,
                "disclaimer": DISCLAIMER[lang],
                "_key": key,
                "resolved_q": R["standalone"] if R["followup"] else None,
                "_history": history,
                "_steps": steps,
            }
        )
        res.setdefault("memo", res.get("answer", ""))
        res.setdefault(
            "context", {"cats": R["cats"], "place": _ctx_place(res.get("place"), R, STORE)}
        )
        if R["asked"]:
            res["context"] = {**res["context"], "asked_as_of": R["asked"]["iso"]}
            res["asked_as_of"] = R["asked"]["iso"]
            res["asked_label"] = fmt_date(R["asked"]["iso"], lang)
        if not res.pop("_nocache", False):
            _cache_put(key, res)
    _INFLIGHT.pop(key, None)
    return {**res, "q": q, "cached": False, "ms": int((time.time() - t0) * 1000)}


def _ctx_place(place: dict | None, R: dict, store) -> dict | None:
    """The place of an answer as the client sends it back with the next question."""
    p = _own_place(R, store)
    if not p:
        return None
    if place and place.get("label"):
        p = {**p, "label": place["label"]}
    return p


def _hist_turn(res: dict) -> dict:
    """This turn as the client sends it back with the next question."""
    return {
        "q": res.get("q", ""),
        "resolved_q": res.get("resolved_q"),
        "lang": res.get("lang"),
        "memo": res.get("memo"),
        "context": res.get("context"),
    }


_CHIP_POOL = ThreadPoolExecutor(max_workers=MAX_PARALLEL, thread_name_prefix="ask-chip")


def verify_chips(res: dict, *, persist: bool = False, deadline: float = 25.0) -> list[str]:
    """Show only follow-ups that come back with a cited answer in this conversation's context; asking them here
    also pre-warms them, so a tap is instant (Isaac 2026-10-04)."""
    if res.get("_verified"):
        return res.get("followups") or []
    cands = [c for c in res.get("_cands") or [] if chip_ok(c)][:4]
    hist = [*(res.get("_history") or []), _hist_turn(res)][-5:]
    futs = [
        (
            c,
            _CHIP_POOL.submit(
                answer,
                c,
                res.get("lang", "en"),
                res.get("as_of"),
                history=hist,
                persist=persist,
                background=True,
            ),
        )
        for c in cands
    ]
    ok, t_end = [], time.time() + deadline
    for c, f in futs:
        try:
            r = f.result(timeout=max(0.1, t_end - time.time()))
        except Exception:  # noqa: BLE001
            continue
        if r.get("kind") == "answer" and r.get("citations") and not r.get("degraded"):
            ok.append(c)
    ok = ok[:3]
    key = res.get("_key")
    if key is not None:
        with _CACHE_LOCK:
            if key in _CACHE:
                _CACHE[key] = {**_CACHE[key], "followups": ok, "_verified": True}
    return ok


def _answer(q, lang, as_of, emit, ip, persist, STORE, R, wait=SLOT_WAIT) -> dict:
    T = TXT[lang]
    places, address_id, cats = R["places"], R["address_id"], R["cats"]
    place = None
    jurs: dict[str, float] | None = None
    scope_note = ""  # shown to the user (e.g. a city whose local rules we do not have)
    official_j: list[str] = []

    if address_id:
        a = STORE.addresses[address_id]
        st = a.get("resolved_state") or a["state"]
        city = a.get("resolved_city")
        official_j = ([f"{city}, {st}"] if city else []) + [st]
    elif places["outside"] and not places["cities"] and not places["states"]:
        kind, name = places["outside"][0]
        emit("rules", {"n": 0})
        return _refusal("place", lang, {"label": OFFICIAL[kind][0], "url": OFFICIAL[kind][1]}, name)
    elif places["cities"] or places["states"] or places["other_local"]:
        jurs = {}
        for c in places["cities"]:
            jurs[c] = 1.0
            jurs[c.split(", ")[1]] = max(jurs.get(c.split(", ")[1], 0), 0.9)
            official_j.append(c)
        for s in places["states"]:
            jurs[s] = 1.0
            if not places["cities"]:
                for c in CITY_ALIASES:
                    if c.endswith(", " + s):
                        jurs.setdefault(c, 0.45)
            official_j.append(s)
        for s, name in places["other_local"]:
            if not places["cities"]:
                jurs[s] = 1.0
                jurs = {k: v for k, v in jurs.items() if not k.endswith(", " + s)}
                scope_note = T["local_note"].format(city=name, state=STATE_NAME[s])
                official_j.append(s)
        city = places["cities"][0] if places["cities"] else None
        if city:
            place = {
                "kind": "city",
                "label": city.split(",")[0],
                "jurisdiction": city,
                "city": city.split(",")[0],
                "state": city.split(", ")[1],
            }
        elif places["states"] or places["other_local"]:
            s = (places["states"] or [places["other_local"][0][0]])[0]
            place = {
                "kind": "state",
                "label": places["other_local"][0][1] + ", " + s
                if places["other_local"]
                else STATE_NAME_L[lang][s],
                "state": s,
                "jurisdiction": s,
                "local": places["other_local"][0][1] if places["other_local"] else None,
            }

    named = R.get("named") or []
    if (
        URGENT.search(R.get("q") or q) and not cats
    ):  # an eviction notice, a lockout, court papers: an eviction question
        cats = R["cats"] = ["just_cause_eviction"]
    if (
        named and not address_id and not place
    ):  # "What does AB 1482 say?": the named law's own place
        js = list(dict.fromkeys(STORE.rules[r]["jurisdiction"] for r in named))
        j = js[0]
        if j in CITY_ALIASES:
            place = {
                "kind": "city",
                "label": j.split(",")[0],
                "jurisdiction": j,
                "city": j.split(",")[0],
                "state": j.split(", ")[1],
            }
        else:
            place = {
                "kind": "state",
                "label": STATE_NAME_L[lang].get(j, j),
                "state": j,
                "jurisdiction": j,
            }
        jurs = {x: 1.0 for x in js} | {x.split(", ")[1]: 0.9 for x in js if ", " in x}
        official_j = js
    if EVASION.search(
        R.get("q") or q
    ):  # never a workaround: what the law requires, and where to ask
        return _evasion(q, lang, as_of, jurs, cats, place, address_id, official_j, STORE)
    if not cats and not named:
        hi = intent_reply(R.get("q") or q, lang, place, address_id, STORE)
        if hi:
            emit("rules", {"n": 0})
            return hi
        if (address_id or place) and not is_rental(strip_place_words(q)):
            emit("rules", {"n": 0})
            return _place_ack(address_id, place, lang, STORE)
    chat = (
        not cats and not is_rental(q) and not named
    )  # small talk or off-topic: a kind reply, no sources
    no_place = (
        bool(cats) and not address_id and not place
    )  # it will ask where; quick replies attached

    # ---- retrieval (and the engine first, for an address)
    idx = index()
    items: list[dict] = []
    if chat:
        emit("rules", {"n": 0})
    elif address_id:
        emit("rules", {})
        place, items = address_evidence(STORE, address_id, as_of, lang, cats)
        if not cats:  # rank the engine's rules by the question
            ranked = {it["id"]: s for s, it in idx.search(q, None, [])}
            items.sort(key=lambda e: -ranked.get(e["id"], 0))
        items = _trim(items, cats)
        emit("rules", {"n": len(items)})
        emit("engine", {"address": place["label"]})
    else:
        hits = idx.search(q, jurs, cats)
        top = hits[0][0] if hits else 0
        if not cats and top < 6.0:  # rental words but none of our topics: talk, without sources
            chat = True
            hits = []
        chosen = [it for s, it in hits[: TOP_K * 2] if s >= max(1.0, top * 0.25)]
        city = place.get("jurisdiction") if place and place.get("kind") == "city" else None
        if (
            city and cats
        ):  # a city's own rules on the topic always come first (they are few), then its state's
            local = [it for it in idx.items if it["jur"] == city and it["cat"] in cats]
            state = [
                it
                for it in idx.items
                if it["jur"] == city.split(", ")[1] and it["cat"] in cats and it["kind"] == "rule"
            ]
            seen = {it["id"] for it in local + state}
            chosen = local + state + [it for it in chosen if it["id"] not in seen]
        if no_place:  # each state's main rule first, then the strongest city rules
            states = [_state_rule(STORE, cats[0], st, as_of) for st in ("CA", "NJ", "MA")]
            chosen = [{"id": i} for i in states if i] + [
                it for it in chosen if it["id"] not in states
            ]
        items = [e for e in (evidence_item(STORE, it["id"], as_of, lang) for it in chosen) if e]
        items = [e for e in items if e["status"] != "failed" or e["jurisdiction"] == (city or "")]
        items = _trim(items, cats, TOP_K + 2 if city else TOP_K)
        emit("rules", {"n": len(items)})
    if named and not chat:  # the law the question names is always among the sources, first
        by = {e["id"]: e for e in items}
        first = [by.get(r) or evidence_item(STORE, r, as_of, lang) for r in named]
        items = ([e for e in first if e] + [e for e in items if e["id"] not in named])[: TOP_K + 1]
    if not items and not chat:
        return _refusal("source", lang, _official(official_j, STORE))
    stated = (
        stated_facts(R.get("q") or q)
        if not address_id and not chat and place and place.get("kind") in ("city", "state")
        else None
    )
    if stated and not stated_engine(items, place, stated, as_of):
        stated = None
    if place:
        if R.get("definition"):
            emit("general", {})
        else:
            emit("place", {"place": {**place, "image": _slug(place.get("city"))}})
    if items:
        emit("quotes", {"n": len(items), "verbatim": sum(1 for e in items if e["verbatim"])})

    # ---- the model writes; the server validates
    if ip is not None and not LLM_LIMIT.allow(ip):
        raise HTTPException(429, T["busy"])
    emit("writing", {})
    notes = [scope_note] if scope_note else []
    computed = None
    if "rent_increase_limits" in (cats or []) and (address_id or place) and not chat:
        from web import ask_increase as INC

        parsed_inc = INC.parse_increases(R.get("q") or q)
        dollar_pct = INC.money_pct(INC.parse_money(R.get("q") or q))
        if not parsed_inc and dollar_pct:  # "$300 more on $2,000": checked as a 15% increase
            parsed_inc = {"pcts": [dollar_pct], "count": 1, "how": "single"}
        if parsed_inc:
            if address_id:
                body = {"address_id": address_id}
            elif place.get("kind") == "city" and place.get("jurisdiction") in CITY_ALIASES:
                body = {"place": {"state": place["state"], "jurisdiction": place["jurisdiction"]}}
            else:
                body = {"place": {"state": place.get("state")}}
            c = INC.compute(parsed_inc, body, as_of)
            a_line, why = (
                INC.sentence(
                    c, lang, (place or {}).get("label", ""), asked_date=bool(R.get("asked"))
                )
                if c
                else ("", "")
            )
            if a_line:
                computed = {"c": c, "answer": a_line, "why": why}
                note_en = INC.sentence(c, "en", "", asked_date=bool(R.get("asked")))
                notes.append(
                    f"COMPUTED CHECK (done by code from the rule's cap; your answer must agree with it): {note_en[1] or note_en[0]}"
                )
    for rx, note in GLOSSARY:
        if rx.search(R.get("q") or q):
            notes.append(note)
    failed = [e for e in items if e.get("status") == "failed"]
    if failed and re.search(  # "Since the ballot question passed, ...": a false premise (eval T05)
        r"\b(?:passed|was approved|got approved|won|became law|aprobad\w*|se aprob\w*)\b",
        R.get("q") or q,
        re.I,
    ):
        notes.append(
            "The question assumes a proposal passed. In the SOURCES, "
            + "; ".join(f"{e['id']} ({e.get('title_en') or ''})" for e in failed[:2])
            + " failed and is not law: say that first, in the first part, citing it."
        )
    if R.get("asked"):
        d = fmt_date(as_of, "en")
        notes.append(
            f"The question is about {d}"
            + (
                " (the person named only the year; that is the first day of it)"
                if R["asked"]["grain"] == "year"
                else ""
            )
            + (
                " (the person named only the month; that is its first day)"
                if R["asked"]["grain"] == "month"
                else ""
            )
            + f". Answer for {d}, using the 'Status on the as-of date' lines. A rule 'not yet in force' on that date did not"
            " apply then: say when it starts. If no source rule on the topic was in force on that date, say plainly that"
            " our sources don't include the older rule, so you can't give the figure for that date. Never give a later"
            " rule's figure as the figure for that date."
        )
    if stated:
        notes.append(
            f"BUILDING FACTS the person stated: built {stated['year_built']}"
            + (f", {stated['units']} units" if stated["units"] else ", unit count not given")
            + ". The ENGINE lines apply each rule to these facts: follow them and never decide coverage yourself."
        )
    if no_place:
        notes.append(
            "PLACE is not given: give the per-state picture in one short cited sentence, then ask where."
        )
    if PREEMPT.search(q) and items:
        notes.append(
            "The question asks whether one rule overrides or conflicts with another. Answer only from the "
            "'Conflict note' lines: say plainly that they may conflict and that it is not decided; never "
            "decide it yourself."
        )
    if chat:
        notes.append(
            "No SOURCES this turn: reply kindly in one or two sentences about what you can help with. "
            "State no law."
        )
    helps = _help_for(place, address_id, STORE)
    system = system_prompt(lang, as_of)
    if R.get("followup"):
        notes.append(
            f"Read with the conversation, the question is about (untrusted): <q>{q[:600]}</q>"
        )
    prompt = build_prompt(
        R.get("q") or q,
        items,
        place,
        address_id,
        as_of,
        " ".join(notes),
        R.get("history") or [],
        helps,
    )
    extra = prompt.split("SOURCES:")[0]
    city_j = (
        place.get("jurisdiction")
        if place and place.get("kind") == "city"
        else (place.get("jurisdiction") if place and place.get("kind") == "address" else None)
    )
    shown = {"key": None}

    def on_text(text: str) -> None:  # stream validated sentences as soon as they are complete
        pv = validate(
            partial_json(text),
            items,
            q,
            as_of,
            lang,
            extra,
            address=bool(address_id or stated),
            partial=True,
            chat=chat,
            city=city_j,
            scope_local=bool(scope_note),
        )
        if not (pv["answer"] or pv["parts"]):
            return
        key = (pv["answer"], len(pv["parts"]))
        if key != shown["key"]:
            shown["key"] = key
            num = {i: n + 1 for n, i in enumerate(pv["cites"])}
            emit("partial", {"answer": pv["answer"], "parts": _numbered(pv["parts"], num)})

    try:
        out = call_model(
            system, prompt, persist, on_text, wait=wait, background=bool(R.get("background"))
        )
        llm_error = False
    except Exception:  # noqa: BLE001 - busy, out of budget, timed out: the deterministic answer instead
        out, llm_error = {}, True
    if llm_error:
        if chat or (no_place and not items):
            return {
                **_refusal(
                    "source" if is_rental(q) else "topic",
                    lang,
                    _official(official_j, STORE),
                    (place or {}).get("label", ""),
                ),
                "_nocache": True,
            }
        if no_place:
            return {**chooser(cats, lang, as_of, STORE), "_nocache": True}
        res = _sources_only(
            items, lang, place, address_id, as_of, q=R.get("q") or q, asked=bool(R.get("asked"))
        )
        if "rent_increase_limits" in (
            cats or []
        ):  # the dollar maths by code, no model needed (eval DM1)
            from web import ask_increase as INC

            said = f"{R.get('standalone') or ''} {R.get('q') or q}"
            money = INC.parse_money(R.get("q") or q) or INC.parse_money(said)
            line = INC.money_line(
                money,
                (INC.parse_increases(R.get("q") or q) or INC.parse_increases(said) or {}).get(
                    "pcts"
                )
                or [],
                lang,
            )
            if line:
                res["parts"] = [{"text": line, "cites": []}] + (res.get("parts") or [])
            if computed:  # the cap check is code too: its verdict leads (eval DM1)
                rid = computed["c"].get("rule_id")
                n = next((c["n"] for c in res.get("citations") or [] if c["id"] == rid), None)
                res["answer"] = computed["answer"]
                if computed["why"] and n:
                    res["parts"].insert(1 if line else 0, {"text": computed["why"], "cites": [n]})
        res["_nocache"] = True
        return res
    v = validate(
        out if isinstance(out, dict) else {},
        items,
        q,
        as_of,
        lang,
        extra,
        address=bool(address_id or stated),
        chat=chat,
        city=city_j,
        scope_local=bool(scope_note),
    )
    if lang == "es" and _english(" ".join([v["answer"]] + [x["text"] for x in v["parts"]])):
        # the model answered a Spanish question in English (eval ES05): the fixed Spanish answer instead
        res = _sources_only(
            items, lang, place, address_id, as_of, q=R.get("q") or q, asked=bool(R.get("asked"))
        )
        res["_nocache"] = True
        return res
    by_id = {e["id"]: e for e in items}
    out_rules = [
        e
        for e in items
        if address_id
        and e["kind"] == "rule"
        and (e.get("engine") or {}).get("result") == "excluded"
        and e.get("category") in (cats or [e.get("category")])
    ]
    if (
        out_rules
        and not any(out_rules[0]["id"] in x["cites"] for x in v["parts"])
        and not any(
            (by_id.get(i, {}).get("engine") or {}).get("result") in ("applies", "unknown")
            for x in v["parts"]
            for i in x["cites"]
            if by_id.get(i, {}).get("category") == out_rules[0].get("category")
            and by_id.get(i, {}).get("kind") == "rule"
        )
    ):  # an exempt building: the engine's reason, cited (eval AD12, rounds 9 and 16)
        e = out_rules[0]
        v["parts"].insert(0, {"text": _exempt_line(e, lang), "cites": [e["id"]]})
        if e["id"] not in v["cites"]:
            v["cites"].insert(0, e["id"])
    if address_id and not any(
        x["cites"] for x in v["parts"]
    ):  # the engine's "it depends on ..." is always said
        unk = sorted(
            (
                e
                for e in items
                if e["kind"] == "rule"
                and e.get("status") == "in_force"
                and (e.get("engine") or {}).get("result") == "unknown"
                and e["engine"].get("missing_fact")
            ),
            key=lambda e: e.get("level") == "state",
        )
        if unk:
            e = unk[0]
            text = (FALLBACK_PLAIN.get(e["id"]) or {}).get(lang) or _first_sentence(
                e.get("requirement")
            )
            text = TXT[lang]["depends"].format(f=e["engine"]["missing_fact"].lower()) + (
                " " + text if text else ""
            )
            v["parts"].insert(0, {"text": text, "cites": [e["id"]]})
            if e["id"] not in v["cites"]:
                v["cites"].insert(0, e["id"])
    _date_conflict(v, by_id, R.get("q") or q, lang)
    if computed:  # the verdict is the computation's; model sentences that disagree with it go
        rid = computed["c"].get("rule_id")
        if rid and rid not in by_id:
            e = evidence_item(STORE, rid, as_of, lang)
            if e:
                items.append(e)
                by_id[rid] = e
        if rid in by_id and rid not in v["cites"]:
            v["cites"].insert(0, rid)
        over = computed["c"]["verdict"] == "over"
        okv = computed["c"]["verdict"] == "ok"
        keep_parts = []
        for x in v["parts"]:
            allow, deny = bool(ALLOW.search(x["text"])), bool(DENY.search(x["text"]))
            if (
                (over and allow and not deny and not NEGATION.search(x["text"]))
                or (okv and deny and not allow)
                or (
                    okv and re.match(r"No\b[.,]", x["text"])
                )  # "No. ..." under a computed yes (eval DM4)
                or (over and re.match(r"Yes\b[.,]", x["text"]))
            ):
                v["dropped"].append(
                    {
                        "text": x["text"],
                        "cites": x["cites"],
                        "why": "disagrees with the computed check",
                    }
                )
                continue
            keep_parts.append(x)
        v["parts"] = (
            [{"text": computed["why"], "cites": [rid] if rid in by_id else []}]
            if computed["why"]
            else []
        ) + keep_parts[:3]
        v["answer"] = computed["answer"]
    if (
        not chat
        and v["answer"]
        and (
            v["ask"]
            or (
                re.search(
                    r"\bnot in (?:my|our) sources|\bdon't have (?:that|this)", v["answer"], re.I
                )
                and cats
            )
        )
        and not any(x["cites"] for x in v["parts"])
        and any(e["kind"] == "rule" for e in items)
    ):  # a headline and a question only: the quoted rule's own sentence, cited (eval R11, round 19)
        so = _sources_only(
            items, lang, place, address_id, as_of, q=R.get("q") or q, asked=bool(R.get("asked"))
        )
        num = {c["n"]: c["id"] for c in so.get("citations") or []}
        for x in (so.get("parts") or [])[:1]:
            ids_ = [num[n] for n in x["cites"] if n in num]
            if ids_:
                v["parts"].insert(0, {"text": x["text"], "cites": ids_})
                for i in ids_:
                    if i not in v["cites"]:
                        v["cites"].append(i)
    if (
        not chat
        and not computed
        and v["answer"]
        and not re.search(  # an honest "not in my sources" stays as it is
            r"\b(?:don't|do not|doesn't|does not) (?:have|say|cover)|\bnot in (?:my|our) sources|\bno (?:est[aá]|tengo|dicen)\b",
            v["answer"],
            re.I,
        )
        and not (v["ask"] or v["steps"])
        and not any(x["cites"] for x in v["parts"])
        and any(e["kind"] == "rule" for e in items)
    ):  # every cited sentence was dropped: the quoted rules instead of a bare headline (eval D01)
        res = _sources_only(
            items, lang, place, address_id, as_of, q=R.get("q") or q, asked=bool(R.get("asked"))
        )
        if res.get("parts"):
            res["_nocache"] = True
            return res
    if (
        not chat
    ):  # the dollar arithmetic of a stated rent, by code (persona Keisha): never a verdict
        from web import ask_increase as INC

        said = f"{R.get('standalone') or ''} {R.get('q') or q}"
        money = INC.parse_money(R.get("q") or q) or INC.parse_money(said)
        line = INC.money_line(
            money,
            (INC.parse_increases(R.get("q") or q) or INC.parse_increases(said) or {}).get("pcts")
            or [],
            lang,
        )
        if line:
            v["parts"].insert(0, {"text": line, "cites": []})
    if (
        not chat
        and not computed
        and not v["answer"]
        and re.search(r"\b(?:maximum|max|how much|m[aá]ximo|cu[aá]nto)\b", R.get("q") or q, re.I)
        and any(
            d.get("cites") for d in v["dropped"]
        )  # the model wrote about the rule, and that went
        and not any(
            re.search(
                r"[$%]|\d|\b(?:one|two|three|half|un|dos|tres) (?:months?|mes(?:es)?)\b",
                x["text"],
                re.I,
            )
            for x in v["parts"]
            if x["cites"]
        )
    ):  # an amount question whose figure sentences were all dropped: the quoted rule with the figure (eval F01)
        res = _sources_only(
            items, lang, place, address_id, as_of, q=R.get("q") or q, asked=bool(R.get("asked"))
        )
        if res.get("answer") and res.get("parts"):
            audit(R, lang, as_of, items, v, STORE)
            res["_nocache"] = True
            return res
    if (
        not chat and not v["answer"] and not str((out or {}).get("answer") or "").strip()
    ):  # the model left the headline empty: never an empty card head (the demo question, 08:43)
        v["answer"] = _fill_headline(v["parts"], lang, as_of)
    audit(R, lang, as_of, items, v, STORE)
    if chat and not (v["answer"] or v["parts"] or v["ask"]):
        return _refusal(  # a renting question we hold no rule for is "not in my sources", not off-topic
            "source" if is_rental(q) else "topic",
            lang,
            _official(official_j, STORE),
            (place or {}).get("label", ""),
        )
    if (
        not chat
        and items
        and not (v["answer"] or v["parts"] or v["ask"] or v["steps"])
        and any(d.get("cites") for d in v["dropped"])
    ):  # the model used the sources but every sentence went: the quoted rules (eval DT04, round 9)
        res = _sources_only(
            items, lang, place, address_id, as_of, q=R.get("q") or q, asked=bool(R.get("asked"))
        )
        if res.get("parts"):
            res["_nocache"] = True
            return res
    if no_place and not (v["answer"] or v["parts"] or v["ask"] or v["steps"]):
        return {
            **chooser(cats, lang, as_of, STORE),
            "_nocache": True,
        }  # ask where, never 'none covers this' (MT1)
    if not (v["answer"] or v["parts"] or v["ask"] or v["steps"]):
        r = _refusal(
            "source", lang, _official(official_j or [e["jurisdiction"] for e in items[:1]], STORE)
        )
        r["place"] = place
        return r
    by_id = {e["id"]: e for e in items}
    num = {i: n + 1 for n, i in enumerate(v["cites"])}
    res = {
        "kind": "answer",
        "answer": v["answer"],
        "answer_cites": [],
        "parts": _numbered(v["parts"], num),
        "ask": v["ask"] or None,
        "steps": _numbered(v["steps"], num),
        "help": [
            {"id": h, "label": HELP[h][0], "url": HELP[h][1]} for h in v["help"] if h in helps
        ],
        "body": [],
        "citations": [{**by_id[i], "n": num[i]} for i in v["cites"]],
        "followups": [],
        "_cands": v["followups"],
        "place": {**place, "image": _slug(place.get("city"))} if place else None,
        "engine_checked": bool(address_id),
        "scope_note": scope_note or None,
        "official": _official(official_j, STORE) if scope_note else None,
        "memo": _memo(v),
    }
    if no_place:
        ch = chooser(
            cats, lang, as_of, STORE, WHERE[lang]["geo_failed"] if R["geo_failed"] else None
        )
        res.update(
            {
                "quick": ch["options"],
                "address_label": ch["address_label"],
                "note": ch["note"],
                "context": {"cats": cats, "place": None, "awaiting": True},
            }
        )
    if chat or not v["cites"]:
        res["_verified"], res["followups"] = True, SUGGEST[lang][:3] if chat else []
    return res


WHEN_Q = re.compile(
    r"\b(?:when|what date|since when|take effect|took effect|start(?:ed|s)?|begin|began|cu[aá]ndo|desde cu[aá]ndo|entr[oó] en vigor)\b",
    re.I,
)


def _date_conflict(v: dict, by_id: dict, q: str, lang: str) -> None:
    """'When did it take effect?' for a rule whose sources give two start dates: say both (eval A04)."""
    if not WHEN_Q.search(q):
        return
    for i in [i for x in v["parts"] for i in x["cites"]] or v["cites"]:
        note = str((by_id.get(i) or {}).get("conflict_note") or "")
        m = re.match(
            r"Two (?:published )?effective dates(?: published)?(?: for [^:]*)?:\s*([^.;]+)", note
        )
        if not m:
            continue
        dates = [
            _iso_dates(re.sub(r"\s*\([^)]*\)", "", d).strip(), lang)
            for d in re.split(r"\s+(?:vs\.?|and|or)\s+", m.group(1))
        ]
        said = " ".join([v["answer"]] + [x["text"] for x in v["parts"]])
        if len(dates) < 2 or all(d in said for d in dates):
            return
        joined = (" or " if lang == "en" else " o ").join(dates)
        v["parts"].append(
            {
                "text": f"Published sources give two start dates: {joined}."
                if lang == "en"
                else f"Las fuentes publicadas dan dos fechas de inicio: {joined}.",
                "cites": [i],
            }
        )
        if i not in v["cites"]:
            v["cites"].append(i)
        if v["answer"] and not re.search(r"differ|two|difieren|dos", v["answer"], re.I):
            v["answer"] = v["answer"].rstrip(".") + (
                " (sources differ)." if lang == "en" else " (las fuentes difieren)."
            )
        return


def _out_of_range(found: dict, lang: str) -> dict:
    a, b = fmt_date(MIN_DATE, lang), fmt_date(MAX_DATE, lang)
    T = {
        "en": (
            "I can only answer for dates from {a} to {b}.",
            "You asked about {d}. Ask again with a date in that range, or without a date for today.",
        ),
        "es": (
            "Solo puedo responder para fechas del {a} al {b}.",
            "Preguntó por el {d}. Pregunte de nuevo con una fecha en ese rango, o sin fecha para hoy.",
        ),
    }[lang]
    return {
        "kind": "refusal",
        "reason": "date",
        "quiet": True,
        "answer": T[0].format(a=a, b=b),
        "answer_cites": [],
        "body": [{"text": T[1].format(d=fmt_date(found["iso"], lang)), "cites": []}],
        "citations": [],
        "official": None,
        "followups": SUGGEST[lang][:3],
        "_verified": True,
    }


_URGENT_ALWAYS = re.compile(
    r"\b(?:locked me out|changed the locks|lock(?:ed)? me out|lockout|shut off (?:my |the )?(?:water|power|heat|gas|electricity|utilities)"
    r"|(?:water|power|heat|gas|electricity|utilities) (?:was |were |is |are )?(?:shut|cut) off|sheriff|marshal"
    r"|cambi[oó] (?:las )?cerraduras|me dej[oó] fuera|cort[oó] (?:el agua|la luz|el gas)"
    r"|threw (?:out )?my (?:things|stuff|belongings)|tir[oó] mis cosas)\b",
    re.I,
)
_URGENT_PAPER = re.compile(
    r"\b(?:court date|summons|eviction notice|notice to quit|\d+[- ]day notice|notice to pay or quit|pay or quit|court papers"
    r"|eviction hearing|aviso de desalojo|orden de desalojo|cita en la corte|papeles de la corte)\b",
    re.I,
)
# the person has the paper (or it has a date): "I got / I have / my landlord gave me / served / due by", not "does a landlord have to file an eviction notice?"
_HAVE = re.compile(
    r"\b(?:i got|i received|i have|i've got|got a|got an|received a|received an|gave me|served me|handed me|on my door|my (?:landlord|owner)\b.*\b(?:gave|sent|served|filed)"
    r"|hearing (?:is )?on|by (?:\w+ )?\d|today|tomorrow|recib[ií]|me dieron|me entreg|tengo (?:un|una)|me lleg[oó])\b",
    re.I,
)


class _Urgent:
    def search(self, q: str):
        return _URGENT_ALWAYS.search(q) or (_URGENT_PAPER.search(q) and _HAVE.search(q))


URGENT = _Urgent()
LAW_NAME = re.compile(
    r"\b((?:the )?(?:[A-Z][\w'-]+ ){1,6}(?:Act|Ordinance|Law|Bill)(?: of (?:19|20)\d{2})?"
    r"|(?:AB|SB|HB|Prop(?:osition)?\.?) ?\d{1,5}|Measure [A-Z]{1,3})\b"
)
FEDERAL = re.compile(
    r"\b(?:federal|nationwide|national|congress|biden|trump|white house|hud capped|federal government|todo el pa[ií]s|gobierno federal)\b",
    re.I,
)


def _premise_parts(q: str, named: list[str], lang: str) -> list[dict]:
    """Premises the sources can't back, corrected first: a law name we don't have, a federal rule."""
    out = []
    names = [
        m.group(1)
        for m in LAW_NAME.finditer(q)
        if not re.match(r"(?i)^(?:the )?(?:Fair Housing|Tenant)$", m.group(1))
    ]
    unknown = [n for n in names if not named_rules(n)]
    if unknown:
        out.append({"text": TXT[lang]["no_law"].format(n=unknown[0].strip()), "cites": []})
    if FEDERAL.search(q) and re.search(r"\b(?:rent|cap|limit|control|renta|tope)\b", q, re.I):
        out.append({"text": TXT[lang]["no_federal"].format(n=len(CITY_ALIASES)), "cites": []})
    return out


def strip_place_words(q: str) -> str:
    t = " " + fold(q) + " "
    for n in PLACE_PHRASES:
        t = re.sub(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", " ", t)
    return re.sub(r"\d+\w*", " ", t)


def _place_ack(address_id, place, lang, store) -> dict:
    """'I live at 3515 Fillmore St in San Francisco': noted, and the six topics as chips for that place."""
    if address_id:
        a = store.addresses[address_id]
        label = f"{_title(a['street_address'])}, {a.get('resolved_city') or a['postal_city']}"
        pl = {"kind": "address", "address_id": address_id, "label": label}
    else:
        label, pl = (
            place["label"],
            {k: place.get(k) for k in ("kind", "jurisdiction", "state", "local", "label")},
        )
    T = TXT[lang]
    return {
        "kind": "answer",
        "intent": "place",
        "quiet": True,
        "answer": T["place_ack"].format(p=label),
        "answer_cites": [],
        "parts": [{"text": T["place_ack_b"], "cites": []}],
        "body": [],
        "citations": [],
        "followups": T["topic_qs"],
        "_verified": True,
        "context": {"cats": [], "place": pl, "awaiting": False},
    }


def _safety(res: dict, R: dict, q: str, lang: str, store, as_of: str | None = None) -> dict:
    """Applied to every reply, the model's, the fallback's and refusals alike (the eval: a busy box once answered a
    lockout with rent-control lines): urgent situations get 'get help today' first, with the help offices for the
    place; premises the sources can't back are corrected first."""
    if res.get("reason") in ("evasion", "date"):
        return res
    T = TXT[lang]
    hz = data_horizon(store)
    when = as_of or res.get("as_of")
    if when and when > hz and res.get("kind") == "answer" and not res.get("intent"):
        note = {"text": T["horizon"].format(d=fmt_date(hz, lang)), "cites": []}
        res = {**res, "parts": (res.get("parts") or []) + [note]}
    if URGENT.search(q):
        pl = res.get("place") or {}
        helps = _help_for(pl or None, R.get("address_id"), store)[:3]
        lead = [{"text": T["urgent"], "cites": []}]
        if COURT.search(q):
            lead.append({"text": T["court"], "cites": []})
        if res.get("kind") == "refusal" or res.get("degraded"):
            # no model this time: the fixed urgent reply, the quotes of the rules found stay one tap away
            res = {
                **res,
                "kind": "answer",
                "reason": None,
                "answer": T["urgent_a"],
                "parts": lead,
                "body": [],
                "quiet": False,
                "official": None,
            }
        else:
            res = {**res, "parts": lead + (res.get("parts") or [])}
            if not res.get("answer"):
                res["answer"] = T["urgent_a"]
        have = {h["id"] for h in res.get("help") or []}
        res["help"] = (res.get("help") or []) + [
            {"id": h, "label": HELP[h][0], "url": HELP[h][1]} for h in helps if h not in have
        ]
        res["urgent"] = True
    if res.get("kind") == "answer" and not res.get("intent"):
        pre = _premise_parts(q, R.get("named") or [], lang)
        if pre:
            rest = [
                p
                for p in res.get("parts") or []
                if not re.match(
                    r"I don't have a law (?:by that name|called)|No tengo una ley", p["text"]
                )
            ]
            res = {**res, "parts": pre + rest}
    return res


def data_horizon(store) -> str:
    """The last date the sources describe: the latest effective date, sunset or figure period in the data."""
    from web import headlines as H

    key = getattr(store, "_sig", None)
    if _HORIZON.get("key") != key:
        ds = []
        for r in store.rules.values():
            for k in (
                "effective_date",
                "sunset_date",
                "current_version_effective",
                "in_force_since",
            ):
                v = str(r.get(k) or "")
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v[:10]):
                    ds.append(v[:10])
        for d in H.HEADLINES.values():
            ds += [d[k] for k in ("until", "from") if d.get(k)]
        _HORIZON.update(key=key, date=max(ds) if ds else MAX_DATE)
    return _HORIZON["date"]


_HORIZON: dict = {}
COURT = re.compile(r"\b(?:court|hearing|summons|tribunal|audiencia|corte|citaci[oó]n)\b", re.I)


def _evasion(q, lang, as_of, jurs, cats, place, address_id, official_j, store) -> dict:
    """A kind refusal for questions that ask how to get around a rule: the rules themselves, quoted, and help."""
    hits = index().search(q, jurs, cats)
    items = [
        e
        for e in (
            evidence_item(store, it["id"], as_of, lang)
            for _s, it in hits[:6]
            if it["kind"] == "rule"
        )
        if e
    ][:3]
    T = TXT[lang]
    helps = _help_for(place, address_id, store)
    return {
        "kind": "refusal",
        "reason": "evasion",
        "answer": T["ev"],
        "answer_cites": [],
        "body": [{"text": T["ev_b"], "cites": [n + 1 for n in range(len(items))]}],
        "citations": [{**e, "n": n + 1} for n, e in enumerate(items)],
        "official": _official(official_j or [e["jurisdiction"] for e in items[:1]], store),
        "help": [{"id": h, "label": HELP[h][0], "url": HELP[h][1]} for h in helps[:2]],
        "place": {**place, "image": _slug(place.get("city"))} if place else None,
        "followups": [],
        "_verified": True,
    }


AUDIT_FILE = Path(
    os.environ.get(
        "NAVIGATOR_ASK_AUDIT", Path(__file__).resolve().parent.parent / "output" / "ask_audit.jsonl"
    )
)
_AUDIT_LOCK = threading.Lock()
_PHONE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_STREET = re.compile(
    r"\b\d{1,6}[a-z]?(?:\s*-\s*\d{1,6})?\s+(?:[A-Za-z0-9.'-]+\s+){0,4}?"
    r"(?:st|street|ave|av|avenue|blvd|boulevard|rd|road|dr|drive|way|pl|place|ct|court|ln|lane|ter|terrace|pkwy|sq|cir)\b\.?",
    re.I,
)


def redact(text: str, address_id: str | None = None) -> str:
    """No personal data in the audit log: e-mails, phone numbers, street addresses and unit numbers go (a matched
    sample address is kept as its public id)."""
    t = _EMAIL.sub("[email]", text or "")
    t = _PHONE.sub("[phone]", t)
    t = _STREET.sub(f"[address {address_id}]" if address_id else "[address]", t)
    t = re.sub(r"\b(?:apt|apartment|unit|#)\s*\d+\w*\b", "[unit]", t, flags=re.I)
    return t[:600]


def audit(R: dict, lang: str, as_of: str, items: list[dict], v: dict, store) -> None:
    """The brief: an auditable log of sources, model outputs and changes. One line per model answer."""
    addr = R.get("address_id")
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "prompt_sha": hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest()[:12],
        "model": f"claude-cli:{MODEL}",
        "lang": lang,
        "as_of": as_of,
        "question": redact(R.get("q") or "", addr),
        "turn": len(R.get("history") or []) + 1,
        "place": _place_key(R, store) or None,
        "topics": R.get("cats"),
        "retrieved": [e["id"] for e in items],
        "engine": {e["id"]: e["engine"]["result"] for e in items if e.get("engine")},
        "answer": redact(_memo(v), addr),
        "steps": [redact(x["text"], addr) for x in v.get("steps") or []],
        "cited": v.get("cites"),
        "dropped": [{**d, "text": redact(d["text"], addr)} for d in v.get("dropped") or []],
    }
    try:
        with _AUDIT_LOCK, AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        log.warning("ask: audit log not writable")


def _numbered(parts: list[dict], num: dict) -> list[dict]:
    return [{"text": p["text"], "cites": [num[i] for i in p["cites"] if i in num]} for p in parts]


def _memo(v: dict) -> str:
    """What the helper said, as plain text for the next turn's CONVERSATION (the client sends it back)."""
    t = " ".join([v["answer"], *[p["text"] for p in v["parts"]], v["ask"] or ""]).strip()
    return t[:700]


def _trim(items: list[dict], cats: list[str], k: int = TOP_K) -> list[dict]:
    """At most TOP_K items; for an address keep what applies first."""
    rank = {
        "applies": 0,
        "unknown": 1,
        "superseded": 2,
        "not_yet_effective": 3,
        "excluded": 4,
        "no_rule": 5,
        "pending": 6,
        "failed": 7,
    }
    if items and items[0].get("engine"):
        items = sorted(items, key=lambda e: rank.get(e["engine"]["result"], 9))
    seen, out = set(), []
    for e in items:
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e)
    return out[:k]


GLOSSARY = [  # what an everyday term means in the rules, so the asked case gets the matching branch
    (
        re.compile(r"\bmonth[- ]to[- ]month\b|\bmes a mes\b", re.I),
        "A month-to-month tenancy is a tenancy at will with rent paid every month (an interval under three months): use"
        " the branch for rent paid at intervals under three months, not the three-month rule.",
    ),
    (
        re.compile(r"\bno lease\b|\bwithout a lease\b|\bsin contrato\b", re.I),
        "Without a lease the tenancy is a tenancy at will.",
    ),
]
FALLBACK_PLAIN = {
    "CA-RENT-01": {  # the eval: "once a year", "each increase capped", "for two years" all drift from 1947.12(a)
        "en": "Over any 12 months, rent can go up at most 5% plus inflation or 10%, whichever is lower, in total, in up to two increases.",
        "es": "En cualquier periodo de 12 meses, la renta puede subir como máximo un 5% más la inflación o un 10%, lo que sea menor, en total, en hasta dos aumentos.",
    },  # legal review 2026-10-04: where a rule's first sentence alone would mislead
    "MA-EVIC-02": {
        "en": "Without a lease (a tenancy at will), either party may end it with written notice of one rent period or 30 days, whichever is longer, or three months if rent is paid every three months or less often.",
        "es": "Sin contrato (arrendamiento a voluntad), cualquiera de las partes puede terminarlo con aviso escrito de un período de renta o 30 días, lo que sea mayor, o tres meses si la renta se paga cada tres meses o con menos frecuencia.",
    },
}


def _first_sentence(t: str | None) -> str:
    t = (t or "").strip()
    m = re.match(r"(.+?[.!?])(?:\s|$)", t)
    return (m.group(1) if m else t)[:260]


def _best_sentence(t: str | None, q: str) -> tuple[str, bool]:
    """The requirement sentence that matches the question ('how long ... return' -> the 21-day sentence), whole;
    and whether it is the first one (the headline sums up the first)."""
    sents = _split_sentences(t or "") or [""]
    qt = {w for w in tokens(q) if len(w) > 3}
    best = max(range(len(sents)), key=lambda n: (len(qt & set(tokens(sents[n]))), -n))
    return sents[best][:400], best == 0


def _fill_headline(parts: list[dict], lang: str, as_of: str) -> str:
    """The model left the headline empty: the first cited sentence when it is short enough. Never a rule's generic
    headline (it can be the state's rule where a city's own rule governs); nothing new is written."""
    for x in parts:
        if not x.get("cites"):
            continue
        first = (_split_sentences(x["text"]) or [""])[0].strip()
        return first if first and len(first.split()) <= 16 else ""
    return ""


def _exempt_line(c: dict, lang: str) -> str:
    """'Hoboken Rent Control Ordinance doesn't cover this building. Built 2001: exempt as new construction ...'"""
    why = (c.get("engine") or {}).get("explanation") if lang == "en" else ""
    if lang == "en":
        return f"{c.get('title_en') or c['title']} doesn't cover this building." + (
            f" {why[:1].upper()}{why[1:]}." if why else ""
        )
    return f"{c['title']} no cubre este edificio."


COVER_Q = re.compile(
    r"\b(?:covered|cover|covers|apply|applies|rent[- ]controlled|rent control|protected|cubiert[oa]|aplica\w*|control de renta)\b",
    re.I,
)


LAW_Q = re.compile(
    r"\b(?:illegal|legal|banned|ban|allowed|still|repeal\w*|expire\w*|sunset|will|ilegal|prohibid\w*|todav[ií]a)\b",
    re.I,
)


def _year_dependent(rid: str) -> bool:
    cov = (ask_store().rules.get(rid) or {}).get("coverage") or {}
    return bool(cov.get("construction_cutoff") or cov.get("new_construction_exemption"))


def _sources_only(
    items, lang, place, address_id, as_of=None, q: str = "", asked: bool = True
) -> dict:
    """No model this time (busy, over budget, timed out): the rules engine's fixed one-line answer and the plain
    requirement of the deciding rules, each with its quote. No error text: it is a real, if shorter, answer."""
    from web import headlines as H
    from web.app import DEFAULT_AS_OF

    as_of = as_of or DEFAULT_AS_OF
    rank = {"applies": 0, "unknown": 1, "not_yet_effective": 2, "superseded": 3}
    rules = [
        e
        for e in items
        if e["kind"] == "rule"
        and (e.get("engine") or {}).get("result")
        not in ("excluded", "failed", "pending", "superseded")
    ]
    qt = {w for w in tokens(q) if len(w) > 3}
    how_much = bool(
        re.search(r"\bhow much|\bhow many|\bcu[aá]nt[oa]s?\b|\bamount\b|\bmonto\b", q, re.I)
    )
    rules.sort(
        key=lambda e: (
            rank.get((e.get("engine") or {}).get("result"), 0 if not e.get("engine") else 5),
            # "how much": the rule with the figure first (eval E03: LA-EVIC-04, not the just-cause list)
            not (
                how_much and re.search(r"^\W*\d|[$%]", str(e.get("key_value") or ""))
            ),  # "1 month's rent" too
            # a state question: the state's own rule first (eval D01 on the no-model path)
            not ((place or {}).get("kind") == "state" and e.get("level") == "state"),
            -len(qt & set(tokens(f"{e.get('key_value') or ''} {e.get('requirement') or ''}"))),
            # the rule whose words match the question leads ("broker fee" -> MA-FEE-01, eval F05)
            (H.HEADLINES.get(e["id"]) or {}).get("priority") or 9,
        )
    )
    rules = [
        e for e in rules if e.get("status") == "in_force"
    ]  # never a rule that was not in force on the date
    top = rules[:2]
    out = [
        e
        for e in items
        if (e.get("engine") or {}).get("result") in ("excluded", "no_rule")
        and e.get("status") in ("in_force", "no_rule")
    ][:2]
    if (
        not top and address_id and out
    ):  # the engine left no rule on the topic: say why, never a blank card (eval AD12)
        cites = [{**e, "n": n + 1} for n, e in enumerate(out)]
        parts = []
        for c in cites:
            if c["engine"]["result"] == "excluded":
                text = _exempt_line(c, lang)
            else:
                text = _first_sentence(c.get("requirement"))
            if text:
                parts.append({"text": f"{c['jurisdiction_label']}: {text}", "cites": [c["n"]]})
        return {
            "kind": "answer",
            "answer": TXT[lang]["not_here"],
            "answer_cites": [],
            "parts": parts,
            "body": [],
            "citations": cites,
            "followups": [],
            "_verified": True,
            "place": {**place, "image": _slug(place.get("city"))} if place else None,
            "engine_checked": True,
            "degraded": True,
        }
    cites = [{**e, "n": n + 1} for n, e in enumerate(top)]
    hl = next((h for h in (H.headline(e["id"], lang, as_of) for e in top) if h), None)
    later = [
        e
        for e in items
        if e["kind"] == "rule" and e.get("status") in ("not_yet_effective", "older_version")
    ][:2]
    if (
        later
        and (asked or not top)  # no date asked and a rule in force: just that rule (eval ES08)
        and not any(e.get("status") == "in_force" and e.get("level") == "state" for e in top)
    ):
        # the main rule on the topic was not in force on that date: say so first, never its later figure
        T = {
            "en": "On {d} the rules in our sources didn't apply yet ({w}). Our sources don't include the older rule, so I can't give the figure for that date.",
            "es": "El {d} las normas de nuestras fuentes aún no se aplicaban ({w}). Nuestras fuentes no incluyen la norma anterior, así que no puedo dar la cifra para esa fecha.",
        }[lang]
        w = "; ".join(
            f"{e['jurisdiction_label']}: {('from' if lang == 'en' else 'desde')} {fmt_date(str(e.get('version_from') or e.get('effective_date'))[:10], lang)}"
            for e in later
            if re.match(
                r"\d{4}-\d{2}-\d{2}", str(e.get("version_from") or e.get("effective_date") or "")
            )
        )
        cites = [{**e, "n": n + 1} for n, e in enumerate(later + top[:1])]
        parts = [
            {
                "text": T.format(d=fmt_date(as_of, lang), w=w or "-"),
                "cites": list(range(1, len(later) + 1)),
            }
        ]
        for c in cites[len(later) :]:
            text = _first_sentence(c.get("requirement"))
            if text:
                parts.append({"text": f"{c['jurisdiction_label']}: {text}", "cites": [c["n"]]})
        return {
            "kind": "answer",
            "answer": "",
            "answer_cites": [],
            "body": [],
            "citations": cites,
            "parts": parts,
            "followups": [],
            "_verified": True,
            "degraded": True,
            "engine_checked": bool(address_id),
            "place": {**place, "image": _slug(place.get("city"))} if place else None,
        }
    parts = []
    state_later = [
        e
        for e in later
        if e.get("level") == "state"
        and e.get("status") == "not_yet_effective"
        and e.get("effective_date")
    ]
    n_top = len(cites)
    if (
        place
        and place.get("kind") == "state"
        and state_later
        and not any(e.get("level") == "state" for e in top)
    ):
        # a state question answered by city rules: the state law has not started (eval A05)
        e = state_later[0]
        d = fmt_date(str(e["effective_date"])[:10], lang)
        cites = cites + [{**e, "n": len(cites) + 1}]
        parts.append(
            {
                "text": (
                    f"{e['jurisdiction_label']}: the state law starts {d}; until then only these cities' own rules apply."
                    if lang == "en"
                    else f"{e['jurisdiction_label']}: la ley estatal empieza el {d}; hasta entonces solo aplican las normas propias de estas ciudades."
                ),
                "cites": [len(cites)],
            }
        )
        hl = None
    for c in cites[:n_top]:
        text, first = _best_sentence(c.get("requirement"), q)
        if not first and c is cites[0]:  # the headline speaks of another sentence of the rule
            hl = None
        text = ((FALLBACK_PLAIN.get(c["id"]) or {}).get(lang) if first else None) or text
        if (
            c.get("engine")
            and c["engine"].get("result") == "unknown"
            and c["engine"].get("missing_fact")
        ):
            text = TXT[lang]["depends"].format(f=c["engine"]["missing_fact"].lower()) + " " + text
        elif (
            not c.get("engine")
            and _year_dependent(c["id"])
            and c.get("category") in ("rent_increase_limits", "just_cause_eviction")
            and COVER_Q.search(q)
            and not LAW_Q.search(q)
            and not stated_facts(q)
        ):  # E04, DT08, T03 (round 11): not for notice duties, sunsets or "is rent control illegal?"
            # no building: coverage turns on the build year, say so first (brief audit R6, San Diego)
            dep = TXT[lang]["depends"].format(f=TXT[lang]["when_built"])
            text = f"{dep} {text}"
            if c is cites[0] and COVER_Q.search(q):
                hl = dep
        if text:
            parts.append({"text": f"{c['jurisdiction_label']}: {text}", "cites": [c["n"]]})
    if not hl and parts:  # never an empty headline: the first quoted sentence when it is short
        first = (_split_sentences(parts[0]["text"].split(": ", 1)[-1]) or [""])[0].strip()
        hl = first if first and len(first.split()) <= 14 else None
    return {
        "kind": "answer",
        "answer": hl or "",
        "answer_cites": [],
        "parts": parts,
        "body": [],
        "citations": cites,
        "followups": [],
        "_verified": True,
        "place": {**place, "image": _slug(place.get("city"))} if place else None,
        "engine_checked": bool(address_id),
        "degraded": True,
    }


# ------------------------------------------------------------------ endpoints
def _check_as_of(v: str | None) -> str | None:
    if v is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise HTTPException(400, "as_of must be YYYY-MM-DD")
    return v


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _ip(v: str) -> str | None:
    try:
        return str(ipaddress.ip_address(v.strip()))
    except ValueError:
        return None


def real_ip(request: Request) -> str:
    """The client's address for rate limits. Only our own proxy chain (Cloudflare -> cloudflared -> Caddy, all on
    this box) connects from loopback; its CF-Connecting-IP / X-Real-IP are set by Cloudflare and Caddy and cannot be
    chosen by the client. From X-Forwarded-For only the last hop counts (the one our proxy appended), never the
    client-supplied first entry. A non-loopback peer is used as it is: no header can override it."""
    peer = request.client.host if request.client else ""
    if peer not in LOOPBACK:
        return peer or "unknown"
    for h in ("cf-connecting-ip", "x-real-ip"):
        v = _ip(request.headers.get(h, ""))
        if v:
            return v
    xff = [x for x in request.headers.get("x-forwarded-for", "").split(",") if x.strip()]
    return (_ip(xff[-1]) if xff else None) or peer


@router.post("/api/ask")
def ask(body: AskIn, request: Request):
    ip = real_ip(request)
    if not ASK_LIMIT.allow(ip):
        raise HTTPException(429, TXT["es" if body.lang == "es" else "en"]["busy"])
    as_of = _check_as_of(body.as_of)
    hist = [h.model_dump() for h in body.history]
    if "text/event-stream" not in request.headers.get("accept", ""):
        res = answer(body.q, body.lang, as_of, history=hist, ip=ip, place=body.place)
        if not res.get("_verified"):
            res["followups"] = verify_chips(res)
        return _public(res)

    def stream():
        import queue

        qu: queue.Queue = queue.Queue()

        def emit(step, info):
            qu.put(("step", {"id": step, **(info or {})}))

        def work():
            try:
                res = answer(
                    body.q, body.lang, as_of, history=hist, emit=emit, ip=ip, place=body.place
                )
                pending = not res.get("_verified")
                qu.put(("answer", {**_public(res), "followups_pending": pending}))
                if pending:  # the answer is on screen; the checked follow-ups arrive a moment later
                    qu.put(("followups", {"followups": verify_chips(res)}))
            except HTTPException as e:
                qu.put(("error", {"status": e.status_code, "detail": e.detail}))
            except Exception:  # noqa: BLE001
                log.exception("ask failed")
                qu.put(("error", {"status": 500, "detail": "Something went wrong."}))
            qu.put(None)

        threading.Thread(target=work, daemon=True).start()
        yield ": ok\n\n"
        while True:
            try:
                item = qu.get(timeout=15)
            except Exception:  # noqa: BLE001 - keep the connection alive through proxies
                yield ": ping\n\n"
                continue
            if item is None:
                break
            ev, data = item
            yield f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


TOPIC_NAME = {
    "rent_increase_limits": "rent increase",
    "just_cause_eviction": "eviction",
    "security_deposits": "deposit",
    "application_screening_fees": "fees",
    "screening_restrictions": "screening",
    "algorithmic_rent_setting": "rent software",
}


def public_entry(e: dict) -> dict:
    """What reviewers see: no free text at all (a name or other detail typed into a question could survive redaction),
    only what the system did with it."""
    topics = [TOPIC_NAME.get(t, t) for t in e.get("topics") or []]
    place = e.get("place") or ""
    place_label = place.split(":")[0] if place else ""
    if place_label.startswith("A") and place_label[1:].isdigit():
        place_label = f"sample address {place_label}"
    kind = (
        (" / ".join(topics) or "general")
        + " question"
        + (f" · {place_label}" if place_label else "")
    )
    reasons = Counter(d.get("why", "") for d in e.get("dropped") or [])
    return {
        "ts": e.get("ts"),
        "model": e.get("model"),
        "prompt_sha": e.get("prompt_sha"),
        "lang": e.get("lang"),
        "as_of": e.get("as_of"),
        "turn": e.get("turn"),
        "question_type": kind,
        "topics": e.get("topics"),
        "place": place or None,
        "retrieved": e.get("retrieved") or [],
        "engine": e.get("engine") or {},
        "cited": e.get("cited") or [],
        "kept_steps": len(e.get("steps") or []),
        "dropped": len(e.get("dropped") or []),
        "dropped_reasons": dict(reasons),
    }


def audit_tail(limit: int) -> list[dict]:
    """The last `limit` entries of the audit log, newest first (they are written redacted, see audit())."""
    try:
        with AUDIT_FILE.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 2_000_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
        if len(out) >= limit:
            break
    return out


@router.get("/api/ask/audit")
def ask_audit(limit: int = 50):
    """Read-only, for reviewers: the latest Ask answers as logged (questions redacted, no personal data)."""
    limit = max(1, min(int(limit), 200))
    return {
        "entries": [public_entry(e) for e in audit_tail(limit)],
        "file": "output/ask_audit.jsonl",
        "limit": limit,
        "note": "No question or answer text is shown here; the server keeps a redacted copy. Not legal advice.",
    }


@router.get("/ask/audit", include_in_schema=False)
def ask_audit_page(limit: int = 50):
    """The same log as a plain page (linked from Sources > For reviewers)."""
    from html import escape as h

    from fastapi.responses import HTMLResponse

    rows = []
    for e in (public_entry(x) for x in audit_tail(max(1, min(int(limit), 200)))):
        reasons = "".join(f"<li>{h(w)}: {n}</li>" for w, n in e["dropped_reasons"].items())
        rows.append(
            f"<tr><td>{h(e['ts'] or '')}<br><small>{h(e['model'] or '')} · prompt {h(e['prompt_sha'] or '')}"
            f" · {h(e['lang'] or '')} · as of {h(e['as_of'] or '')}</small></td>"
            f"<td><b>{h(e['question_type'])}</b><br><small>turn {h(str(e['turn'] or ''))}</small></td>"
            f"<td><small>retrieved {h(', '.join(e['retrieved']))}<br>engine {h(json.dumps(e['engine']))}<br>"
            f"cited {h(', '.join(e['cited']))} · {e['kept_steps']} next steps</small></td>"
            f"<td><small>{e['dropped']} sentences removed</small>{'<ul>' + reasons + '</ul>' if reasons else ''}</td></tr>"
        )
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ask audit log · Clause &amp; Effect</title><meta name="robots" content="noindex">
<style>body{{font:14px/1.45 Inter,system-ui,sans-serif;margin:0;background:#f6f7f9;color:#0e1014}}main{{max-width:1240px;margin:0 auto;padding:28px 18px}}
h1{{font:400 34px/1.1 "Instrument Serif",Georgia,serif;margin:0 0 6px}}p{{color:#555;margin:0 0 18px}}table{{border-collapse:collapse;width:100%;background:#fff;border-radius:12px;overflow:hidden}}
td{{padding:10px 12px;border-top:1px solid #eee;vertical-align:top}}small{{color:#666}}ul{{margin:6px 0 0 16px;padding:0;color:#8f5200}}</style></head>
<body><main><h1>Ask: audit log</h1><p>The latest {len(rows)} model answers, newest first: what kind of question it was, the rules
retrieved, the engine's verdicts, the citations kept and how many sentences the checks removed, with the reasons. No question or answer
text is shown: the server keeps a redacted copy for audits. Read-only. JSON: <a href="/api/ask/audit?limit=50">/api/ask/audit</a>. Not legal advice.</p>
<table>{"".join(rows) or "<tr><td>No entries yet.</td></tr>"}</table></main></body></html>"""
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})


@router.get("/api/ask/suggest")
def suggest(lang: str = "en"):
    return {"questions": suggestions(lang if lang in SUGGEST else "en")}


def suggestions(lang: str) -> list[str]:
    """The fixed suggestions, plus one for each city added later (newest first), so it can be tried at once."""
    index()
    added = [j for j in CITY_ALIASES if j not in (_STATIC_CITIES or {})]
    extra = [
        (
            f"How much can my rent go up in {j.split(',')[0]}?"
            if lang == "en"
            else f"¿Cuánto me pueden subir la renta en {j.split(',')[0]}?"
        )
        for j in reversed(added)
    ][:2]
    base = SUGGEST[lang]
    return base[:3] + extra + base[3:]


# ------------------------------------------------------------------ pre-warm
PREWARM = {"done": 0, "total": 0, "running": False}


def prewarm(as_of: str | None = None) -> None:
    """Answer the suggested questions once, check their follow-up chips (which answers those too) and, for a
    suggestion without a place, the three state choices, so a judge's first taps are instant. Model answers are
    kept in cache/llm/ (questions we wrote ourselves, no personal data)."""
    qs = list(dict.fromkeys(suggestions("en") + suggestions("es")))
    PREWARM.update(running=True, total=len(qs), done=0)
    for q in qs:
        try:
            lg = "es" if q in SUGGEST["es"] and q not in SUGGEST["en"][:3] else detect_lang(q)
            r = answer(q, lg, as_of, persist=True)
            verify_chips(r, persist=True, deadline=120)
            if r.get("kind") == "choose":
                for o in [o for o in r["options"] if o["group"] == "state"]:
                    r2 = answer(o["q"], lg, as_of, history=[_hist_turn(r)], persist=True)
                    verify_chips(r2, persist=True, deadline=120)
        except Exception:  # noqa: BLE001
            log.exception("prewarm %s", q)
        PREWARM["done"] += 1
    PREWARM["running"] = False


if os.environ.get("NAVIGATOR_ASK_PREWARM", "1") == "1" and "pytest" not in sys.modules:
    _t = threading.Timer(3.0, prewarm)
    _t.daemon = True
    _t.start()
