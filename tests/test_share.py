"""Share an answer (#117): the frozen page, its Open Graph tags, the card image, strict params, Spanish.

Run: uv run --with pytest --with httpx pytest tests/test_share.py -q
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from web import share as S
from web.app import app

client = TestClient(app)
PAGE = "/s/A0027/rent/2026-10-01"


class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.m: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("property") or a.get("name")):
            self.m[a.get("property") or a["name"]] = a.get("content", "")


def meta(html: str) -> dict:
    p = Meta()
    p.feed(html)
    return p.m


@pytest.fixture(autouse=True)
def fresh():
    S.CARD_LIMIT.hits.clear()
    S.CARD_ALL.hits.clear()
    yield


def test_page_renders_the_frozen_answer_without_js():
    r = client.get(PAGE)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    h = r.text
    assert "Answer as of Oct 1, 2026" in h
    assert "3918 Fulton St, San Francisco" in h
    assert "Can they raise my rent?" in h
    assert '<h1 class="sh-a">Yes, but only 1.6% until Feb 2027.</h1>' in h
    assert "San Francisco sets one small raise per year." in h
    assert (
        'href="/#/a/A0027"' in h and "See today&#x27;s answer" in h
    )  # one primary action, into the app
    assert (
        "Not legal advice · from San Francisco&#x27;s official rent rules" in h
    )  # one footer line


def test_the_law_sits_behind_one_closed_disclosure():
    h = client.get(PAGE).text
    law = h[h.index('<details class="sh-law">') : h.index("</details>")]
    assert "Show me the law" in law
    assert (
        "For rent-controlled units, the annual allowable increase amount" in law
    )  # verbatim quote
    assert "S.F. Admin. Code ch. 37" in law and 'href="https://www.sf.gov/' in law
    assert "retrieved Oct 1, 2026" in law and "quote checked word for word" in law
    assert "Not legal advice." in law and "tenant group" in law  # the full note
    assert '<details class="sh-law" open' not in h
    before = h[: h.index('<details class="sh-law">')]
    assert "For rent-controlled units" not in before.split("</head>")[1]


def test_the_page_stays_short():
    h = client.get(PAGE).text
    body = h.split("</head>")[1]
    for gone in (
        "How this link looks",
        "No account, no database",
        "Data version",
        "sh-side",
        '<img src="/s/',  # no preview card on the page
    ):
        assert gone not in body, gone
    m = meta(h)
    assert re.fullmatch(r"[0-9a-f]{7}", m["ce:data-version"])  # the hash stays, out of sight
    assert f'data-v="{m["ce:data-version"]}"' in body
    assert "changed after" not in body


def test_open_graph_and_twitter_tags_are_absolute():
    m = meta(client.get(PAGE).text)
    assert m["og:title"] == "Can they raise my rent? · 3918 Fulton St"
    assert m["og:description"] == "Yes, but only 1.6% until Feb 2027."
    assert m["og:type"] == "article" and m["og:site_name"] == "Clause & Effect"
    assert m["og:url"].startswith("https://navigator.isaaclins.com/s/A0027/rent/2026-10-01")
    assert re.fullmatch(
        r"https://navigator\.isaaclins\.com/s/A0027/rent/2026-10-01/card\.png\?v=[0-9a-f]{7}",
        m["og:image"],
    )
    assert (m["og:image:width"], m["og:image:height"], m["og:image:type"]) == (
        "1200",
        "630",
        "image/png",
    )
    assert m["twitter:card"] == "summary_large_image" and m["twitter:image"] == m["og:image"]
    assert m["og:locale"] == "en_US"


def test_card_is_a_1200x630_png_and_cached():
    r = client.get(PAGE + "/card.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = int.from_bytes(r.content[16:20], "big"), int.from_bytes(r.content[20:24], "big")
    assert (w, h) == (1200, 630)
    assert len(r.content) < 300_000  # WhatsApp drops big preview images
    assert "max-age" in r.headers["cache-control"]
    assert client.get(PAGE + "/card.png").content == r.content
    assert client.head(PAGE + "/card.png").status_code == 200


def test_card_generation_is_rate_limited(tmp_path, monkeypatch):
    from web import og_card

    assert client.get(PAGE + "/card.png").status_code == 200  # rendered and cached
    hit = og_card.cached(S.answer("A0027", "rent", "2026-10-01", "en"))
    monkeypatch.setattr(og_card, "CACHE", tmp_path)
    (tmp_path / hit.name).write_bytes(hit.read_bytes())
    monkeypatch.setattr(S.CARD_LIMIT, "n", 0)  # no fresh renders left for this client
    assert client.get(PAGE + "/card.png").status_code == 200  # a cached card still serves
    assert client.get("/s/A0027/deposit/2021-07-13/card.png?lang=es").status_code == 429


@pytest.mark.parametrize(
    "path",
    [
        "/s/A9999/rent/2026-10-01",  # unknown address
        "/s/a0027/rent/2026-10-01",  # not the exact id form
        "/s/A0027x/rent/2026-10-01",
        "/s/A0027/rents/2026-10-01",  # unknown topic
        "/s/A0027/rent_increase_limits/2026-10-01",
        "/s/A0027/rent/2026-02-30",  # not a date
        "/s/A0027/rent/2026-1-01",
        "/s/A0027/rent/20261001",
        "/s/A0027/rent/2019-12-31",  # outside the supported range
        "/s/A0027/rent/2031-01-01",
        "/s/A0027/rent/%3Cscript%3E",
        "/s/A0027/rent/2026-10-01/card.png/x",
    ],
)
def test_invalid_params_are_404(path):
    assert client.get(path).status_code == 404
    if not path.endswith("/x"):
        assert client.get(path + "/card.png").status_code == 404
        assert client.get(path.replace("/s/", "/api/share/")).status_code == 404


def test_escaping_and_no_reflection():
    r = client.get(PAGE + '?lang="><script>alert(1)</script>&v="><b>')
    assert r.status_code == 200
    assert "<script>alert(1)" not in r.text and "<b>" not in r.text.split("</head>")[0]


def test_spanish_page_and_meta():
    r = client.get(PAGE + "?lang=es")
    m = meta(r.text)
    assert '<html lang="es">' in r.text
    assert m["og:title"] == "¿Pueden subirme la renta? · 3918 Fulton St"
    assert m["og:description"].startswith("Sí, pero solo 1.6%")
    assert m["og:locale"] == "es_US"
    assert "lang=es" in m["og:image"]
    assert "Respuesta al 1 oct 2026" in r.text and "No es asesoría legal." in r.text
    assert "Muéstreme la ley" in r.text
    assert "No es asesoría legal · según las reglas de renta oficiales de San Francisco" in r.text
    assert "For rent-controlled units" in r.text  # the law's words stay in English
    c = client.get(PAGE + "/card.png?lang=es")
    assert c.status_code == 200 and c.content[:4] == b"\x89PNG"


def test_api_and_version_are_stable_across_languages():
    en = client.get("/api/share/A0027/rent/2026-10-01").json()
    es = client.get("/api/share/A0027/rent/2026-10-01?lang=es").json()
    assert en["url"] == f"https://navigator.isaaclins.com/s/A0027/rent/2026-10-01?v={en['v']}"
    assert es["url"].endswith(f"?lang=es&v={en['v']}") and es["v"] == en["v"]
    assert en["title"] == "Can they raise my rent? · 3918 Fulton St" and en["text"] == en["answer"]


def test_a_changed_data_version_is_shown():
    h = client.get(PAGE + "?v=0000000").text
    assert "changed after the link was shared" in h
    assert "changed after" not in client.get(PAGE).text


def test_every_topic_renders():
    for slug in S.TOPICS:
        r = client.get(f"/s/A0016/{slug}/2026-10-01")
        assert r.status_code == 200, slug
        m = meta(r.text)
        assert m["og:description"] and " · 3515 Fillmore St" in m["og:title"]
