"""Markdown generation and parsing for ReadLoot chapter files.

Each chapter is stored as a single Markdown file with YAML front matter
(book name, chapter name, chapter number, word count) followed by one
section per word entry.

See also: models.py for the Chapter and WordEntry dataclasses.
"""

from __future__ import annotations

from datetime import date

from readloot.models import WordEntry


def generate_chapter_markdown(chapter, entries: list[WordEntry]) -> str:
    """Generate a complete chapter Markdown file with YAML front matter.

    Parameters
    ----------
    chapter : Chapter
        The chapter metadata (must have ``book_name`` or be paired with a
        Book whose ``name`` is passed via the chapter's attributes).
        Expected attributes: book_id, name, chapter_number.  The caller
        must also supply ``book_name`` — typically available on the
        Chapter or passed separately.  For convenience the function
        accepts any object with ``.name`` and ``.chapter_number``; the
        book name is taken from the first entry's ``book_name`` when
        available, or from ``chapter.book_name`` if the caller attached
        it.
    entries : list[WordEntry]
        Word entries belonging to this chapter, in the order they should
        appear in the file.

    Returns
    -------
    str
        The full Markdown content ready to be written to disk.
    """
    book_name = _resolve_book_name(chapter, entries)
    lines: list[str] = []

    # YAML front matter
    lines.append("---")
    lines.append(f'book: "{_escape_yaml(book_name)}"')
    lines.append(f'chapter: "{_escape_yaml(chapter.name)}"')
    lines.append(f"chapter_number: {chapter.chapter_number}")
    lines.append(f"word_count: {len(entries)}")
    lines.append("---")

    for entry in entries:
        lines.append("")
        lines.append(f"## {entry.word}")
        lines.append("")
        lines.append(f"- **Meaning:** {entry.meaning}")
        synonyms = entry.synonyms if entry.synonyms else ""
        lines.append(f"- **Synonyms:** {synonyms}")
        lines.append(f'- **Context:** "{entry.context}"')
        lines.append(f"- **Date Added:** {entry.date_added.isoformat()}")

    # Ensure trailing newline
    lines.append("")
    return "\n".join(lines)


def parse_chapter_markdown(content: str) -> tuple[dict, list[WordEntry]]:
    """Parse a chapter Markdown file into front matter metadata and WordEntry list.

    Parameters
    ----------
    content : str
        The raw Markdown text of a chapter file.

    Returns
    -------
    tuple[dict, list[WordEntry]]
        A 2-tuple of (metadata_dict, word_entries).
        ``metadata_dict`` contains keys: ``book``, ``chapter``,
        ``chapter_number``, ``word_count`` (all as strings/ints parsed
        from YAML front matter).
        ``word_entries`` is a list of :class:`WordEntry` objects with
        ``word``, ``meaning``, ``synonyms``, ``context``, and
        ``date_added`` populated.
    """
    metadata, body = _split_front_matter(content)
    entries = _parse_word_sections(body)
    return metadata, entries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_book_name(chapter, entries: list[WordEntry]) -> str:
    """Determine the book name from the chapter or entries."""
    # Prefer an explicit attribute on the chapter object
    if hasattr(chapter, "book_name") and chapter.book_name:
        return chapter.book_name
    # Fall back to the first entry's book_name
    if entries:
        return entries[0].book_name
    return ""


def _escape_yaml(value: str) -> str:
    """Escape characters that would break YAML double-quoted strings."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _unescape_yaml(value: str) -> str:
    """Reverse the escaping applied by ``_escape_yaml``."""
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _split_front_matter(content: str) -> tuple[dict, str]:
    """Split YAML front matter from the Markdown body.

    Returns (metadata_dict, remaining_body).  If no valid front matter
    is found, returns an empty dict and the full content.
    """
    stripped = content.lstrip("\n")
    if not stripped.startswith("---"):
        return {}, content

    # Find the closing ---
    end_idx = stripped.find("\n---", 3)
    if end_idx == -1:
        return {}, content

    yaml_block = stripped[3:end_idx].strip()
    body = stripped[end_idx + 4:]  # skip past "\n---"

    metadata: dict = {}
    for line in yaml_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if value.startswith('"') and value.endswith('"'):
            value = _unescape_yaml(value[1:-1])
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        # Try to parse as int
        if key in ("chapter_number", "word_count"):
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
        metadata[key] = value

    return metadata, body


def _parse_word_sections(body: str) -> list[WordEntry]:
    """Parse the body (after front matter) into WordEntry objects."""
    entries: list[WordEntry] = []
    sections = _split_into_sections(body)

    for word, section_lines in sections:
        entry = _parse_single_entry(word, section_lines)
        if entry is not None:
            entries.append(entry)

    return entries


def _split_into_sections(body: str) -> list[tuple[str, list[str]]]:
    """Split the body into (heading_text, [lines]) pairs on ``## `` headings."""
    sections: list[tuple[str, list[str]]] = []
    current_word: str | None = None
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_word is not None:
                sections.append((current_word, current_lines))
            current_word = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_word is not None:
        sections.append((current_word, current_lines))

    return sections


def _parse_single_entry(word: str, lines: list[str]) -> WordEntry | None:
    """Parse a single word section's lines into a WordEntry."""
    meaning = ""
    synonyms = ""
    context = ""
    date_added = date.today()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- **Meaning:**"):
            meaning = stripped[len("- **Meaning:**"):].strip()
        elif stripped.startswith("- **Synonyms:**"):
            synonyms = stripped[len("- **Synonyms:**"):].strip()
        elif stripped.startswith("- **Context:**"):
            raw_context = stripped[len("- **Context:**"):].strip()
            # Remove surrounding quotes if present
            if raw_context.startswith('"') and raw_context.endswith('"'):
                raw_context = raw_context[1:-1]
            context = raw_context
        elif stripped.startswith("- **Date Added:**"):
            date_str = stripped[len("- **Date Added:**"):].strip()
            try:
                date_added = date.fromisoformat(date_str)
            except ValueError:
                pass  # keep default

    if not word:
        return None

    return WordEntry(
        word=word,
        meaning=meaning,
        synonyms=synonyms,
        context=context,
        date_added=date_added,
    )
