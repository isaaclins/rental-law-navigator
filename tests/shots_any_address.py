"""Playwright QA screenshots for the any-address flow (#39), desktop 1440 + mobile 390.

Server: uv run uvicorn web.app:app --port 8798
Run:    uv run --with playwright python tests/shots_any_address.py   (PNGs -> $SHOTS_DIR)
"""

import asyncio
import os

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8798/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/any-address")
os.makedirs(OUT, exist_ok=True)
SM = "1685 Main St, Santa Monica, CA 90401"
DC = "1600 Pennsylvania Ave NW, Washington, DC 20500"
OAK = "1000 Broadway, Oakland, CA 94607"


async def run(b, w, h, tag, errors):
    ctx = await b.new_context(
        viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1
    )
    pg = await ctx.new_page()
    pg.on("console", lambda m: errors.append(f"{tag} {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"{tag} PAGEERROR {e}"))

    async def shot(name, full=False):
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full)
        print("saved", f"{tag}-{name}.png")

    await pg.goto(BASE)
    await pg.wait_for_selector("#hq")
    await pg.click("#hq")
    await pg.keyboard.type(SM, delay=8)
    await pg.wait_for_selector("#hs .aa-opt")
    await pg.wait_for_timeout(400)
    await shot("01-search-option")
    await pg.dispatch_event("#hs .aa-opt", "mousedown")
    await pg.wait_for_selector(".aa-facts input[name=year_built]")
    await pg.wait_for_selector(".aa-answers .rule")
    await pg.wait_for_timeout(900)
    await shot("02-resolved")
    await pg.fill(".aa-facts input[name=year_built]", "1962")
    await pg.fill(".aa-facts input[name=units]", "6")
    await pg.click(".aa-seg [data-oo=no]")
    await pg.wait_for_timeout(1200)
    await shot("03-facts-filled")
    await pg.evaluate("document.querySelector('.aa-results').scrollIntoView()")
    await pg.wait_for_timeout(500)
    await shot("04-answers")
    # out of scope
    await pg.fill(".aa-search input", DC)
    await pg.press(".aa-search input", "Enter")
    await pg.wait_for_selector(".aa-covered")
    await pg.wait_for_timeout(600)
    await shot("05-out-of-scope")
    # state law only (city not in the corpus)
    await pg.fill(".aa-search input", OAK)
    await pg.press(".aa-search input", "Enter")
    await pg.wait_for_selector(".aa-answers .rule, .aa-msg")
    await pg.wait_for_timeout(900)
    await shot("06-state-only")
    # search palette entry point
    await pg.keyboard.press("Escape")
    await pg.wait_for_selector(".aa-scrim", state="hidden")
    await pg.click(".search-trigger")
    await pg.wait_for_selector("#cmdk input")
    await pg.wait_for_timeout(100)
    await pg.keyboard.type("88 Hope St, Boston, MA", delay=8)
    await pg.wait_for_selector("#cmdk-list .aa-opt")
    await pg.wait_for_timeout(300)
    await shot("07-palette-option")
    await ctx.close()


async def main():
    errors: list[str] = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await run(b, 1440, 900, "desktop", errors)
        await run(b, 390, 844, "mobile", errors)
        await b.close()
    print("console errors:", errors or "none")


asyncio.run(main())
