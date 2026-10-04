"""My properties (#38): sign in with Google, save buildings, get alerted before rules change. Not legal advice.

Routes
  GET    /auth/google/login           redirect to Google: authorization code + PKCE (S256), scopes openid email profile
  GET    /auth/google/callback        exchange the code server-side, verify the ID token, set the session cookie
  POST   /auth/demo                   read-only demo landlord account with 3 sample properties (no Google needed)
  POST   /auth/logout
  GET    /api/me                      {signed_in, google, user, csrf}
  GET    /api/properties              saved properties with rule counts and the next upcoming change
  POST   /api/properties              save {label, address, place: {state, jurisdiction, ...}, facts}
  GET    /api/properties/{id}         property + answer view (the POST /api/evaluate shape, #39) + what's changing
  PATCH  /api/properties/{id}, DELETE /api/properties/{id}
  GET    /api/alerts, PUT /api/alerts calendar feed links, email digest opt-in
  POST   /api/alerts/calendar/rotate  new secret calendar URL (the old one stops working)
  POST   /api/alerts/test-email       one test alert to the signed-in user's own address (internal; Resend SMTP)
  GET/POST /alerts/unsubscribe?t=...  signed link from every digest: turns the email digest off (POST = RFC 8058)

CLI (run by a systemd timer): uv run python -m web.accounts send-digests [--dry-run] [--today YYYY-MM-DD]
  One email per opted-in user listing changes at their saved properties that take effect within 30 days or took
  effect since their last digest. Every sent item is recorded in digest_log, so nothing is mailed twice.
  DELETE /api/account                 wipes the user, the properties and the preferences
  GET    /cal/{token}.ics             every upcoming effective date for the user's properties (#42)
  GET    /privacy, /terms

/api/properties, /api/me, /api/alerts, /api/account and /auth/* are on the PWA service worker's bypass list (#44),
so private data never lands in its offline cache.
Evaluation reuses the any-address engine (#39): navigator.user_facts + web.any_address.build_view; the street address
never reaches the evaluator. Storage: SQLite outside the repo ($NAVIGATOR_ACCOUNTS_DB). Secrets live in files with
mode 600 and are never logged. Every POST/PATCH/PUT/DELETE needs the session's CSRF token (X-CSRF-Token header) and a
same-site Origin; the session cookie is signed, HttpOnly, SameSite=Lax and Secure outside localhost.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, deque
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import make_msgid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from navigator import user_facts as U
from navigator.config import STATES
from web.any_address import build_view

router = APIRouter()

HOME = Path.home()
CFG = {
    "oauth": ("NAVIGATOR_GOOGLE_OAUTH", HOME / ".config/hacknation/google-oauth.json"),
    "secret": ("NAVIGATOR_SESSION_SECRET", HOME / ".config/hacknation/session-secret"),
    "db": ("NAVIGATOR_ACCOUNTS_DB", HOME / "hacknation/realpage/private/accounts.db"),
    "resend": ("NAVIGATOR_RESEND_KEY", HOME / ".config/resend/api-key"),
}
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
SESSION_COOKIE, OAUTH_COOKIE = "ce_session", "ce_oauth"
SESSION_TTL, OAUTH_TTL = 30 * 86400, 600
MAIL_FROM = "Clause & Effect <no-reply-navigator@isaaclins.com>"
SMTP_HOST, SMTP_PORT = "smtp.resend.com", 587
MAX_PROPERTIES = 25
DEFAULT_AS_OF = "2026-10-01"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "testserver", "[::1]")
DEMO_SUB, DEMO_TOKEN = "demo:landlord", "demo"
DEMO_READONLY = "The demo account is read-only. Sign in with Google to save your own properties."
NLA = "Not legal advice. Information about public law with citations; check the cited source."


def cfg_path(key: str) -> Path:
    env, default = CFG[key]
    return Path(os.environ.get(env) or default)


def log(msg: str) -> None:
    """Operational events only: never addresses, emails, tokens or codes."""
    print(f"[accounts] {msg}", file=sys.stderr, flush=True)


# ------------------------------------------------------------------ secrets + signing
_secret_lock = threading.Lock()
_secret: dict[str, bytes] = {}


def secret() -> bytes:
    """Session signing key, generated once into a mode-600 file."""
    p = cfg_path("secret")
    with _secret_lock:
        if str(p) not in _secret:
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, "w") as fh:
                        fh.write(secrets.token_urlsafe(48))
                except FileExistsError:
                    pass
            _secret[str(p)] = p.read_text().strip().encode()
        return _secret[str(p)]


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _mac(msg: str) -> str:
    return _b64(hmac.new(secret(), msg.encode(), hashlib.sha256).digest())


def sign(purpose: str, data: dict, ttl: int) -> str:
    body = _b64(
        json.dumps(
            {**data, "p": purpose, "exp": int(time.time()) + ttl}, separators=(",", ":")
        ).encode()
    )
    return f"{body}.{_mac(body)}"


def unsign(purpose: str, token: str | None) -> dict | None:
    if not token or token.count(".") != 1:
        return None
    body, mac = token.split(".")
    if not hmac.compare_digest(mac, _mac(body)):
        return None
    try:
        d = json.loads(_unb64(body))
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("p") != purpose or d.get("exp", 0) < time.time():
        return None
    return d


# ------------------------------------------------------------------ storage
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  google_sub TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL,
  name TEXT,
  is_demo INTEGER NOT NULL DEFAULT 0,
  calendar_token TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS properties (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  address TEXT NOT NULL,
  matched_address TEXT,
  state TEXT NOT NULL,
  jurisdiction TEXT,
  place TEXT,
  county TEXT,
  year_built INTEGER,
  units INTEGER,
  owner_occupied INTEGER,
  certificate_of_occupancy_date TEXT,
  last_increase_date TEXT,
  current_rent REAL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS properties_user ON properties(user_id);
CREATE TABLE IF NOT EXISTS alert_prefs (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  email_digest INTEGER NOT NULL DEFAULT 0,
  last_test_email_at TEXT
);
CREATE TABLE IF NOT EXISTS digest_state (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  last_sent_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS digest_log (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  event_date TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  sent_at TEXT NOT NULL,
  PRIMARY KEY (user_id, property_id, event_date, rule_id, kind)
);
"""
# Public sample buildings (starter data); facts chosen to show a definite answer set, an upcoming change and one
# unknown that a fact would resolve.
DEMO_PROPERTIES = [
    {
        "label": "Fulton Street flats",
        "address": "3918 Fulton St, San Francisco, CA 94118",
        "matched_address": "3918 FULTON ST, SAN FRANCISCO, CA, 94118",
        "state": "CA",
        "jurisdiction": "San Francisco, CA",
        "place": "San Francisco",
        "county": "San Francisco County",
        "year_built": 1923,
        "units": 6,
        "owner_occupied": 0,
        "last_increase_date": "2026-01-01",
        "current_rent": 2400.0,
    },
    {
        "label": "Tujunga courtyard",
        "address": "10050 Mountair Ave, Tujunga, CA 91042",
        "matched_address": "10050 MOUNTAIR AVE, TUJUNGA, CA, 91042",
        "state": "CA",
        "jurisdiction": "Los Angeles, CA",
        "place": "Los Angeles",
        "county": "Los Angeles County",
        "year_built": 1964,
        "units": 39,
        "owner_occupied": 0,
        "last_increase_date": "2025-12-01",
        "current_rent": 1850.0,
    },
    {
        "label": "Bloomfield brownstone",
        "address": "323 Bloomfield St, Hoboken, NJ 07030",
        "matched_address": "323 BLOOMFIELD ST, HOBOKEN, NJ, 07030",
        "state": "NJ",
        "jurisdiction": "Hoboken, NJ",
        "place": "Hoboken",
        "county": "Hudson County",
        "year_built": 1890,
        "units": 4,
        "owner_occupied": None,
        "last_increase_date": "2026-04-01",
        "current_rent": 3100.0,
    },
]
PROP_COLS = (
    "label address matched_address state jurisdiction place county year_built units owner_occupied "
    "certificate_of_occupancy_date last_increase_date current_rent"
).split()
# columns added after the first release: (name, type), added in place by _init_db
PROP_MIGRATIONS = (("last_increase_date", "TEXT"), ("current_rent", "REAL"))
_db_ready: set[str] = set()
_db_lock = threading.Lock()


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _connect(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(path, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _init_db(path: Path) -> None:
    with _db_lock:
        if str(path) in _db_ready:
            return
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        old = os.umask(0o077)  # database, WAL and SHM files: owner only
        try:
            c = _connect(path)
            c.execute("PRAGMA journal_mode = WAL")
            c.executescript(SCHEMA)
            have = {r["name"] for r in c.execute("PRAGMA table_info(properties)")}
            for col, typ in PROP_MIGRATIONS:
                if col not in have:
                    c.execute(f"ALTER TABLE properties ADD COLUMN {col} {typ}")
            seed_demo(c)
            c.commit()
            c.close()
        finally:
            os.umask(old)
        os.chmod(path, 0o600)
        _db_ready.add(str(path))


def seed_demo(c: sqlite3.Connection) -> None:
    """The demo landlord is read-only and re-seeded on start, so it always shows the same three buildings."""
    row = c.execute("SELECT id FROM users WHERE google_sub = ?", (DEMO_SUB,)).fetchone()
    if row:
        uid = row["id"]
        c.execute("DELETE FROM properties WHERE user_id = ?", (uid,))
    else:
        uid = c.execute(
            "INSERT INTO users (google_sub, email, name, is_demo, calendar_token, created_at) VALUES (?,?,?,?,?,?)",
            (DEMO_SUB, "demo@example.com", "Demo landlord", 1, DEMO_TOKEN, now_iso()),
        ).lastrowid
        c.execute("INSERT INTO alert_prefs (user_id) VALUES (?)", (uid,))
    for p in DEMO_PROPERTIES:
        insert_property(c, uid, {k: p.get(k) for k in PROP_COLS})


@contextmanager
def db():
    path = cfg_path("db")
    if str(path) not in _db_ready:
        _init_db(path)
    c = _connect(path)
    try:
        with c:
            yield c
    finally:
        c.close()


def insert_property(c: sqlite3.Connection, uid: int, vals: dict) -> int:
    ts = now_iso()
    cols = ["user_id", *PROP_COLS, "created_at", "updated_at"]
    return c.execute(
        f"INSERT INTO properties ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        (uid, *[vals.get(k) for k in PROP_COLS], ts, ts),
    ).lastrowid


def get_user(uid: int) -> sqlite3.Row | None:
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def upsert_google_user(sub: str, email: str, name: str | None) -> int:
    with db() as c:
        row = c.execute("SELECT id FROM users WHERE google_sub = ?", (sub,)).fetchone()
        if row:
            c.execute(
                "UPDATE users SET email = ?, name = ?, last_login_at = ? WHERE id = ?",
                (email, name, now_iso(), row["id"]),
            )
            return row["id"]
        uid = c.execute(
            "INSERT INTO users (google_sub, email, name, calendar_token, created_at, last_login_at) VALUES (?,?,?,?,?,?)",
            (sub, email, name, secrets.token_urlsafe(24), now_iso(), now_iso()),
        ).lastrowid
        c.execute("INSERT INTO alert_prefs (user_id) VALUES (?)", (uid,))
        return uid


def demo_user_id() -> int:
    with db() as c:
        return c.execute("SELECT id FROM users WHERE google_sub = ?", (DEMO_SUB,)).fetchone()["id"]


# ------------------------------------------------------------------ requests: host, rate limits, session, CSRF
def public_host(request: Request) -> str:
    return (
        (request.headers.get("x-forwarded-host") or request.headers.get("host") or "")
        .split(",")[0]
        .strip()
    )


def is_local(request: Request) -> bool:
    return public_host(request).rsplit(":", 1)[0] in LOCAL_HOSTS


def base_url(request: Request) -> str:
    return f"{'http' if is_local(request) else 'https'}://{public_host(request)}"


def client_ip(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    if host in ("127.0.0.1", "::1", "localhost"):  # behind our own tunnel/proxy
        fwd = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
        if fwd.split(",")[0].strip():
            return fwd.split(",")[0].strip()
    return host


class RateLimit:
    def __init__(self, n: int, per: float) -> None:
        self.n, self.per, self.hits, self.lock = n, per, {}, threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.hits) > 5000:
                self.hits = {k: q for k, q in self.hits.items() if q and now - q[-1] < self.per}
            q = self.hits.setdefault(key, deque())
            while q and now - q[0] >= self.per:
                q.popleft()
            if len(q) >= self.n:
                return False
            q.append(now)
            return True


LIMITS = {
    "auth": RateLimit(30, 60),
    "read": RateLimit(120, 60),
    "write": RateLimit(40, 60),
    "ics": RateLimit(60, 60),
    "mail_user": RateLimit(3, 3600),
    "mail_all": RateLimit(50, 86400),
}


def limit(name: str, key: str) -> None:
    if not LIMITS[name].allow(key):
        raise HTTPException(429, "Too many requests. Please wait a minute.")


def session(request: Request) -> dict | None:
    return unsign("session", request.cookies.get(SESSION_COOKIE))


def csrf_for(sess: dict) -> str:
    return _mac(f"csrf:{sess['sid']}")[:32]


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin and urllib.parse.urlsplit(origin).netloc not in (
        public_host(request),
        request.headers.get("host"),
    ):
        raise HTTPException(403, "Cross-site request blocked.")


def require_user(request: Request, write: bool = False) -> sqlite3.Row:
    sess = session(request)
    user = get_user(sess["uid"]) if sess else None
    if not user:
        raise HTTPException(401, "Please sign in.")
    if request.method not in ("GET", "HEAD"):
        check_origin(request)
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), csrf_for(sess)):
            raise HTTPException(403, "Security token missing or expired. Reload the page.")
        limit("write", f"u{user['id']}")
    else:
        limit("read", f"u{user['id']}")
    if write and user["is_demo"]:
        raise HTTPException(403, DEMO_READONLY)
    return user


