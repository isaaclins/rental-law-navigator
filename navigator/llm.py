"""LLM backends with a content-addressed response cache.

Backends (NAVIGATOR_LLM=claude|codex|api, default claude):
  claude : `claude -p --model sonnet --output-format json --json-schema ...` (headless CLI)
  codex  : `codex exec --output-schema ...` (fallback)
  api    : Anthropic Messages API (used when ANTHROPIC_API_KEY is set and chosen, or as fallback)

Every response is cached in cache/llm/<sha256>.json keyed by backend+model+system+prompt+schema,
so reruns are free and reproducible. Callers get (parsed_json, meta) where meta carries the
prompt hash, model, cache hit flag and raw text for the audit log.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request

from .config import CACHE_DIR

CLAUDE_MODEL = os.environ.get("NAVIGATOR_CLAUDE_MODEL", "sonnet")
API_MODEL = os.environ.get("NAVIGATOR_API_MODEL", "claude-sonnet-5-5")
CODEX_MODEL = os.environ.get("NAVIGATOR_CODEX_MODEL", "")
MAX_PARALLEL = int(os.environ.get("NAVIGATOR_MAX_PARALLEL", "3"))
_sem = threading.Semaphore(MAX_PARALLEL)


class LLMError(RuntimeError):
    pass


def _backend_order() -> list[str]:
    first = os.environ.get("NAVIGATOR_LLM", "claude")
    order = [first]
    for b in ("claude", "api", "codex"):
        if b not in order:
            order.append(b)
    return [b for b in order if _available(b)]


def _available(b: str) -> bool:
    if b == "claude":
        return shutil.which("claude") is not None
    if b == "codex":
        return shutil.which("codex") is not None
    if b == "api":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    return False


def _model_name(b: str) -> str:
    return {
        "claude": f"claude-cli:{CLAUDE_MODEL}",
        "api": f"anthropic-api:{API_MODEL}",
        "codex": f"codex:{CODEX_MODEL or 'default'}",
    }[b]


def prompt_hash(system: str, prompt: str, schema: dict | None) -> str:
    h = hashlib.sha256()
    for part in (system, prompt, json.dumps(schema, sort_keys=True) if schema else ""):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _extract_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i:
        return json.loads(text[i : j + 1])
    raise LLMError("no JSON object in model output")


def _run(cmd: list[str], stdin: str, timeout: int) -> str:
    p = subprocess.run(
        ["nice", "-n", "19", *cmd],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=tempfile.gettempdir(),
        # no auto-memory: the model sees only our system prompt and prompt
        env={**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
    )
    if p.returncode != 0:
        raise LLMError(f"{cmd[0]} exit {p.returncode}: {p.stderr[-800:] or p.stdout[-800:]}")
    return p.stdout


def _call_claude(
    system: str, prompt: str, schema: dict | None, timeout: int, model: str | None = None
):
    cmd = [
        "claude",
        "-p",
        "--model",
        model or CLAUDE_MODEL,
        "--output-format",
        "json",
        "--tools",
        "",
        "--no-session-persistence",
        # isolated: no user CLAUDE.md / settings / MCP servers / skills in the model's context
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--system-prompt",
        system,
    ]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    out = _run(cmd, prompt, timeout)
    env = json.loads(out)
    if env.get("is_error"):
        raise LLMError(f"claude error: {str(env)[:800]}")
    usage = env.get("modelUsage") or {}
    want = model or CLAUDE_MODEL
    model = ",".join(k for k in usage if "haiku" not in k or "haiku" in want) or want
    extra = {"cost_usd": env.get("total_cost_usd"), "usage": env.get("usage")}
    if env.get("structured_output") is not None:
        return env["structured_output"], json.dumps(env["structured_output"]), model, extra
    raw = env.get("result", "")
    return _extract_json(raw), raw, model, extra


def _call_codex(system: str, prompt: str, schema: dict | None, timeout: int):
    with tempfile.TemporaryDirectory() as td:
        last = os.path.join(td, "last.txt")
        cmd = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-o", last]
        if CODEX_MODEL:
            cmd += ["-m", CODEX_MODEL]
        if schema:
            sp = os.path.join(td, "schema.json")
            open(sp, "w").write(json.dumps(_strict_schema(schema)))
            cmd += ["--output-schema", sp]
        cmd.append("-")
        _run(cmd, f"{system}\n\n{prompt}\n\nReturn only the JSON object.", timeout)
        raw = open(last, encoding="utf-8").read()
    return _extract_json(raw), raw, _model_name("codex"), {}


def _strict_schema(s):
    """codex/OpenAI structured outputs want additionalProperties:false everywhere; keep it loose otherwise."""
    return s


def _call_api(system: str, prompt: str, schema: dict | None, timeout: int):
    body = {
        "model": API_MODEL,
        "max_tokens": 32000,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": prompt
                + (
                    "\n\nReturn only one JSON object matching this JSON schema:\n"
                    + json.dumps(schema)
                    if schema
                    else ""
                ),
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        env = json.loads(r.read())
    raw = "".join(b.get("text", "") for b in env.get("content", []) if b.get("type") == "text")
    return _extract_json(raw), raw, env.get("model", API_MODEL), {"usage": env.get("usage")}


_CALLERS = {"claude": _call_claude, "codex": _call_codex, "api": _call_api}


def call_llm(
    system: str,
    prompt: str,
    schema: dict | None = None,
    *,
    tag: str = "",
    timeout: int = 900,
    use_cache: bool = True,
    retries: int = 2,
    model: str | None = None,
    backends: tuple[str, ...] | None = None,
    store: bool = True,
):
    """Returns (parsed_json, meta). Raises LLMError when every backend fails.
    model: claude CLI model alias for this call (default NAVIGATOR_CLAUDE_MODEL); backends: restrict the order;
    store=False: nothing is written to the cache (answers to user questions are never kept on disk)."""
    ph = prompt_hash(system, prompt, schema)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cpath = CACHE_DIR / f"{ph}.json"
    if use_cache and cpath.exists():
        c = json.loads(cpath.read_text(encoding="utf-8"))
        return c["parsed"], {
            "prompt_hash": ph,
            "model": c["model"],
            "cached": True,
            "raw": c["raw"],
            "tag": tag,
            "created": c.get("created"),
        }
    errors = []
    for backend in [b for b in _backend_order() if not backends or b in backends]:
        for attempt in range(retries + 1):
            try:
                with _sem:
                    t0 = time.time()
                    kw = {"model": model} if model and backend == "claude" else {}
                    parsed, raw, used, extra = _CALLERS[backend](
                        system, prompt, schema, timeout, **kw
                    )
                rec = {
                    "parsed": parsed,
                    "raw": raw,
                    "model": used,
                    "backend": backend,
                    "tag": tag,
                    "seconds": round(time.time() - t0, 1),
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "prompt_chars": len(system) + len(prompt),
                    **extra,
                }
                if store:
                    tmp = cpath.with_suffix(".tmp")
                    tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
                    tmp.replace(cpath)
                return parsed, {
                    "prompt_hash": ph,
                    "model": used,
                    "cached": False,
                    "raw": raw,
                    "tag": tag,
                    "created": rec["created"],
                }
            except Exception as e:  # noqa: BLE001 - try next attempt/backend
                errors.append(f"{backend}#{attempt}: {e}")
                if attempt < retries:
                    time.sleep(3 * (attempt + 1))
    raise LLMError(f"all LLM backends failed for {tag}: " + " | ".join(errors)[-2000:])


def stream_cached(system: str, prompt: str, cache_dir=None) -> bool:
    """True when stream_llm(..., use_cache=True) would answer from the cache without calling the model."""
    return (
        (cache_dir or CACHE_DIR) / f"{prompt_hash(system, prompt, {'stream': True})}.json"
    ).exists()


def stream_llm(
    system: str,
    prompt: str,
    on_text=None,
    *,
    model: str | None = None,
    timeout: int = 60,
    tag: str = "",
    use_cache: bool = False,
    store: bool = False,
    cache_dir=None,
):
    """Streaming variant for interactive answers (web/ask.py): claude CLI with stream-json, no extended thinking
    (first token ~1 s instead of ~30 s), JSON requested in the prompt instead of --json-schema (one turn, not two).
    on_text(text_so_far) is called as tokens arrive. Returns (parsed_json, meta); same cache files as call_llm."""
    ph = prompt_hash(system, prompt, {"stream": True})
    cdir = cache_dir or CACHE_DIR
    cpath = cdir / f"{ph}.json"
    if use_cache and cpath.exists():
        c = json.loads(cpath.read_text(encoding="utf-8"))
        if on_text:
            on_text(c["raw"])
        return c["parsed"], {
            "prompt_hash": ph,
            "model": c["model"],
            "cached": True,
            "raw": c["raw"],
            "tag": tag,
        }
    if not _available("claude"):
        parsed, meta = call_llm(
            system,
            prompt,
            None,
            tag=tag,
            timeout=timeout,
            retries=0,
            use_cache=False,
            store=False,
            backends=("api",),
        )
        if on_text:
            on_text(meta["raw"])
        return parsed, meta
    cmd = [
        "nice",
        "-n",
        "5",  # interactive answers: a little below the site, well above batch jobs (nice 19)
        "claude",
        "-p",
        "--model",
        model or CLAUDE_MODEL,
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--tools",
        "",
        "--no-session-persistence",
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--system-prompt",
        system,
    ]
    env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "MAX_THINKING_TOKENS": "0"}
    t0 = time.time()
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
        cwd=tempfile.gettempdir(),
        start_new_session=True,  # own process group: a timeout kills the whole tree
    )

    def kill_tree() -> None:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            p.kill()

    killer = threading.Timer(timeout, kill_tree)
    killer.daemon = True
    killer.start()
    text, used, err = "", model or CLAUDE_MODEL, None
    try:
        p.stdin.write(prompt)
        p.stdin.close()
        for line in p.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("type")
            if kind == "stream_event":
                e = ev.get("event") or {}
                d = e.get("delta") or {}
                if e.get("type") == "content_block_delta" and d.get("type") == "text_delta":
                    text += d.get("text", "")
                    if on_text:
                        on_text(text)
            elif kind == "system" and ev.get("subtype") == "init":
                used = ev.get("model") or used
            elif kind == "result":
                if ev.get("is_error"):
                    err = str(ev.get("result") or "error")[:300]
                elif ev.get("result") and not text:
                    text = ev["result"]
        p.wait(timeout=5)
    finally:
        killer.cancel()
        if p.poll() is None:
            kill_tree()
    if err or not text:
        raise LLMError(f"claude stream failed for {tag}: {err or 'no output (timeout?)'}")
    parsed = _extract_json(text)
    if store:
        rec = {
            "parsed": parsed,
            "raw": text,
            "model": used,
            "backend": "claude-stream",
            "tag": tag,
            "seconds": round(time.time() - t0, 1),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        cdir.mkdir(parents=True, exist_ok=True)
        tmp = cpath.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cpath)
    return parsed, {"prompt_hash": ph, "model": used, "cached": False, "raw": text, "tag": tag}
