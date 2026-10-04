"""Pre-generate Spanish text for the renter view (stretch goal), cached.

Collects every unique English string the UI shows from the rule data (titles,
plain-language requirements, key values, conflict notes, lookup explanations),
translates only the ones not yet cached, in batches, via the headless Claude CLI
(`claude -p --model sonnet`), and stores them in web/translations/es.json keyed by
sha1(text)[:16]. Citations, quoted source spans and rule ids are never translated:
the legal text stays in the original English.

Run:  python3 web/translate.py [--limit N]     (reruns only translate new strings)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "translations" / "es.json"
LOG = ROOT / "web" / "translations" / "es.log.jsonl"
BATCH = 50

PROMPT = """You translate short plain-language summaries of US rental housing law from English into clear, neutral US Spanish for renters (reading level: general public).
Rules:
- Keep citations, section numbers, bill numbers (e.g. AB 325, S.2983), rule ids (e.g. CA-ALG-01), dollar amounts, percentages and dates exactly as written.
- Keep official names of laws/ordinances in English, optionally followed by a short Spanish gloss in parentheses the first time.
- Do not add advice, do not soften or strengthen the meaning, do not add information.
- Return ONLY a JSON object mapping each input key to its Spanish translation. No markdown fences, no commentary.

Input JSON:
"""


def key(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def plain_expected(s: str | None) -> str:
    """Change-test 'expected' text for people: no JSON rule maps, no snake_case status tokens (#73)."""
    s = re.sub(r"Key rules -> ours: \{.*?\}\.\s*", "", s or "")
    s = re.sub(r"\b[a-z]+(?:_[a-z]+)+\b", lambda m: m.group(0).replace("_", " "), s)
    s = s.replace("not yet effective", "not yet in effect").strip()
    return s[:1].upper() + s[1:]


TEST_FILES = (
    "starter/dev/change_tests.json",
    "output/new_tests.json",
    "new_docs/change_tests.json",
)


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]
_EN_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ]
    )
    for m in names
}
_MONTH_RE = "|".join(sorted(_EN_MONTHS, key=len, reverse=True))


def _es_date(day: int, month: int, year: int | None) -> str:
    return f"{day} {MESES[month]}" + (f" {year}" if year else "")


def es_dates(text: str | None) -> str | None:
    """Dates inside Spanish text in Spanish order and month names (#es-dates): 2026-03-01, 3/1/2026, 3/1/26 and
    'March 1, 2026' all become '1 mar 2026'. Citations and section numbers are left alone."""
    if not text:
        return text

    def iso(m):
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        return _es_date(d, mo - 1, y) if 1 <= mo <= 12 and 1 <= d <= 31 else m[0]

    def slash(m):
        mo, d, y = int(m[1]), int(m[2]), int(m[3])
        y = y + 2000 if y < 100 else y
        return _es_date(d, mo - 1, y) if 1 <= mo <= 12 and 1 <= d <= 31 else m[0]

    def words(m):
        mo = _EN_MONTHS[m[1].lower().rstrip(".")]
        return _es_date(int(m[2]), mo, int(m[3]) if m[3] else None)

    text = re.sub(r"(?<![\d§.-])(\d{4})-(\d{2})-(\d{2})(?![\d])", iso, text)
    text = re.sub(r"(?<![\d/.§])(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?![\d/])", slash, text)
    return re.sub(rf"\b({_MONTH_RE})\.? (\d{{1,2}})(?:, (\d{{4}}))?\b", words, text, flags=re.I)


_BASIS_ES = {
    "certificate of occupancy": "certificado de ocupación",
    "year built": "año de construcción",
    "construction completed": "construcción terminada",
    "first certificate of occupancy": "primer certificado de ocupación",
}
_CI_ES = {
    "on or before": "el {d} o antes",
    "before": "antes del {d}",
    "on or after": "el {d} o después",
    "after": "después del {d}",
}


