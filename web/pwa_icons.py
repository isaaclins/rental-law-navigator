"""Render the PWA icons (#44) from the § brand mark: uv run --with playwright --with pillow python web/pwa_icons.py
Server must run (for the manifest screenshots): BASE=http://127.0.0.1:8799/ (default). Writes web/static/icons/."""

import asyncio
import io
import os
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

HERE = Path(__file__).parent
OUT = HERE / "static" / "icons"
FONT = (HERE / "static" / "fonts" / "InstrumentSerif-Regular.woff2").as_uri()
BASE = os.environ.get("BASE", "http://127.0.0.1:8799/")

# kind: (canvas px, corner radius as share of size, glyph size as share of size)
#  any      : rounded tile with transparent corners (desktop launchers show it as is)
#  maskable : full bleed, glyph inside the 80% safe circle (Android crops to any shape)
#  apple    : full bleed square, iOS rounds the corners itself
ICONS = [
    ("icon-192.png", 192, 0.3, 0.66),
    ("icon-512.png", 512, 0.3, 0.66),
    ("maskable-192.png", 192, 0, 0.5),
    ("maskable-512.png", 512, 0, 0.5),
    ("apple-touch-icon.png", 180, 0, 0.62),
    ("favicon-32.png", 32, 0.3, 0.74),
]
SHORTCUTS = {
    "shortcut-search.png": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "shortcut-changes.png": '<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>',
}


def tile(size: int, radius: float, glyph: float) -> str:
    return f"""<html><head><style>
@font-face {{ font-family: IS; src: url({FONT}) format('woff2'); }}
html, body {{ margin: 0; background: transparent; }}
.t {{ width: {size}px; height: {size}px; border-radius: {radius * size}px; overflow: hidden; position: relative;
  background: radial-gradient(120% 90% at 22% 12%, #1d4c9e 0%, #0a3a8c 28%, #002664 62%, #001a47 100%); }}
.t::after {{ content: ""; position: absolute; inset: 0; border-radius: inherit; display: {"block" if radius else "none"};
  box-shadow: inset 0 {size * 0.012}px {size * 0.02}px rgb(255 255 255 / .14); }}
.g {{ position: absolute; inset: 0; display: grid; place-items: center; color: #fff;
  font: 400 {glyph * size}px/1 IS; padding-bottom: {glyph * size * 0.06}px; box-sizing: border-box; }}
</style></head><body><div class="t"><div class="g">§</div></div></body></html>"""


def shortcut(paths: str) -> str:
    return f"""<html><body style="margin:0;background:transparent">
<div style="width:96px;height:96px;border-radius:30px;background:#eef2f9;display:grid;place-items:center">
<svg viewBox="0 0 24 24" width="52" height="52" fill="none" stroke="#002664" stroke-width="1.9"
 stroke-linecap="round" stroke-linejoin="round">{paths}</svg></div></body></html>"""


def save(png: bytes, name: str, size: int) -> None:
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    if im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    if name.startswith(("apple", "maskable")):
        im = im.convert("RGB")  # no alpha: iOS/Android would show black corners
    im.save(OUT / name, optimize=True)


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 600, "height": 600}, device_scale_factor=2)
        for name, size, radius, glyph in ICONS:
            # render at 2x and downsample: crisper glyph edges than a 1x render
            await pg.set_content(tile(size, radius, glyph))
            await pg.evaluate("document.fonts.ready")
            png = await pg.locator(".t").screenshot(omit_background=True)
            save(png, name, size)
        for name, paths in SHORTCUTS.items():
            await pg.set_content(shortcut(paths))
            save(await pg.locator("div").screenshot(omit_background=True), name, 96)
        # manifest screenshots (richer install dialog on Android and desktop Chrome)
        for name, w, h, dpr, route in [
            ("screen-narrow.webp", 390, 844, 2, ""),
            ("screen-wide.webp", 1440, 900, 1, ""),
        ]:
            sp = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=dpr)
            await sp.add_init_script(
                "localStorage.setItem('ce.pwa', JSON.stringify({installed: 1}))"
            )
            await sp.goto(BASE + route)
            await sp.wait_for_timeout(1800)
            Image.open(io.BytesIO(await sp.screenshot())).convert("RGB").save(
                OUT / name, "WEBP", quality=82, method=6
            )
            await sp.close()
        await b.close()


asyncio.run(main())
