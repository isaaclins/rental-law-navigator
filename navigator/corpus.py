"""Corpus access: documents, chunking and verbatim span verification."""

from __future__ import annotations

import csv
import difflib
import re
from dataclasses import dataclass, field
from functools import lru_cache

from .config import CORPUS_TEXT, EXTENSION_DIR, LINKS_ONLY_CSV, MANIFEST_CSV, NEW_DOCS_DIR, SUPP_DIR

CHUNK_LIMIT = 60_000  # characters; longer documents are split
CHUNK_SIZE = 45_000
CHUNK_OVERLAP = 2_000


@dataclass
class Doc:
    doc_id: str
    jurisdictions: str
    url: str
    source_type: str
    retrieved_at: str
    text: str
    origin: str  # "corpus" | "supplementary" | "new"
    path: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def is_primary(self) -> bool:
        return self.origin in ("corpus", "new") and not self.source_type.startswith("secondary")


def _header_value(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", text[:600], re.M)
    return m.group(1).strip() if m else ""


@lru_cache(maxsize=1)
def manifest() -> dict[str, dict]:
    return {r["doc_id"]: r for r in csv.DictReader(open(MANIFEST_CSV, encoding="utf-8"))}


def link_only_rows() -> list[dict]:
    return list(csv.DictReader(open(LINKS_ONLY_CSV, encoding="utf-8")))


def new_doc_rows() -> list[dict]:
    p = NEW_DOCS_DIR / "manifest.csv"
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def extension_doc_rows() -> list[dict]:
    """Documents of the extension jurisdiction (NAVIGATOR_EXTENSION), same columns as the corpus manifest."""
    p = EXTENSION_DIR / "manifest.csv" if EXTENSION_DIR else None
    if not p or not p.exists():
        return []
    return [r for r in csv.DictReader(open(p, encoding="utf-8")) if r.get("status") == "ok"]


def load_docs(include_supplementary: bool = True, include_new: bool = True) -> list[Doc]:
    docs: list[Doc] = []
    for doc_id, r in manifest().items():
        if r.get("status") != "ok" or not r.get("text_file"):
            continue
        p = CORPUS_TEXT / f"{doc_id}.txt"
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        docs.append(
            Doc(
                doc_id,
                r["jurisdictions"],
                r["url"],
                r["source_type"],
                r["retrieved_at"] or _header_value(t, "RETRIEVED"),
                t,
                "corpus",
                str(p),
            )
        )
    if include_supplementary and SUPP_DIR.exists():
        for p in sorted(SUPP_DIR.glob("D*.txt")):
            r = manifest().get(p.stem, {})
            t = p.read_text(encoding="utf-8")
            docs.append(
                Doc(
                    p.stem,
                    r.get("jurisdictions", ""),
                    _header_value(t, "SOURCE") or r.get("url", ""),
                    r.get("source_type", "secondary"),
                    _header_value(t, "RETRIEVED"),
                    t,
                    "supplementary",
                    str(p),
                )
            )
    if include_new:
        for base, r in [(NEW_DOCS_DIR, r) for r in new_doc_rows()] + [
            (EXTENSION_DIR, r) for r in extension_doc_rows()
        ]:
            p = base / r["text_file"]
            if p.exists():
                t = p.read_text(encoding="utf-8")
                docs.append(
                    Doc(
                        r["doc_id"],
                        r["jurisdictions"],
                        r["url"],
                        r["source_type"],
                        r["retrieved_at"],
                        t,
                        "new",
                        str(p),
                        dict(r),
                    )
                )
    return docs


@lru_cache(maxsize=1)
def docs_by_id() -> dict[str, Doc]:
    return {d.doc_id: d for d in load_docs()}


def get_doc(doc_id: str) -> Doc | None:
    d = docs_by_id().get(doc_id)
    if d is None:  # newly ingested docs after cache fill
        docs_by_id.cache_clear()
        d = docs_by_id().get(doc_id)
    return d


def chunks(doc: Doc) -> list[tuple[int, str]]:
    t = doc.text
    if len(t) <= CHUNK_LIMIT:
        return [(0, t)]
    out, start = [], 0
    while start < len(t):
        end = min(len(t), start + CHUNK_SIZE)
        if end < len(t):
            cut = t.rfind("\n\n", start + CHUNK_SIZE // 2, end)
            if cut == -1:
                cut = t.rfind("\n", start + CHUNK_SIZE // 2, end)
            end = cut if cut > start else end
        out.append((start, t[start:end]))
        if end >= len(t):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return out


# ---------------------------------------------------------------- span verification
_QUOTES = str.maketrans(
    {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " ", "…": "..."}
)


def _norm_with_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-collapsed, quote-normalised text plus a map norm_index -> original index."""
    out, idx = [], []
    prev_space = True
    for i, ch in enumerate(text):
        c = ch.translate(_QUOTES)
        if c.isspace():
            if prev_space:
                continue
            out.append(" ")
            idx.append(i)
            prev_space = True
        else:
            for cc in c:
                out.append(cc)
                idx.append(i)
            prev_space = False
    return "".join(out), idx


@lru_cache(maxsize=256)
def _normed(doc_id: str) -> tuple[str, tuple[int, ...]]:
    d = get_doc(doc_id)
    n, m = _norm_with_map(d.text if d else "")
    return n, tuple(m)


def norm(s: str) -> str:
    return _norm_with_map(s)[0].strip()


def verify_span(doc_id: str, span: str) -> str | None:
    """Return the exact original substring of the doc matching `span` (whitespace/quote-insensitive) or None."""
    if not span or len(span.strip()) < 20:
        return None
    d = get_doc(doc_id)
    if not d:
        return None
    n, m = _normed(doc_id)
    s = norm(span).strip(" .")
    if "..." in s:  # elided quotes are not verbatim: verify the longest contiguous piece instead
        s = max((p.strip(" .") for p in s.split("...")), key=len)
        if len(s) < 20:
            return None
    pos = n.find(s)
    if pos < 0:
        pos = n.lower().find(s.lower())
    if pos < 0:
        return None
    start, end = m[pos], m[pos + len(s) - 1] + 1
    return d.text[start:end]


def _sentences(doc_id: str) -> list[str]:
    n, _ = _normed(doc_id)
    parts = re.split(r"(?<=[.;:!?])\s+|\s(?=\(\w{1,4}\)\s)", n)
    return [p.strip() for p in parts if len(p.strip()) >= 20]


def snap_span(doc_id: str, span: str, min_ratio: float = 0.55) -> tuple[str | None, float]:
    """Find the doc passage (1-3 consecutive sentences) most similar to `span`; return its exact original text."""
    target = norm(span).lower()
    if not target:
        return None, 0.0
    sents = _sentences(doc_id)
    tw = set(re.findall(r"\w+", target))
    best, best_r = None, 0.0
    for i in range(len(sents)):
        for k in (1, 2, 3):
            cand = " ".join(sents[i : i + k])
            if len(cand) > 3 * len(target) + 200:
                break
            cw = set(re.findall(r"\w+", cand.lower()))
            if not cw or len(tw & cw) / max(1, len(tw)) < 0.4:
                continue
            r = difflib.SequenceMatcher(None, target, cand.lower(), autojunk=False).ratio()
            if r > best_r:
                best, best_r = cand, r
    if best and best_r >= min_ratio:
        exact = verify_span(doc_id, best)
        if exact:
            return exact, best_r
    return None, best_r


def span_in_corpus(span: str, doc_id: str | None = None) -> bool:
    if doc_id and verify_span(doc_id, span):
        return True
    s = norm(span)
    return any(s in _normed(d.doc_id)[0] for d in load_docs())
