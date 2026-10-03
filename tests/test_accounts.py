"""API tests for My properties (#38): Google sign-in (mocked), sessions + CSRF, demo account, CRUD, alerts, .ics feed.

Run: uv run --with pytest --with httpx2 pytest tests/test_accounts.py -q
Google, the Census geocoder and SMTP are never contacted: every test uses a temporary database, secret and OAuth file.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import time
import urllib.parse

import pytest
from fastapi.testclient import TestClient

from web import accounts as A
from web.app import app

CLIENT_ID = "test-client.apps.googleusercontent.com"
LA = {
    "state": "CA",
    "jurisdiction": "Los Angeles, CA",
    "place": "Los Angeles",
    "county": "Los Angeles County",
}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    oauth = tmp_path / "google-oauth.json"
    oauth.write_text(
        json.dumps(
            {
                "client_id": CLIENT_ID,
                "client_secret": "test-secret",
                "redirect_uris": [
                    "https://navigator.isaaclins.com/auth/google/callback",
                    "http://localhost:8798/auth/google/callback",
                ],
            }
        )
    )
    monkeypatch.setenv("NAVIGATOR_GOOGLE_OAUTH", str(oauth))
    monkeypatch.setenv("NAVIGATOR_SESSION_SECRET", str(tmp_path / "secret"))
    monkeypatch.setenv("NAVIGATOR_ACCOUNTS_DB", str(tmp_path / "private" / "accounts.db"))
    monkeypatch.setenv("NAVIGATOR_RESEND_KEY", str(tmp_path / "resend-key"))
    monkeypatch.setattr(
        A, "LIMITS", {k: A.RateLimit(v.n, v.per) for k, v in A.LIMITS.items()}
    )  # fresh rate limits per test
    monkeypatch.setattr(A, "_http_json", lambda *a, **k: pytest.fail("network call not mocked"))
    return tmp_path


def client(base="http://testserver") -> TestClient:
    return TestClient(app, base_url=base)


# ------------------------------------------------------------------ Google sign-in (mocked)
def start_login(c: TestClient) -> dict:
    r = c.get("/auth/google/login", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(loc).query).items()}


def mock_google(monkeypatch, q: dict, **claims):
    seen = {}

    def fake(url, data=None):
        if url == A.GOOGLE_TOKEN:
            seen["token"] = data
            return {"id_token": "header.payload.sig", "access_token": "x"}
        assert url.startswith(A.GOOGLE_TOKENINFO + "?id_token=")
        info = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": "1234567890",
            "email": "Landlord@Example.com",
            "email_verified": "true",
            "name": "Lee Landlord",
            "exp": str(int(time.time()) + 3600),
            "nonce": q["nonce"],
        }
        info.update(claims)
        return {k: v for k, v in info.items() if v is not None}

    monkeypatch.setattr(A, "_http_json", fake)
    return seen


def test_login_redirect_uses_pkce_and_minimal_scopes():
    c = client("http://localhost:8798")
    q = start_login(c)
    assert q["client_id"] == CLIENT_ID
    assert q["scope"] == "openid email profile"
    assert q["response_type"] == "code" and q["code_challenge_method"] == "S256"
    assert q["redirect_uri"] == "http://localhost:8798/auth/google/callback"
    assert len(q["state"]) >= 40 and len(q["nonce"]) >= 40
    assert A.OAUTH_COOKIE in c.cookies
    q2 = start_login(client("https://navigator.isaaclins.com"))
    assert q2["redirect_uri"] == "https://navigator.isaaclins.com/auth/google/callback"


def test_callback_signs_in_and_verifies_pkce(monkeypatch):
    c = client()
    q = start_login(c)
    seen = mock_google(monkeypatch, q)
    r = c.get(f"/auth/google/callback?code=abc&state={q['state']}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/#/properties"
    # the verifier sent to Google matches the challenge of the authorization request
    v = seen["token"]["code_verifier"]
    assert (
        base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
        == q["code_challenge"]
    )
    assert seen["token"]["client_secret"] == "test-secret" and seen["token"]["code"] == "abc"
    me = c.get("/api/me").json()
    assert me["signed_in"] and me["user"] == {
        "email": "landlord@example.com",
        "name": "Lee Landlord",
        "demo": False,
    }
    assert me["csrf"]
    # the same Google account signs into the same user
    q = start_login(c)
    mock_google(monkeypatch, q, name="Lee L.")
    c.get(f"/auth/google/callback?code=abc&state={q['state']}", follow_redirects=False)
    with sqlite3.connect(A.cfg_path("db")) as db:
        assert db.execute("SELECT COUNT(*) FROM users WHERE is_demo = 0").fetchone()[0] == 1


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.example"},
        {"exp": "1000"},
        {"nonce": "wrong"},
        {"email_verified": "false"},
    ],
)
def test_callback_rejects_bad_id_tokens(monkeypatch, claims):
    c = client()
    q = start_login(c)
    mock_google(monkeypatch, q, **claims)
    r = c.get(f"/auth/google/callback?code=abc&state={q['state']}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/#/properties/signin-failed"
    assert c.get("/api/me").json()["signed_in"] is False


def test_callback_rejects_wrong_state_and_missing_cookie(monkeypatch):
    c = client()
    q = start_login(c)
    mock_google(monkeypatch, q)
    r = c.get("/auth/google/callback?code=abc&state=forged", follow_redirects=False)
    assert r.headers["location"].endswith("signin-failed")
    r = client().get(f"/auth/google/callback?code=abc&state={q['state']}", follow_redirects=False)
    assert r.headers["location"].endswith("signin-failed")
    r = c.get("/auth/google/callback?error=access_denied", follow_redirects=False)
    assert r.headers["location"].endswith("signin-failed")


def test_unconfigured_google(monkeypatch, tmp_path):
    monkeypatch.setenv("NAVIGATOR_GOOGLE_OAUTH", str(tmp_path / "missing.json"))
    c = client()
    assert c.get("/api/me").json()["google"] is False
    assert c.get("/auth/google/login", follow_redirects=False).status_code == 503


def test_secret_file_is_private(env):
    client().post("/auth/demo")
    p = env / "secret"
    assert p.exists() and (p.stat().st_mode & 0o777) == 0o600
    assert (A.cfg_path("db").stat().st_mode & 0o777) == 0o600


# ------------------------------------------------------------------ sessions, cookies, CSRF
def signed_in(email="owner@example.com", sub="sub-1") -> tuple[TestClient, dict]:
    c = client()
    uid = A.upsert_google_user(sub, email, "Owner")
    c.cookies.set(
        A.SESSION_COOKIE,
        A.sign("session", {"uid": uid, "sid": f"s-{sub}"}, 3600),
        domain="testserver.local",
    )
    me = c.get("/api/me").json()
    assert me["signed_in"]
    return c, {"X-CSRF-Token": me["csrf"]}


def test_cookie_flags():
    r = client("https://navigator.isaaclins.com").post("/auth/demo")
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "secure" in sc and "samesite=lax" in sc and "max-age=2592000" in sc
    assert "secure" not in client().post("/auth/demo").headers["set-cookie"].lower()


def test_tampered_or_foreign_session_is_signed_out():
    c, _ = signed_in()
    tok = c.cookies.get(A.SESSION_COOKIE)
    body, mac = tok.split(".")
    forged = A._b64(json.dumps({"uid": 1, "sid": "x", "p": "session", "exp": 9999999999}).encode())
    for bad in (f"{forged}.{mac}", tok[:-2] + "xx", "garbage"):
        c.cookies.set(A.SESSION_COOKIE, bad, domain="testserver.local")
        assert c.get("/api/me").json()["signed_in"] is False
    # an oauth-flow token is not a session token
    c.cookies.set(
        A.SESSION_COOKIE, A.sign("oauth", {"uid": 1, "sid": "x"}, 60), domain="testserver.local"
    )
    assert c.get("/api/me").json()["signed_in"] is False


def test_writes_need_csrf_and_same_origin():
    c, h = signed_in()
    body = {"label": "Home", "address": "6238 De Longpre Ave, Los Angeles, CA", "place": LA}
    assert c.post("/api/properties", json=body).status_code == 403
    assert c.post("/api/properties", json=body, headers={"X-CSRF-Token": "nope"}).status_code == 403
    r = c.post("/api/properties", json=body, headers={**h, "Origin": "https://evil.example"})
    assert r.status_code == 403
    assert c.post("/api/properties", json=body, headers=h).status_code == 201
    assert c.post("/auth/logout").status_code == 403  # logout needs the token too
    assert c.post("/auth/logout", headers=h).status_code == 200
    assert c.get("/api/me").json()["signed_in"] is False


def test_signed_out_gets_401():
    c = client()
    for m, u in [("get", "/api/properties"), ("get", "/api/alerts"), ("delete", "/api/account")]:
        assert getattr(c, m)(u).status_code == 401


# ------------------------------------------------------------------ properties CRUD
def test_crud_and_facts_resolve_unknowns():
    c, h = signed_in()
    body = {
        "label": "  Bloomfield   brownstone ",
        "address": "323 Bloomfield St, Hoboken, NJ 07030",
        "place": {
            "state": "NJ",
            "jurisdiction": "Hoboken, NJ",
            "place": "Hoboken",
            "extra": "ignored",
        },
        "facts": {"year_built": 1890, "units": 4},
    }
    r = c.post("/api/properties", json=body, headers=h)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["label"] == "Bloomfield brownstone" and p["facts"]["owner_occupied"] is None
    pid = p["id"]
    lst = c.get("/api/properties").json()
    assert [x["id"] for x in lst["properties"]] == [pid] and lst["demo"] is False
    s = lst["properties"][0]["summary"]
    assert s["counts"]["applies"] > 0 and s["counts"].get("unknown", 0) >= 1
    assert s["next"]["date"] == "2027-07-01" and "FAIR" in s["next"]["title"]  # NJ FAIR Act
    d = c.get(f"/api/properties/{pid}?as_of=2026-10-01").json()
    assert d["view"]["categories"] and d["view"]["fact_counts"].get("owner_occupied", 0) >= 1
    ev = d["changes"]["events"][0]
    assert ev["date"] == "2027-07-01" and ev["items"][0]["kind"] == "takes_effect"
    before = d["view"]["summary"].get("unknown", 0)
    # the owner-occupancy fact resolves an unknown
    r = c.patch(
        f"/api/properties/{pid}",
        json={"facts": {"year_built": 1890, "units": 4, "owner_occupied": True}},
        headers=h,
    )
    assert r.status_code == 200 and r.json()["facts"]["owner_occupied"] is True
    after = c.get(f"/api/properties/{pid}").json()["view"]["summary"].get("unknown", 0)
    assert after < before
    # on the effective date the FAIR Act applies and is no longer "coming"
    later = c.get(f"/api/properties/{pid}?as_of=2027-07-01").json()
    assert all(e["date"] > "2027-07-01" for e in later["changes"]["events"])
    assert c.delete(f"/api/properties/{pid}", headers=h).json() == {"ok": True}
    assert c.get(f"/api/properties/{pid}").status_code == 404


def test_validation():
    c, h = signed_in()
    bad = [
        {"label": "x", "address": "1 Main St", "place": {"state": "TX"}},
        {
            "label": "x",
            "address": "1 Main St",
            "place": {"state": "CA", "jurisdiction": "Gotham, CA"},
        },
        {"label": "x", "address": "1 Main St", "place": LA, "facts": {"units": 0}},
        {"label": "x", "address": "1 Main St", "place": LA, "facts": {"tenant_name": "Bob"}},
        {"label": "", "address": "1 Main St", "place": LA},
    ]
    for b in bad:
        assert c.post("/api/properties", json=b, headers=h).status_code == 422, b
    assert c.get("/api/properties?as_of=nope").status_code == 422


def test_users_cannot_see_each_other():
    a, ha = signed_in("a@example.com", "a")
    b, hb = signed_in("b@example.com", "b")
    pid = a.post(
        "/api/properties",
        json={"label": "A's", "address": "6238 De Longpre Ave, Los Angeles, CA", "place": LA},
        headers=ha,
    ).json()["id"]
    assert b.get(f"/api/properties/{pid}").status_code == 404
    assert b.patch(f"/api/properties/{pid}", json={"label": "mine"}, headers=hb).status_code == 404
    assert b.delete(f"/api/properties/{pid}", headers=hb).status_code == 404
    assert b.get("/api/properties").json()["properties"] == []


def test_property_limit(monkeypatch):
    monkeypatch.setattr(A, "MAX_PROPERTIES", 2)
    c, h = signed_in()
    body = {"label": "x", "address": "6238 De Longpre Ave, Los Angeles, CA", "place": LA}
    assert [c.post("/api/properties", json=body, headers=h).status_code for _ in range(3)] == [
        201,
        201,
        422,
    ]


# ------------------------------------------------------------------ demo account
def test_demo_account_is_read_only():
    c = client()
    assert c.post("/auth/demo").status_code == 200
    me = c.get("/api/me").json()
    assert me["user"]["demo"] is True
    h = {"X-CSRF-Token": me["csrf"]}
    props = c.get("/api/properties").json()["properties"]
    assert [p["jurisdiction"] for p in props] == [
        "San Francisco, CA",
        "Los Angeles, CA",
        "Hoboken, NJ",
    ]
    assert props[0]["facts"]["year_built"] < 1979
    pid = props[0]["id"]
    body = {"label": "x", "address": "6238 De Longpre Ave, Los Angeles, CA", "place": LA}
    assert c.post("/api/properties", json=body, headers=h).status_code == 403
    assert c.patch(f"/api/properties/{pid}", json={"label": "x"}, headers=h).status_code == 403
    assert c.delete(f"/api/properties/{pid}", headers=h).status_code == 403
    assert c.delete("/api/account", headers=h).status_code == 403
    assert c.put("/api/alerts", json={"email_digest": True}, headers=h).status_code == 403
    assert c.post("/api/alerts/test-email", headers=h).status_code == 403
    assert c.get(f"/api/properties/{pid}").json()["demo"] is True


# ------------------------------------------------------------------ alerts: calendar feed + email
def test_ics_feed():
    c = client()
    c.post("/auth/demo")
    r = c.get("/cal/demo.ics")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    raw = r.content
    assert raw.startswith(b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\n") and raw.endswith(
        b"END:VCALENDAR\r\n"
    )
    lines = raw.split(b"\r\n")
    assert all(len(x) <= 75 for x in lines), max(lines, key=len)
    assert b"\n" not in raw.replace(b"\r\n", b"")
    text = raw.decode().replace("\r\n ", "")  # unfold
    assert text.count("BEGIN:VEVENT") == text.count("END:VEVENT") >= 3
    assert "DTSTART;VALUE=DATE:20270701" in text and "Algorithmic Inflation of Rent" in text
    assert "DTSTART;VALUE=DATE:20270301" in text  # SF annual allowable increase: new figure due
    assert "Not legal advice" in text and "TRIGGER:-P14D" in text
    assert "UID:ce-" in text
    assert client().get("/cal/unknown-token.ics").status_code == 404
    assert client().get("/cal/a%20b.ics").status_code == 404


def test_calendar_rotation_and_alert_prefs():
    c, h = signed_in()
    a = c.get("/api/alerts").json()
    url = a["calendar"]["url"]
    tok = url.rsplit("/", 1)[1]
    assert (
        a["calendar"]["webcal"].startswith("webcal://")
        and "calendar.google.com" in a["calendar"]["google"]
    )
    assert len(tok) > 30 and c.get(f"/cal/{tok}").status_code == 200
    new = c.post("/api/alerts/calendar/rotate", headers=h).json()["calendar"]["url"]
    assert new != url
    assert c.get(f"/cal/{tok}").status_code == 404
    assert (
        c.put("/api/alerts", json={"email_digest": True}, headers=h).json()["email_digest"] is True
    )
    assert c.get("/api/alerts").json()["email_digest"] is True


def test_test_email_goes_only_to_the_user(monkeypatch):
    sent = []
    monkeypatch.setattr(
        A, "send_mail", lambda to, subject, text, html=None: sent.append((to, subject, text, html))
    )
    c, h = signed_in("me@example.com")
    c.post(
        "/api/properties",
        json={
            "label": "Brownstone",
            "address": "323 Bloomfield St, Hoboken, NJ",
            "place": {"state": "NJ", "jurisdiction": "Hoboken, NJ"},
        },
        headers=h,
    )
    r = c.post("/api/alerts/test-email", headers=h)
    assert r.status_code == 200 and r.json()["sent_to"] == "me@example.com"
    to, subject, text, html = sent[0]
    assert to == "me@example.com" and "Test alert" in subject
    assert "Brownstone" in text and "Not legal advice" in text and "Jul 1, 2027" in text
    assert "<table" in html
    assert c.post("/api/alerts/test-email").status_code == 403  # CSRF
    codes = [c.post("/api/alerts/test-email", headers=h).status_code for _ in range(3)]
    assert codes == [200, 200, 429]  # 3 per hour per user
    assert len(sent) == 3


def test_send_mail_uses_resend_smtp(monkeypatch, env):
    (env / "resend-key").write_text("re_test_key\n")
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self, context):
            calls.append(("starttls",))

        def login(self, user, pw):
            calls.append(("login", user, pw))

        def send_message(self, msg):
            calls.append(("send", msg["From"], msg["To"]))

    monkeypatch.setattr(A.smtplib, "SMTP", FakeSMTP)
    A.send_mail("me@example.com", "s", "t", "<p>h</p>")
    assert calls == [
        ("connect", "smtp.resend.com", 587),
        ("starttls",),
        ("login", "resend", "re_test_key"),
        ("send", "Clause & Effect <contact@isaaclins.com>", "me@example.com"),
    ]


def test_delete_account_wipes_everything():
    c, h = signed_in("gone@example.com", "gone")
    c.post(
        "/api/properties",
        json={"label": "x", "address": "6238 De Longpre Ave, Los Angeles, CA", "place": LA},
        headers=h,
    )
    tok = c.get("/api/alerts").json()["calendar"]["url"].rsplit("/", 1)[1]
    r = c.delete("/api/account", headers=h)
    assert r.status_code == 200 and "ce_session=" in r.headers["set-cookie"]
    with sqlite3.connect(A.cfg_path("db")) as db:
        assert (
            db.execute("SELECT COUNT(*) FROM users WHERE email = 'gone@example.com'").fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM properties p JOIN users u ON u.id = p.user_id WHERE u.is_demo = 0"
            ).fetchone()[0]
            == 0
        )
        assert db.execute("SELECT COUNT(*) FROM properties").fetchone()[0] == len(A.DEMO_PROPERTIES)
        assert db.execute("SELECT COUNT(*) FROM alert_prefs").fetchone()[0] == 1  # demo only
    assert client().get(f"/cal/{tok}").status_code == 404


def test_public_pages():
    c = client()
    for path, words in [
        ("/privacy", ["Delete anytime", "never sell"]),
        ("/terms", ["not advice", "No warranty"]),
    ]:
        r = c.get(path)
        assert r.status_code == 200 and "Not legal advice" in r.text
        for w in words:
            assert w.lower() in r.text.lower()


def test_safe_next():
    assert A.safe_next("/#/properties/3") == "/#/properties/3"
    for bad in ("https://evil.example", "//evil.example", "/\\evil", None):
        assert A.safe_next(bad) == "/#/properties"
