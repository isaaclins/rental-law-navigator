"""Listen (#49): a spoken briefing on what the rules at an address mean for a renter or an owner, EN and ES.

POST /api/tts  {"address_id": "A0016", "as_of": "2026-10-01", "lang": "es", "persona": "owner", "topic": null}
    -> 200 audio/mpeg                               briefing (cached, or synthesized now); X-TTS-Chapters and
                                                    X-TTS-Chars let the page highlight the topic being spoken
    -> 200 {"fallback": true, "text", "lang", "chapters", ...}  the browser speaks `text` itself (speechSynthesis)
"topic" = one category id: only that topic's short explanation ("Explain this", about 10-15 s).

The text is always built here from the evaluator result (web/briefing.py: deterministic templates, no LLM), so
clients cannot send their own text: this is not a general TTS proxy. Characters are precious:
- mp3s are cached on disk by sha256(text, voice, model) and are only ever paid for once;
- new synthesis has a hard global budget (characters, file counter shared by every process) and a per-IP limit;
- over budget, rate-limited, no key, or any ElevenLabs error -> the fallback answer above, never an error page.
The API key is read from ~/.config/hacknation/elevenlabs-key on the server only; it is never logged or returned.

POST /api/tts/captions  (same body) -> {text, lang, chapters, sentences, words, timing, duration}
    the time-synced transcript of the same clip: sentences = [[first char, end char], ...]; words =
    [[first char, end char, start s, end s], ...] when its audio is cached, else null (the browser voice drives it
    with boundary events). timing = "elevenlabs" (character alignment from the with-timestamps endpoint, saved as
    <hash>.align.json next to <hash>.mp3), "whisper" (aligned locally from the cached mp3, no characters spent:
    `align` below) or "estimated" (spread over the mp3's length by characters and pauses). Never synthesizes.

CLI: python -m web.tts status | prewarm [--dry] [--reserve N] | align [--model base]
     align = alignment for cached mp3s that have none (needs `uv run --with faster-whisper`; free, local)
     prewarm = the home page examples x both personas, English, default as-of; it stops before the budget left
     would fall under N characters (default 1000), so first clicks elsewhere still get the real voice.
"""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import difflib
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

from web import briefing as B
from web.any_address import RateLimit, client_ip

HOME = Path.home()
DIR = Path(os.environ.get("NAVIGATOR_TTS_DIR") or HOME / "hacknation/realpage/private/tts-cache")
KEY_FILE = HOME / ".config/hacknation/elevenlabs-key"
BUDGET = int(os.environ.get("NAVIGATOR_TTS_BUDGET") or 4000)  # characters of NEW synthesis, ever
API = "https://api.elevenlabs.io/v1"
VOICE = "EXAVITQu4vr4xnSDxMaL"  # "Sarah", the voice of our product videos
MODEL = "eleven_v4"  # multilingual (EN + ES), same model as the videos
FORMAT = "mp3_44100_64"
MAX_TEXT = 1000  # a briefing never needs more (longest Spanish one: ~850); longer texts go to the browser voice

REQUEST_LIMIT = RateLimit(30, 60.0)  # any /api/tts call, per IP
SYNTH_LIMIT = RateLimit(6, 3600.0)  # new (uncached) syntheses, per IP

router = APIRouter()
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

# ------------------------------------------------------------------ text
PERSONAS = Literal["renter", "owner"]
TOPICS = Literal[
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
    "screening_restrictions",
    "algorithmic_rent_setting",
]


def script_for(
    address_id: str, as_of: str, lang: str, persona: str = "renter", topic: str | None = None
) -> B.Script:
    """The spoken script (category, sentence) for an address: the briefing, or one topic's explanation."""
    from web import app as A  # late import: web.app includes this router

    if lang != "en" and lang not in A.STORE.tr:
        raise HTTPException(400, "lang must be en or es")
    d = A.build_address(address_id, as_of, lang)
    return B.topic(d, topic, persona, lang) if topic else B.briefing(d, persona, lang)


def script_text(*args, **kw) -> str:
    return B.text_of(script_for(*args, **kw))


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


