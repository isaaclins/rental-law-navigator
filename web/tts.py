"""Listen to an answer (#49): the address summary read aloud (ElevenLabs), EN and ES. Not legal advice.

POST /api/tts  {"address_id": "A0016", "as_of": "2026-10-01", "lang": "es"}
    -> 200 audio/mpeg                               spoken summary (cached, or synthesized now)
    -> 200 {"fallback": true, "text", "lang", ...}  the browser speaks `text` itself (speechSynthesis)

The text is always built here from the evaluator result (address, as-of date, one line per topic, "not legal
advice"), so clients cannot send their own text: this is not a general TTS proxy. Characters are precious:
- mp3s are cached on disk by sha256(text, voice, model) and are only ever paid for once;
- new synthesis has a hard global budget (characters, file counter shared by every process) and a per-IP limit;
- over budget, rate-limited, no key, or any ElevenLabs error -> the fallback answer above, never an error page.
The API key is read from ~/.config/hacknation/elevenlabs-key on the server only; it is never logged or returned.

CLI: python -m web.tts status | prewarm [--dry]   (prewarm = the home page examples, EN + ES, default as-of)
"""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from web.any_address import RateLimit, client_ip

HOME = Path.home()
DIR = Path(os.environ.get("NAVIGATOR_TTS_DIR") or HOME / "hacknation/realpage/private/tts-cache")
KEY_FILE = HOME / ".config/hacknation/elevenlabs-key"
BUDGET = int(os.environ.get("NAVIGATOR_TTS_BUDGET") or 4000)  # characters of NEW synthesis, ever
API = "https://api.elevenlabs.io/v1"
VOICE = "EXAVITQu4vr4xnSDxMaL"  # "Sarah", the voice of our product videos
MODEL = "eleven_v4"  # multilingual (EN + ES), same model as the videos
FORMAT = "mp3_44100_64"
MAX_TEXT = 900  # a summary never needs more; longer texts go to the browser voice

REQUEST_LIMIT = RateLimit(30, 60.0)  # any /api/tts call, per IP
SYNTH_LIMIT = RateLimit(6, 3600.0)  # new (uncached) syntheses, per IP

router = APIRouter()
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

# ------------------------------------------------------------------ text
# Topic names as spoken (shorter than the headings; the summary must stay brief).
SPOKEN_CAT = {
    "en": {
        "rent_increase_limits": "Rent increases",
        "just_cause_eviction": "Evictions",
        "security_deposits": "Deposit",
        "application_screening_fees": "Fees",
        "screening_restrictions": "Screening",
        "algorithmic_rent_setting": "Rent software",
    },
    "es": {
        "rent_increase_limits": "Aumentos de renta",
        "just_cause_eviction": "Desalojos",
        "security_deposits": "Depósito",
        "application_screening_fees": "Cuotas",
        "screening_restrictions": "Selección de inquilinos",
        "algorithmic_rent_setting": "Software de rentas",
    },
}
MISSING_ES = {
    "Year built / certificate-of-occupancy date": "el año de construcción",
    "Owner type": "el tipo de propietario",
    "Number of units": "el número de unidades",
    "Exemption filing / registration status": "el registro de exención",
    "Length of tenancy": "la duración del arrendamiento",
    "A fact not contained in the public data": "un dato que no está en las fuentes públicas",
}
WORDS = {
    "en": {
        "as_of": "As of {d}.",
        "depends": "depends on {f}",
        "starts": "{x}, from {d}",
        "exempt": "no rule applies to this building",
        "none": "no rule for this address",
        "nla": "This is not legal advice.",
        "or": " or ",
        "to": " to ",
        "is": " is ",
    },
    "es": {
        "as_of": "Reglas al {d}.",
        "depends": "depende de {f}",
        "starts": "{x}, a partir del {d}",
        "exempt": "ninguna regla se aplica a este edificio",
        "none": "no hay regla para esta dirección",
        "nla": "Esto no es asesoría legal.",
        "or": " o ",
        "to": " a ",
        "is": " es ",
    },
}
MONTHS_ES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
LIMIT = {"en": 48, "es": 56}  # characters per spoken topic line
RANK = {
    "applies": 0,
    "unknown": 1,
    "not_yet_effective": 2,
    "superseded": 3,
    "pending": 4,
    "failed": 5,
}


