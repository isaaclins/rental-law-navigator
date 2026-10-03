"""Screenshot the running web app: uv run --with playwright python web/screenshot.py name=#/route[@width][!lang] ...
Server must run on 127.0.0.1:8765. PNGs go to $SHOTS_DIR (default ../screenshots)."""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8765/")
OUT = os.environ.get(
    "SHOTS_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "screenshots")
)
os.makedirs(OUT, exist_ok=True)
shots = [(a.split("=")[0], a.split("=", 1)[1]) for a in sys.argv[1:]]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, spec in shots:
            spec, _, lng = spec.partition("!")
            path, _, w = spec.partition("@")
            width = int(w or 1440)
            pg = await b.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
            msgs = []
            pg.on(
                "console",
                lambda m, msgs=msgs: (
                    msgs.append(m.text) if m.type in ("error", "warning") else None
                ),
            )
            pg.on("pageerror", lambda e, msgs=msgs: msgs.append("PAGEERROR " + str(e)))
            if lng:
                await pg.add_init_script(f"localStorage.setItem('lang','{lng}')")
            await pg.goto(BASE + path)
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
            print(name, "errors:", msgs)
            await pg.close()
        await b.close()


asyncio.run(main())
