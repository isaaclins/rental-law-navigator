"""Playwright QA screenshots for Share an answer (#117): the frozen page 1440/390 (EN, ES), the popover on an address
page, the phone sheet, and the card image itself. Fails on console errors or horizontal overflow.

Server: uv run uvicorn web.app:app --port 8803
Run:    uv run --with playwright python tests/shots_share.py   (PNGs -> $SHOTS_DIR)
"""

import asyncio
import os
import sys
import urllib.request

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8803").rstrip("/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/share")
os.makedirs(OUT, exist_ok=True)
PAGE = "/s/A0027/rent/2026-10-01"


async def main():
    problems: list[str] = []
    async with async_playwright() as p:
        b = await p.chromium.launch()

        async def ctx(w, h, lang="en", touch=False):
            c = await b.new_context(
                viewport={"width": w, "height": h},
                device_scale_factor=2 if w < 500 else 1,
                has_touch=touch,
                is_mobile=touch,
            )
            await c.add_init_script(f"localStorage.setItem('lang', '{lang}');")
            await c.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
            pg = await c.new_page()
            tag = f"{w}-{lang}"
            pg.on(
                "console",
                lambda m: (
                    problems.append(f"{tag} console: {m.text}") if m.type == "error" else None
                ),
            )
            pg.on("pageerror", lambda e: problems.append(f"{tag} pageerror: {e}"))
            return c, pg

        async def shot(pg, name, full=False):
            over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
            if over > 0:
                problems.append(f"{name}: horizontal overflow {over}px")
            await pg.screenshot(path=f"{OUT}/{name}.png", full_page=full)
            print("saved", f"{name}.png")

        # the frozen page
        for w, h in ((1440, 1000), (390, 844), (320, 640), (2560, 1300)):
            for lang in ("en", "es") if w in (1440, 390) else ("en",):
                c, pg = await ctx(w, h, lang)
                await pg.goto(
                    f"{BASE}{PAGE}{'?lang=es' if lang == 'es' else ''}", wait_until="networkidle"
                )
                await pg.wait_for_function(
                    "[...document.images].every((i) => i.complete && i.naturalWidth)"
                )
                await pg.wait_for_timeout(300)
                await shot(pg, f"page-{w}-{lang}", full=True)
                if w in (1440, 390):
                    await pg.click(".sh-law > summary")
                    await pg.wait_for_timeout(450)
                    await shot(pg, f"page-{w}-{lang}-law", full=True)
                    await pg.click(".sh-law > summary")
                if w == 1440 and lang == "en":
                    await pg.click(".sh-share")
                    await pg.wait_for_timeout(600)
                    await shot(pg, "page-1440-share-popover")
                await c.close()

        # the popover on an address page: open the rent topic, press Share, then Copy link
        c, pg = await ctx(1440, 1000)
        await pg.goto(f"{BASE}/#/a/A0027", wait_until="networkidle")
        await pg.wait_for_selector("#t-rent_increase_limits")
        await pg.click("#t-rent_increase_limits > summary")
        await pg.wait_for_selector("#t-rent_increase_limits .ce-share-b")
        await pg.wait_for_timeout(400)
        await pg.locator("#t-rent_increase_limits").scroll_into_view_if_needed()
        await shot(pg, "app-1440-topic-share-button")
        await pg.click("#t-rent_increase_limits .ce-share-b")
        await pg.wait_for_selector(".ce-sp img.is-in", timeout=8000)
        await pg.wait_for_timeout(450)
        await shot(pg, "app-1440-popover")
        await pg.click(".ce-sp-copy")
        await pg.wait_for_timeout(500)
        await shot(pg, "app-1440-popover-copied")
        clip = await pg.evaluate("navigator.clipboard.readText()")
        if "/s/A0027/rent/2026-10-01" not in clip:
            problems.append(f"clipboard has {clip!r}")
        await c.close()

        # phone without navigator.share (headless): the bottom sheet
        c, pg = await ctx(390, 844, "es")
        await pg.goto(f"{BASE}/#/a/A0027", wait_until="networkidle")
        await pg.wait_for_selector("#t-rent_increase_limits")
        await pg.click("#t-rent_increase_limits > summary")
        await pg.wait_for_selector("#t-rent_increase_limits .ce-share-b")
        await pg.click("#t-rent_increase_limits .ce-share-b")
        await pg.wait_for_selector(".ce-sp img.is-in", timeout=8000)
        await pg.wait_for_timeout(500)
        await shot(pg, "app-390-es-sheet")
        await c.close()
        await b.close()

    # the card images
    for q, name in (("", "card-en"), ("?lang=es", "card-es")):
        with urllib.request.urlopen(f"{BASE}{PAGE}/card.png{q}") as r:
            open(f"{OUT}/{name}.png", "wb").write(r.read())
        print("saved", f"{name}.png")
    for path, name in (
        ("/s/A0016/eviction/2026-10-01", "card-a0016-eviction"),
        ("/s/A0027/screening/2025-06-01", "card-a0027-screening-2025"),
    ):
        with urllib.request.urlopen(f"{BASE}{path}/card.png") as r:
            open(f"{OUT}/{name}.png", "wb").write(r.read())
        print("saved", f"{name}.png")

    if problems:
        print("\n".join(problems))
        sys.exit(1)


asyncio.run(main())