def set_session(resp: Response, request: Request, uid: int) -> None:
    token = sign("session", {"uid": uid, "sid": secrets.token_urlsafe(16)}, SESSION_TTL)
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL,
        httponly=True,
        secure=not is_local(request),
        samesite="lax",
        path="/",
    )


def clear_session(resp: Response, request: Request) -> None:
    resp.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, secure=not is_local(request), samesite="lax"
    )


def safe_next(n: str | None) -> str:
    n = n or "/#/properties"
    if not n.startswith("/") or n.startswith("//") or "\\" in n or len(n) > 200:
        return "/#/properties"
    return n


# ------------------------------------------------------------------ Google sign-in (authorization code + PKCE)
class AuthError(Exception):
    pass


def google_cfg() -> dict | None:
    try:
        d = json.loads(cfg_path("oauth").read_text())
    except (OSError, ValueError):
        return None
    d = d.get("web") or d  # also accept Google's downloaded client_secret_*.json shape
    return d if d.get("client_id") and d.get("client_secret") else None


def redirect_uri(cfg: dict, request: Request) -> str:
    uris = cfg.get("redirect_uris") or []
    host = public_host(request)
    for u in uris:
        if urllib.parse.urlsplit(u).netloc == host:
            return u
    return os.environ.get("NAVIGATOR_OAUTH_REDIRECT") or next(
        (u for u in uris if u.startswith("https://")), f"{base_url(request)}/auth/google/callback"
    )


