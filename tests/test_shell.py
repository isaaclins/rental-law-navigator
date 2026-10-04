"""First screen before app.js (web/static/index.html): the pre-rendered home hero stays in step with viewHome, the
deep-link skeletons exist, and the preloads match what the page actually uses.

Run: uv run --with pytest --with httpx pytest tests/test_shell.py -q
If a hero string changed: rerun tests/make_shell.py (see its docstring).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from web.app import app

STATIC = Path(__file__).resolve().parents[1] / "web/static"
INDEX = (STATIC / "index.html").read_text()
APP_JS = (STATIC / "app.js").read_text()
ES = json.loads((STATIC / "i18n/es.json").read_text())


def en(key: str) -> str:
    m = re.search(rf"\b{key}: \"([^\"]*)\"", APP_JS)
    assert m, key
    return m.group(1)


def shell(lang: str) -> str:
    m = re.search(rf"<!--shell-{lang}-->(.*?)<!--/shell-{lang}-->", INDEX, re.S)
    assert m and m.group(1).strip(), f"shell-{lang} is empty: run tests/make_shell.py"
    return html.unescape(m.group(1))


def test_home_shell_carries_the_current_hero():
    for lang, t in (("en", en), ("es", ES.get)):
        s = shell(lang)
        assert s.startswith('<div class="home" data-shell="home"><section class="hero">'), lang
        for key in ("hero_a", "hero_b", "hero_lead"):
            assert t(key) in s, (lang, key, "hero text changed: rerun tests/make_shell.py")
        assert f'placeholder="{t("search_try")}"' in s, lang
        assert 'id="hq"' in s and 'class="big-search"' in s and 'class="slides"' in s, lang


def test_only_the_first_photo_loads_and_it_is_preloaded():
    s = shell("en")
    imgs = re.findall(r"<img [^>]*>", s)
    assert len(imgs) == 1, "only the first street photo belongs in the shell"
    assert 'fetchpriority="high"' in imgs[0] and 'loading="eager"' in imgs[0]
    src = re.search(r'src="([^"]+)"', imgs[0]).group(1)
    assert f'l.href = "{src}"' in INDEX, "the home preload must name the shell's first photo"


def test_deep_links_get_a_skeleton_and_the_picker_mirrors_app_js():
    for tpl in ("shell-page", "shell-addr"):
        m = re.search(rf'<template id="{tpl}">(.*?)</template>', INDEX, re.S)
        assert m and 'data-shell="skeleton"' in m.group(1) and 'aria-hidden="true"' in m.group(1)
    # the inline picker decides the language exactly like app.js does
    rule = '(/^es\\b/i.test(navigator.language || "") ? "es" : "en")'
    assert 'localStorage.getItem("lang")' in INDEX and rule in INDEX
    assert 'localStorage.getItem("lang") || ' + rule in APP_JS


def test_font_preloads_match_the_font_faces():
    css = (STATIC / "app.css").read_text()
    for href in re.findall(r'<link rel="preload" href="([^"]+\.woff2)"', INDEX):
        assert f'url("{href}")' in css, href
        assert (STATIC / href.split("/static/", 1)[1]).exists(), href


def test_served_page_has_the_shell():
    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert '<template id="shell-en"><!--shell-en--><div class="home" data-shell="home">' in r.text
    assert "/static/features/shell.css?v=" in r.text


def test_static_header_spanish_and_date_match_app_js():
    dic = json.loads(re.search(r"/\*es\*/(.*?)/\*/es\*/", INDEX, re.S).group(1))
    for k in set(re.findall(r'data-i18n="([a-z_]+)"', INDEX)) | {"as_of"}:
        if k in ES:
            assert dic.get(k) == ES[k], (k, "rerun tests/make_shell.py")
    default = re.search(r'const DEFAULT_AS_OF = "([\d-]+)"', APP_JS).group(1)
    assert f'new Date("{default}T12:00:00")' in INDEX, (
        "the inline as-of label uses app.js DEFAULT_AS_OF"
    )


def test_inline_scripts_run_before_first_paint_behind_cloudflare():
    """Cloudflare Rocket Loader defers every script without data-cfasync="false": the picker would then run after
    app.js and the shell would land on top of the real page."""
    for tag in re.findall(r"<script[^>]*>", INDEX):
        assert 'data-cfasync="false"' in tag, tag
