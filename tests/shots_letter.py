"""Playwright QA screenshots for the letter to the landlord (#122): desktop 1440 + mobile 390, EN and ES, the print
preview (Chromium's print PDF, rendered to PNG) and the PDF the page generates itself.

Server: uv run uvicorn web.app:app --port 8802
Run:    uv run --with playwright python tests/shots_letter.py   (PNGs -> $SHOTS_DIR)
Fails on console errors or horizontal overflow. Extra widths: WIDTHS=320,2560.
"""

import asyncio
import os
import subprocess
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8802/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/letter")
os.makedirs(OUT, exist_ok=True)


def png(pdf: str, name: str) -> None:
    subprocess.run(
        ["pdftoppm", "-png", "-r", "80", "-singlefile", pdf, f"{OUT}/{name}"], check=True
    )
    os.remove(pdf)
    print("saved", f"{name}.png")


async def run(b, w, h, lang, problems, full=True):
    tag = f"{'d' if w > 640 else 'm'}{w}-{lang}"
    ctx = await b.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=2 if w < 500 else 1,
        accept_downloads=True,
        is_mobile=w < 500,
        has_touch=w < 500,
    )
    await ctx.add_init_script(f"localStorage.setItem('lang', '{lang}');")
    if w < 500:  # headless Chromium has no share sheet; phones do
        await ctx.add_init_script("navigator.share = navigator.share || (async () => {});")
    pg = await ctx.new_page()
    pg.on(
        "console",
        lambda m: problems.append(f"{tag} console: {m.text}") if m.type == "error" else None,
    )
    pg.on("pageerror", lambda e: problems.append(f"{tag} pageerror: {e}"))

    async def shot(name, full_page=False):
        over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
        if over > 0:
            problems.append(f"{tag}-{name}: horizontal overflow {over}px")
        clipped = await pg.evaluate("""() => [...document.querySelectorAll('.lt-view *, .lt-cta *')]
            .filter((e) => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'visible'
                     && !['INPUT'].includes(e.tagName)).map((e) => e.className).slice(0, 5)""")
        if clipped:
            problems.append(f"{tag}-{name}: clipped {clipped}")
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full_page)
        print("saved", f"{tag}-{name}.png")

    await pg.goto(BASE + "#/check/A0027")
    await pg.wait_for_selector(".ck-form")
    await pg.fill("#ck-current_rent", "2400")
    await pg.fill("#ck-new", "2520")
    await pg.fill("#ck-notice_date", "2026-09-20")
    await pg.fill("#ck-effective_date", "2026-11-01")
    await pg.click(".ck-actions .btn")
    await pg.wait_for_selector(".lt-go")
    await pg.wait_for_timeout(1900)
    await pg.evaluate(
        "document.querySelector('.ck-hero').scrollIntoView({block: 'start'}); scrollBy(0, -90)"
    )
    await pg.wait_for_timeout(300)
    await shot("01-cta")

    await pg.click(".lt-go")
    await pg.wait_for_selector(".lt-sheet .lt-in")
    await pg.wait_for_timeout(250)
    await shot("02-writing-in")
    await pg.wait_for_timeout(1500)
    await shot("03-letter", full_page=full)

    # the reader fills the fields; the same field fills everywhere it appears
    await pg.fill('.lt-f[data-f="name"] >> nth=0', "Maria Lopez")
    await pg.fill('.lt-f[data-f="unit"]', "Apt 3")
    await pg.fill('.lt-f[data-f="landlord"]', "Mr. Chen")
    both = await pg.evaluate(
        "[...document.querySelectorAll('.lt-f[data-f=name]')].map((e) => e.value)"
    )
    if both != ["Maria Lopez", "Maria Lopez"]:
        problems.append(f"{tag}: name fields not in sync: {both}")
    await shot("04-filled", full_page=full)

    other = "es" if lang == "en" else "en"
    await pg.click(f'.lt-seg button[data-ll="{other}"]')
    await pg.wait_for_timeout(1500)
    await shot(f"05-letter-in-{other}", full_page=full)
    await pg.click(f'.lt-seg button[data-ll="{lang}"]')
    await pg.wait_for_timeout(1200)

    if w == 1440:
        # print preview: Chromium's print PDF with the print stylesheet
        await pg.emulate_media(media="print")
        await pg.pdf(path=f"{OUT}/{tag}-print.pdf", format="Letter")
        png(f"{OUT}/{tag}-print.pdf", f"{tag}-06-print-letter")
        await pg.pdf(path=f"{OUT}/{tag}-print-a4.pdf", format="A4")
        png(f"{OUT}/{tag}-print-a4.pdf", f"{tag}-06-print-a4")
        await pg.emulate_media(media="screen")
        # the PDF the page writes itself (Download PDF)
        async with pg.expect_download() as dl:
            await pg.click(".lt-acts-d [data-act=pdf]")
        d = await dl.value
        path = f"{OUT}/{tag}-download.pdf"
        await d.save_as(path)
        print("download", d.suggested_filename)
        png(path, f"{tag}-07-pdf-download")
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