def _http_json(url: str, data: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise AuthError(f"{urllib.parse.urlsplit(url).path} answered {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise AuthError(f"{urllib.parse.urlsplit(url).path}: {type(e).__name__}") from None


def exchange_code(cfg: dict, code: str, verifier: str, redirect: str) -> dict:
    return _http_json(
        GOOGLE_TOKEN,
        {
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        },
    )


def verify_id_token(id_token: str, client_id: str, nonce: str) -> dict:
    """Google's tokeninfo endpoint checks the signature; we check issuer, audience, expiry, nonce, verified email."""
    info = _http_json(f"{GOOGLE_TOKENINFO}?{urllib.parse.urlencode({'id_token': id_token})}")
    if info.get("iss") not in GOOGLE_ISSUERS:
        raise AuthError("wrong issuer")
    if info.get("aud") != client_id:
        raise AuthError("wrong audience")
    try:
        exp = int(info.get("exp", 0))
    except (TypeError, ValueError):
        exp = 0
    if exp < time.time():
        raise AuthError("expired")
    if not hmac.compare_digest(str(info.get("nonce", "")), nonce):
        raise AuthError("nonce mismatch")
    if str(info.get("email_verified")).lower() != "true" or not info.get("email"):
        raise AuthError("email not verified")
    if not info.get("sub"):
        raise AuthError("no subject")
    return info


def _fail(request: Request, reason: str) -> RedirectResponse:
    log(f"google sign-in failed: {reason}")
    r = RedirectResponse("/#/properties/signin-failed", status_code=303)
    r.delete_cookie(OAUTH_COOKIE, path="/auth/google")
    return r


@router.get("/auth/google/login")
def google_login(request: Request, next: str | None = None):
    limit("auth", client_ip(request))
    cfg = google_cfg()
    if not cfg:
        raise HTTPException(503, "Google sign-in is not configured on this server.")
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    redirect = redirect_uri(cfg, request)
    q = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{GOOGLE_AUTH}?{urllib.parse.urlencode(q)}", status_code=302)
    flow = {"s": state, "n": nonce, "v": verifier, "r": redirect, "next": safe_next(next)}
    resp.set_cookie(
        OAUTH_COOKIE,
        sign("oauth", flow, OAUTH_TTL),
        max_age=OAUTH_TTL,
        httponly=True,
        secure=not is_local(request),
        samesite="lax",
        path="/auth/google",
    )
    return resp


@router.get("/auth/google/callback")
def google_callback(
    request: Request, code: str | None = None, state: str | None = None, error: str | None = None
):
    limit("auth", client_ip(request))
    flow = unsign("oauth", request.cookies.get(OAUTH_COOKIE))
    if error:
        return _fail(request, f"google returned error={error[:40]}")
    if not flow or not state or not code:
        return _fail(request, "missing or expired sign-in state")
    if not hmac.compare_digest(state, flow["s"]):
        return _fail(request, "state mismatch")
    cfg = google_cfg()
    if not cfg:
        return _fail(request, "not configured")
    try:
        tok = exchange_code(cfg, code, flow["v"], flow["r"])
        if not tok.get("id_token"):
            raise AuthError("no id_token in token response")
        info = verify_id_token(tok["id_token"], cfg["client_id"], flow["n"])
    except AuthError as e:
        return _fail(request, str(e))
    name = (info.get("name") or info.get("given_name") or "").strip()[:80] or None
    uid = upsert_google_user(info["sub"], info["email"].strip().lower()[:200], name)
    log("google sign-in ok")
    resp = RedirectResponse(safe_next(flow.get("next")), status_code=303)
    resp.delete_cookie(OAUTH_COOKIE, path="/auth/google")
    set_session(resp, request, uid)
    return resp


@router.post("/auth/demo")
def demo_login(request: Request):
    limit("auth", client_ip(request))
    check_origin(request)
    resp = JSONResponse({"ok": True})
    set_session(resp, request, demo_user_id())
    return resp


@router.post("/auth/logout")
def logout(request: Request):
    sess = session(request)
    if sess:
        check_origin(request)
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), csrf_for(sess)):
            raise HTTPException(403, "Security token missing or expired. Reload the page.")
    resp = JSONResponse({"ok": True})
    clear_session(resp, request)
    return resp


@router.get("/api/me")
def me(request: Request):
    sess = session(request)
    user = get_user(sess["uid"]) if sess else None
    out = {"signed_in": bool(user), "google": bool(google_cfg()), "disclaimer": NLA}
    if user:
        out["user"] = {"email": user["email"], "name": user["name"], "demo": bool(user["is_demo"])}
        out["csrf"] = csrf_for(sess)
    return out


@router.delete("/api/account")
def delete_account(request: Request):
    user = require_user(request, write=True)
    with db() as c:
        c.execute("DELETE FROM users WHERE id = ?", (user["id"],))  # cascades to properties + prefs
    log("account deleted")
    resp = JSONResponse({"ok": True, "deleted": True})
    clear_session(resp, request)
    return resp


# ------------------------------------------------------------------ evaluation (any-address engine, #39)
def _sig() -> float:
    from navigator.config import RULES_JSON

    try:
        return RULES_JSON.stat().st_mtime
    except OSError:
        return 0.0


def prop_facts(p: sqlite3.Row | dict) -> dict:
    oo = p["owner_occupied"]
    return {
        "year_built": p["year_built"],
        "units": p["units"],
        "owner_occupied": None if oo is None else bool(oo),
        "certificate_of_occupancy_date": p["certificate_of_occupancy_date"],
    }


def _key(p) -> tuple:
    return (p["state"], p["jurisdiction"], json.dumps(prop_facts(p), sort_keys=True))


DATE_KEYS = ("effective_date", "sunset_date", "current_version_effective", "enacted_date")
LIVE = ("applies", "unknown", "superseded")


@lru_cache(maxsize=512)
def _changes(state: str, jur: str | None, facts_json: str, as_of: str, sig: float) -> dict:
    """Upcoming changes for one building: re-evaluate on every date a rule (or the building's age) can flip a result
    and diff against the day before. Plus figure updates (a key-figure period ends) and pending bills."""
    from navigator import evaluate as E
    from navigator import normalize as N

    rules, _, _ = U.rules_for(jur)
    f = U.make_facts(state, jur, json.loads(facts_json))
    here = [r for r in rules if E._applies_here(r, f)]
    by_id = {r["team_rule_id"]: r for r in here}
    d0 = dt.date.fromisoformat(as_of)
    horizon = d0 + dt.timedelta(days=20 * 365)
    cands: set[dt.date] = set()
    for r in here:
        for k in DATE_KEYS:
            d = N.date_floor(r.get(k))
            if d:
                cands |= {d, d + dt.timedelta(days=1)}
        nce = (r.get("coverage") or {}).get("new_construction_exemption") or {}
        # the building ages out of a new-construction exemption
        if nce.get("years") and f.year_built:
            y = f.year_built + int(nce["years"])
            cands |= {dt.date(y, 1, 1), dt.date(y + 1, 1, 1)}
    cands = {d for d in cands if d0 < d <= horizon}

    def state_on(d: dt.date) -> dict[str, str]:
        return {e["team_rule_id"]: e["result"] for e in E.evaluate_address(f, rules, d)}

    def info(rid: str) -> dict:
        r = by_id[rid]
        return {
            "rule_id": rid,
            "title": r.get("title"),
            "citation": r.get("citation"),
            "jurisdiction": r.get("jurisdiction"),
            "level": r.get("level"),
            "category": r.get("category"),
            "key_value": r.get("key_value"),
            "source_url": r.get("source_url"),
            "effective_date": r.get("effective_date"),
            "status": r.get("status"),
        }

    now = state_on(d0)
    prev, events = now, []
    for d in sorted(cands):
        cur = state_on(d)
        items = []
        for rid in sorted(set(prev) | set(cur)):
            a, b = prev.get(rid), cur.get(rid)
            if a == b or rid not in by_id:
                continue
            if b in LIVE and a in (None, "not_yet_effective", "pending"):
                kind = "takes_effect"
            elif b is None:
                kind = "ends"
            else:
                kind = "changes"
            items.append({**info(rid), "kind": kind, "from": a, "to": b})
        if items:
            events.append({"date": d.isoformat(), "items": items})
        prev = cur
    for rid, res in now.items():  # a key-figure period ends: the law continues, a new figure is due
        r = by_id.get(rid) or {}
        end = N.date_floor(r.get("sunset_date"))
        if res in LIVE and end and d0 <= end < horizon and not E._sunset_is_repeal(r):
            d = (end + dt.timedelta(days=1)).isoformat()
            item = {
                **info(rid),
                "kind": "figure",
                "from": res,
                "to": res,
                "period_end": end.isoformat(),
            }
            ev = next((e for e in events if e["date"] == d), None)
            if ev:
                ev["items"].append(item)
            else:
                events.append({"date": d, "items": [item]})
    events.sort(key=lambda e: e["date"])
    pending = [{**info(rid), "kind": "pending"} for rid, res in now.items() if res == "pending"]
    counts = Counter(now.values())
    return {"as_of": as_of, "events": events, "pending": pending, "counts": dict(counts)}


def property_changes(p, as_of: str) -> dict:
    return _changes(*_key(p), as_of, _sig())


@lru_cache(maxsize=256)
def _view(state: str, jur: str | None, facts_json: str, as_of: str, lang: str, sig: float) -> dict:
    return build_view(U.evaluate_user(state, jur, json.loads(facts_json), as_of), lang)


def _event_title(ev: dict) -> str:
    it = ev["items"][0]
    verb = {
        "takes_effect": "takes effect",
        "ends": "ends",
        "figure": "new figure due",
        "changes": "changes",
    }[it["kind"]]
    more = f" (+{len(ev['items']) - 1} more)" if len(ev["items"]) > 1 else ""
    return f"{it['title']}: {verb}{more}"