def synthesize(text: str) -> tuple[bytes, dict | None]:
    """One ElevenLabs call (with-timestamps: the audio and its character alignment, same price).
    Raises on any failure; the key goes only into the request header."""
    req = urllib.request.Request(
        f"{API}/text-to-speech/{VOICE}/with-timestamps?output_format={FORMAT}",
        data=json.dumps({"text": text, "model_id": MODEL}).encode(),
        method="POST",
        headers={
            "xi-api-key": _key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read())
    data = base64.b64decode(d.get("audio_base64") or "")
    if len(data) < 1000:
        raise ValueError("audio too short")
    return data, d.get("alignment") or d.get("normalized_alignment")


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
            data, alignment = synthesize(text)
        except Exception as e:  # network, quota, 4xx/5xx: the browser voice takes over
            refund(n)
            _log({"event": "error", "error": type(e).__name__, "chars": n})
            return None, "unavailable"
        if alignment:  # written before the mp3, so a cached mp3 always finds its timing
            save_alignment(h, {"source": "elevenlabs", "alignment": alignment})
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
    persona: PERSONAS = "renter"
    topic: TOPICS | None = None


@router.post("/api/tts")
def tts(body: TtsIn, request: Request):
    from web.app import _as_of

    script = script_for(
        body.address_id.upper(), _as_of(body.as_of), body.lang, body.persona, body.topic
    )
    text = B.text_of(script)
    chapters = B.chapters(script)
    ip = client_ip(request)
    if not REQUEST_LIMIT.allow(ip):
        data, how = None, "rate_limited"
    else:
        data, how = audio_for(text, ip)
    if data is None:
        return JSONResponse(
            {"fallback": True, "reason": how, "lang": body.lang, "text": text, "chapters": chapters}
        )
    return Response(
        data,
        media_type="audio/mpeg",
        headers={
            "X-TTS": how,
            "X-TTS-Chars": str(len(text)),
            "X-TTS-Chapters": json.dumps(chapters, separators=(",", ":")),
        },
    )


# ------------------------------------------------------------------ captions (time-synced transcript)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡'\"0-9])")


def sentences(script: B.Script) -> list[list[int]]:
    """[[first char, end char], ...] of every sentence in text_of(script) (a script line can hold several)."""
    out, pos = [], 0
    for _, line in script:
        start = 0
        for m in SENTENCE_END.finditer(line):
            out.append([pos + start, pos + m.start()])
            start = m.end()
        out.append([pos + start, pos + len(line)])
        pos += len(line) + 1
    return out


def word_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]


def _align_path(h: str) -> Path:
    return DIR / f"{h}.align.json"