def say_date(iso: str, lang: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    if lang == "es":
        return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"
    return f"{d:%B} {d.day}, {d.year}"


def title_case(s: str) -> str:
    return " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in (s or "").split())


# Where a long line may end without sounding cut off: before a comma, slash or one of these words.
BREAK = re.compile(
    r"(?:,| /)\s| (?=(?:using|with|in|for|based|within|after|under|including|que|con|en|para|según|desde|dentro|"
    r"después|incluid[oa]s?)\b)"
)


def spoken(s: str, lang: str) -> str:
    """One short spoken line: no parentheticals, ranges read as words, cut at a natural break near LIMIT."""
    w, limit = WORDS[lang], LIMIT[lang]
    s = re.sub(r"\s*\([^)]*\)", "", s or "").strip()
    s = re.sub(
        r"(?<=[\d%])\s*[–-]\s*(?=[$\d])", w["to"], s
    )  # $87,450–$115,480 -> $87,450 to $115,480
    s = re.sub(r"(?<=[A-Za-zÀ-ÿ])/(?=[A-Za-zÀ-ÿ])", w["or"], s)  # lock/key -> lock or key
    s = s.replace(" = ", w["is"])
    parts = [p.strip() for p in s.split(";") if p.strip()]
    out = parts[0] if parts else ""
    for p in parts[1:]:
        if len(out) + 2 + len(p) > limit:
            break
        out += ", " + p
    if len(out) > limit + 12:  # a little over is fine; much over is cut where a sentence may end
        cuts = [m.start() for m in BREAK.finditer(out) if 16 <= m.start() <= limit]
        if cuts:
            out = out[: cuts[-1]]
        else:
            out = out[: limit + 12].rsplit(" ", 1)[0]
            out = re.sub(
                r"(?:\s+(?:a|an|the|of|to|and|or|by|on|de|del|la|el|los|las|y|o|por|al))+$", "", out
            )
    return cap(out.rstrip(" .,;:/"))


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _order_key(item: dict):
    r = item["rule"]
    return (
        RANK.get(item["result"], 9),
        0 if item.get("overrides_here") else 1,
        0 if r.get("level") == "state" else 1,
    )


def topic_line(c: dict, lang: str) -> str:
    """The topic's one-line answer, as on the address page (top rule's key value), made speakable."""
    w = WORDS[lang]
    items = sorted(c.get("enacted") or [], key=_order_key)
    if items:
        top, r = items[0], items[0]["rule"]
        if top["result"] == "unknown":
            f = top.get("missing_fact") or "A fact not contained in the public data"
            f = MISSING_ES.get(f, MISSING_ES[next(iter(MISSING_ES))]) if lang == "es" else f.lower()
            return cap(w["depends"].format(f=f))
        line = spoken(
            r.get("key_value_display") or r.get("key_value") or r.get("title_display") or "", lang
        )
        eff = r.get("effective_date_norm")
        if top["result"] == "not_yet_effective" and eff:
            line = w["starts"].format(x=line, d=say_date(eff, lang))
        return line
    return cap(w["exempt"] if c.get("excluded") else w["none"])


def summary_text(address_id: str, as_of: str, lang: str) -> str:
    from web import app as A  # late import: web.app includes this router

    if lang == "en" or lang in A.STORE.tr:
        d = A.build_address(address_id, as_of, lang)
    else:
        raise HTTPException(400, "lang must be en or es")
    a = d["address"]
    w = WORDS[lang]
    labels = {cid: label for cid, label, _ in A.CATEGORIES} | SPOKEN_CAT[lang]
    lines = [
        f"{title_case(a['street_address'])}, {title_case(a['postal_city'])}.",
        w["as_of"].format(d=say_date(d["as_of"], lang)),
    ]
    lines += [f"{labels.get(c['id'], c['id'])}: {topic_line(c, lang)}." for c in d["categories"]]
    lines.append(w["nla"])
    return " ".join(lines)


# ------------------------------------------------------------------ cache + budget
def cache_key(text: str, voice: str = VOICE, model: str = MODEL) -> str:
    return hashlib.sha256(json.dumps([text, voice, model]).encode()).hexdigest()


@contextlib.contextmanager
def _budget_file():
    """Exclusive access to the shared character counter (every server process uses the same file)."""
    DIR.mkdir(parents=True, exist_ok=True)
    p = DIR / "budget.json"
    with open(p, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            state = json.loads(f.read() or "{}")
        except ValueError:
            state = {}
        state.setdefault("used", 0)
        state["budget"] = BUDGET
        yield state
        f.seek(0)
        f.truncate()
        f.write(json.dumps(state))


def budget_status() -> dict:
    with _budget_file() as s:
        return {"used": s["used"], "budget": BUDGET, "left": max(0, BUDGET - s["used"])}


def reserve(n: int) -> bool:
    with _budget_file() as s:
        if s["used"] + n > BUDGET:
            return False
        s["used"] += n
        return True


def refund(n: int) -> None:
    with _budget_file() as s:
        s["used"] = max(0, s["used"] - n)


def _key() -> str:
    return KEY_FILE.read_text().strip()


def synthesize(text: str) -> bytes:
    """One ElevenLabs call. Raises on any failure; the key goes only into the request header."""
    req = urllib.request.Request(
        f"{API}/text-to-speech/{VOICE}?output_format={FORMAT}",
        data=json.dumps({"text": text, "model_id": MODEL}).encode(),
        method="POST",
        headers={"xi-api-key": _key(), "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 1000:
        raise ValueError("audio too short")
    return data


def _lock(h: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(h, threading.Lock())


def audio_for(text: str, ip: str | None = None) -> tuple[bytes | None, str]:
    """(mp3, "cache"|"new") or (None, reason). Pays only on a cache miss, within budget and limits."""
    h = cache_key(text)
    mp3 = DIR / f"{h}.mp3"
    if mp3.exists():
        return mp3.read_bytes(), "cache"
    if len(text) > MAX_TEXT:
        return None, "too_long"
    if not KEY_FILE.exists():
        return None, "unavailable"
    with _lock(h):
        if mp3.exists():  # another request just made it
            return mp3.read_bytes(), "cache"
        if ip is not None and not SYNTH_LIMIT.allow(ip):
            return None, "rate_limited"
        n = len(text)
        if not reserve(n):
            return None, "budget"
        try:
            data = synthesize(text)
        except Exception as e:  # network, quota, 4xx/5xx: the browser voice takes over
            refund(n)
            _log({"event": "error", "error": type(e).__name__, "chars": n})
            return None, "unavailable"
        tmp = mp3.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(mp3)
        _log({"event": "synth", "hash": h[:16], "chars": n, "voice": VOICE, "model": MODEL})
        return data, "new"


def _log(d: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    with (DIR / "ledger.jsonl").open("a") as f:
        f.write(
            json.dumps({"at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), **d}) + "\n"
        )


# ------------------------------------------------------------------ API
class TtsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # no "text": clients cannot choose what is spoken
    address_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    as_of: str | None = None
    lang: Literal["en", "es"] = "en"


@router.post("/api/tts")
def tts(body: TtsIn, request: Request):
    from web.app import _as_of

    text = summary_text(body.address_id.upper(), _as_of(body.as_of), body.lang)
    ip = client_ip(request)
    if not REQUEST_LIMIT.allow(ip):
        data, how = None, "rate_limited"
    else:
        data, how = audio_for(text, ip)
    if data is None:
        return JSONResponse({"fallback": True, "reason": how, "lang": body.lang, "text": text})
    return Response(data, media_type="audio/mpeg", headers={"X-TTS": how})


# ------------------------------------------------------------------ CLI
def example_ids() -> list[str]:
    """The first three example addresses of the home page (same picks as app.js examplePicks)."""
    from web import app as A

    rows = list(A.STORE.addresses.values())

    def yr(a):
        try:
            return int(a.get("year_built") or 0)
        except ValueError:
            return 0

    def units(a):
        try:
            return int(float(a.get("units") or 0))
        except ValueError:
            return 0

    def city(a):
        return a.get("resolved_city") or ""

    def pick(f):
        return next((a["address_id"] for a in rows if f(a)), None)

    picks = [
        pick(
            lambda a: city(a) == "Los Angeles" and 0 < yr(a) < 1978 and a["postal_city"] != city(a)
        )
        or pick(lambda a: city(a) == "Los Angeles" and 0 < yr(a) < 1978),
        pick(lambda a: city(a) == "San Francisco" and 0 < yr(a) < 1979 and units(a) >= 10),
        pick(lambda a: a["postal_city"] == "Dorchester"),
    ]
    return [p for p in picks if p]


def main(argv: list[str]) -> None:
    from web import app as A

    cmd = argv[0] if argv else "status"
    if cmd == "status":
        print(json.dumps(budget_status()))
    elif cmd == "prewarm":
        dry = "--dry" in argv
        total = 0
        for aid in example_ids():
            for lang in ("en", "es"):
                text = summary_text(aid, A.DEFAULT_AS_OF, lang)
                cached = (DIR / f"{cache_key(text)}.mp3").exists()
                how = "cached" if cached else ("would synthesize" if dry else audio_for(text)[1])
                total += 0 if cached else len(text)
                print(f"{aid} {lang} {len(text):4d} chars  {how}\n    {text}")
        print(f"new characters: {total}; budget: {json.dumps(budget_status())}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
