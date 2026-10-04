"""Playwright QA screenshots for Ask the law (#101), desktop 1440 + mobile 390, English and Spanish.

Server: uv run uvicorn web.app:app --port 8799
Run:    uv run --with playwright python tests/shots_ask.py   (PNGs -> $SHOTS_DIR)
Fails on console errors or horizontal overflow.
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8799/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/ask")
os.makedirs(OUT, exist_ok=True)
EN = "How much deposit can my landlord ask for at 6238 De Longpre Ave?"
ES = "¿Me pueden desalojar sin motivo en Berkeley?"


async def run(b, w, h, lang, problems, reduced=False):
    tag = f"{'d' if w > 500 else 'm'}-{lang}"
    ctx = await b.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=2 if w < 500 else 1,
        reduced_motion="reduce" if reduced else "no-preference",
    )
    await ctx.add_init_script(f"localStorage.setItem('lang', '{lang}');")
    pg = await ctx.new_page()
    pg.on(
        "console",
        lambda m: problems.append(f"{tag} console: {m.text}") if m.type == "error" else None,
    )
    pg.on("pageerror", lambda e: problems.append(f"{tag} pageerror: {e}"))

    async def shot(name, full=False):
        over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
        if over > 0:
            problems.append(f"{tag}-{name}: horizontal overflow {over}px")
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full)
        print("saved", f"{tag}-{name}.png")

    await pg.goto(BASE + "#/ask")
    await pg.wait_for_selector(".ask-chip")
    await pg.wait_for_timeout(1400)
    await shot("01-home")
    await pg.evaluate("scrollTo(0, document.querySelector('.ask-statement').offsetTop - 120)")
    await pg.wait_for_timeout(700)
    await shot("02-statement")
    await pg.evaluate("scrollTo(0, 0)")
    # ask a suggested question (pre-warmed: instant) and wait for the citations
    q = EN if lang == "en" else ES
    await pg.fill("#ask-q-hero", q)
    await pg.press("#ask-q-hero", "Enter")
    await pg.wait_for_selector(".ask-steps", timeout=5000)
    await shot("03-steps")
    await pg.wait_for_selector(".ask-law-btn", timeout=30000)
    await pg.wait_for_timeout(1600)
    await pg.evaluate("scrollTo(0, 0)")
    await pg.wait_for_timeout(200)
    await shot("04-answer")
    await pg.click(".ask-law-btn")
    await pg.wait_for_timeout(1200)
    await shot("05-law-open", full=True)
    # a refusal: out of scope place
    await pg.fill("#ask-q-dock", "Can my landlord raise the rent 10% in Chicago?")
    await pg.press("#ask-q-dock", "Enter")
    await pg.wait_for_selector(".ask-turn:nth-child(2) .ask-a:not(.is-partial)", timeout=30000)
    await pg.wait_for_timeout(1400)
    await shot("06-refusal")
    await ctx.close()


async def main():
    problems = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--disable-gpu"])
        await run(b, 1440, 900, "en", problems)
        await run(b, 390, 844, "en", problems)
        await run(b, 1440, 900, "es", problems)
        await run(b, 390, 844, "es", problems, reduced=True)
        await b.close()
    for x in problems:
        print("PROBLEM", x)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    asyncio.run(main())