def prop_out(p: sqlite3.Row) -> dict:
    return {
        "id": p["id"],
        "label": p["label"],
        "address": p["address"],
        "matched_address": p["matched_address"],
        "state": p["state"],
        "jurisdiction": p["jurisdiction"],
        "place": p["place"],
        "county": p["county"],
        "facts": prop_facts(p),
        "rent": {"last_increase_date": p["last_increase_date"], "current_rent": p["current_rent"]},
        "created_at": p["created_at"],
        "updated_at": p["updated_at"],
    }


def summary(p: sqlite3.Row, as_of: str) -> dict:
    ch = property_changes(p, as_of)
    nxt = ch["events"][0] if ch["events"] else None
    return {
        "counts": ch["counts"],
        "changes": sum(len(e["items"]) for e in ch["events"]),
        "pending": len(ch["pending"]),
        "events": ch["events"],
        "next": {"date": nxt["date"], "title": _event_title(nxt), "items": nxt["items"]}
        if nxt
        else None,
    }


# ------------------------------------------------------------------ next lawful rent increase (#152)
def raise_dates(last: dt.date, as_of: dt.date, notice_days: int | None) -> dict:
    """Pure: the earliest date of the next raise and the last day to send its written notice.

    One raise per 12 months, counted from the last one (LA RSO "once every 12 months", SF's annual allowable
    increase, AB 1482 "any 12-month period"). A notice cannot be sent in the past: when the 12 months are already
    over (or too close), the earliest date is today + the notice period."""
    from web.check import _add_months

    spaced = _add_months(last, 12)
    soonest = as_of + dt.timedelta(days=notice_days or 0)
    date = max(spaced, soonest)
    return {
        "date": date,
        "spaced": spaced,
        "notice_by": date - dt.timedelta(days=notice_days) if notice_days else None,
        "now": spaced < soonest,
    }


def max_rent(cur: float, pct: float) -> float:
    return round(cur * (1 + pct / 100) + 1e-9, 2)


@lru_cache(maxsize=512)
def _next_raise(
    state: str,
    jur: str | None,
    facts_json: str,
    last: str | None,
    rent: float | None,
    as_of: str,
    lang: str,
    sig: float,
) -> dict:
    """Date, most-you-may-charge and notice deadline of the next raise, from the deterministic check engine
    (web/check.py) evaluated on that future date. A figure the sources do not state is reported as missing."""
    from web import check as C

    W = C._web()
    d0 = dt.date.fromisoformat(as_of)
    facts = {k: v for k, v in json.loads(facts_json).items() if v is not None}
    now = _cap_now(C, state, jur, facts, d0, lang)
    if not last or not rent:
        return {"state": "need_input", "cap_now": now}
    last_d = dt.date.fromisoformat(last)
    nrs = [
        r
        for r in C.NOTICE_RULES
        if state in r["states"] and W.STORE.verify(r).get("status") in ("exact", "normalized")
    ]
    nr = nrs[0] if nrs else None
    dates = raise_dates(last_d, d0, nr["days"] if nr else None)
    body = C.CheckIn(
        place={"state": state, "jurisdiction": jur},
        facts=facts,
        effective_date=min(dates["date"], dt.date(2035, 12, 31)),
        lang=lang,
    )
    ctx = C._context(body, body.effective_date)
    rv = C.check_rent(ctx, rent, rent + 0.01, None, lang)
    out = {
        "last_increase_date": last,
        "current_rent": rent,
        "date": dates["date"].isoformat(),
        "now": dates["now"],
        "rules": rv.get("rules") or [],
        "notice": None,
        "cap_now": now,
    }
    code, v = rv["code"], rv.get("values") or {}
    gov = ctx["rules"].get(out["rules"][0]["id"]) if out["rules"] else None
    out["place"] = (gov or {}).get("jurisdiction")
    pct_for_notice = None
    if code == "within":
        out |= {"state": "ok", "cap_pct": v["cap_pct"], "max_rent": max_rent(rent, v["cap_pct"])}
        out["cap_end"] = (rv.get("cap") or {}).get("end")
        pct_for_notice = v["cap_pct"]
    elif code == "need_cpi":
        out |= {
            "state": "need_cpi",
            "cap_max": v["cap_max"],
            "cap_base": v["cap_base"],
            "max_rent": max_rent(rent, v["cap_max"]),
        }
    elif code == "need_figure":
        periods = (
            C.parse_rent_cap(gov.get("key_value"), gov.get("requirement"))["periods"] if gov else []
        )
        last_p = max(periods, key=lambda x: x[2]) if periods else None
        # the agency has not published the figure yet (its current period still runs) vs. it is out but not in
        # our sources (the period it replaces is already over)
        out["state"] = "cap_not_out" if last_p and last_p[2] >= d0 else "not_in_sources"
        if last_p:
            out |= {"last_pct": last_p[0], "cap_end": last_p[2].isoformat()}
    elif code == "need_fact":
        need = rv.get("need") or {}
        out["state"] = "need_fact" if need.get("key") in FACT_KEYS else "not_in_sources"
        out["need"] = need.get("key")
        if gov:
            out["why"] = W.rule_view(gov, lang).get("why_display")
    else:  # no cap here, or the state bars local rent control
        out["state"] = "no_cap"
    if nr:
        ok = pct_for_notice is not None and pct_for_notice < nr["below_pct"]
        out["notice"] = {
            "days": nr["days"],
            "by": dates["notice_by"].isoformat() if dates["notice_by"] else None,
            "below_pct": nr["below_pct"],
            # the period applies to raises under 10%: certain when the cap is known and below it
            "sure": ok,
            "rule": C._src(nr, lang),
        }
    return out


FACT_KEYS = ("year_built", "units", "owner_occupied")


def _cap_now(C, state: str, jur: str | None, facts: dict, d0: dt.date, lang: str) -> dict:
    """The rent cap in force today (for the card's status line), whatever the rent: kind + pct / period end."""
    body = C.CheckIn(
        place={"state": state, "jurisdiction": jur}, facts=facts, effective_date=d0, lang=lang
    )
    rv = C.check_rent(C._context(body, d0), 1000.0, 1000.01, None, lang)
    v, cap = rv.get("values") or {}, rv.get("cap") or {}
    out = {"code": rv["code"]}
    if rv["code"] == "within":
        out |= {"pct": v["cap_pct"], "end": cap.get("end")}
    elif rv["code"] == "need_cpi":
        out |= {"base": v["cap_base"], "max": v["cap_max"]}
    return out


def next_raise(p, as_of: str, lang: str = "en") -> dict:
    return _next_raise(*_key(p), p["last_increase_date"], p["current_rent"], as_of, lang, _sig())


# The building card (list): per topic the leading answer and its status, one question a fact would settle.
RANK = {"applies": 0, "unknown": 1, "not_yet_effective": 2, "superseded": 3, "pending": 4}


def _lead(c: dict) -> dict | None:
    items = sorted(
        c.get("enacted") or [],
        key=lambda x: (
            RANK.get(x["result"], 9),
            x["rule"].get("headline_priority") or 1.5,
            x["rule"].get("level") != "state",
        ),
    )
    return items[0] if items else None


def _year_cuts(view: dict) -> list[int]:
    ys, now = set(), dt.date.fromisoformat(view["as_of"])
    for c in view["categories"]:
        for it in c.get("enacted") or []:
            if it["result"] != "unknown" or "year_built" not in (it.get("needs_fact") or []):
                continue
            cov = it["rule"].get("coverage") or {}
            if (cov.get("construction_cutoff") or {}).get("date"):
                ys.add(int(cov["construction_cutoff"]["date"][:4]))
            if (cov.get("new_construction_exemption") or {}).get("years"):
                ys.add(now.year - int(cov["new_construction_exemption"]["years"]))
    return sorted(ys)


def card_brief(view: dict, as_of: str) -> dict:
    topics, question = [], None
    for c in view["categories"]:
        top = _lead(c)
        if not top:
            topics.append({"id": c["id"], "status": "exempt" if c.get("excluded") else "no_rule"})
            continue
        r = top["rule"]
        plain = (
            r.get("answer_display")
            if not (r.get("plain_until") and as_of > r["plain_until"])
            else None
        )
        status = (
            "no_rule"
            if r.get("removes_protection") and top["result"] == "applies"
            else top["result"]
        )
        topics.append(
            {
                "id": c["id"],
                "status": status,
                "answer": plain or r.get("headline_short") or r.get("headline_display"),
            }
        )
        for it in c.get("enacted") or []:
            k = next((x for x in it.get("needs_fact") or [] if x in FACT_KEYS), None)
            if it["result"] == "unknown" and k and not question:
                question = {"fact": k, "topic": c["id"]}
                if k == "year_built":
                    question["cuts"] = _year_cuts(view)
    return {"topics": topics, "question": question}


