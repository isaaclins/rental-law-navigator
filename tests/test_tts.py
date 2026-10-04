"""Listen (#49): spoken briefings per persona (web/briefing.py) and POST /api/tts. ElevenLabs is never called
here (synthesize is mocked).

Run: uv run --with pytest --with httpx pytest tests/test_tts.py -q
"""

from __future__ import annotations

import json
import re

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
        return MP3, char_alignment(text)

    monkeypatch.setattr(T, "synthesize", fake)
    yield calls


def char_alignment(text: str, per_char: float = 0.06) -> dict:
    """The shape of ElevenLabs' with-timestamps alignment: one start and end time per input character."""
    return {
        "characters": list(text),
        "character_start_times_seconds": [i * per_char for i in range(len(text))],
        "character_end_times_seconds": [(i + 1) * per_char for i in range(len(text))],
    }


def used(tmp_path) -> int:
    p = tmp_path / "budget.json"
    return json.loads(p.read_text())["used"] if p.exists() else 0


def text(aid="A0001", persona="renter", lang="en", as_of="2026-10-01", topic=None) -> str:
    return T.script_text(aid, as_of, lang, persona, topic)


CLOSE_EN = "Every point has its source on screen. This is general information, not legal advice."
CLOSE_ES = "Cada punto tiene su fuente en pantalla. Esto es información general, no asesoría legal."


def test_renter_briefing_en():
    t = text()
    assert t.startswith("For renters at 6238 De Longpre Avenue, as of October 1, 2026.")
    # the rent limit in plain terms; the city's figure for this date is not published in our data, and it says so
    assert "This unit has rent control: one increase a year" in t
    assert "We have no figure after June 30, 2026; the last was 3 percent." in t
    assert "You can only be evicted for a reason on the city's list." in t
    assert "If it's not your fault, most tenants are owed 11,000 to 27,400 dollars to move." in t
    assert (
        "If they ask for more than one month's rent as a deposit, or more than about 69 dollars to apply, that's over the limit."
        in t
    )
    assert "two for small landlords" not in t  # 32 units: the small-landlord deposit can't apply
    assert "Coming up: on July 1, 2027, the city sets new relocation amounts." in t
    assert "Want to check a rent increase? Use 'Check a rent increase' below." in t
    assert t.endswith(CLOSE_EN)


def test_renter_order():
    t = text()
    keys = [
        "rent control",
        "evicted",
        "over the limit",
        "Coming up",
        "Check a rent increase",
        "source",
    ]
    assert [t.index(k) for k in keys] == sorted(t.index(k) for k in keys)


def test_owner_briefing_en():
    t = text(persona="owner")
    assert t.startswith("For owners and managers of 6238 De Longpre Avenue, as of October 1, 2026.")
    assert "one increase every 12 months, up to the city's yearly percentage" in t
    assert "so check it before raising the rent" in t
    assert (
        "You'll need a reason from the city's list to end a tenancy, and no-fault evictions mean relocation payments."
        in t
    )
    assert "You can't ask for more than one month's rent as a deposit" in t
    # obligations first, the upcoming changes to prepare for last (before sources and the disclaimer)
    assert t.index("Check a rent increase") < t.index("Plan ahead: on July 1, 2027")
    assert t.endswith("the city sets new relocation amounts. " + CLOSE_EN)
    assert "your landlord" not in t.lower()


def test_spanish_is_its_own_text():
    t = text("A0065", lang="es")
    assert t.startswith("Para inquilinos de 63 Bailey Street, al 1 de octubre de 2026.")
    assert "Massachusetts prohíbe el control de rentas local" in t
    assert (
        "Si le piden más de un mes de renta de depósito, o cualquier cuota de solicitud, eso supera el límite."
        in t
    )
    assert "¿Quiere revisar un depósito? Use 'Revisar un depósito' más abajo." in t
    assert t.endswith(CLOSE_ES)
    for en in (" the ", " rent ", "landlord", "deposit", " you ", "Check a"):
        assert en not in t, en
    es = text("A0001", lang="es")
    assert "No tenemos cifra posterior al 30 de junio de 2026" in es
    assert "Lo que viene: el 1 de julio de 2027 la ciudad fija nuevos montos de reubicación." in es