def _units_es(u: str) -> str | None:
    if u == "unit count not given":
        return "no se sabe cuántas unidades tiene"
    m = re.fullmatch(r"(\d+) units?( \(you entered\))?", u)
    if m:
        n = int(m[1])
        return f"{n} unidad{'' if n == 1 else 'es'}" + (", según usted" if m[2] else "")
    return None


def _phr_es(p: str) -> str | None:
    m = re.fullmatch(r"(.+?) (on or before|on or after|before|after) (\d{4}-\d{2}-\d{2})", p)
    if not m or m[1] not in _BASIS_ES:
        return None
    return f"{_BASIS_ES[m[1]]} {_CI_ES[m[2]].format(d=m[3])}"


def _why_es(seg: str, tr) -> str | None:
    """One coverage reason of navigator/evaluate.coverage() in Spanish, or None."""
    U = r"(unit count not given|\d+ units?(?: \(you entered\))?)"
    pats = [
        (
            rf"building has {U}, meets the (\d+)\+ unit threshold",
            lambda m: f"el edificio tiene {_units_es(m[1])}: cumple el mínimo de {m[2]} unidades",
        ),
        (
            rf"building has {U}, below the (\d+)-unit threshold",
            lambda m: f"el edificio tiene {_units_es(m[1])}: menos del mínimo de {m[2]} unidades",
        ),
        (
            r"coverage needs (\d+)\+ units",
            lambda m: f"solo cubre edificios de {m[1]} unidades o más",
        ),
        (
            rf"building has {U}, within the (\d+)-unit limit",
            lambda m: f"el edificio tiene {_units_es(m[1])}: dentro del límite de {m[2]} unidades",
        ),
        (
            rf"building has {U}, above the (\d+)-unit limit",
            lambda m: f"el edificio tiene {_units_es(m[1])}: más del límite de {m[2]} unidades",
        ),
        (
            r"coverage limited to buildings of at most (\d+) units",
            lambda m: f"solo cubre edificios de {m[1]} unidades o menos",
        ),
        (
            rf"owner-occupied exemption \(<= (\d+) units\) cannot apply: {U}",
            lambda m: (
                f"la exención cuando el dueño vive en el edificio ({m[1]} unidades o menos) no aplica: {_units_es(m[2])}"
            ),
        ),
        (
            r"not owner-occupied: the owner-occupied exemption \(<= (\d+) units\) does not apply",
            lambda m: (
                f"el dueño no vive en el edificio: no aplica la exención para edificios de {m[1]} unidades o menos donde vive el dueño"
            ),
        ),
        (
            rf"owner-occupied with {U}: exempt \(<= (\d+) units\)",
            lambda m: (
                f"el dueño vive en el edificio, que tiene {_units_es(m[1])}: exento ({m[2]} unidades o menos)"
            ),
        ),
        (
            r"exempt if owner-occupied with <= (\d+) units",
            lambda m: f"exento si el dueño vive en el edificio y tiene {m[1]} unidades o menos",
        ),
        (
            r"owner-occupied exemption \(<= (\d+) units\) not checkable",
            lambda m: (
                f"no se puede comprobar la exención cuando el dueño vive en el edificio ({m[1]} unidades o menos)"
            ),
        ),
        (
            r"sample rows are multifamily buildings",
            lambda m: "los registros de muestra son edificios multifamiliares",
        ),
        (
            rf"owner occupancy is not in the data \({U}\)",
            lambda m: f"los datos no dicen si el dueño vive en el edificio ({_units_es(m[1])})",
        ),
        (
            r"certificate date (\d{4}-\d{2}-\d{2}): meets the cutoff \((.+)\)",
            lambda m: _ok(
                _phr_es(m[2]), lambda p: f"certificado del {m[1]}: cumple la fecha límite ({p})"
            ),
        ),
        (
            r"certificate date (\d{4}-\d{2}-\d{2}): outside the cutoff \((.+)\)",
            lambda m: _ok(
                _phr_es(m[2]), lambda p: f"certificado del {m[1]}: fuera de la fecha límite ({p})"
            ),
        ),
        (
            r"coverage depends on (.+)",
            lambda m: _ok(_phr_es(m[1]), lambda p: f"la cobertura depende de: {p}"),
        ),
        (
            r"year built is not in the data",
            lambda m: "el año de construcción no consta en los datos",
        ),
        (
            r"built (\d{4}): meets the cutoff \((.+)\)",
            lambda m: _ok(
                _phr_es(m[2]), lambda p: f"construido en {m[1]}: cumple la fecha límite ({p})"
            ),
        ),
        (
            r"built (\d{4}): outside the cutoff \((.+)\)",
            lambda m: _ok(
                _phr_es(m[2]), lambda p: f"construido en {m[1]}: fuera de la fecha límite ({p})"
            ),
        ),
        (
            r"built (\d{4}), the cutoff year",
            lambda m: f"construido en {m[1]}, el año de la fecha límite",
        ),
        (
            r"the (.+?) date is not in the data \((.+)\)",
            lambda m: _ok(_phr_es(m[2]), lambda p: f"la fecha exacta no consta en los datos ({p})"),
        ),
        (
            r"certificate date (\d{4}-\d{2}-\d{2}): older than the (\d+)-year new-construction exemption",
            lambda m: (
                f"certificado del {m[1]}: más antiguo que la exención de {m[2]} años para construcciones nuevas"
            ),
        ),
        (
            r"(?:certificate date (\d{4}-\d{2}-\d{2})|built (\d{4})): may be exempt as new construction \(< (\d+) years\) if the owner filed for the exemption",
            lambda m: (
                f"{'certificado del ' + m[1] if m[1] else 'construido en ' + m[2]}: puede estar exento como construcción nueva (menos de {m[3]} años) si el dueño pidió la exención"
            ),
        ),
        (r"filing not in the data", lambda m: "los datos no dicen si la pidió"),
        (
            r"certificate date (\d{4}-\d{2}-\d{2}): exempt as new construction \(within (\d+) years\)",
            lambda m: (
                f"certificado del {m[1]}: exento como construcción nueva (menos de {m[2]} años)"
            ),
        ),
        (
            r"exempt if newer than (\d+) years \((\d{4}-\d{2}-\d{2})\)",
            lambda m: f"exento si tiene menos de {m[1]} años (después del {m[2]})",
        ),
        (
            r"built (\d{4}): older than the (\d+)-year new-construction exemption",
            lambda m: (
                f"construido en {m[1]}: más antiguo que la exención de {m[2]} años para construcciones nuevas"
            ),
        ),
        (
            r"built (\d{4}): exempt as new construction \(certificate of occupancy within (\d+) years\)",
            lambda m: (
                f"construido en {m[1]}: exento como construcción nueva (certificado de ocupación de menos de {m[2]} años)"
            ),
        ),
        (
            r"built (\d{4}): the (\d+)-year new-construction exemption turns on the exact certificate date \((\d{4}-\d{2}-\d{2})\)",
            lambda m: (
                f"construido en {m[1]}: la exención de {m[2]} años para construcciones nuevas depende de la fecha exacta del certificado ({m[3]})"
            ),
        ),
    ]
    for rx, fn in pats:
        m = re.fullmatch(rx, seg)
        if m:
            return fn(m)
    return _units_es(seg) or tr(seg)