def _as_of(v: str | None) -> str:
    v = v or DEFAULT_AS_OF
    try:
        d = dt.date.fromisoformat(v)
    except ValueError:
        raise HTTPException(422, "as_of must be YYYY-MM-DD") from None
    if not (dt.date(2000, 1, 1) <= d <= dt.date(2035, 12, 31)):
        raise HTTPException(422, "as_of must be between 2000 and 2035")
    return v


# ------------------------------------------------------------------ properties API
def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", "".join(ch for ch in v if ch.isprintable())).strip()


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
    model_config = ConfigDict(extra="ignore")  # the client may echo the whole /api/resolve answer
    state: str = Field(pattern=r"^[A-Z]{2}$")
    jurisdiction: str | None = Field(None, max_length=60)
    place: str | None = Field(None, max_length=80)
    county: str | None = Field(None, max_length=80)
    matched_address: str | None = Field(None, max_length=200)


class RentIn(BaseModel):
    """The last increase and the rent now (#152); both null clears them."""

    model_config = ConfigDict(extra="forbid")
    last_increase_date: dt.date | None = None
    current_rent: float | None = Field(None, gt=0, le=1_000_000)

    @field_validator("last_increase_date")
    @classmethod
    def date_range(cls, v):
        if v is not None and not (dt.date(1990, 1, 1) <= v <= dt.date(2035, 12, 31)):
            raise ValueError("last increase date out of range")
        return v


class PropertyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=60)
    address: str = Field(min_length=5, max_length=200)
    place: PlaceIn | None = None
    # one of the 500 sample addresses: place and public facts come from our data (the typeahead's first group)
    address_id: str | None = Field(None, pattern=r"^[A-Za-z0-9-]{1,20}$")
    facts: FactsIn = FactsIn()
    rent: RentIn = RentIn()

    @field_validator("label", "address")
    @classmethod
    def clean(cls, v: str) -> str:
        v = _clean(v)
        if not v:
            raise ValueError("must not be empty")
        return v


class PropertyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(None, min_length=1, max_length=60)
    facts: FactsIn | None = None
    rent: RentIn | None = None

    @field_validator("label")
    @classmethod
    def clean(cls, v):
        return _clean(v) if v is not None else v


def _facts_row(f: FactsIn) -> dict:
    return {
        "year_built": f.year_built,
        "units": f.units,
        "owner_occupied": None if f.owner_occupied is None else int(f.owner_occupied),
        "certificate_of_occupancy_date": f.certificate_of_occupancy_date.isoformat()
        if f.certificate_of_occupancy_date
        else None,
    }


def _check_place(pl: PlaceIn) -> None:
    if pl.state not in STATES:
        raise HTTPException(422, "This address is outside the states we cover (CA, NJ, MA).")
    if pl.jurisdiction is not None and pl.jurisdiction not in U.covered_cities()[pl.state]:
        raise HTTPException(422, "Unknown city jurisdiction for this state.")


def _own(c: sqlite3.Connection, uid: int, pid: int) -> sqlite3.Row:
    p = c.execute("SELECT * FROM properties WHERE id = ? AND user_id = ?", (pid, uid)).fetchone()
    if not p:
        raise HTTPException(404, "No such property.")
    return p


def card(p, d: str, lang: str) -> dict:
    """What a building card in the list needs: summary, per-topic status, one question, the next raise."""
    return {
        "summary": summary(p, d),
        "brief": card_brief(_view(*_key(p), d, lang, _sig()), d),
        "next_raise": next_raise(p, d, lang),
    }


@router.get("/api/properties")
def list_props(request: Request, as_of: str | None = None, lang: str = "en"):
    user = require_user(request)
    d = _as_of(as_of)
    lang = lang if lang in ("en", "es") else "en"
    with db() as c:
        rows = c.execute(
            "SELECT * FROM properties WHERE user_id = ? ORDER BY id", (user["id"],)
        ).fetchall()
    return {
        "as_of": d,
        "disclaimer": NLA,
        "demo": bool(user["is_demo"]),
        "max": MAX_PROPERTIES,
        "properties": [{**prop_out(p), **card(p, d, lang)} for p in rows],
    }


