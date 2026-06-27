"""Project Gutenberg book import for ReadLoot.

Search a small curated catalog of public-domain books, fetch a book's plain
text from gutenberg.org, split it into chapters, and feed each chapter through
the vocabulary extractor.

Why a bundled catalog instead of the Gutendex API: the public gutendex.com
instance was unreachable (no DNS) when this was built, so search runs against a
local JSON list of well-known titles. Book *text* still comes live from
gutenberg.org, which is reliable. Swapping in a live Gutendex search later only
means replacing :func:`search_catalog`.

Gutenberg asks automated clients to identify themselves and throttle; we send a
descriptive User-Agent and fetch one file per import.

See also: vocab_extractor.extract_vocabulary, word_service.add_words_bulk.
"""

from __future__ import annotations

import json
import re
from importlib import resources

import requests

_USER_AGENT = "readloot/0.1 (personal vocabulary-learning app)"
_TIMEOUT = 30
# Books with no detectable chapter headings fall back to fixed-size chunks.
_CHUNK_CHARS = 8000
_MAX_CHAPTERS = 40

# Roman-numeral or numbered chapter headings on their own line.
_HEADING = re.compile(
    r"(?mi)^\s{0,4}((?:chapter|adventure|letter|book|part)\s+[ivxlcdm0-9]+|[ivxlcdm]+)\.?\s*$"
)
_START = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
_END = re.compile(r"\*\*\*\s*END OF", re.IGNORECASE)


def _format_heading(raw: str) -> str:
    """Title-case a heading but keep roman numerals upper (Chapter II, not Ii)."""
    return " ".join(
        w.upper() if re.fullmatch(r"(?i)[ivxlcdm]+\.?", w) else w.capitalize()
        for w in raw.split()
    )


def search_catalog(query: str = "") -> list[dict]:
    """Search the bundled catalog by title or author (case-insensitive substring)."""
    with resources.files("readloot.data").joinpath("book_catalog.json").open(
        encoding="utf-8"
    ) as f:
        catalog = json.load(f)
    q = (query or "").strip().lower()
    if not q:
        return catalog
    return [
        b
        for b in catalog
        if q in b["title"].lower() or q in b["author"].lower()
    ]


def _catalog_entry(gutenberg_id: int) -> dict | None:
    for b in search_catalog(""):
        if b["gutenberg_id"] == gutenberg_id:
            return b
    return None


def fetch_book_text(gutenberg_id: int) -> str:
    """Download a book's plain-text from gutenberg.org. Raises on failure."""
    url = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
    resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT})
    resp.raise_for_status()
    return resp.text


def _strip_gutenberg_boilerplate(text: str) -> str:
    """Drop the Project Gutenberg license header and footer."""
    start = _START.search(text)
    body = text[start.end():] if start else text
    end = _END.search(body)
    if end:
        body = body[: end.start()]
    return body.strip()


def split_chapters(text: str) -> list[dict]:
    """Split book text into chapters.

    Prefers real chapter headings; if too few are found, falls back to
    fixed-size chunks so every book yields something usable. Returns a list of
    ``{"name", "text"}`` capped at :data:`_MAX_CHAPTERS`.
    """
    body = _strip_gutenberg_boilerplate(text)

    matches = list(_HEADING.finditer(body))
    # Need a few headings to trust them; a single stray "I." isn't structure.
    if len(matches) >= 3:
        chapters = []
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            chunk = body[start:end].strip()
            if len(chunk) < 200:  # heading with no real body (front matter)
                continue
            title = _format_heading(m.group(0).strip())
            chapters.append({"name": title, "text": chunk})
            if len(chapters) >= _MAX_CHAPTERS:
                break
        if chapters:
            return chapters

    # Fallback: fixed-size chunks on paragraph boundaries.
    chapters = []
    pos = 0
    n = 1
    while pos < len(body) and n <= _MAX_CHAPTERS:
        end = min(pos + _CHUNK_CHARS, len(body))
        # extend to the next paragraph break so we don't cut mid-sentence
        nxt = body.find("\n\n", end)
        if nxt != -1 and nxt - end < 2000:
            end = nxt
        chunk = body[pos:end].strip()
        if chunk:
            chapters.append({"name": f"Part {n}", "text": chunk})
            n += 1
        pos = end
    return chapters