def _ok(v, fn):
    return fn(v) if v else None


def _whys_es(why: str, tr) -> str | None:
    out, facts = [], False
    for seg in why.split("; "):
        if seg.startswith("coverage depends on facts not in the data: "):
            seg, facts = seg.split(": ", 1)[1], True
            x = tr(seg)
            out.append(x and "la cobertura depende de datos que no tenemos: " + x)
        else:
            out.append(tr(seg) if facts else _why_es(seg, tr))
        if not out[-1]:
            return None
    return "; ".join(out)


def es_explanation(text: str | None, tr) -> str | None:
    """A rule-engine explanation (navigator/evaluate.py) in Spanish when it is not in the translation cache: the
    Rules page, Check and any-address views build them live for the facts a person gives (#151 sweep).
    `tr(s)` returns the cached Spanish for a fixed English string or None. Version, figure and review notes are
    left out (the page shows them from the English parse); any part we don't know returns None (English stays)."""
    if not text:
        return None
    s = re.sub(
        r"(?: Earlier version in force on .*| The figure above covers the period ending .*| Note: .*)$",
        "",
        text,
    )
    pre = ""
    if m := re.match(r"In effect since (\d{4}-\d{2}-\d{2})\. ", s):
        s, pre = s[m.end() :], f"Vigente desde el {m[1]}. "
    if m := re.match(
        r"The stricter local rule is not in effect on (\d{4}-\d{2}-\d{2}), so this rule governs\. ",
        s,
    ):
        s, pre = (
            s[m.end() :],
            pre
            + f"La regla local más estricta no está vigente el {m[1]}, así que rige esta regla. ",
        )
    tail = ""
    if m := re.search(
        r" This state law restricts local [a-z ]+ ordinances; no local ordinance of this kind applies at this address\.$",
        s,
    ):
        s, tail = (
            s[: m.start()],
            " Esta ley estatal limita las ordenanzas locales de este tipo; aquí no aplica ninguna ordenanza local de ese tipo.",
        )
    s = re.sub(r" Rule: .*$", "", s) if re.match(r".+? applies in ", s) else s

    def where_es(w):
        m = re.fullmatch(r"(.+?)(?: \(([A-Z]{2}) statewide rule\))?", w)
        return m[1] + (f" (regla estatal de {m[2]})" if m[2] else "")

    def body():
        if m := re.fullmatch(r"(.+?) applies in ([^:.]+?)(?:: (.+))?\.", s):
            w = _whys_es(m[3], tr) if m[3] else ""
            return (
                w is not None
                and f"{m[1]} se aplica en {where_es(m[2])}" + (f": {w}" if w else "") + "."
            )
        if m := re.fullmatch(r"(.+?) may apply in ([^:.]+?): (.+)\.", s):
            w = _whys_es(m[3], tr)
            return w and f"{m[1]} podría aplicarse en {where_es(m[2])}: {w}."
        if m := re.fullmatch(
            r"(.+?) is a pending bill, not law, as of (\S+)\. If enacted it would cover this address in ([^:]+?)\.",
            s,
        ):
            return f"{m[1]} es un proyecto de ley pendiente, no es ley al {m[2]}. Si se aprueba, cubriría esta dirección en {where_es(m[3])}."
        if m := re.fullmatch(
            r"(.+?) is enacted but takes effect (\S+), after (\S+); it will cover this address in ([^:]+?)\.(?: Coverage then depends on facts not in the data: (.+))?",
            s,
        ):
            w = _whys_es(m[5].rstrip("."), tr) if m[5] else ""
            return w is not None and (
                f"{m[1]} ya se aprobó, pero entra en vigor el {m[2]}, después del {m[3]}; entonces cubrirá esta dirección en {where_es(m[4])}."
                + (f" La cobertura dependerá de datos que no tenemos: {w}." if w else "")
            )
        if m := re.fullmatch(
            r"(.+?) would cover this address, but local (.+) governs here; the state rule yields to it\.",
            s,
        ):
            return f"{m[1]} cubriría esta dirección, pero aquí rige la regla local {m[2]}; la regla estatal cede ante ella."
        if m := re.fullmatch(
            r"(.+?) would cover this address, but one of the complementary local ordinances (.+) governs every building \(which one depends on the construction date\); the state rule yields\.",
            s,
        ):
            return f"{m[1]} cubriría esta dirección, pero en cada edificio rige una de las ordenanzas locales complementarias {m[2]} (cuál depende de la fecha de construcción); la regla estatal cede."
        if m := re.fullmatch(
            r"(.+?) covers this address unless local (.+) applies \(then the state rule yields\); local coverage is unknown from the data\.",
            s,
        ):
            return f"{m[1]} cubre esta dirección, salvo que aplique la regla local {m[2]} (entonces cede la regla estatal); los datos no dicen si la regla local la cubre."
        if m := re.fullmatch(
            r"(.+?) may apply in ([^:]+?), but the version in our sources took effect (\S+); on (\S+) an earlier version applied(, which our sources mention but our data does not hold| that our sources don't include)\.",
            s,
        ):
            return (
                f"{m[1]} podría aplicarse en {where_es(m[2])}, pero la versión de nuestras fuentes entró en vigor el {m[3]}; el {m[4]} regía una versión anterior"
                + (
                    ", que nuestras fuentes mencionan pero nuestros datos no contienen."
                    if m[5].startswith(",")
                    else " que nuestras fuentes no incluyen."
                )
            )
        return None

    b = body()
    return es_dates(pre + b + tail) if b else None


