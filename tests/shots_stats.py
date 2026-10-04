"""Playwright QA for "Protections over time" on #/changes: desktop 1440 + mobile 390, English and Spanish.

Server: uv run uvicorn web.app:app --port 8814
Run:    uv run --with playwright python tests/shots_stats.py   (PNGs -> $SHOTS_DIR; BROWSER=webkit for WebKit)
Fails on console errors, horizontal overflow, a tooltip that does not open on tap, or an as-of line that does not move.
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8814/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/stats")
BROWSER = os.environ.get("BROWSER", "chromium")
os.makedirs(OUT, exist_ok=True)

NOW_X = "() => getComputedStyle(document.querySelector('.pt-row[data-p=algorithmic_ban] .pt-now')).transform"
VAL = "(p) => document.querySelector(`.pt-row[data-p=${p}] [data-val] b`).textContent"


async def run(b, w, h, lang, problems):
    tag = f"{'d' if w > 500 else 'm'}-{lang}" + ("" if BROWSER == "chromium" else f"-{BROWSER}")
    mobile = w < 500
    ctx = await b.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=2 if mobile else 1,
        has_touch=mobile,
        is_mobile=mobile and BROWSER == "chromium",
    )
    await ctx.add_init_script(f"localStorage.setItem('lang', '{lang}'); sessionStorage.clear();")
    pg = await ctx.new_page()
    pg.on(
        "console",
        lambda m: problems.append(f"{tag} console: {m.text}") if m.type == "error" else None,
    )
    pg.on("pageerror", lambda e: problems.append(f"{tag} pageerror: {e}"))
    await pg.goto(BASE + "#/changes")
    await pg.wait_for_selector(".pt .pt-row svg")
    # top of the page as a visitor lands on it
    await pg.screenshot(path=f"{OUT}/{tag}-1-landing.png")
    sec = pg.locator(".pt")
    await sec.scroll_into_view_if_needed()
    await pg.wait_for_timeout(2200)  # the lines draw once
    await sec.screenshot(path=f"{OUT}/{tag}-2-chart.png")
    if await pg.evaluate("document.documentElement.scrollWidth > innerWidth"):
        problems.append(f"{tag}: horizontal overflow")
    if await pg.evaluate(VAL, "algorithmic_ban") != "7":
        problems.append(f"{tag}: algorithmic readout on 2026-10-01 is not 7")

    # tap the 2026-01-01 step of the algorithmic row (CA AB 325)
    hit = pg.locator(".pt-row[data-p=algorithmic_ban] .pt-hit[data-dates*='2026-01-01']")
    if mobile:
        await hit.tap()
    else:
        await hit.click()
    await pg.wait_for_timeout(200)
    tip = pg.locator(".pt-tip")
    if not await tip.is_visible():
        problems.append(f"{tag}: tooltip did not open")
    else:
        txt = await tip.inner_text()
        if "AB 325" not in txt:
            problems.append(f"{tag}: tooltip lacks AB 325: {txt[:120]}")
        box, vb = await tip.bounding_box(), pg.viewport_size
        if box["x"] < 0 or box["x"] + box["width"] > vb["width"] + 1:
            problems.append(f"{tag}: tooltip off screen {box}")
    await sec.screenshot(path=f"{OUT}/{tag}-3-tooltip.png")

    # "See the answers on Jan 1, 2026": CE.setAsOf re-renders the page; the line must move there
    before = await pg.evaluate(NOW_X)
    await pg.locator(".pt-tip [data-go='2026-01-01']").click()
    await pg.wait_for_timeout(900)
    if await pg.evaluate("CE.asOf()") != "2026-01-01":
        problems.append(f"{tag}: as-of not set by the tooltip button")
    after = await pg.evaluate(NOW_X)
    if after == before:
        problems.append(f"{tag}: as-of line did not move ({before})")
    if await pg.evaluate(VAL, "algorithmic_ban") != "7":
        problems.append(f"{tag}: readout on 2026-01-01 is not 7")

    # the page's own date slider (silent as-of change): line and readouts follow
    await pg.evaluate("CE.setAsOf('2025-03-01')")
    await pg.wait_for_timeout(900)
    await pg.locator(".pt").scroll_into_view_if_needed()
    if await pg.evaluate(VAL, "algorithmic_ban") != "1":
        problems.append(f"{tag}: readout on 2025-03-01 is not 1")
    if await pg.evaluate(NOW_X) == after:
        problems.append(f"{tag}: as-of line did not move to 2025-03-01")
    await pg.locator(".pt").screenshot(path=f"{OUT}/{tag}-4-asof-2025.png")

    # tap on a line away from a step: sets the as-of date there
    plot = pg.locator(".pt-row[data-p=deposit_cap] .pt-plot")
    pb = await plot.bounding_box()
    x = (pb["width"] - 44) * 5.5 / 9  # mid-2024 on the 2019-2027 axis (44 px "Not law" column)
    if mobile:
        await plot.tap(position={"x": x, "y": pb["height"] / 2})
    else:
        await plot.click(position={"x": x, "y": pb["height"] / 2})
    await pg.wait_for_timeout(900)
    got = await pg.evaluate("CE.asOf()")
    if not got.startswith("2024"):
        problems.append(f"{tag}: tap on the line set as-of to {got}, expected 2024")
    # (the shared header's own width is not this feature's: check the chart section)
    if await pg.evaluate(
        "document.querySelector('.pt').getBoundingClientRect().right > innerWidth"
    ):
        problems.append(f"{tag}: chart wider than the screen after as-of changes")
    await ctx.close()


async def main():
    problems: list[str] = []
    async with async_playwright() as p:
        b = await getattr(p, BROWSER).launch()
        for w, h in ((1440, 900), (390, 844)):
            for lang in ("en", "es"):
                await run(b, w, h, lang, problems)
        await b.close()
    for x in problems:
        print("PROBLEM", x)
    print("shots in", OUT)
    sys.exit(1 if problems else 0)


asyncio.run(main())
