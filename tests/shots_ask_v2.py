"""Playwright transcripts of Ask conversations (#101 v2): multi-turn, Spanish, urgent. Desktop 1440 and phone 390.

Server: uv run uvicorn web.app:app --port 8799
Run:    uv run --with playwright python tests/shots_ask_v2.py   (PNGs -> $SHOTS_DIR)
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8799/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/ask/v2")
os.makedirs(OUT, exist_ok=True)
CONVS = {
    "1-deposit": (
        "en",
        1440,
        [
            "How much deposit can they ask for?",
            "@California",
            "and if it's a duplex?",
            "what should I tell my landlord?",
        ],
    ),
    "2-spanish": (
        "es",
        390,
        [
            "¿Cuánto depósito me pueden pedir?",
            "@Nueva Jersey",
            "¿y si el casero no me lo devuelve?",
        ],
    ),
    "3-urgent": (
        "en",
        390,
        [
            "I got an eviction notice that says I have to leave by October 10. I live in Los Angeles.",
            "what should I do?",
        ],
    ),
}


async def run(b, name, lang, w, turns, problems):
    ctx = await b.new_context(
        viewport={"width": w, "height": 900 if w > 500 else 844},
        device_scale_factor=1 if w > 500 else 2,
    )
    await ctx.add_init_script(f"localStorage.setItem('lang', '{lang}');")
    pg = await ctx.new_page()
    pg.on(
        "console",
        lambda m: problems.append(f"{name} console: {m.text}") if m.type == "error" else None,
    )
    pg.on("pageerror", lambda e: problems.append(f"{name} pageerror: {e}"))
    await pg.goto(BASE + "#/ask")
    await pg.wait_for_selector(".ask-chip")
    for i, t in enumerate(turns):
        n = await pg.locator(".ask-turn .ask-a:not(.is-partial)").count()
        if t.startswith("@"):  # tap a quick reply
            await pg.locator(".ask-quick .ask-chip", has_text=t[1:]).last.click()
        else:
            sel = "#ask-q-hero" if i == 0 else "#ask-q-dock"
            await pg.fill(sel, t)
            await pg.press(sel, "Enter")
        await pg.wait_for_function(
            f"document.querySelectorAll('.ask-turn .ask-a:not(.is-partial)').length > {n}",
            timeout=45000,
        )
        await pg.wait_for_timeout(1500)
    await pg.wait_for_timeout(6000)  # the checked follow-up chips arrive
    law = pg.locator(".ask-law-btn").last
    if await law.count():
        await law.click()
        await pg.wait_for_timeout(900)
    over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
    if over > 0:
        problems.append(f"{name}: horizontal overflow {over}px")
    await pg.evaluate(
        "scrollTo(0, 0); document.querySelector('.ask-dock')?.style.setProperty('display', 'none'); document.querySelector('.tabs')?.style.setProperty('display', 'none')"
    )
    await pg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    print("saved", name)
    await ctx.close()


async def main():
    problems = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--disable-gpu"])
        for name, (lang, w, turns) in CONVS.items():
            await run(b, name, lang, w, turns, problems)
        await b.close()
    for x in problems:
        print("PROBLEM", x)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    asyncio.run(main())