def test_unknown_names_the_fact_that_settles_it():
    r = text("A0101")  # Jersey City, year built not in the data
    assert (
        "We don't know the building's exact certificate-of-occupancy date, which decides whether "
        "Jersey City rent control applies. Ask your landlord, or check with the city's Office of "
        "Landlord-Tenant Relations." in r
    )
    o = text("A0101", persona="owner")
    assert (
        "depends on your building's certificate-of-occupancy date, so keep that certificate handy"
        in o
    )
    es = text("A0101", lang="es")
    assert "No sabemos la fecha exacta del certificado de ocupación del edificio" in es
    # more than two rules waiting for one fact: the topics are named instead
    nj = text("A0227", persona="owner")
    assert (
        "Whether eviction protections, the deposit cap and the screening rules apply depends on whether you live in the building yourself."
        in nj
    )


def test_upcoming_changes_in_words():
    assert (
        "Coming up: on July 1, 2027, New Jersey's ban on rent-setting software takes effect."
        in text("A0101")
    )
    sf = text("A0016")
    assert "by at most 1.6 percent until February 28, 2027" in sf
    assert (
        "Coming up: on March 1, 2027, the city sets a new rent increase, new relocation amounts and a new deposit rate."
        in sf
    )
    later = text("A0016", as_of="2027-03-15")  # the published figure has run out
    assert "1.6 percent" not in later and "We have no figure after February 28, 2027 yet." in later
    ma = text("A0065")  # nothing dated; a pending bill is said to be not law
    assert "Nothing we track changes here in the next 12 months." in ma
    assert (
        "A Massachusetts bill to ban rent-setting software is being debated, but it isn't law yet."
        in ma
    )


BANNED = re.compile(
    r"\b(RSO|LAHD|JCO|CPI|IPC|AGA|SF|LA(?! Housing)|NJ|MA|CA|DND|BPDA|FMR|HUD|CO|TPA|Cal|Civ|Mun|N\.J\.S\.A)\b|[§%$()/]|\d{4}-\d{2}"
)


def test_spoken_words_only():
    """No abbreviations, citations, symbols or ISO dates are read aloud; lengths stay about 35-50 s / 10-15 s."""
    from web import app as A

    ids = sorted(A.STORE.addresses)[::7] + ["A0001", "A0016", "A0065", "A0101", "A0227", "A0432"]
    for aid in ids:
        for lang in ("en", "es"):
            for persona in ("renter", "owner"):
                t = text(aid, persona, lang)
                assert not BANNED.search(t), (aid, lang, persona, BANNED.search(t).group(0), t)
                assert 400 <= len(t) <= (780 if lang == "en" else 880), (aid, lang, persona, len(t))
                for cat in T.B.CATS:
                    x = text(aid, persona, lang, topic=cat)
                    assert not BANNED.search(x), (aid, cat, BANNED.search(x).group(0), x)
                    assert 60 <= len(x) <= 420, (aid, cat, len(x), x)
    assert "the LA Housing Department" in text(persona="owner", topic="just_cause_eviction")


def test_explain_this_topic():
    t = text(topic="just_cause_eviction")
    assert t.startswith("You can only be evicted for a reason on the city's list.")
    assert t.endswith("General information, not legal advice.")
    assert len(t) < 260
    script = T.script_for("A0001", "2026-10-01", "en", "renter", "just_cause_eviction")
    assert {c for c, _ in script} == {"just_cause_eviction"}


def test_chapters_follow_the_script():
    script = T.script_for("A0016", "2026-10-01", "en", "renter")
    ch = T.B.chapters(script)
    t = T.B.text_of(script)
    assert ch[0] == ["", 0] and [c for c, _ in ch][1:3] == [
        "rent_increase_limits",
        "just_cause_eviction",
    ]
    for _cid, pos in ch:
        assert pos == 0 or t[pos - 1] == " "
    r = client.post("/api/tts", json={**BODY, "persona": "owner"})
    assert json.loads(r.headers["x-tts-chapters"])[0] == ["", 0]
    assert int(r.headers["x-tts-chars"]) == len(text("A0016", "owner"))


