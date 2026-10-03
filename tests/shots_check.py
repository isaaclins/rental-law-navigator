"""Playwright QA screenshots for the rent-increase check (#40), desktop 1440 + mobile 390, English and Spanish.

Server: uv run uvicorn web.app:app --port 8811
Run:    uv run --with playwright python tests/shots_check.py   (PNGs -> $SHOTS_DIR)
Fails on console errors or horizontal overflow.
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8811/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/check")
os.makedirs(OUT, exist_ok=True)


async def run(b, w, h, lang, problems):
    tag = f"{'d' if w > 500 else 'm'}-{lang}"
    ctx = await b.new_context(
        viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1
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

    async def fill(sel, v):
        await pg.fill(sel, v)

    # entry point on the address page
    await pg.goto(BASE + "#/a/A0001")
    await pg.wait_for_selector("a.ck-entry", state="attached")
    await pg.evaluate("""() => { const a = document.querySelector('a.ck-entry'); a.closest('details')?.setAttribute('open', '');
        a.scrollIntoView({block: 'center'}); }""")
    await pg.wait_for_timeout(400)
    await shot("01-entry")

    # LA RSO building: 5% increase against the 3% cap, plus deposit, fee and a no-reason notice
    await pg.click("a.ck-entry")
    await pg.wait_for_selector(".ck-form")
    await pg.wait_for_timeout(300)
    await shot("02-form")
    await fill("#ck-current_rent", "2000")
    await fill("#ck-new", "2100")
    await fill("#ck-notice_date", "2026-02-20")
    await fill("#ck-effective_date", "2026-03-15")
    await pg.click(".ck-more > summary")
    await fill("#ck-deposit", "4000")
    await fill("#ck-application_fee", "80")
    await pg.select_option("#ck-termination", "no_reason")
    await pg.click(".ck-actions .btn")
    await pg.wait_for_selector(".ck-v")
    await pg.evaluate(
        "document.querySelector('.ck-v').open = true; document.querySelector('.ck-result').scrollIntoView()"
    )
    await pg.wait_for_timeout(300)
    await shot("03-la-result")
    await shot("04-la-full", full=True)

    # AB 1482 building, CPI unknown -> can't tell
    await pg.goto(BASE + "#/check/A0023")
    await pg.wait_for_selector(".ck-form")
    await fill("#ck-current_rent", "1800")
    await fill("#ck-new", "4%")
    await fill("#ck-notice_date", "2026-09-01")
    await fill("#ck-effective_date", "2026-10-15")
    await pg.click(".ck-actions .btn")
    await pg.wait_for_selector(".ck-v")
    await pg.evaluate(
        "document.querySelector('.ck-v').open = true; document.querySelector('.ck-result').scrollIntoView()"
    )
    await pg.wait_for_timeout(300)
    await shot("05-ab1482-cpi")

    # new construction: no cap applies
    await pg.goto(BASE + "#/check/A0022")
    await pg.wait_for_selector(".ck-form")
    await fill("#ck-current_rent", "3000")
    await fill("#ck-new", "3300")
    await fill("#ck-notice_date", "2026-09-01")
    await fill("#ck-effective_date", "2026-10-15")
    await pg.click(".ck-actions .btn")
    await pg.wait_for_selector(".ck-v")
    await pg.evaluate(
        "document.querySelector('.ck-v').open = true; document.querySelector('.ck-result').scrollIntoView()"
    )
    await pg.wait_for_timeout(300)
    await shot("06-exempt")

    # San Francisco, notice too short
    await pg.goto(BASE + "#/check/A0016")
    await pg.wait_for_selector(".ck-form")
    await fill("#ck-current_rent", "3000")
    await fill("#ck-new", "3048")
    await fill("#ck-notice_date", "2026-09-25")
    await fill("#ck-effective_date", "2026-10-15")
    await pg.click(".ck-actions .btn")
    await pg.wait_for_selector(".ck-v")
    await pg.evaluate(
        "document.querySelectorAll('.ck-v')[1].open = true; document.querySelector('.ck-result').scrollIntoView()"
    )
    await pg.wait_for_timeout(300)
    await shot("07-sf-notice")
    await ctx.close()


async def main():
    problems: list[str] = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, h in ((1440, 900), (390, 844)):
            for lang in ("en", "es"):
                await run(b, w, h, lang, problems)
        await b.close()
    print("\n".join(problems) or "no console errors, no horizontal overflow")
    sys.exit(1 if problems else 0)


asyncio.run(main())
