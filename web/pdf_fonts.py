"""Build the fonts the browser embeds in the letter and notice PDFs (features/paper.js).

    uv run --no-project --with fonttools --with brotli --with uharfbuzz --with skia-pathops python -m web.pdf_fonts

From the site's own fonts (web/static/fonts, OFL): Inter 400 and 600 (static instances of InterVariable, tabular
figures frozen in so amounts line up) and Instrument Serif. Each is cut to the WinAnsi characters (Latin-1 plus
the curly quotes and dashes, enough for English and Spanish), hinting dropped, then zlib-compressed so the PDF can
carry it as is (/FlateDecode). metrics.json has, per font, the advance widths of the 256 WinAnsi codes (1/1000 em),
the kerning pairs Inter and Instrument Serif define for those characters, and the descriptor values the PDF needs.
Output: web/static/fonts/pdf/<name>.ttf.z + metrics.json (loaded only when someone makes a PDF).
"""

from __future__ import annotations

import io
import json
import zlib
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

SRC = Path(__file__).parent / "static" / "fonts"
OUT = SRC / "pdf"
FONTS = {
    "Inter-Regular": ("InterVariable.woff2", {"wght": 400, "opsz": 14}),
    "Inter-SemiBold": ("InterVariable.woff2", {"wght": 600, "opsz": 14}),
    "InstrumentSerif-Regular": ("InstrumentSerif-Regular.woff2", None),
}


def winansi() -> dict[int, str]:
    """WinAnsi code -> character (cp1252; its five holes stay empty)."""
    out = {}
    for c in range(32, 256):
        try:
            out[c] = bytes([c]).decode("cp1252")
        except UnicodeDecodeError:
            pass
    out.pop(0x7F, None)
    out[0xA0] = " "
    out[0xAD] = "­"
    return out


def freeze(font: TTFont, feature: str) -> None:
    """Apply a feature's single substitutions for the digits to the cmap (tabular figures)."""
    gsub = font["GSUB"].table
    idx = {
        i
        for fr in gsub.FeatureList.FeatureRecord
        if fr.FeatureTag == feature
        for i in fr.Feature.LookupListIndex
    }
    sub = {}
    for i in idx:
        for st in gsub.LookupList.Lookup[i].SubTable:
            if st.LookupType == 7:
                st = st.ExtSubTable
            if hasattr(st, "mapping"):
                sub.update(st.mapping)
    for t in font["cmap"].tables:
        for cp, g in list(t.cmap.items()):
            if (
                g in sub and chr(cp).isdigit()
            ):  # the figures only (Inter's tnum also widens - + : etc.)
                t.cmap[cp] = sub[g]


def kerning(data: bytes, chars: list[str], upem: int) -> dict[str, int]:
    """Pair adjustments (1/1000 em) by shaping each pair with HarfBuzz: advance of 'ab' minus a + b."""
    face = hb.Face(data)
    font = hb.Font(face)

    def adv(s: str) -> int:
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"kern": True, "liga": False, "calt": False, "tnum": False})
        return sum(p.x_advance for p in buf.glyph_positions)

    single = {c: adv(c) for c in chars}
    out = {}
    for a in chars:
        for b in chars:
            k = adv(a + b) - single[a] - single[b]
            k = round(k * 1000 / upem)
            if abs(k) >= 4:
                out[a + b] = k
    return out


def build() -> None:
    OUT.mkdir(exist_ok=True)
    enc = winansi()
    metrics = {}
    for name, (src, axes) in FONTS.items():
        font = TTFont(SRC / src)
        if axes:
            font = instancer.instantiateVariableFont(
                font, axes, overlap=instancer.OverlapMode.REMOVE
            )
            freeze(font, "tnum")
        font.flavor = None
        buf = io.BytesIO()
        font.save(buf)
        full = buf.getvalue()
        upem = font["head"].unitsPerEm
        # kerning between the letters, digits and punctuation a letter uses (not every Latin-1 pair)
        kchars = [chr(c) for c in range(33, 127)] + list("áéíóúñÁÉÍÓÚÑü¿¡“”‘’–—…×§")
        kern = kerning(full, kchars, upem)

        opts = subset.Options()
        opts.layout_features = []
        opts.hinting = False
        opts.desubroutinize = True
        opts.name_IDs = [0, 1, 2, 3, 4, 5, 6]
        opts.notdef_outline = True
        opts.drop_tables += ["GSUB", "GPOS", "GDEF", "STAT", "DSIG", "meta"]
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=[ord(ch) for ch in enc.values()])
        sub.subset(font)
        buf = io.BytesIO()
        font.save(buf)
        ttf = buf.getvalue()
        (OUT / f"{name}.ttf.z").write_bytes(zlib.compress(ttf, 9))

        cmap = font.getBestCmap()
        hmtx = font["hmtx"]
        widths = [0] * 256
        for code, ch in enc.items():
            g = cmap.get(ord(ch))
            widths[code] = round(hmtx[g][0] * 1000 / upem) if g else 0
        os2, head, post = font["OS/2"], font["head"], font["post"]
        sc = 1000 / upem
        serif = name.startswith("Instrument")
        metrics[name] = {
            "file": f"{name}.ttf.z",
            "length1": len(ttf),
            "widths": widths,
            "kern": kern,
            "ascent": round(os2.sTypoAscender * sc),
            "descent": round(os2.sTypoDescender * sc),
            "capHeight": round(getattr(os2, "sCapHeight", 700) * sc),
            "xHeight": round(getattr(os2, "sxHeight", 500) * sc),
            "bbox": [round(v * sc) for v in (head.xMin, head.yMin, head.xMax, head.yMax)],
            "italicAngle": post.italicAngle,
            "flags": 32 | (2 if serif else 0),
            "stemV": 120 if "SemiBold" in name else 80,
        }
        print(
            name,
            len(ttf),
            "bytes ->",
            (OUT / f"{name}.ttf.z").stat().st_size,
            "z,",
            len(kern),
            "kern pairs",
        )
    (OUT / "metrics.json").write_text(
        json.dumps(metrics, separators=(",", ":"), ensure_ascii=False)
    )
    print("metrics.json", (OUT / "metrics.json").stat().st_size, "bytes")


if __name__ == "__main__":
    build()