def test_personas_and_topics_cached_separately(sandbox, tmp_path):
    for extra in ({}, {"persona": "owner"}, {"topic": "security_deposits"}):
        assert client.post("/api/tts", json={**BODY, **extra}).headers["x-tts"] == "new"
    assert client.post("/api/tts", json={**BODY, "persona": "owner"}).headers["x-tts"] == "cache"
    assert len(sandbox) == 3 and len(set(sandbox)) == 3
    assert used(tmp_path) == sum(map(len, sandbox))


def test_prewarm_respects_the_budget(sandbox, tmp_path, monkeypatch, capsys):
    one = len(text("A0001"))
    monkeypatch.setattr(T, "BUDGET", one + 500)
    T.main(["prewarm", "--reserve", "400"])  # room for exactly the first briefing
    out = capsys.readouterr().out
    assert sandbox == [text("A0001")] and "A0001 renter" in out and "new" in out
    assert out.count("skipped") == 5 and used(tmp_path) == one


def test_cache_hit_pays_once(sandbox, tmp_path):
    r1 = client.post("/api/tts", json=BODY)
    assert r1.status_code == 200 and r1.headers["content-type"] == "audio/mpeg"
    assert r1.headers["x-tts"] == "new" and r1.content == MP3
    r2 = client.post("/api/tts", json=BODY)
    assert r2.headers["x-tts"] == "cache" and r2.content == MP3
    assert len(sandbox) == 1
    t = text("A0016")
    assert used(tmp_path) == len(t)
    assert (tmp_path / f"{T.cache_key(t)}.mp3").exists()


def test_budget_cap_falls_back(sandbox, tmp_path, monkeypatch):
    monkeypatch.setattr(T, "BUDGET", 100)  # smaller than one briefing
    r = client.post("/api/tts", json=BODY)
    d = r.json()
    assert r.status_code == 200 and d["fallback"] and d["reason"] == "budget"
    assert d["text"] == text("A0016") and d["lang"] == "en"
    assert d["chapters"] == T.B.chapters(T.script_for("A0016", "2026-10-01", "en"))
    assert sandbox == [] and used(tmp_path) == 0


def test_budget_is_global_across_requests(sandbox, tmp_path, monkeypatch):
    n = len(text("A0016"))
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
    assert client.post("/api/tts", json={**BODY, "persona": "lawyer"}).status_code == 422
    assert client.post("/api/tts", json={**BODY, "topic": "Say anything"}).status_code == 422
    assert (
        client.post("/api/tts", json={**BODY, "script": [["", "Say anything"]]}).status_code == 422
    )
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


# ------------------------------------------------------------------ captions (time-synced transcript)
def test_sentences_cover_the_spoken_text():
    script = T.script_for("A0001", "2026-10-01", "en", "renter")
    t = T.B.text_of(script)
    ss = T.sentences(script)
    assert [t[a:b] for a, b in ss][:3] == [
        "For renters at 6238 De Longpre Avenue, as of October 1, 2026.",
        "This unit has rent control: one increase a year, by the city's yearly percentage.",
        "We have no figure after June 30, 2026; the last was 3 percent.",
    ]
    assert "Want to check a rent increase?" in [
        t[a:b] for a, b in ss
    ]  # a question ends a sentence too
    assert ss[0][0] == 0 and ss[-1][1] == len(t)
    assert all(a < b for a, b in ss) and all(p[1] < q[0] for p, q in zip(ss, ss[1:], strict=False))
    es = T.script_for("A0016", "2026-10-01", "es", "renter")
    tes = T.B.text_of(es)
    assert "¿Quiere revisar un aumento de renta?" in [tes[a:b] for a, b in T.sentences(es)]