def load(name: str):
    for d in (ROOT / "output", ROOT / "web" / "fixtures"):
        p = d / name
        if p.exists() and p.stat().st_size > 2:
            return json.loads(p.read_text())
    return None


def collect() -> list[str]:
    texts: list[str] = ["Proposal failed or was withdrawn. It is not law and does not apply."]
    rules = load("rules.json") or {"rules": []}
    for f in rules.get("no_rule_findings", []) if isinstance(rules, dict) else []:
        if f.get("finding"):
            texts.append(f["finding"])
    rules = rules["rules"] if isinstance(rules, dict) else rules
    for r in rules:
        for f in (
            "title",
            "requirement",
            "key_value",
            "conflict_note",
            "interaction",
            "prior_version_note",
        ):
            if isinstance(r.get(f), str) and r[f].strip():
                texts.append(r[f])
        texts += [x for x in ((r.get("coverage") or {}).get("requires_unknown_facts") or []) if x]
    for f in TEST_FILES:  # change-test titles and expected behaviour (#74)
        if (ROOT / f).exists():
            for t in json.loads((ROOT / f).read_text()):
                texts += [t.get("title") or "", plain_expected(t.get("expected_behavior"))]
    texts = [t for t in texts if t]
    lk = load("lookups.json") or {"lookups": {}}
    for entries in lk["lookups"].values():
        for e in entries:
            if e.get("explanation"):
                texts.append(e["explanation"])
    seen, out = set(), []
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def translate_batch(items: dict[str, str]) -> dict[str, str]:
    prompt = PROMPT + json.dumps(items, ensure_ascii=False, indent=0)
    for attempt in range(3):
        try:
            res = subprocess.run(
                ["claude", "-p", "--model", "sonnet"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,
            )
            txt = res.stdout.strip()
            if txt.startswith("```"):
                txt = txt.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(txt[txt.find("{") : txt.rfind("}") + 1])
            return {k: v for k, v in data.items() if k in items and isinstance(v, str)}
        except Exception as e:  # retry on malformed output / timeouts
            print(f"  batch failed (attempt {attempt + 1}): {e}", file=sys.stderr)
            time.sleep(3)
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max new strings this run (0 = all)")
    args = ap.parse_args()
    cache: dict[str, str] = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [t for t in collect() if key(t) not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(cache)} cached, {len(todo)} to translate", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(todo), BATCH):
        chunk = todo[i : i + BATCH]
        items = {key(t): t for t in chunk}
        got = translate_batch(items)
        cache.update(got)
        OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True))
        with LOG.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "model": "claude sonnet (claude -p)",
                        "requested": len(items),
                        "received": len(got),
                    }
                )
                + "\n"
            )
        print(f"  batch {i // BATCH + 1}: {len(got)}/{len(items)}", file=sys.stderr)
    print(f"done: {len(cache)} strings in {OUT.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