def save_alignment(h: str, d: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    p = _align_path(h)
    tmp = p.with_suffix(".part")
    tmp.write_text(json.dumps({"v": 1, **d}, separators=(",", ":")))
    tmp.replace(p)


def words_from_chars(text: str, al: dict) -> list[list]:
    """ElevenLabs character alignment -> [[c0, c1, t0, t1], ...] per word of `text`."""
    chars = al.get("characters") or []
    t0s = al.get("character_start_times_seconds") or []
    t1s = al.get("character_end_times_seconds") or []
    n = min(len(chars), len(t0s), len(t1s))
    if not n:
        return []
    if "".join(chars[:n]) == text:
        at = lambda i: i  # noqa: E731  same characters: index i is character i
    else:  # normalized differently: map by position
        at = lambda i: min(n - 1, round(i * (n - 1) / max(1, len(text) - 1)))  # noqa: E731
    return [[a, b, round(t0s[at(a)], 3), round(t1s[at(b - 1)], 3)] for a, b in word_spans(text)]


def _norm(w: str) -> str:
    return "".join(c for c in w.lower() if c.isalnum())


def fit_words(text: str, heard: list[tuple[str, float, float]], duration: float) -> list[list]:
    """Recognized words with times (any recognizer) -> timings for the words of `text`. Words matched in order
    (difflib on normalized spellings) take their times; the rest share the gaps around them by length."""
    spans = word_spans(text)
    mine = [_norm(text[a:b]) for a, b in spans]
    theirs = [_norm(w) for w, _, _ in heard]
    times: list[tuple[float, float] | None] = [None] * len(spans)
    sm = difflib.SequenceMatcher(None, mine, theirs, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            _, t0, t1 = heard[blk.b + k]
            times[blk.a + k] = (t0, t1)
    i = 0
    while i < len(spans):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(spans) and times[j] is None:
            j += 1
        lo = times[i - 1][1] if i else (heard[0][1] if heard else 0.0) * 0.5
        hi = times[j][0] if j < len(spans) else max(lo, duration or lo)
        lens = [spans[k][1] - spans[k][0] + 1 for k in range(i, j)]
        tot, t = sum(lens), lo
        for k, n in zip(range(i, j), lens, strict=True):
            d = (hi - lo) * n / tot
            times[k] = (t, t + d)
            t += d
        i = j
    return [
        [a, b, round(t0, 3), round(t1, 3)] for (a, b), (t0, t1) in zip(spans, times, strict=True)
    ]


def mp3_seconds(p: Path) -> float:
    return p.stat().st_size * 8 / 64000  # FORMAT is constant 64 kbit/s


def estimate_words(text: str, duration: float) -> list[list]:
    """No alignment saved: spread the words over the clip by length, with room for the pauses at punctuation."""
    spans = word_spans(text)
    weight = []
    for a, b in spans:
        w = text[a:b]
        weight.append(len(w) + 1 + (6 if w[-1] in ".!?;:" else 2.5 if w[-1] == "," else 0))
    lead, tail = 0.12, 0.35
    span = max(0.1, duration - lead - tail)
    tot, t, out = sum(weight) or 1, lead, []
    for (a, b), w in zip(spans, weight, strict=True):
        d = span * w / tot
        out.append([a, b, round(t, 3), round(t + d * 0.92, 3)])
        t += d
    return out


def timing_for(text: str) -> tuple[list | None, str | None, float | None]:
    """(words, source, duration) of the cached clip of `text`; (None, None, None) when it has no audio."""
    h = cache_key(text)
    mp3 = DIR / f"{h}.mp3"
    if not mp3.exists():
        return None, None, None
    dur = round(mp3_seconds(mp3), 3)
    p = _align_path(h)
    if p.exists():
        try:
            d = json.loads(p.read_text())
            if d.get("source") == "elevenlabs" and d.get("alignment"):
                words = words_from_chars(text, d["alignment"])
                if words:
                    return words, "elevenlabs", max(dur, words[-1][3])
            elif d.get("words") and len(d["words"]) == len(word_spans(text)):
                return d["words"], d.get("source") or "aligned", dur
        except (ValueError, KeyError, TypeError, IndexError):
            pass  # a broken file only costs precision
    return estimate_words(text, dur), "estimated", dur


@router.post("/api/tts/captions")
def captions(body: TtsIn):
    """The transcript of exactly the clip /api/tts plays, with its timing. Reads the cache only (free)."""
    from web.app import _as_of

    script = script_for(
        body.address_id.upper(), _as_of(body.as_of), body.lang, body.persona, body.topic
    )
    text = B.text_of(script)
    words, timing, duration = timing_for(text)
    return {
        "text": text,
        "lang": body.lang,
        "chapters": B.chapters(script),
        "sentences": sentences(script),
        "words": words,
        "timing": timing,
        "duration": duration,
    }


def align_cached(model: str = "base") -> None:
    """Free, local alignment (faster-whisper word timestamps) for cached mp3s of current scripts without one."""
    from web import app as A

    todo = {p.stem for p in DIR.glob("*.mp3") if not _align_path(p.stem).exists()}
    if not todo:
        print("every cached clip has its alignment")
        return
    found: dict[str, tuple[str, str]] = {}
    for aid in sorted(A.STORE.addresses):
        for lang in ("en", "es"):
            for persona in ("renter", "owner"):
                for topic in (None, *B.CATS):
                    try:
                        t = script_text(aid, A.DEFAULT_AS_OF, lang, persona, topic)
                    except HTTPException:
                        continue
                    h = cache_key(t)
                    if h in todo:
                        found[h] = (t, lang)
        if len(found) == len(todo):
            break
    import subprocess

    import numpy as np
    from faster_whisper import WhisperModel  # uv run --with faster-whisper python -m web.tts align

    wm = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=2)
    for h, (t, lang) in found.items():
        pcm = subprocess.run(  # 16 kHz mono float, decoded by ffmpeg (avoids PyAV version quirks)
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(DIR / f"{h}.mp3"),
                "-f",
                "s16le",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
        segs, _ = wm.transcribe(audio, language=lang, word_timestamps=True, vad_filter=False)
        heard = [(w.word, w.start, w.end) for s in segs for w in (s.words or [])]
        words = fit_words(t, heard, mp3_seconds(DIR / f"{h}.mp3"))
        save_alignment(h, {"source": "whisper", "words": words})
        hit = difflib.SequenceMatcher(
            None, [_norm(w) for w in t.split()], [_norm(w) for w, _, _ in heard], autojunk=False
        ).ratio()
        print(
            f"{h[:12]} {lang} {len(t)} chars, {len(heard)} words heard, {hit:.0%} matched -> aligned"
        )
    print(f"{len(todo) - len(found)} cached clips belong to older scripts (left as they are)")


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
        reserve = int(argv[argv.index("--reserve") + 1]) if "--reserve" in argv else 1000
        total = 0
        for aid in example_ids():
            for persona in ("renter", "owner"):
                text = script_text(aid, A.DEFAULT_AS_OF, "en", persona)
                cached = (DIR / f"{cache_key(text)}.mp3").exists()
                if cached:
                    how = "cached"
                elif budget_status()["left"] - (total if dry else 0) - len(text) < reserve:
                    how = f"skipped (would leave under {reserve} characters)"
                elif dry:
                    how, total = "would synthesize", total + len(text)
                else:
                    how = audio_for(text)[1]
                    total += len(text) if how == "new" else 0
                print(f"{aid} {persona} {len(text):4d} chars  {how}")
        print(f"new characters: {total}; budget: {json.dumps(budget_status())}")
    elif cmd == "align":
        align_cached(argv[argv.index("--model") + 1] if "--model" in argv else "base")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
