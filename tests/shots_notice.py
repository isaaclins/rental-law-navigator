"""Playwright QA screenshots for the rent-increase notice (#96): desktop 1440 + mobile 390, EN and ES, an amount over
the cap (the draft turns red), a saved property of the demo landlord, the print preview and the generated PDF.

Server: uv run uvicorn web.app:app --port 8802
Run:    uv run --with playwright python tests/shots_notice.py   (PNGs -> $SHOTS_DIR)
Fails on console errors or horizontal overflow. Extra widths: WIDTHS=320,2560.
"""

import asyncio
import os
import subprocess
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8802/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/notice")
os.makedirs(OUT, exist_ok=True)


def png(pdf: str, name: str) -> None:
    subprocess.run(
        ["pdftoppm", "-png", "-r", "80", "-singlefile", pdf, f"{OUT}/{name}"], check=True
    )
    os.remove(pdf)
    print("saved", f"{name}.png")


async def run(b, w, h, lang, problems):
    tag = f"{'d' if w > 640 else 'm'}{w}-{lang}"
    ctx = await b.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=2 if w < 500 else 1,
        accept_downloads=True,
        is_mobile=w < 500,
        has_touch=w < 500,
    )
    await ctx.add_init_script(f"localStorage.setItem('lang', '{lang}');")
    if w < 500:
        await ctx.add_init_script("navigator.share = navigator.share || (async () => {});")
    pg = await ctx.new_page()
    pg.on(
        "console",
        lambda m: problems.append(f"{tag} console: {m.text}") if m.type == "error" else None,
    )
    pg.on("pageerror", lambda e: problems.append(f"{tag} pageerror: {e}"))

    async def shot(name, full_page=True):
        over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
        if over > 0:
            problems.append(f"{tag}-{name}: horizontal overflow {over}px")
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full_page)
        print("saved", f"{tag}-{name}.png")

    await pg.goto(BASE + "#/notice/A0027?rent=2400&last=2026-01-01")
    await pg.wait_for_selector(".lt-sheet .lt-in")
    await pg.wait_for_timeout(250)
    await shot("01-writing-in", full_page=False)
    await pg.wait_for_timeout(1600)
    await shot("02-notice")
    await pg.fill('.lt-f[data-f="tenant"]', "Maria Lopez")
    await pg.fill('.lt-f[data-f="unit"]', "Apt 3")
    await pg.fill('.lt-f[data-f="owner"]', "Fulton Street LLC")
    await pg.fill('.nt-row input[name="new"]', "2500")
    await pg.wait_for_selector(".lt-sheet.is-over")
    await pg.wait_for_timeout(500)
    await shot("03-over-the-cap")
    await pg.fill('.nt-row input[name="new"]', "")
    await pg.wait_for_function("!document.querySelector('.lt-sheet').classList.contains('is-over')")
    other = "es" if lang == "en" else "en"
    await pg.click(f'.lt-seg button[data-ll="{other}"]')
    await pg.wait_for_timeout(1400)
    await shot(f"04-notice-in-{other}")
    await pg.click(f'.lt-seg button[data-ll="{lang}"]')
    await pg.wait_for_timeout(900)
    if w == 1440:
        await pg.emulate_media(media="print")
        await pg.pdf(path=f"{OUT}/{tag}-print.pdf", format="Letter")
        png(f"{OUT}/{tag}-print.pdf", f"{tag}-05-print")
        await pg.emulate_media(media="screen")
        async with pg.expect_download() as dl:
            await pg.click(".lt-acts-d [data-act=pdf]")
        d = await dl.value
        await d.save_as(f"{OUT}/{tag}-download.pdf")
        print("download", d.suggested_filename)
        png(f"{OUT}/{tag}-download.pdf", f"{tag}-06-pdf-download")
    # a saved property of the demo landlord
    await pg.request.post(BASE + "auth/demo")
    props = (await (await pg.request.get(BASE + "api/properties")).json())["properties"]
    await pg.goto(BASE + f"#/notice/p{props[0]['id']}?rent=2000&last=2025-11-01")
    await pg.reload()
    await pg.wait_for_selector(".lt-sheet .lt-in")
    await pg.wait_for_timeout(1600)
    await shot("07-saved-property")
    await ctx.close()


async def main():
    problems = []
    widths = [int(x) for x in os.environ.get("WIDTHS", "1440,390").split(",")]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in widths:
            for lang in ("en", "es") if w in (1440, 390) else ("en",):
                await run(b, w, 900 if w > 640 else 844, lang, problems)
        await b.close()
    for x in problems:
        print("PROBLEM", x)
    sys.exit(1 if problems else 0)


asyncio.run(main())
