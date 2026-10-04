"""The 1200x630 link-preview card for a shared answer (#117), drawn with Pillow and cached on disk.

Layout (approved mockup, ~/share/hacknation/ideas/share-answer): the wordmark, the address, the answer in large
Instrument Serif, the citation and "checked" date with "Not legal advice" at the foot; the city's building photo on
the right, on its own stage colour so no image box shows. Fonts: web/static/fonts (Pillow reads the WOFF2 files).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "web" / "static" / "fonts"
IMG = ROOT / "web" / "static" / "img"
CACHE = Path(os.environ.get("SHARE_CARD_CACHE", ROOT / "cache" / "og"))
VERSION = "2"  # bump when the drawing changes: old files are simply not looked up again

W, H = 1200, 630
STAGE = (242, 243, 240)  # --stage: the backdrop of every generated image
INK = (0, 12, 31)
INK2 = (74, 82, 96)
INK3 = (104, 111, 124)
NAVY = (0, 38, 100)
PHOTO_W = 470

_lock = threading.Lock()


def _key(a: dict) -> str:
    raw = "|".join(
        [
            VERSION,
            a["address_id"],
            a["topic"],
            a["as_of"],
            a["lang"],
            a["v"],
            a["image"],
            a["answer"],
        ]
    )
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def cached(a: dict) -> Path | None:
    p = CACHE / f"{_key(a)}.png"
    return p if p.is_file() else None


def _serif(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / "InstrumentSerif-Regular.woff2"), size)


def _sans(size: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / "InterVariable.woff2"), size)
    try:
        f.set_variation_by_axes([min(max(size, 14), 32), weight])  # optical size, weight
    except (OSError, ValueError):
        pass
    return f


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, text: str, width: int, max_lines: int, sizes) -> tuple:
    for s in sizes:
        f = _serif(s)
        lines = _wrap(draw, text, f, width)
        if len(lines) <= max_lines and all(draw.textlength(x, font=f) <= width for x in lines):
            return f, s, lines
    f = _serif(sizes[-1])
    lines = _wrap(draw, text, f, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + " …", font=f) > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
        lines[-1] += " …"
    return f, sizes[-1], lines


def _ellipsize(draw, text: str, font, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text.rstrip(" ·,") + "…"


def _photo(slug: str) -> Image.Image | None:
    for name in (slug, "hero-building-card"):
        p = IMG / f"{name}.webp"
        if p.is_file():
            try:
                return Image.open(p).convert("RGB")
            except OSError:
                continue
    return None


def render(a: dict, fmt_date, t) -> Image.Image:
    lang = a["lang"]
    im = Image.new("RGB", (W, H), STAGE)
    d = ImageDraw.Draw(im)

    # the building, cover-cropped into the right column (object-position 48% 60%, as in the mockup)
    ph = _photo(a["image"])
    if ph is not None:
        scale = max(PHOTO_W / ph.width, H / ph.height) * 1.04
        pw, phh = round(ph.width * scale), round(ph.height * scale)
        ph = ph.resize((pw, phh), Image.LANCZOS)
        x0, y0 = round((pw - PHOTO_W) * 0.48), round((phh - H) * 0.6)
        im.paste(ph.crop((x0, y0, x0 + PHOTO_W, y0 + H)), (W - PHOTO_W, 0))
        # soft fade from the stage colour into the photo, so the column has no hard edge
        fade = (
            Image.linear_gradient("L").rotate(-90).resize((110, H))
        )  # 255 (stage) at the left edge
        im.paste(Image.new("RGB", (110, H), STAGE), (W - PHOTO_W, 0), fade)

    left, right = 64, W - PHOTO_W - 28
    text_w = right - left

    # wordmark: navy round § mark + serif name
    r = 26
    cy = 74
    d.ellipse((left, cy - r, left + 2 * r, cy + r), fill=NAVY)
    sec = _serif(36)
    d.text((left + r, cy + 1), "§", font=sec, fill=(255, 255, 255), anchor="mm")
    d.text((left + 2 * r + 14, cy), "Clause & Effect", font=_serif(40), fill=INK, anchor="lm")

    # address line
    addr_f = _sans(26, 600)
    addr = _ellipsize(
        d, f"{a['street']}, {a['city']}" if a.get("city") else a["street"], addr_f, text_w
    )
    d.text((left, 150), addr, font=addr_f, fill=INK2, anchor="lt")

    # the question (small) and the answer (large serif)
    q_f = _sans(26, 500)
    d.text((left, 196), _ellipsize(d, a["question"], q_f, text_w), font=q_f, fill=INK3, anchor="lt")
    f, size, lines = _fit(d, a["answer"], text_w, 3, range(96, 55, -4))
    y = 246
    lh = round(size * 1.05)
    for line in lines:
        d.text((left, y), line, font=f, fill=INK, anchor="lt")
        y += lh

    # foot: citation, then checked date and not legal advice
    q = a.get("quote") or {}
    cite_f = _sans(22, 600)
    meta_f = _sans(22, 500)
    checked = (q.get("retrieved") or "")[:10]
    if checked and checked == a["as_of"]:
        when = t("checked_card", lang).replace("{d}", fmt_date(checked, lang))
    else:  # an answer for another date says which date it answers for
        when = t("asof_card", lang).replace("{d}", fmt_date(a["as_of"], lang))
    foot2 = f"{when} · {t('nla_card', lang)}"
    if q.get("citation"):
        d.text(
            (left, H - 92),
            _ellipsize(d, q["citation"], cite_f, text_w),
            font=cite_f,
            fill=INK2,
            anchor="lt",
        )
    d.text(
        (left, H - 58), _ellipsize(d, foot2, meta_f, text_w), font=meta_f, fill=INK3, anchor="lt"
    )
    # a thin navy rule above the foot, the page's quote rule in miniature
    d.rectangle((left, H - 122, left + 44, H - 119), fill=NAVY)
    return im


def render_cached(a: dict, fmt_date, t) -> Path:
    """Render once per answer; a lock keeps renders one at a time (they take ~100 ms)."""
    with _lock:
        p = cached(a)
        if p:
            return p
        CACHE.mkdir(parents=True, exist_ok=True)
        im = render(a, fmt_date, t)
        # 256 colours keep the file small for WhatsApp (< 300 kB) and still look like the photo
        out = im.quantize(
            colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG
        )
        fd, tmp = tempfile.mkstemp(dir=CACHE, suffix=".tmp")
        os.close(fd)
        out.save(tmp, "PNG", optimize=True)
        p = CACHE / f"{_key(a)}.png"
        os.replace(tmp, p)
        return p