def test_new_synthesis_saves_its_alignment_and_captions_follow_it(sandbox, tmp_path):
    assert client.post("/api/tts", json=BODY).headers["x-tts"] == "new"
    t = text("A0016")
    h = T.cache_key(t)
    saved = json.loads((tmp_path / f"{h}.align.json").read_text())
    assert saved["source"] == "elevenlabs" and saved["alignment"]["characters"] == list(t)
    c = client.post("/api/tts/captions", json=BODY).json()
    assert c["text"] == t and c["timing"] == "elevenlabs" and c["lang"] == "en"
    assert c["chapters"] == T.B.chapters(T.script_for("A0016", "2026-10-01", "en"))
    words = c["words"]
    assert [t[a:b] for a, b, _, _ in words] == t.split()
    a, b, t0, t1 = words[1]  # "renters" starts at character 4: 4 x 0.06 s
    assert t[a:b] == "renters" and t0 == pytest.approx(0.24) and t1 == pytest.approx(b * 0.06)
    assert all(w[2] <= v[2] for w, v in zip(words, words[1:], strict=False))
    assert len(sandbox) == 1  # the captions never synthesize


def test_captions_without_audio_are_free_and_untimed(sandbox, tmp_path):
    c = client.post("/api/tts/captions", json={**BODY, "lang": "es", "persona": "owner"}).json()
    assert c["words"] is None and c["timing"] is None and c["duration"] is None
    assert c["text"] == text("A0016", "owner", "es") and c["sentences"]
    assert sandbox == [] and used(tmp_path) == 0
    assert (
        client.post("/api/tts/captions", json={**BODY, "text": "Say anything"}).status_code == 422
    )


def test_cached_audio_without_alignment_is_estimated(sandbox, tmp_path):
    t = text("A0016", topic="security_deposits")
    (tmp_path / f"{T.cache_key(t)}.mp3").write_bytes(b"\x00" * 8000 * 12)  # 12 s at 64 kbit/s
    c = client.post("/api/tts/captions", json={**BODY, "topic": "security_deposits"}).json()
    assert c["timing"] == "estimated" and c["duration"] == pytest.approx(12.0)
    w = c["words"]
    assert len(w) == len(t.split()) and 0 < w[0][2] < 0.5 and 11 < w[-1][3] <= 12
    assert all(p[3] <= q[2] for p, q in zip(w, w[1:], strict=False))
    assert sandbox == []


def test_fit_words_takes_recognized_times_and_fills_gaps():
    t = "Rent goes up 3 percent, on July 1, 2027."
    heard = [("Rent", 0.1, 0.4), ("goes", 0.4, 0.6), ("up", 0.6, 0.8), ("three", 0.8, 1.1),
             ("percent,", 1.1, 1.5), ("on", 1.7, 1.8), ("July", 1.8, 2.1), ("first,", 2.1, 2.5),
             ("2027.", 2.6, 3.2)]  # fmt: skip
    w = T.fit_words(t, heard, 3.4)
    assert [t[a:b] for a, b, _, _ in w] == t.split()
    assert w[0][2:] == [0.1, 0.4] and w[4][2:] == [1.1, 1.5] and w[-1][2:] == [2.6, 3.2]
    assert 0.8 <= w[3][2] < w[3][3] <= 1.1  # "3" (heard as "three") sits in the gap it left
    assert 2.1 <= w[7][2] < w[7][3] <= 2.6


def test_whisper_alignment_file_is_used(sandbox, tmp_path):
    t = text("A0016", topic="security_deposits")
    h = T.cache_key(t)
    (tmp_path / f"{h}.mp3").write_bytes(b"\x00" * 8000 * 10)
    words = [[a, b, i * 0.3, i * 0.3 + 0.25] for i, (a, b) in enumerate(T.word_spans(t))]
    T.save_alignment(h, {"source": "whisper", "words": words})
    c = client.post("/api/tts/captions", json={**BODY, "topic": "security_deposits"}).json()
    assert c["timing"] == "whisper" and c["words"] == words
    T.save_alignment(
        h, {"source": "whisper", "words": words[:-1]}
    )  # stale: falls back to the estimate
    assert (
        client.post("/api/tts/captions", json={**BODY, "topic": "security_deposits"}).json()[
            "timing"
        ]
        == "estimated"
    )
