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
    )
    if p.returncode != 0:
        raise LLMError(f"{cmd[0]} exit {p.returncode}: {p.stderr[-800:] or p.stdout[-800:]}")
    return p.stdout


def _call_claude(system: str, prompt: str, schema: dict | None, timeout: int):
    cmd = [
        "claude",
        "-p",
        "--model",
        CLAUDE_MODEL,
        "--output-format",
        "json",
        "--tools",
        "",
        "--no-session-persistence",
        "--system-prompt",
        system,
    ]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    out = _run(cmd, prompt, timeout)
    env = json.loads(out)
    if env.get("is_error"):
        raise LLMError(f"claude error: {str(env)[:800]}")
    model = ",".join(k for k in (env.get("modelUsage") or {}) if "haiku" not in k) or CLAUDE_MODEL
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
):
    """Returns (parsed_json, meta). Raises LLMError when every backend fails."""
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
    for backend in _backend_order():
        for attempt in range(retries + 1):
            try:
                with _sem:
                    t0 = time.time()
                    parsed, raw, model, extra = _CALLERS[backend](system, prompt, schema, timeout)
                rec = {
                    "parsed": parsed,
                    "raw": raw,
                    "model": model,
                    "backend": backend,
                    "tag": tag,
                    "seconds": round(time.time() - t0, 1),
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "prompt_chars": len(system) + len(prompt),
                    **extra,
                }
                tmp = cpath.with_suffix(".tmp")
                tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
                tmp.replace(cpath)
                return parsed, {
                    "prompt_hash": ph,
                    "model": model,
                    "cached": False,
                    "raw": raw,
                    "tag": tag,
                    "created": rec["created"],
                }
            except Exception as e:  # noqa: BLE001 - try next attempt/backend
                errors.append(f"{backend}#{attempt}: {e}")
                time.sleep(3 * (attempt + 1))
    raise LLMError(f"all LLM backends failed for {tag}: " + " | ".join(errors)[-2000:])