@router.post("/api/properties", status_code=201)
def create_prop(body: PropertyIn, request: Request):
    user = require_user(request, write=True)
    place, facts = body.place, _facts_row(body.facts)
    if body.address_id:
        from navigator import api as NA

        f = NA._addresses().get(body.address_id.upper())
        if not f:
            raise HTTPException(404, "Unknown address.")
        a = f.raw
        place = PlaceIn(
            state=f.state,
            jurisdiction=f.city,
            place=(f.city or "").removesuffix(f", {f.state}") or a.get("postal_city"),
            county=a.get("county"),
            matched_address=f"{a.get('street_address')}, {a.get('postal_city')}, {f.state}, {a.get('zip')}",
        )
        facts = {
            "year_built": facts["year_built"] or f.year_built,
            "units": facts["units"] or (f.units_lo if f.units_lo == f.units_hi else None),
            "owner_occupied": facts["owner_occupied"]
            if facts["owner_occupied"] is not None
            else (None if f.owner_occupied is None else int(f.owner_occupied)),
            "certificate_of_occupancy_date": facts["certificate_of_occupancy_date"],
        }
    if place is None:
        raise HTTPException(422, "place or address_id is required")
    _check_place(place)
    with db() as c:
        n = c.execute(
            "SELECT COUNT(*) FROM properties WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        if n >= MAX_PROPERTIES:
            raise HTTPException(422, f"You can save up to {MAX_PROPERTIES} properties.")
        vals = {
            "label": body.label,
            "address": body.address,
            **place.model_dump(),
            **facts,
            "last_increase_date": body.rent.last_increase_date.isoformat()
            if body.rent.last_increase_date
            else None,
            "current_rent": body.rent.current_rent,
        }
        pid = insert_property(c, user["id"], vals)
        p = _own(c, user["id"], pid)
    return {**prop_out(p), "summary": summary(p, DEFAULT_AS_OF)}


@router.get("/api/properties/{pid}")
def get_prop(pid: int, request: Request, as_of: str | None = None, lang: str = "en"):
    user = require_user(request)
    d = _as_of(as_of)
    lang = lang if lang in ("en", "es") else "en"
    with db() as c:
        p = _own(c, user["id"], pid)
    return {
        **prop_out(p),
        "as_of": d,
        "demo": bool(user["is_demo"]),
        "view": _view(*_key(p), d, lang, _sig()),
        "changes": property_changes(p, d),
        "summary": summary(p, d),
        "next_raise": next_raise(p, d, lang),
    }


class PreviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: FactsIn
    as_of: str | None = None
    lang: str = "en"


@router.post("/api/properties/{pid}/preview")
def preview_prop(pid: int, body: PreviewIn, request: Request):
    """The card with other facts, nothing saved (the one-tap answer on the read-only example portfolio)."""
    user = require_user(request)
    d = _as_of(body.as_of)
    with db() as c:
        p = dict(_own(c, user["id"], pid))
    p.update(_facts_row(body.facts))
    return {
        "id": pid,
        "facts": prop_facts(p),
        **card(p, d, body.lang if body.lang in ("en", "es") else "en"),
    }


@router.patch("/api/properties/{pid}")
def update_prop(pid: int, body: PropertyPatch, request: Request):
    user = require_user(request, write=True)
    with db() as c:
        _own(c, user["id"], pid)
        sets = {}
        if body.label:
            sets["label"] = body.label
        if body.facts is not None:
            sets.update(_facts_row(body.facts))
        if body.rent is not None:
            sets["last_increase_date"] = (
                body.rent.last_increase_date.isoformat() if body.rent.last_increase_date else None
            )
            sets["current_rent"] = body.rent.current_rent
        if sets:
            c.execute(
                f"UPDATE properties SET {', '.join(f'{k} = ?' for k in sets)}, updated_at = ? WHERE id = ?",
                (*sets.values(), now_iso(), pid),
            )
        p = _own(c, user["id"], pid)
    return prop_out(p)


@router.delete("/api/properties/{pid}")
def delete_prop(pid: int, request: Request):
    user = require_user(request, write=True)
    with db() as c:
        _own(c, user["id"], pid)
        c.execute("DELETE FROM properties WHERE id = ?", (pid,))
    return {"ok": True}


# ------------------------------------------------------------------ alerts: calendar feed + email
def _alerts(user: sqlite3.Row, request: Request) -> dict:
    with db() as c:
        pref = c.execute("SELECT * FROM alert_prefs WHERE user_id = ?", (user["id"],)).fetchone()
    url = f"{base_url(request)}/cal/{user['calendar_token']}.ics"
    webcal = "webcal://" + url.split("://", 1)[1]
    return {
        "calendar": {
            "url": url,
            "webcal": webcal,
            "google": "https://calendar.google.com/calendar/render?"
            + urllib.parse.urlencode({"cid": webcal}),
        },
        "email": None if user["is_demo"] else user["email"],
        "email_digest": bool(pref and pref["email_digest"]),
        "last_test_email_at": pref["last_test_email_at"] if pref else None,
        "demo": bool(user["is_demo"]),
    }


class AlertsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_digest: bool


@router.get("/api/alerts")
def get_alerts(request: Request):
    return _alerts(require_user(request), request)


@router.put("/api/alerts")
def put_alerts(body: AlertsIn, request: Request):
    user = require_user(request, write=True)
    with db() as c:
        c.execute(
            "INSERT INTO alert_prefs (user_id, email_digest) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET email_digest = excluded.email_digest",
            (user["id"], int(body.email_digest)),
        )
    return _alerts(user, request)


@router.post("/api/alerts/calendar/rotate")
def rotate_calendar(request: Request):
    user = require_user(request, write=True)
    with db() as c:
        c.execute(
            "UPDATE users SET calendar_token = ? WHERE id = ?",
            (secrets.token_urlsafe(24), user["id"]),
        )
    return _alerts(get_user(user["id"]), request)


def upcoming(uid: int, start: dt.date) -> list[tuple[sqlite3.Row, dict]]:
    """(property, event) pairs for every dated change on or after `start`, soonest first."""
    with db() as c:
        rows = c.execute(
            "SELECT * FROM properties WHERE user_id = ? ORDER BY id", (uid,)
        ).fetchall()
    out = []
    for p in rows:
        for ev in property_changes(p, start.isoformat())["events"]:
            out.append((p, ev))
    return sorted(out, key=lambda x: (x[1]["date"], x[0]["id"]))


def _ics_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545 3.1: lines of at most 75 octets, continuation lines start with a space; never split a UTF-8 char."""
    b, out, first = line.encode(), [], True
    while len(b) > (75 if first else 74):
        cut = 75 if first else 74
        while (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut])
        b, first = b[cut:], False
    out.append(b)
    return "\r\n ".join(x.decode() for x in out)


ITEM_VERB = {
    "takes_effect": "takes effect",
    "ends": "ends",
    "figure": "current figure period ends; check the new figure",
    "changes": "changes",
}


def build_ics(user: sqlite3.Row, base: str, today: dt.date) -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    host = urllib.parse.urlsplit(base).netloc or "navigator.isaaclins.com"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Clause & Effect//My properties//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Clause & Effect · My properties",
        "X-WR-CALDESC:" + _ics_text("Upcoming effective dates for your saved properties. " + NLA),
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]
    for p, ev in upcoming(user["id"], today):
        d = dt.date.fromisoformat(ev["date"])
        desc = [f"{p['label']} ({p['place'] or p['state']})", ""]
        for it in ev["items"]:
            desc.append(f"- {it['title']} ({it['citation']}): {ITEM_VERB[it['kind']]}.")
            if it.get("key_value") and it["kind"] != "ends":
                desc.append(f"  {it['key_value']}")
            if it.get("source_url"):
                desc.append(f"  Source: {it['source_url']}")
        desc += ["", f"Details: {base}/#/properties/{p['id']}", NLA]
        lines += [
            "BEGIN:VEVENT",
            f"UID:ce-{p['id']}-{ev['date']}@{host}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
            "SUMMARY:" + _ics_text(f"{p['label']}: {_event_title(ev)}"),
            "DESCRIPTION:" + _ics_text("\n".join(desc)),
            f"URL:{base}/#/properties/{p['id']}",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "TRIGGER:-P14D",
            "DESCRIPTION:" + _ics_text(f"In two weeks: {p['label']}: {_event_title(ev)}"),
            "END:VALARM",
            "END:VEVENT",
        ]
    lines += notice_events(user["id"], base, host, stamp, today)
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"


def notice_events(uid: int, base: str, host: str, stamp: str, today: dt.date) -> list[str]:
    """#152: the last day to send the written notice of the next raise, per building (when the engine knows it)."""
    with db() as c:
        rows = c.execute(
            "SELECT * FROM properties WHERE user_id = ? ORDER BY id", (uid,)
        ).fetchall()
    out = []
    for p in rows:
        nx = next_raise(p, today.isoformat())
        n = nx.get("notice") or {}
        if nx.get("state") not in ("ok", "need_cpi", "no_cap") or not n.get("by"):
            continue
        d = dt.date.fromisoformat(n["by"])
        raise_on = dt.date.fromisoformat(nx["date"])
        amount = f"up to ${nx['max_rent']:,.2f} a month" if nx.get("max_rent") else "no legal cap"
        if nx["state"] == "need_cpi":
            amount = f"at most ${nx['max_rent']:,.2f} a month ({nx['cap_max']:g}% max; the exact cap depends on inflation)"
        desc = [
            f"{p['label']} ({p['place'] or p['state']})",
            "",
            f"Next lawful raise: {raise_on:%b} {raise_on.day}, {raise_on.year}, {amount}.",
            f"Send the written notice by today: {n['days']} days ahead"
            + ("." if n.get("sure") else f", for a raise under {n['below_pct']:g}%."),
            f"Source: {n['rule'].get('url') or ''}",
            "",
            f"Details: {base}/#/properties",
            NLA,
        ]
        out += [
            "BEGIN:VEVENT",
            f"UID:ce-notice-{p['id']}-{nx['date']}@{host}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
            "SUMMARY:" + _ics_text(f"Send rent notice: {p['label']}"),
            "DESCRIPTION:" + _ics_text("\n".join(desc)),
            f"URL:{base}/#/properties",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "TRIGGER:-P7D",
            "DESCRIPTION:" + _ics_text(f"In one week: send the rent notice for {p['label']}"),
            "END:VALARM",
            "END:VEVENT",
        ]
    return out


@router.get("/cal/{token}.ics")
def calendar_feed(token: str, request: Request):
    limit("ics", client_ip(request))
    if not re.fullmatch(r"[\w-]{4,64}", token):
        raise HTTPException(404, "No such calendar.")
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE calendar_token = ?", (token,)).fetchone()
    if not user:
        raise HTTPException(404, "No such calendar.")
    body = build_ics(user, base_url(request), dt.date.today())
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="clause-and-effect.ics"'},
    )


def send_mail(
    to: str,
    subject: str,
    text: str,
    html_body: str | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    """One message through Resend SMTP (STARTTLS). The API key is read from its mode-600 file per send."""
    key = cfg_path("resend").read_text().strip()
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="isaaclins.com")
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(text)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login("resend", key)
        s.send_message(msg)


def test_alert(user: sqlite3.Row, base: str, today: dt.date) -> tuple[str, str, str]:
    ups = upcoming(user["id"], today)
    subject = "Test alert: what's changing for your properties"
    text = [
        f"Hi{' ' + user['name'].split()[0] if user['name'] else ''},",
        "",
        "This is the test alert you asked for. Upcoming dates for your saved properties:",
        "",
    ]
    rows = []
    for p, ev in ups[:12]:
        d = dt.date.fromisoformat(ev["date"]).strftime("%b %d, %Y").replace(" 0", " ")
        text.append(f"{d}  {p['label']}: {_event_title(ev)}")
        rows.append(
            f'<tr><td style="padding:6px 14px 6px 0;white-space:nowrap;color:#002664;font-weight:600">{html.escape(d)}</td>'
            f'<td style="padding:6px 0"><b>{html.escape(p["label"])}</b><br>{html.escape(_event_title(ev))}</td></tr>'
        )
    if not ups:
        text.append("No upcoming effective dates for your properties right now.")
    text += [
        "",
        f"Open My properties: {base}/#/properties",
        "",
        NLA,
        "You get this email because you asked for a test alert.",
    ]
    body = (
        '<div style="font:15px/1.55 -apple-system,Segoe UI,Arial,sans-serif;color:#000c1f;max-width:560px">'
        '<p style="font:28px/1.1 Georgia,serif;margin:0 0 14px">Clause <i>&amp;</i> Effect</p>'
        "<p>This is the test alert you asked for. Upcoming dates for your saved properties:</p>"
        + (
            f'<table style="border-collapse:collapse;margin:10px 0 18px">{"".join(rows)}</table>'
            if rows
            else "<p>No upcoming effective dates for your properties right now.</p>"
        )
        + f'<p><a href="{html.escape(base)}/#/properties" style="display:inline-block;background:#002664;color:#fff;'
        'padding:10px 18px;border-radius:999px;text-decoration:none;font-weight:600">Open My properties</a></p>'
        f'<p style="color:#5a6372;font-size:12.5px;margin-top:22px"><b>Not legal advice.</b> Information about public law with citations; check the cited source.<br>'
        "You get this email because you asked for a test alert.</p></div>"
    )
    return subject, "\n".join(text), body


