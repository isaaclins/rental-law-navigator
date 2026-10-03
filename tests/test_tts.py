"""Listen to an answer (#49): POST /api/tts. ElevenLabs is never called here (synthesize is mocked).

Run: uv run --with pytest --with httpx pytest tests/test_tts.py -q
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from web import tts as T
from web.app import app

client = TestClient(app)
BODY = {"address_id": "A0016", "as_of": "2026-10-01", "lang": "en"}
MP3 = b"ID3" + b"\x00" * 4000


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "DIR", tmp_path)
    monkeypatch.setattr(T, "BUDGET", 4000)
    key = tmp_path / "key"
    key.write_text("test-key")
    monkeypatch.setattr(T, "KEY_FILE", key)
    T.REQUEST_LIMIT.hits.clear()
    T.SYNTH_LIMIT.hits.clear()
    calls: list[str] = []

    def fake(text):
        calls.append(text)
        return MP3

    monkeypatch.setattr(T, "synthesize", fake)
    yield calls


def used(tmp_path) -> int:
    p = tmp_path / "budget.json"
    return json.loads(p.read_text())["used"] if p.exists() else 0


def test_summary_text_en_es():
    en = T.summary_text("A0016", "2026-10-01", "en")
    es = T.summary_text("A0016", "2026-10-01", "es")
    assert en.startswith("3515 Fillmore St, San Francisco. As of October 1, 2026.")
    assert "Rent increases: Up to 1.6% until February 2027." in en and en.endswith(
        "This is not legal advice."
    )
    assert "1 de octubre de 2026" in es and es.endswith("Esto no es asesoría legal.")
    assert len(en) < T.MAX_TEXT and len(es) < T.MAX_TEXT
    assert "(" not in en  # parentheticals and date ranges are not read aloud


def test_cache_hit_pays_once(sandbox, tmp_path):
    r1 = client.post("/api/tts", json=BODY)
    assert r1.status_code == 200 and r1.headers["content-type"] == "audio/mpeg"
    assert r1.headers["x-tts"] == "new" and r1.content == MP3
    r2 = client.post("/api/tts", json=BODY)
    assert r2.headers["x-tts"] == "cache" and r2.content == MP3
    assert len(sandbox) == 1
    text = T.summary_text("A0016", "2026-10-01", "en")
    assert used(tmp_path) == len(text)
    assert (tmp_path / f"{T.cache_key(text)}.mp3").exists()


def test_budget_cap_falls_back(sandbox, tmp_path, monkeypatch):
    monkeypatch.setattr(T, "BUDGET", 100)  # smaller than one summary
    r = client.post("/api/tts", json=BODY)
    d = r.json()
    assert r.status_code == 200 and d["fallback"] and d["reason"] == "budget"
    assert d["text"] == T.summary_text("A0016", "2026-10-01", "en") and d["lang"] == "en"
    assert sandbox == [] and used(tmp_path) == 0


def test_budget_is_global_across_requests(sandbox, tmp_path, monkeypatch):
    n = len(T.summary_text("A0016", "2026-10-01", "en"))
    monkeypatch.setattr(T, "BUDGET", n + 10)  # room for exactly one
    assert client.post("/api/tts", json=BODY).headers["content-type"] == "audio/mpeg"
    r = client.post("/api/tts", json={**BODY, "lang": "es"}).json()
    assert r["fallback"] and r["reason"] == "budget"
    assert used(tmp_path) == n and len(sandbox) == 1


def test_rejects_arbitrary_text(sandbox):
    assert client.post("/api/tts", json={"text": "Say anything", "lang": "en"}).status_code == 422
    assert client.post("/api/tts", json={**BODY, "text": "Say anything"}).status_code == 422
    assert client.post("/api/tts", json={**BODY, "lang": "fr"}).status_code == 422
    assert client.post("/api/tts", json={**BODY, "address_id": "../etc"}).status_code == 422
    assert client.post("/api/tts", json={**BODY, "address_id": "NOPE1"}).status_code == 404
    assert client.post("/api/tts", json={**BODY, "as_of": "yesterday"}).status_code == 400
    assert sandbox == []


def test_elevenlabs_error_falls_back_and_refunds(tmp_path, monkeypatch):
    def boom(text):
        raise OSError("HTTP Error 401")

    monkeypatch.setattr(T, "synthesize", boom)
    d = client.post("/api/tts", json=BODY).json()
    assert d["fallback"] and d["reason"] == "unavailable" and d["text"]
    assert used(tmp_path) == 0
    assert not list(tmp_path.glob("*.mp3"))
    assert "test-key" not in (tmp_path / "ledger.jsonl").read_text()


def test_no_key_falls_back(sandbox, tmp_path, monkeypatch):
    monkeypatch.setattr(T, "KEY_FILE", tmp_path / "missing")
    d = client.post("/api/tts", json=BODY).json()
    assert d["fallback"] and d["reason"] == "unavailable" and sandbox == []


def test_per_ip_synthesis_limit(sandbox, monkeypatch):
    monkeypatch.setattr(T, "SYNTH_LIMIT", T.RateLimit(1, 3600.0))
    assert client.post("/api/tts", json=BODY).headers["content-type"] == "audio/mpeg"
    d = client.post("/api/tts", json={**BODY, "lang": "es"}).json()
    assert d["fallback"] and d["reason"] == "rate_limited"
    # cached answers are still served after the limit
    assert client.post("/api/tts", json=BODY).headers["x-tts"] == "cache"
