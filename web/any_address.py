"""Any address, not just the 500 samples (#39): live geocode + user-supplied building facts. Not legal advice.

POST /api/resolve   {"address": "1685 Main St, Santa Monica, CA"}
    -> US Census geocoder (onelineaddress + geographies): state, county, incorporated place, and whether the
       place is one of our jurisdictions (main corpus or an extension such as Santa Monica).
POST /api/evaluate  {"address": {"state": "CA", "jurisdiction": "Santa Monica, CA"}, "as_of": "2026-10-01",
                     "facts": {"year_built": 1962, "units": 8, "owner_occupied": false,
                               "certificate_of_occupancy_date": null}}
    -> the address view's category shape (same items as /api/address/{id}); every unknown carries
       needs_fact (which fact resolves it), plus fact_counts / fact_depends for the facts form.

Privacy: addresses are never written to disk or logs. Geocoder answers stay in memory for 15 minutes (keyed by a
hash of the address) and only counters are kept. /api/evaluate does not see the street at all.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, OrderedDict, deque
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from navigator import user_facts as U
from navigator.config import STATES
from web import headlines as H

router = APIRouter()

CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
UA = "RentalHousingLawNavigator/0.1 (Hack-Nation hackathon prototype; contact via GitHub isaaclins)"
TIMEOUT = 8.0
CACHE_TTL = 15 * 60
CACHE_MAX = 256
STATE_NAMES = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}
FACT_LABELS = {
    "year_built": "Year built",
    "units": "Number of units",
    "owner_occupied": "Whether the owner lives in the building",
    "certificate_of_occupancy_date": "Certificate-of-occupancy date",
}
FACT_LABELS_ES = {
    "year_built": "Año de construcción",
    "units": "Número de unidades",
    "owner_occupied": "Si el dueño vive en el edificio",
    "certificate_of_occupancy_date": "Fecha del certificado de ocupación",
}
OTHER_ES = {
    "The source is only linked, not captured; check the official text.": "La fuente solo está enlazada, no guardada aquí; revise el texto oficial.",
    "Depends on whether the owner filed for the new-construction exemption.": "Depende de si el dueño pidió la exención para construcciones nuevas.",
}


def _missing_es(needs: list[str], other: str | None) -> str | None:
    """The missing fact in Spanish (Rules page, Check, any address); None keeps the English label."""
    if needs:
        return " o ".join(FACT_LABELS_ES[k] for k in needs)
    if other in OTHER_ES:
        return OTHER_ES[other]
    if other and other.startswith("Depends on: "):
        parts = [
            _web().STORE.t(x, "es") if _web().STORE.has_t(x, "es") else None
            for x in other[12:].rstrip(".").split("; ")
        ]
        if all(parts):
            return "Depende de: " + "; ".join(parts) + "."
    return None


STATS: Counter = Counter()  # counts only, never addresses
_UPSTREAM = threading.Semaphore(2)  # polite: at most two concurrent Census calls
# every US state (+ DC, PR), to name a state we don't cover when the geocoder finds no match ("…, Springfield, IL")
US_STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
COVERED_SENTENCE = "We cover California, New Jersey and Massachusetts."


def not_covered_message(name: str) -> str:
    return f"{name} isn't covered yet. {COVERED_SENTENCE}"


def state_in_text(address: str) -> str | None:
    """The state an address names at its end: ', IL', ', IL 62701', 'IL 62701', ', Illinois', 'Illinois 62701'."""
    a = address.strip().rstrip(".")
    m = re.search(r",\s*([A-Za-z]{2})\.?\s*(\d{5}(-\d{4})?)?$", a) or re.search(
        r"\s([A-Z]{2})\s+\d{5}(-\d{4})?$", a
    )
    if m and m.group(1).upper() in US_STATES:
        return m.group(1).upper()
    tail = re.sub(r"[\s,]*(\d{5}(-\d{4})?)?$", "", a).lower()
    for code, name in sorted(
        US_STATES.items(), key=lambda kv: -len(kv[1])
    ):  # "West Virginia" before "Virginia"
        n = name.lower()
        if tail.endswith(n) and (len(tail) == len(n) or not tail[-len(n) - 1].isalpha()):
            return code
    return None


# ------------------------------------------------------------------ rate limiting (in memory, per IP)
class RateLimit:
    def __init__(self, n: int, per: float) -> None:
        self.n, self.per = n, per
        self.hits: dict[str, deque] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.hits) > 5000:  # drop idle clients
                self.hits = {k: q for k, q in self.hits.items() if q and now - q[-1] < self.per}
            q = self.hits.setdefault(key, deque())
            while q and now - q[0] >= self.per:
                q.popleft()
            if len(q) >= self.n:
                return False
            q.append(now)
            return True


RESOLVE_LIMIT = RateLimit(20, 60.0)
EVALUATE_LIMIT = RateLimit(60, 60.0)


def client_ip(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    # behind our own tunnel/proxy: use the forwarded client address
    if host in ("127.0.0.1", "::1", "localhost"):
        fwd = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
        fwd = fwd.split(",")[0].strip()
        if fwd:
            return fwd
    return host


def _limit(rl: RateLimit, request: Request) -> None:
    if not rl.allow(client_ip(request)):
        STATS["rate_limited"] += 1
        raise HTTPException(429, "Too many lookups from this connection. Please wait a minute.")


# ------------------------------------------------------------------ geocoding
_cache: OrderedDict[str, tuple[float, dict | None]] = OrderedDict()
_cache_lock = threading.Lock()


def _norm_address(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def census_lookup(address: str) -> dict | None:
    """First Census match (with geographies) or None. Raises RuntimeError when the geocoder does not answer."""
    q = urllib.parse.urlencode(
        {
            "address": address,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "layers": "States,Counties,Incorporated Places",
            "format": "json",
        }
    )
    req = urllib.request.Request(f"{CENSUS}?{q}", headers={"User-Agent": UA})
    if not _UPSTREAM.acquire(timeout=TIMEOUT):
        raise RuntimeError("geocoder busy")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        raise RuntimeError(type(e).__name__) from None
    finally:
        _UPSTREAM.release()
    matches = (data.get("result") or {}).get("addressMatches") or []
    return matches[0] if matches else None


def geocode(address: str) -> dict | None:
    key = hashlib.sha256(address.lower().encode()).hexdigest()
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL:
            _cache.move_to_end(key)
            STATS["resolve_cached"] += 1
            return hit[1]
    m = census_lookup(address)
    with _cache_lock:
        _cache[key] = (now, m)
        while len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)
    return m


def interpret(m: dict) -> dict:
    """Census match -> jurisdiction stack and scope (city / state / none)."""
    g = m.get("geographies") or {}
    states = g.get("States") or []
    counties = g.get("Counties") or []
    places = g.get("Incorporated Places") or []
    st = states[0].get("STUSAB", "") if states else ""
    county = counties[0].get("NAME", "") if counties else ""
    place = places[0].get("BASENAME", "") if places else ""
    covered = U.covered_cities()
    jur = f"{place}, {st}" if place and f"{place}, {st}" in covered.get(st, []) else None
    ext = U.extension_cities().get(jur or "")
    scope = "city" if jur else "state" if st in STATES else "none"
    stack = [
        {
            "level": "state",
            "name": STATE_NAMES.get(st, states[0].get("NAME", st) if states else st),
            "code": st,
            "covered": st in STATES,
        }
    ]
    if county:
        stack.append(
            {
                "level": "county",
                "name": county,
                "covered": False,
                "note": "consolidated city-county"
                if place == "San Francisco"
                else "no county rules in our corpus",
            }
        )
    stack.append(
        {
            "level": "city",
            "name": place or "Unincorporated area",
            "covered": bool(jur),
            "jurisdiction": jur,
            **({"extension": ext} if ext else {}),
        }
    )
    if scope == "city":
        msg = f"{place} and {STATE_NAMES[st]} rules are in our corpus."
    elif scope == "state":
        where = place or (f"unincorporated {county}" if county else "this area")
        msg = (
            f"{STATE_NAMES[st]} state law is covered. Local rules of {where} are not in our corpus, "
            "and a city or county ordinance may add protections."
        )
    else:
        msg = not_covered_message(STATE_NAMES.get(st) or US_STATES.get(st) or "This state")
    c = m.get("coordinates") or {}
    return {
        "match": True,
        "matched_address": m.get("matchedAddress"),
        "lat": round(c["y"], 6) if "y" in c else None,
        "lon": round(c["x"], 6) if "x" in c else None,
        "state": st,
        "state_name": US_STATES.get(st) or (states[0].get("NAME") if states else None),
        "county": county,
        "place": place or None,
        "jurisdiction": jur,
        "extension": ext,
        "scope": scope,
        "in_scope": scope != "none",
        "stack": stack,
        "message": msg,
        "covered": covered,
        "source": "US Census Geocoder (Public_AR_Current), live",
    }


class ResolveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: str = Field(min_length=5, max_length=200)

    @field_validator("address")
    @classmethod
    def clean(cls, v: str) -> str:
        v = _norm_address("".join(ch for ch in v if ch.isprintable()))
        if len(v) < 5 or not re.search(r"[A-Za-z]", v):
            raise ValueError("enter a street address with city and state")
        return v


@router.post("/api/resolve")
def resolve(body: ResolveIn, request: Request):
    _limit(RESOLVE_LIMIT, request)
    STATS["resolve"] += 1
    try:
        m = geocode(body.address)
    except RuntimeError:
        STATS["upstream_error"] += 1
        raise HTTPException(
            503, "The US Census geocoder did not answer. Please try again in a moment."
        ) from None
    if not m:
        STATS["resolve_no_match"] += 1
        st = state_in_text(body.address)
        if (
            st and st not in STATES
        ):  # no match, but the address names a state we don't cover: say that
            return {
                "match": False,
                "out_of_area": True,
                "state": st,
                "state_name": US_STATES[st],
                "message": not_covered_message(US_STATES[st]),
                "covered": U.covered_cities(),
            }
        return {
            "match": False,
            "message": "We could not find this address. Add the city and state, e.g. '1685 Main St, Santa Monica, CA'.",
            "covered": U.covered_cities(),
        }
    out = interpret(m)
    STATS[f"resolve_scope_{out['scope']}"] += 1
    return out


# ------------------------------------------------------------------ evaluation
class FactsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year_built: int | None = Field(None, ge=1700, le=2100)
    units: int | None = Field(None, ge=1, le=5000)
    owner_occupied: bool | None = None
    certificate_of_occupancy_date: dt.date | None = None

    @field_validator("certificate_of_occupancy_date")
    @classmethod
    def co_range(cls, v):
        if v is not None and not (dt.date(1700, 1, 1) <= v <= dt.date(2100, 12, 31)):
            raise ValueError("certificate date out of range")
        return v


class PlaceIn(BaseModel):
    # the client may echo the resolve answer; only these fields are read
    model_config = ConfigDict(extra="ignore")
    state: str = Field(pattern=r"^[A-Z]{2}$")
    jurisdiction: str | None = Field(None, max_length=60)


class EvaluateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: PlaceIn
    as_of: dt.date | None = None
    facts: FactsIn = FactsIn()
    lang: Literal["en", "es"] = "en"


def _web():
    from web import app as W  # late import: web.app includes this router

    return W


def _overriders(rid: str, present: set[str], by_id: dict) -> list[str]:
    r = by_id.get(rid, {})
    res = [
        o
        for o in present
        if o != rid and rid in (by_id[o].get("overrides") or []) and by_id[o].get("level") == "city"
    ]
    if r.get("level") == "state":
        res += [
            o
            for o in r.get("overrides") or []
            if o in present and by_id.get(o, {}).get("level") == "city" and o not in res
        ]
    return res


def _excluded(
    d: dict, cid: str, present: set[str], by_id: dict, juris: set, lang: str
) -> list[dict]:
    """In-force rules here that these building facts rule out (same shape as web.app.excluded_rules), so a
    new-construction exemption reads as "exempt" and not as "no rule"."""
    from navigator import evaluate as NE

    W = _web()
    try:
        f = U.make_facts(d["state"], d["jurisdiction"], d["facts"])
        day = dt.date.fromisoformat(d["as_of"])
    except Exception:
        return []
    out = []
    for r in by_id.values():
        if (
            r.get("category") != cid
            or r["team_rule_id"] in present
            or r.get("jurisdiction") not in juris
        ):
            continue
        try:
            if NE.time_status(r, day) != "in_force":
                continue
            verdict, why = NE.coverage(r, f, day)
        except Exception:
            continue
        if verdict == NE.NO:
            out.append(
                {
                    "id": r["team_rule_id"],
                    "title": W.STORE.t(r.get("title"), lang),
                    "jurisdiction": r.get("jurisdiction"),
                    "level": r.get("level"),
                    "citation": r.get("citation"),
                    "reasons": why,
                }
            )
    return out


def build_view(d: dict, lang: str) -> dict:
    """navigator.user_facts output -> the categories shape of /api/address/{id} (web.app.build_address)."""
    W = _web()
    by_id, entries = d["rules"], d["results"]
    present = {e["team_rule_id"] for e in entries}
    juris = {d["state"], d["jurisdiction"]} - {None}
    cats, counts = [], Counter()
    for cid, label, question in W.CATEGORIES:
        enacted, pending, notlaw = [], [], []
        for e in entries:
            r = by_id[e["team_rule_id"]]
            if r.get("category") != cid:
                continue
            counts[e["result"]] += 1
            item = {
                "result": e["result"],
                "explanation": W.STORE.t_expl(e.get("explanation"), lang),
                "explanation_en": e.get("explanation"),
                "conflict_flag": bool(
                    e.get("conflict_flag")
                ),  # address-level, as in web.app.build_address
                "rule": W.rule_view(r, lang),
            }
            if e["result"] == "superseded":
                item["superseded_by"] = [
                    {
                        "id": b,
                        "title": W.STORE.t(by_id[b].get("title"), lang),
                        "jurisdiction": by_id[b].get("jurisdiction"),
                    }
                    for b in _overriders(r["team_rule_id"], present, by_id)
                ]
            if e.get("version_gap"):
                item["version_gap"] = e["version_gap"]
            if e["result"] == "unknown":
                item["needs_fact"] = e.get("needs_fact", [])
                item["needs_other"] = e.get("needs_other")
                item["missing_fact"] = (
                    " or ".join(FACT_LABELS[k] for k in item["needs_fact"])
                    if item["needs_fact"]
                    else (e.get("needs_other") or W.missing_fact(e.get("explanation", "")))
                )
                if (
                    lang == "es"
                ):  # shown as is; missing_fact stays English for the pages' fact matching
                    item["missing_fact_display"] = _missing_es(
                        item["needs_fact"], e.get("needs_other")
                    )
            H.apply_item(item, d["as_of"], lang, units=(d.get("facts") or {}).get("units"))
            (pending if e["result"] == "pending" else enacted).append(item)
        for r in by_id.values():
            if (
                r.get("category") == cid
                and r.get("status") == "failed"
                and r.get("jurisdiction") in juris
                and r["team_rule_id"] not in present
            ):
                notlaw.append(
                    {
                        "result": "failed",
                        "explanation": W.STORE.t(
                            "Proposal failed or was withdrawn. It is not law and does not apply.",
                            lang,
                        ),
                        "conflict_flag": False,
                        "rule": W.rule_view(r, lang),
                    }
                )
        order = {"applies": 0, "unknown": 1, "superseded": 2, "not_yet_effective": 3}
        enacted.sort(key=lambda x: (order.get(x["result"], 9), x["rule"].get("level") != "city"))
        findings = [
            {
                **f,
                "source": W.STORE.doc_meta(f.get("quoted_span_doc_id") or f.get("source_doc_id")),
                "quote_check": W.STORE.verify(f),
                "finding_display": W.STORE.t(f.get("finding"), lang),
            }
            for f in d["no_rule_findings"]
            if f.get("category") == cid
        ]
        cats.append(
            {
                "id": cid,
                "label": label,
                "question": question,
                "excluded": _excluded(d, cid, present, by_id, juris, lang),
                "enacted": enacted,
                "pending": pending,
                "not_law": notlaw,
                "no_rule": not enacted,
                "no_rule_findings": findings,
            }
        )
    return {
        "as_of": d["as_of"],
        "engine": "live",
        "lang": lang,
        "disclaimer": d["disclaimer"],
        "address": {
            "state": d["state"],
            "jurisdiction": d["jurisdiction"],
            "extension": d["extension"],
        },
        "scope": "city" if d["jurisdiction"] else "state",
        "scope_note": None
        if d["jurisdiction"]
        else "Only state law was checked: local ordinances here are not in our corpus.",
        "facts": d["facts"],
        "fact_counts": d["fact_counts"],
        "fact_depends": d["fact_depends"],
        "fact_labels": FACT_LABELS,
        "categories": cats,
        "summary": dict(counts),
        "unknowns": counts.get("unknown", 0),
        "conflicts": sum(
            1 for c in cats for i in c["enacted"] + c["pending"] if i["conflict_flag"]
        ),
    }


@router.post("/api/evaluate")
def evaluate(body: EvaluateIn, request: Request):
    _limit(EVALUATE_LIMIT, request)
    STATS["evaluate"] += 1
    as_of = (body.as_of or dt.date.fromisoformat(_web().DEFAULT_AS_OF)).isoformat()
    if not ("2000-01-01" <= as_of <= "2035-12-31"):
        raise HTTPException(422, "as_of must be between 2000 and 2035")
    f = body.facts
    if f.year_built and f.year_built > dt.date.fromisoformat(as_of).year + 5:
        raise HTTPException(422, "year_built lies in the future")
    try:
        d = U.evaluate_user(
            body.address.state, body.address.jurisdiction, f.model_dump(mode="json"), as_of
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return build_view(d, body.lang)


@router.get("/api/any-address/stats")
def stats():
    """Usage counters (no addresses are kept)."""
    return dict(STATS)