@router.post("/api/alerts/test-email")
def send_test_email(request: Request):
    user = require_user(request)
    if user["is_demo"]:
        raise HTTPException(
            403, "The demo account has no mailbox. Sign in with Google to get a test alert."
        )
    limit("mail_user", f"u{user['id']}")
    limit("mail_all", "all")
    subject, text, body = test_alert(user, base_url(request), dt.date.today())
    try:
        send_mail(user["email"], subject, text, body)
    except (OSError, smtplib.SMTPException) as e:
        log(f"test email failed: {type(e).__name__}")
        raise HTTPException(502, "The email could not be sent. Please try again later.") from None
    with db() as c:
        c.execute(
            "UPDATE alert_prefs SET last_test_email_at = ? WHERE user_id = ?",
            (now_iso(), user["id"]),
        )
    log("test email sent")
    return {"ok": True, "sent_to": user["email"]}


# ------------------------------------------------------------------ email digests (CLI: send-digests)
PUBLIC_BASE = os.environ.get("NAVIGATOR_PUBLIC_BASE", "https://navigator.isaaclins.com").rstrip("/")
DIGEST_AHEAD_DAYS = 30
UNSUB_TTL = 400 * 86400
DIGEST_VERB = {
    "takes_effect": "takes effect",
    "ends": "ends",
    "figure": "a new figure applies",
    "changes": "changes for this building",
}


def unsubscribe_url(uid: int, base: str = PUBLIC_BASE) -> str:
    return f"{base}/alerts/unsubscribe?t=" + urllib.parse.quote(
        sign("unsub", {"uid": uid}, UNSUB_TTL)
    )


def _plain_summary(rule_id: str, jurisdiction: str | None) -> str:
    """One plain sentence: the first sentence of the rule's requirement."""
    rules, _, _ = U.rules_for(jurisdiction)
    r = next((x for x in rules if x.get("team_rule_id") == rule_id), None)
    txt = (r or {}).get("requirement") or ""
    m = re.match(r"(.{20,}?[.!?])(\s|$)", txt, re.S)
    return (m.group(1) if m else txt).strip()


def digest_items(uid: int, today: dt.date, c: sqlite3.Connection) -> list[dict]:
    """Changes not yet mailed: effective within DIGEST_AHEAD_DAYS, or since the last digest run (first run: today)."""
    st = c.execute("SELECT last_sent_on FROM digest_state WHERE user_id = ?", (uid,)).fetchone()
    start = dt.date.fromisoformat(st["last_sent_on"]) if st else today - dt.timedelta(days=1)
    # at most 30 days back (e.g. alerts were off for a while), and never later than yesterday
    start = max(
        min(start, today - dt.timedelta(days=1)), today - dt.timedelta(days=DIGEST_AHEAD_DAYS)
    )
    end = today + dt.timedelta(days=DIGEST_AHEAD_DAYS)
    sent = {
        (r["property_id"], r["event_date"], r["rule_id"], r["kind"])
        for r in c.execute("SELECT * FROM digest_log WHERE user_id = ?", (uid,))
    }
    props = c.execute("SELECT * FROM properties WHERE user_id = ? ORDER BY id", (uid,)).fetchall()
    out = []
    for p in props:
        for ev in property_changes(p, start.isoformat())["events"]:
            d = dt.date.fromisoformat(ev["date"])
            if not (start < d <= end):
                continue
            for it in ev["items"]:
                k = (p["id"], ev["date"], it["rule_id"], it["kind"])
                if k in sent:
                    continue
                out.append(
                    {
                        "property_id": p["id"],
                        "label": p["label"],
                        "address": p["address"],
                        "date": ev["date"],
                        "past": d <= today,
                        "rule_id": it["rule_id"],
                        "kind": it["kind"],
                        "title": it["title"],
                        "citation": it.get("citation") or "",
                        "source_url": it.get("source_url") or "",
                        "key_value": it.get("key_value") or "",
                        "summary": _plain_summary(it["rule_id"], p["jurisdiction"]),
                    }
                )
    return sorted(out, key=lambda x: (x["date"], x["property_id"], x["rule_id"]))


def _fmt_day(d: str) -> str:
    return dt.date.fromisoformat(d).strftime("%b %d, %Y").replace(" 0", " ")


def build_digest(
    user: sqlite3.Row, items: list[dict], base: str = PUBLIC_BASE
) -> tuple[str, str, str]:
    n = len(items)
    subject = f"{n} rule change{'s' if n != 1 else ''} for your properties"
    unsub = unsubscribe_url(user["id"], base)
    hi = f"Hi {user['name'].split()[0]}," if user["name"] else "Hi,"
    text = [hi, "", "These rules change at your saved properties:", ""]
    blocks = []
    for it in items:
        when = ("Since " if it["past"] else "On ") + _fmt_day(it["date"])
        link = f"{base}/#/properties/{it['property_id']}"
        text += [
            f"{it['address']}",
            f"  {when}: {it['title']} {DIGEST_VERB[it['kind']]}.",
        ]
        if it["summary"]:
            text.append(f"  {it['summary']}")
        cite = it["citation"] + (f" ({it['source_url']})" if it["source_url"] else "")
        text += [f"  Source: {cite}", f"  Details: {link}", ""]
        e = html.escape
        blocks.append(
            '<tr><td style="padding:12px 0;border-top:1px solid #e6e8ec">'
            f'<div style="color:#5a6372;font-size:13px">{e(it["address"])}</div>'
            f'<div style="margin:2px 0"><b style="color:#002664">{e(when)}</b> &middot; '
            f"<b>{e(it['title'])}</b> {e(DIGEST_VERB[it['kind']])}.</div>"
            + (f"<div>{e(it['summary'])}</div>" if it["summary"] else "")
            + '<div style="font-size:13px;margin-top:4px">'
            + (
                f'<a href="{e(it["source_url"])}" style="color:#0066c5">{e(it["citation"])}</a>'
                if it["source_url"]
                else e(it["citation"])
            )
            + f' &middot; <a href="{e(link)}" style="color:#0066c5">Open the property</a></div></td></tr>'
        )
    text += [NLA, "", f"Stop these emails: {unsub}"]
    body = (
        '<div style="font:15px/1.55 -apple-system,Segoe UI,Arial,sans-serif;color:#000c1f;max-width:560px">'
        '<p style="font:26px/1.1 Georgia,serif;margin:0 0 12px">Clause <i>&amp;</i> Effect</p>'
        f"<p>{html.escape(hi)} these rules change at your saved properties:</p>"
        f'<table style="border-collapse:collapse;width:100%">{"".join(blocks)}</table>'
        '<p style="color:#5a6372;font-size:12.5px;margin-top:22px"><b>Not legal advice.</b> Information about public '
        "law with citations; check the cited source.<br>"
        f'<a href="{html.escape(unsub)}" style="color:#5a6372">Stop these emails</a></p></div>'
    )
    return subject, "\n".join(text), body


def _mark_digest(uid: int, today: dt.date) -> None:
    with db() as c:
        c.execute(
            "INSERT INTO digest_state (user_id, last_sent_on) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET last_sent_on = excluded.last_sent_on",
            (uid, today.isoformat()),
        )


