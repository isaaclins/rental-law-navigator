"""Try it with a new law (#/try): a visitor's ordinance text through the batch pipeline, streamed step by step.

  GET  /api/try/meta              places, samples, limits
  GET  /api/try/sample/{id}       the text of a one-click sample
  POST /api/try/file?name=x.pdf   raw bytes of a .txt / .pdf / .html file -> {"text"} (nothing is kept)
  POST /api/try                   {"text", "jurisdiction"} -> text/event-stream: start, step, log, result | error

The work itself is navigator/trylaw.py (the batch pipeline's own extract / review / finalize / validate / plain /
evaluate functions, in a child process with a scratch output folder). Safety:
  - input: 200..30,000 characters; files up to 3 MB; the place must be a US "City, ST" or one of ours
  - fresh runs: per-IP limit, at most TRY_PARALLEL at once, an hourly + daily budget (web.ask.Budget, own file),
    a hard timeout (the child's whole process group is killed) with a friendly message
  - the text is data: wrapped in the pipeline's <document> block (tags that would close it are neutralised), the
    claude CLI runs with no tools and a JSON schema, the output is validated against rule_record.schema.json and
    every quote is searched in the text by code. Lines that talk to an AI are flagged to the reader.
  - nothing pasted is stored: the child's scratch folder (text, model cache) is deleted after the run; only the
    SHA-256 key of the text and the result are kept (cache/try/results, so the same text answers instantly).
    The two samples are prewarmed: their results ship in web/fixtures/trylaw/.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from navigator import trylaw as T
from web.any_address import RateLimit
from web.ask import Budget, real_ip

router = APIRouter()
log = logging.getLogger("navigator.try")
ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "trylaw"
RESULTS = Path(
    os.environ.get("NAVIGATOR_TRY_RESULTS", ROOT / "cache" / "try" / "results")
)  # not in git
MAX_CHARS, MIN_CHARS = T.MAX_CHARS, T.MIN_CHARS
MAX_FILE = 3_000_000
TIMEOUT = int(os.environ.get("NAVIGATOR_TRY_TIMEOUT", "240"))  # seconds for the whole run
TRY_PARALLEL = int(os.environ.get("NAVIGATOR_TRY_PARALLEL", "2"))
PER_IP = RateLimit(
    int(os.environ.get("NAVIGATOR_TRY_PER_IP", "6")), 3600.0
)  # fresh runs per visitor and hour
FILE_LIMIT = RateLimit(30, 600.0)
BUDGET = Budget(
    Path(os.environ.get("NAVIGATOR_TRY_BUDGET_FILE", ROOT / ".try-budget.json")),
    int(os.environ.get("NAVIGATOR_TRY_BUDGET_HOUR", "30")),
    int(os.environ.get("NAVIGATOR_TRY_BUDGET_DAY", "150")),
)
SLOTS = threading.BoundedSemaphore(TRY_PARALLEL)
KEEP_RESULTS = 400

SAMPLES = {
    "santa-monica": {
        "file": "santa-monica-deposits.txt",
        "jurisdiction": "Santa Monica, CA",
        "title_en": "Santa Monica deposits",
        "title_es": "Depósitos en Santa Monica",
        "kind": "real",
        "url": "https://santamonica.gov/media/Document%20Library/Detail/Rent%20Control%20Charter%20Amendment%20&%20Regulations/14,%20Security%20Deposits.pdf",
    },
    "newark": {
        "file": "newark-fictional.txt",
        "jurisdiction": "Newark, NJ",
        "title_en": "Newark fair rent-setting",
        "title_es": "Renta justa en Newark",
        "kind": "fictional",
        "url": "",
    },
}

MSG = {
    "too_long": (
        "That's {n} characters. The limit is 30,000: paste only the sections about renting.",
        "Son {n} caracteres. El límite es 30,000: pegue solo las secciones sobre el alquiler.",
    ),
    "too_short": (
        "Paste at least 200 characters of the law's text.",
        "Pegue al menos 200 caracteres del texto de la ley.",
    ),
    "place": (
        "Pick where the law applies, as a US city and state (for example Austin, TX).",
        "Elija dónde aplica la ley: una ciudad y un estado de EE. UU. (por ejemplo, Austin, TX).",
    ),
    "ip": (
        "You've read several new laws in the last hour. Try again later, or use one of the samples.",
        "Ya leyó varias leyes nuevas en la última hora. Vuelva a intentarlo más tarde o use uno de los ejemplos.",
    ),
    "budget": (
        "We've read as many new laws as we can today. The samples still work.",
        "Hoy ya leímos todas las leyes nuevas que podemos. Los ejemplos siguen funcionando.",
    ),
    "busy": (
        "We're reading other laws right now. Try again in a minute, or use one of the samples.",
        "Ahora mismo estamos leyendo otras leyes. Vuelva a intentarlo en un minuto o use uno de los ejemplos.",
    ),
    "timeout": (
        "This law took longer than {s} seconds to read, so we stopped. Try a shorter part of it.",
        "Leer esta ley tomó más de {s} segundos, así que paramos. Pruebe con una parte más corta.",
    ),
    "failed": (
        "Something went wrong while reading this law. Nothing was saved. Please try again.",
        "Algo salió mal al leer esta ley. No se guardó nada. Vuelva a intentarlo.",
    ),
    "file_type": ("Upload a .txt, .pdf or .html file.", "Suba un archivo .txt, .pdf o .html."),
    "file_big": (
        "That file is over 3 MB. Paste the sections about renting instead.",
        "El archivo pesa más de 3 MB. Pegue las secciones sobre el alquiler.",
    ),
    "file_empty": (
        "We couldn't find any text in that file. A scanned PDF has none: paste the text instead.",
        "No encontramos texto en ese archivo. Un PDF escaneado no tiene: pegue el texto.",
    ),
}


def msg(code: str, **kw) -> dict:
    en, es = MSG[code]
    return {"code": code, "en": en.format(**kw), "es": es.format(**kw)}


# ------------------------------------------------------------------------------------------- places --
def places() -> dict:
    k = T.known_places()
    return {"states": k["states"], "cities": k["cities"], "extension": k["extension"]}


def check_place(p: str) -> str | None:
    k = T.known_places()
    if p in k["states"] or p in k["cities"] or p in k["extension"]:
        return p
    hit = T.parse_place(p)
    if not hit or len(hit[0]) == 2:  # a state outside CA/NJ/MA: we have no state context for it
        return None
    name = hit[0]
    for j in k["cities"] + k["extension"]:  # "newark, nj", "Newark, New Jersey"
        if j.lower() == name.lower():
            return j
    return name


# -------------------------------------------------------------------------------------- the results --
def key_of(text: str, jur: str) -> str:
    return T.text_key(text, jur)


def cached(key: str) -> dict | None:
    for p in (RESULTS / f"{key}.json", *FIXTURES.glob("*.result.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("key") == key:
            return d
    return None


def store(key: str, events: list[dict]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    tmp = RESULTS / f"{key}.tmp"
    tmp.write_text(
        json.dumps(
            {"key": key, "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "events": events},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    tmp.replace(RESULTS / f"{key}.json")
    old = sorted(RESULTS.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for p in old[:-KEEP_RESULTS]:
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------------------- live jobs --
class Job:
    """One pipeline run; every request for the same text follows the same event list (no second run)."""

    def __init__(self, key: str) -> None:
        self.key, self.events, self.done = key, [], False
        self.cond = threading.Condition()

    def add(self, ev: dict) -> None:
        with self.cond:
            self.events.append(ev)
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.done = True
            self.cond.notify_all()

    def follow(self):
        i = 0
        while True:
            with self.cond:
                if i >= len(self.events) and not self.done:
                    self.cond.wait(15)
                new, done = self.events[i:], self.done
            i += len(new)
            if not new and not done:
                yield None  # keep-alive
            yield from new
            if done and i >= len(self.events):
                return


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()


def _run(job: Job, text: str, jur: str, title: str, url: str) -> None:
    """The child process: navigator/trylaw.py launch(), events relayed with their time since the start."""
    t0 = time.time()
    wd = Path(tempfile.mkdtemp(prefix="navigator-try-"))
    ok = False
    try:
        p = T.launch(text, jur, wd, title=title, url=url)
        killer = threading.Timer(TIMEOUT, lambda: _kill(p))
        killer.start()
        try:
            for line in p.stdout:
                el = round(time.time() - t0, 2)
                if line.startswith(T.EVENT_PREFIX):
                    ev = json.loads(line[len(T.EVENT_PREFIX) :])
                    if ev.get("event") == "audit":
                        continue
                    if ev.get("event") == "result":
                        ev["result"]["wall_seconds"] = round(time.time() - t0, 1)
                        ok = True
                    job.add({**ev, "t": el})
                elif line.strip():
                    job.add({"event": "log", "line": line.rstrip()[:400], "t": el})
            p.wait(timeout=10)
        finally:
            killer.cancel()
        if not ok:
            timed_out = time.time() - t0 >= TIMEOUT - 1
            log.warning(
                "try: run failed (%s, exit %s)", "timeout" if timed_out else "error", p.returncode
            )
            job.add(
                {"event": "error", **(msg("timeout", s=TIMEOUT) if timed_out else msg("failed"))}
            )
        else:
            store(job.key, job.events)
    except Exception:  # noqa: BLE001
        log.exception("try failed")
        job.add({"event": "error", **msg("failed")})
    finally:
        shutil.rmtree(wd, ignore_errors=True)  # the pasted text and its model cache go with it
        SLOTS.release()
        job.finish()
        with JOBS_LOCK:
            JOBS.pop(job.key, None)


def _kill(p: subprocess.Popen) -> None:
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


# ------------------------------------------------------------------------------------------- routes --
class TryIn(BaseModel):
    text: str
    jurisdiction: str
    sample: str = ""


def _counts() -> dict:
    """The corpus the page talks about: rules in output/rules.json and sample buildings (main + extension)."""
    import csv

    try:
        rules = len(
            json.loads((ROOT / "output" / "rules.json").read_text(encoding="utf-8"))["rules"]
        )
        n = 0
        for f in (ROOT / "data" / "addresses_resolved.csv", T.SM_OUT / "addresses_resolved.csv"):
            with open(f, encoding="utf-8") as fh:
                n += sum(1 for _ in csv.DictReader(fh))
        return {"rules": rules, "buildings": n}
    except (OSError, ValueError, KeyError):
        return {}


@router.get("/api/try/meta")
def meta():
    return {
        "counts": _counts(),
        "places": places(),
        "samples": [
            {
                "id": k,
                "jurisdiction": v["jurisdiction"],
                "title_en": v["title_en"],
                "title_es": v["title_es"],
                "kind": v["kind"],
                "url": v["url"],
            }
            for k, v in SAMPLES.items()
        ],
        "limits": {
            "max_chars": MAX_CHARS,
            "min_chars": MIN_CHARS,
            "max_file": MAX_FILE,
            "timeout": TIMEOUT,
            "per_ip_hour": PER_IP.n,
            "parallel": TRY_PARALLEL,
        },
    }


@router.get("/api/try/sample/{sid}")
def sample(sid: str):
    s = SAMPLES.get(sid)
    if not s:
        raise HTTPException(404, "No such sample.")
    return {
        "id": sid,
        "text": (FIXTURES / s["file"]).read_text(encoding="utf-8"),
        **{k: s[k] for k in ("jurisdiction", "title_en", "title_es", "kind", "url")},
    }


def _html_text(raw: bytes) -> str:
    import trafilatura

    html = raw.decode("utf-8", errors="replace")
    t = (
        trafilatura.extract(html, include_comments=False, include_tables=True, favor_recall=True)
        or ""
    )
    if not t.strip():
        import lxml.html

        t = lxml.html.fromstring(html).text_content()
    return t


def _pdf_text(raw: bytes) -> str:
    with tempfile.TemporaryDirectory(prefix="navigator-pdf-") as td:
        f = Path(td) / "in.pdf"
        f.write_bytes(raw)
        p = subprocess.run(
            ["nice", "-n", "19", "pdftotext", "-enc", "UTF-8", "-nopgbrk", str(f), "-"],
            capture_output=True,
            timeout=20,
        )
        return p.stdout.decode("utf-8", errors="replace") if p.returncode == 0 else ""


@router.post("/api/try/file")
async def upload(request: Request, name: str = ""):
    if not FILE_LIMIT.allow(real_ip(request)):
        raise HTTPException(429, msg("ip"))
    ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
    if ext not in ("txt", "text", "md", "pdf", "html", "htm"):
        raise HTTPException(415, msg("file_type"))
    raw = await request.body()
    if len(raw) > MAX_FILE:
        raise HTTPException(413, msg("file_big"))
    try:
        if ext == "pdf" or raw[:5] == b"%PDF-":
            text = _pdf_text(raw)
        elif ext in ("html", "htm"):
            text = _html_text(raw)
        else:
            text = raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - a broken file is the visitor's, not a server error
        text = ""
    text = re.sub(r"[ \t]+\n", "\n", text.replace("\r\n", "\n")).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text:
        raise HTTPException(422, msg("file_empty"))
    return {"text": text, "chars": len(text)}


def _replay(d: dict):
    """A cached result streams again quickly: the recorded steps, then the result (marked cached)."""
    last = 0.0
    for ev in d["events"]:
        if ev.get("event") == "log":
            continue
        gap = min(0.2, max(0.0, (ev.get("t") or 0) - last) * 0.04)
        last = ev.get("t") or last
        if gap:
            time.sleep(gap)
        yield ev


def _sse(ev: dict) -> str:
    return f"event: {ev['event']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"


@router.post("/api/try")
def try_law(body: TryIn, request: Request):
    text = body.text or ""
    if len(text) > MAX_CHARS:
        raise HTTPException(413, msg("too_long", n=f"{len(text):,}"))
    if len(text.strip()) < MIN_CHARS:
        raise HTTPException(422, msg("too_short"))
    jur = check_place(body.jurisdiction or "")
    if not jur:
        raise HTTPException(422, msg("place"))
    key = key_of(text, jur)
    flags = T.injection_flags(text)
    s = SAMPLES.get(body.sample)
    title, url = "", ""
    if s and T.clean_text((FIXTURES / s["file"]).read_text(encoding="utf-8")) == T.clean_text(text):
        title, url = s["title_en"], s["url"]
    start = {
        "event": "start",
        "key": key[:16],
        "chars": len(text),
        "jurisdiction": jur,
        "injection": flags,
    }

    hit = cached(key)
    if hit:

        def replay():
            t0 = time.time()
            yield _sse(
                {
                    **start,
                    "cached": True,
                    "first_seconds": next(
                        (
                            e["result"].get("wall_seconds")
                            for e in hit["events"]
                            if e.get("event") == "result"
                        ),
                        None,
                    ),
                }
            )
            for ev in _replay(hit):
                if ev.get("event") == "result":
                    ev = {
                        **ev,
                        "result": {
                            **ev["result"],
                            "cached": True,
                            "replay_seconds": round(time.time() - t0, 1),
                        },
                    }
                yield _sse(ev)

        return StreamingResponse(
            replay(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    with JOBS_LOCK:
        job = JOBS.get(key)
        if not job:
            ip = real_ip(request)
            if not SLOTS.acquire(timeout=0.5):
                raise HTTPException(503, msg("busy"))
            if not PER_IP.allow(ip):
                SLOTS.release()
                raise HTTPException(429, msg("ip"))
            if not BUDGET.take():
                SLOTS.release()
                raise HTTPException(429, msg("budget"))
            job = JOBS[key] = Job(key)
            threading.Thread(target=_run, args=(job, text, jur, title, url), daemon=True).start()

    def live():
        yield _sse({**start, "cached": False, "timeout": TIMEOUT})
        for ev in (
            job.follow()
        ):  # the run goes on if the visitor leaves: its result is cached for the next one
            yield ": ping\n\n" if ev is None else _sse(ev)

    return StreamingResponse(
        live(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
