"""Unknown paths: a branded HTML 404 page for every client (never the offline page, never raw JSON); /api/* keeps JSON."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


@pytest.mark.parametrize("accept", ["text/html,application/xhtml+xml", "*/*", None])
def test_unknown_path_is_the_app_with_its_404(accept):
    """One 404 design: the path 404 is the app shell (tab bar, EN/ES), moved to /#/<path> before it paints, where
    the router shows the same "Page not found" as a wrong #/ link."""
    r = client.get("/nope-404", headers={"accept": accept} if accept else {})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")
    assert "no-store" in r.headers.get("cache-control", "")
    head, body = r.text.split("</head>", 1)
    assert (
        'history.replaceState(null, "", "/#" + location.pathname' in head
        and 'data-cfasync="false"' in head
    )
    assert 'id="main"' in body and "?v=" in body  # the real shell with hashed assets
    assert "<title>Offline" not in r.text


def test_in_app_404_is_bilingual():
    js = client.get("/static/app.js").text
    es = client.get("/static/i18n/es.json").json()
    assert 'nf_page: "Page not found"' in js and es["nf_page"] == "Página no encontrada"
    assert es["nf_lookup"] and es["nf_ask"]


def test_service_worker_registers_under_rocket_loader():
    js = client.get("/static/features/pwa.js").text
    assert 'getEntriesByType?.("navigation")' in js and "setTimeout(registerSW" in js


def test_api_404_stays_json():
    r = client.get("/api/nope", headers={"accept": "text/html"})
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


def test_offline_page_is_branded_and_bilingual():
    r = client.get("/static/offline.html")
    assert r.status_code == 200
    assert "Instrument Serif" in r.text and "#002664" in r.text
    assert "You're offline" in r.text and "No tiene conexión" in r.text and 'id="retry"' in r.text


def test_service_worker_only_falls_back_when_fetch_throws():
    js = client.get("/sw.js").text
    nav = js[js.index("async function navigate") : js.index("async function answer")]
    assert (
        "catch" in nav and "res.ok" not in nav.split("catch")[1]
    )  # the fallback lives in catch only
    assert "InstrumentSerif-Regular.woff2" in js