def send_digests(today: dt.date, dry_run: bool = False, base: str = PUBLIC_BASE) -> dict:
    """One email per opted-in, non-demo user with unsent changes. Returns counts (no addresses or emails)."""
    stats = {"users": 0, "emails": 0, "items": 0, "failed": 0, "dry_run": dry_run}
    with db() as c:
        users = c.execute(
            "SELECT u.* FROM users u JOIN alert_prefs a ON a.user_id = u.id "
            "WHERE a.email_digest = 1 AND u.is_demo = 0 ORDER BY u.id"
        ).fetchall()
    for u in users:
        stats["users"] += 1
        with db() as c:
            items = digest_items(u["id"], today, c)
        if not items:
            if (
                not dry_run
            ):  # checked up to today: a later run only looks at what happens after this
                _mark_digest(u["id"], today)
            continue
        subject, text, body = build_digest(u, items, base)
        if dry_run:
            print(f"[dry-run] user {u['id']}: {len(items)} item(s): {subject}")
            stats["emails"] += 1
            stats["items"] += len(items)
            continue
        try:
            send_mail(
                u["email"],
                subject,
                text,
                body,
                headers={
                    "List-Unsubscribe": f"<{unsubscribe_url(u['id'], base)}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
            )
        except (OSError, smtplib.SMTPException) as e:
            log(f"digest failed for user {u['id']}: {type(e).__name__}")
            stats["failed"] += 1
            continue
        ts = now_iso()
        with db() as c:
            c.executemany(
                "INSERT OR IGNORE INTO digest_log (user_id, property_id, event_date, rule_id, kind, sent_at) "
                "VALUES (?,?,?,?,?,?)",
                [
                    (u["id"], i["property_id"], i["date"], i["rule_id"], i["kind"], ts)
                    for i in items
                ],
            )
        _mark_digest(u["id"], today)
        stats["emails"] += 1
        stats["items"] += len(items)
    log(f"digests: {stats}")
    return stats


UNSUB_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} · Clause &amp; Effect</title>
<style>body{{font:16px/1.55 -apple-system,Segoe UI,Arial,sans-serif;color:#000c1f;max-width:520px;margin:12vh auto;
padding:0 24px}}h1{{font:400 34px/1.1 Georgia,serif}}a{{color:#0066c5}}</style></head>
<body><h1>{title}</h1><p>{body}</p><p><a href="/#/properties">My properties</a></p></body></html>"""


def _unsubscribe(t: str | None) -> tuple[int, str]:
    d = unsign("unsub", t)
    if not d:
        return 400, UNSUB_PAGE.format(
            title="Link expired",
            body="This unsubscribe link is not valid. Turn email alerts off in My properties.",
        )
    with db() as c:
        c.execute("UPDATE alert_prefs SET email_digest = 0 WHERE user_id = ?", (int(d["uid"]),))
    log("digest unsubscribe")
    return 200, UNSUB_PAGE.format(
        title="You're unsubscribed",
        body="We won't email you about rule changes any more. You can turn alerts back on in My properties.",
    )


@router.get("/alerts/unsubscribe", response_class=HTMLResponse)
def unsubscribe_get(t: str | None = None):
    code, page = _unsubscribe(t)
    return HTMLResponse(page, status_code=code)


@router.post("/alerts/unsubscribe", response_class=HTMLResponse)
def unsubscribe_post(t: str | None = None):
    """RFC 8058 one-click unsubscribe (mail clients POST to the List-Unsubscribe URL)."""
    code, page = _unsubscribe(t)
    return HTMLResponse(page, status_code=code)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m web.accounts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sd = sub.add_parser(
        "send-digests", help="email each opted-in user the rule changes at their properties"
    )
    sd.add_argument(
        "--dry-run", action="store_true", help="print what would be sent; send and record nothing"
    )
    sd.add_argument(
        "--today", type=dt.date.fromisoformat, default=None, help="YYYY-MM-DD (default: today)"
    )
    a = ap.parse_args(argv)
    if a.cmd == "send-digests":
        stats = send_digests(a.today or dt.date.today(), dry_run=a.dry_run)
        print(json.dumps(stats))
        return 1 if stats["failed"] else 0
    return 2


# ------------------------------------------------------------------ privacy + terms (linked from Google's consent screen)
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Clause &amp; Effect</title><link rel="stylesheet" href="/static/app.css">
<style>
.legal {{ max-width: 680px; margin: 0 auto; padding: 48px 24px 96px; }}
.legal .brand {{ display: inline-flex; gap: 10px; align-items: center; text-decoration: none; color: var(--ink); }}
.legal h1 {{ font: 400 clamp(2.4rem, 2rem + 2vw, 3.4rem)/1.02 var(--serif); letter-spacing: -.03em; margin: 40px 0 8px; }}
.legal h2 {{ font-size: 17px; margin: 30px 0 6px; }}
.legal p, .legal li {{ color: var(--ink-2); font-size: 15.5px; }}
.legal ul {{ padding-left: 20px; margin: 6px 0; }}
.legal .upd {{ color: var(--ink-3); font-size: 13px; }}
.legal .nla {{ margin-top: 34px; padding: 14px 18px; border-radius: 18px; background: var(--muted); font-size: 14px; }}
</style></head><body><main class="legal">
<a class="brand" href="/"><span class="brand-mark" aria-hidden="true">§</span><span class="brand-word">Clause <i>&amp;</i> Effect</span></a>
<h1>{title}</h1><p class="upd">Last updated October 3, 2026 · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a></p>
{body}
<p class="nla"><b>Not legal advice.</b> Clause &amp; Effect explains public law with citations to the official text. It is
not a compliance check. For your situation, contact a tenant organisation, housing agency or attorney.</p>
</main></body></html>"""

PRIVACY = """
<p>Clause &amp; Effect is a hackathon prototype (Hack-Nation 2026, RealPage challenge) run by Isaac Lins. You can use
the address lookup without an account. An account is only needed for <b>My properties</b>.</p>
<h2>What we store when you sign in</h2>
<ul><li>From Google: your email address, your display name and Google's account ID for you. Nothing else: no contacts,
no calendar, no photos.</li>
<li>What you save: a label and the address of each property, the city and state it belongs to, and the building facts
you enter (year built, number of units, whether the owner lives there).</li>
<li>Your alert settings, a secret calendar link, and which change alerts we already emailed you (so you never get
one twice).</li></ul>
<p>We do not store names of tenants, rents or anything about the people who live in a building. We do not ask for it.</p>
<h2>Cookies</h2>
<p>One cookie keeps you signed in (30 days). A second, short-lived cookie protects the sign-in step. No tracking,
analytics or advertising cookies.</p>
<h2>Who else sees data</h2>
<ul><li><b>Google</b>, to sign you in.</li>
<li><b>US Census Geocoder</b>: the address you type is sent there once to find its city and state.</li>
<li><b>Resend</b> delivers the alert emails, only if you turn on email alerts. Every email has a one-click
unsubscribe link.</li></ul>
<p>We never sell or share your data, and we do not use it for anything except showing you your properties.</p>
<h2>Delete anytime</h2>
<p>In My properties, open the account menu and choose <b>Delete account</b>. Your account, properties and settings are
deleted immediately. Signing out does not delete anything. When this prototype is switched off, all accounts are
deleted.</p>
<h2>Contact</h2><p><a href="mailto:contact@isaaclins.com">contact@isaaclins.com</a></p>
"""

TERMS = """
<p>Clause &amp; Effect is a free hackathon prototype. By using it you agree to these short terms.</p>
<h2>Information, not advice</h2>
<p>Answers are automated summaries of statutes, ordinances and bills from a fixed set of official sources, with the
date they apply to. They can be incomplete or wrong. Always read the cited source before you act.</p>
<h2>Use it fairly</h2>
<ul><li>Use it to understand and follow the rules, not to find ways around them.</li>
<li>No automated scraping, no attempts to break in or to overload the service.</li>
<li>Only save addresses you own, manage or rent.</li></ul>
<h2>Your account</h2>
<p>Your saved properties are yours. You can delete your account at any time. We may remove accounts that break these
terms, and the prototype may change or shut down without notice; then all data is deleted.</p>
<h2>No warranty</h2>
<p>The service is provided as is, without any warranty. We are not liable for decisions made on the basis of it.</p>
<h2>Contact</h2><p><a href="mailto:contact@isaaclins.com">contact@isaaclins.com</a></p>
"""


@router.get("/privacy", response_class=HTMLResponse)
def privacy():
    return PAGE.format(title="Privacy", body=PRIVACY)


@router.get("/terms", response_class=HTMLResponse)
def terms():
    return PAGE.format(title="Terms", body=TERMS)


if __name__ == "__main__":
    sys.exit(main())
