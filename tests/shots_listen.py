"""Playwright QA for Listen (#49): plays at once as a renter, the panel's I rent / I own switch, playback controls, chapter highlighting and "Explain this",
desktop 1440 + mobile 390, English and Spanish.

Server (no ElevenLabs spend: an empty budget and a sandbox cache with test tones for the briefings below):
    NAVIGATOR_TTS_DIR=/tmp/l2tts NAVIGATOR_TTS_BUDGET=0 uv run uvicorn web.app:app --port 8813
Run:    uv run --with playwright python tests/shots_listen.py   (PNGs -> $SHOTS_DIR)
Fails on console errors, horizontal overflow or a missing state.
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8813/")
OUT = os.environ.get("SHOTS_DIR", "/home/steward/share/hacknation/qa/listen2")
os.makedirs(OUT, exist_ok=True)
ADDR = {"en": "A0001", "es": "A0065"}


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

    def need(ok, what):
        if not ok:
            problems.append(f"{tag}: {what}")

    async def shot(name, full=False):
        over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
        need(over <= 0, f"{name}: horizontal overflow {over}px")
        await pg.screenshot(path=f"{OUT}/{tag}-{name}.png", full_page=full)
        print("saved", f"{tag}-{name}.png")

    async def label():
        return (await pg.inner_text(".ce-l-main")).strip()

    await pg.goto(BASE + f"#/a/{ADDR[lang]}")
    await pg.wait_for_selector(".ce-l-main")
    await pg.evaluate("document.querySelector('.ce-listen').scrollIntoView({block: 'center'})")
    await shot("01-idle")

    # first Listen: plays at once as a renter; the transcript panel has the I rent / I own switch
    await pg.click(".ce-l-main")
    await pg.wait_for_selector(".ce-cap .ce-seg-b")
    need(await pg.locator(".ce-cap .ce-seg-b").count() == 2, "two persona options in the panel")
    need(await pg.locator(".ce-listen .ce-seg-b").count() == 0, "no choice next to the button")
    await shot("02-panel")
    await pg.wait_for_function(
        "document.querySelector('.ce-l-main').innerText.match(/Pause|Pausa/)"
    )
    need(await pg.evaluate("localStorage.getItem('ce.listen.persona')") == "renter", "persona kept")
    await pg.wait_for_selector(
        'details.topic.is-speaking[data-cat="rent_increase_limits"]', timeout=12000
    )
    await pg.evaluate(
        "document.querySelector('details.topic.is-speaking').scrollIntoView({block: 'center'})"
    )
    await shot("03-speaking-rent")

    # 1x -> 1.25x, pause, resume
    await pg.click(".ce-cap .ce-speed")
    need((await pg.inner_text(".ce-cap .ce-speed")).strip() == "1.25×", "speed toggles to 1.25x")
    await pg.click(".ce-l-main")
    need(await label() in ("Resume", "Continuar"), "pause")
    await pg.evaluate("document.querySelector('.ce-listen').scrollIntoView({block: 'center'})")
    await shot("04-paused")
    await pg.click(".ce-l-main")
    need(await label() in ("Pause", "Pausa"), "resume")

    # the next chapter (eviction) gets the highlight as the audio moves on
    await pg.wait_for_selector(
        'details.topic.is-speaking[data-cat="just_cause_eviction"]', timeout=40000
    )
    need(await pg.locator("details.topic.is-speaking").count() == 1, "one topic highlighted")

    # Esc stops everything
    await pg.keyboard.press("Escape")
    need(await pg.locator("details.topic.is-speaking").count() == 0, "Esc clears the highlight")
    need(await label() in ("Listen", "Escuchar"), "Esc stops")
    need(await pg.locator(".ce-speed").count() == 0, "controls hide when stopped")

    # "Explain this" in an opened topic plays only that topic
    await pg.evaluate(
        "document.querySelector('details.topic[data-cat=\"just_cause_eviction\"]').open = true"
    )
    x = pg.locator('.ce-explain[data-cat="just_cause_eviction"]')
    await x.wait_for()
    await x.scroll_into_view_if_needed()
    await x.click()
    await pg.wait_for_selector(
        'details.topic.is-speaking[data-cat="just_cause_eviction"]', timeout=8000
    )
    await pg.evaluate(
        "document.querySelector('details.topic[data-cat=\"just_cause_eviction\"] .topic-actions').scrollIntoView({block: 'center'})"
    )
    await shot("05-explain")
    await pg.keyboard.press("Escape")

    # the owner briefing (desktop English) and the browser-voice fallback (no audio cached: A0016)
    if lang == "en" and w > 500:
        await pg.click(".ce-l-main")
        await pg.click('.ce-cap [data-ce-who="owner"]')
        await pg.wait_for_function("document.querySelector('.ce-l-main').innerText.match(/Pause/)")
        await pg.evaluate("document.querySelector('.ce-listen').scrollIntoView({block: 'center'})")
        await shot("06-owner-playing")
        await pg.keyboard.press("Escape")
    await pg.goto(BASE + "#/a/A0016")
    await pg.wait_for_selector(".ce-l-main")
    await pg.click(".ce-l-main")  # persona remembered: plays (or falls back) right away
    await pg.wait_for_timeout(1500)
    await pg.keyboard.press("Escape")
    await ctx.close()


async def main():
    problems: list[str] = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        for w, h in ((1440, 900), (390, 844)):
            for lang in ("en", "es"):
                await run(b, w, h, lang, problems)
        await b.close()
    print("\n".join(problems) or "no problems")
    sys.exit(1 if problems else 0)


asyncio.run(main())
