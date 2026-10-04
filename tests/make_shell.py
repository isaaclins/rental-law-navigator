"""Pre-render the home hero into web/static/index.html (templates #shell-en / #shell-es), from the real viewHome
render, so a cold load paints the home's first screen straight from the HTML; app.js morphs its first render into
these nodes. Rerun after changing the hero markup or its strings:

    uv run uvicorn web.app:app --port 8800 &        (any running server with the current code)
    uv run --with playwright python tests/make_shell.py      (BASE=http://127.0.0.1:8800/ by default)

tests/test_shell.py checks that the shell still carries the hero's current strings.
"""

import asyncio
import json
import os
import re
from pathlib import Path

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8800/")
INDEX = Path(__file__).resolve().parents[1] / "web/static/index.html"

# the hero as viewHome rendered it, without what scripts add afterwards (tour link, suggestions, carousel state)
EXTRACT = """() => {
  const hero = document.querySelector('#main .home > .hero').cloneNode(true);
  hero.querySelectorAll('[data-tour-slot]').forEach((e) => e.replaceChildren());
  hero.querySelectorAll('.suggest').forEach((e) => { e.replaceChildren(); e.hidden = true; });
  hero.querySelectorAll('.ce-spring, .is-springing').forEach((e) => e.classList.remove('ce-spring', 'is-springing'));
  hero.querySelectorAll('[class=""]').forEach((e) => e.removeAttribute('class'));
  // only the first photo: the others are invisible until the carousel turns, and would compete with app.js
  hero.querySelectorAll('.slide:not(.on) img').forEach((e) => e.remove());
  const first = hero.querySelector('.slide.on img');
  if (first) { first.setAttribute('fetchpriority', 'high'); first.setAttribute('loading', 'eager'); }
  return `<div class="home" data-shell="home">${hero.outerHTML}</div>`;
}"""


async def render(p, lang: str) -> str:
    ctx = await p.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
    await ctx.add_init_script(f"localStorage.setItem('lang', '{lang}'); sessionStorage.clear();")
    page = await ctx.new_page()
    await page.goto(BASE + "#/")
    await page.wait_for_selector("#main .home > .hero h1")
    await page.wait_for_function("!document.querySelector('#main [data-shell]')")
    html = await page.evaluate(EXTRACT)
    await ctx.close()
    return re.sub(r">\s+<", "> <", html.strip())


async def main() -> None:
    async with async_playwright() as p:
        b = await p.chromium.launch()
        shells = {lang: await render(b, lang) for lang in ("en", "es")}
        await b.close()
    s = INDEX.read_text()
    for lang, html in shells.items():
        s, n = re.subn(
            rf"<!--shell-{lang}-->.*?<!--/shell-{lang}-->",
            lambda _m, lang=lang, html=html: f"<!--shell-{lang}-->{html}<!--/shell-{lang}-->",
            s,
            flags=re.S,
        )
        assert n == 1, f"marker for {lang} missing in index.html"
    # the Spanish strings of the static header (data-i18n) and the as-of word, for the inline picker
    es = json.loads((INDEX.parent / "i18n/es.json").read_text())
    keys = sorted(set(re.findall(r'data-i18n="([a-z_]+)"', s)) | {"as_of"})
    dic = json.dumps({k: es[k] for k in keys if k in es}, ensure_ascii=False, separators=(",", ":"))
    s, n = re.subn(r"/\*es\*/.*?/\*/es\*/", lambda _m: f"/*es*/{dic}/*/es*/", s, flags=re.S)
    assert n == 1, "es dictionary marker missing in index.html"
    INDEX.write_text(s)
    print({k: len(v) for k, v in shells.items()}, "->", INDEX)


if __name__ == "__main__":
    asyncio.run(main())
