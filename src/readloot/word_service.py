"""Word entry management for ReadLoot.

Handles adding, looking up, searching, and exporting word entries.
All mutations go through SQLite first, then the corresponding chapter
Markdown file is regenerated (design decision #1).

See also: models.py, db.py, markdown.py, book_service.py
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime

from readloot.markdown import generate_chapter_markdown
from readloot.models import Chapter, WordEntry


def add_word(
    conn: sqlite3.Connection,
    vault_dir: str,
    word: str,
    meaning: str,
    synonyms: str,
    context: str,
    book_name: str,
    chapter_name: str,
) -> dict:
    """Add a word entry to the vault.

    Inserts into SQLite, updates the FTS index, and regenerates the
    chapter Markdown file.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialized.
    vault_dir : str
        Path to the vault root directory (e.g. ``"vault"``).
    word : str
        The vocabulary word.
    meaning : str
        The word's definition.
    synonyms : str
        Comma-separated synonyms.
    context : str
        The sentence from the book where the word was found.
    book_name : str
        The book this word belongs to (must exist in DB).
    chapter_name : str
        The chapter this word belongs to (must exist in DB).

    Returns
    -------
    dict
        On success: ``{"entry": WordEntry}``
        If duplicate in same chapter: ``{"duplicate": True, "existing": WordEntry}``
        May also include ``"cross_book_occurrences"`` — a list of dicts
        describing where the same word appears in other books/chapters.
    """
    # Resolve book
    book_row = conn.execute(
        "SELECT id, folder_name FROM books WHERE name = ?",
        (book_name,),
    ).fetchone()
    if book_row is None:
        raise ValueError(f"Book not found: {book_name}")

    book_id = book_row["id"]
    book_folder = book_row["folder_name"]

    # Resolve chapter
    chapter_row = conn.execute(
        "SELECT id, chapter_number, filename FROM chapters WHERE book_id = ? AND name = ?",
        (book_id, chapter_name),
    ).fetchone()
    if chapter_row is None:
        raise ValueError(f"Chapter not found: {chapter_name}")

    chapter_id = chapter_row["id"]

    # Check for duplicate within the same chapter
    existing_row = conn.execute(
        "SELECT * FROM word_entries WHERE word = ? AND chapter_id = ?",
        (word, chapter_id),
    ).fetchone()

    if existing_row is not None:
        existing_entry = _row_to_word_entry(existing_row, book_name, chapter_name)
        return {"duplicate": True, "existing": existing_entry}

    # Check for cross-book occurrences (same word in other books/chapters)
    cross_rows = conn.execute(
        """
        SELECT w.*, b.name AS b_name, c.name AS c_name
        FROM word_entries w
        JOIN books b ON w.book_id = b.id
        JOIN chapters c ON w.chapter_id = c.id
        WHERE w.word = ?
        """,
        (word,),
    ).fetchall()

    cross_book_occurrences = [
        {
            "word": r["word"],
            "meaning": r["meaning"],
            "book_name": r["b_name"],
            "chapter_name": r["c_name"],
        }
        for r in cross_rows
    ]

    # Insert the word entry
    now = datetime.now()
    today = date.today()
    cursor = conn.execute(
        """
        INSERT INTO word_entries
            (word, meaning, synonyms, context, book_id, chapter_id,
             date_added, date_modified, mastery_level, next_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (word, meaning, synonyms, context, book_id, chapter_id,
         today.isoformat(), now.isoformat(), today.isoformat()),
    )
    word_id = cursor.lastrowid

    # Update FTS index
    conn.execute(
        """
        INSERT INTO word_entries_fts(rowid, word, meaning, synonyms, context)
        VALUES (?, ?, ?, ?, ?)
        """,
        (word_id, word, meaning, synonyms, context),
    )

    conn.commit()

    # Regenerate chapter Markdown
    _regenerate_chapter_markdown(conn, vault_dir, chapter_id)

    # Build the created entry
    entry = WordEntry(
        id=word_id,
        word=word,
        meaning=meaning,
        synonyms=synonyms,
        context=context,
        book_id=book_id,
        chapter_id=chapter_id,
        book_name=book_name,
        chapter_name=chapter_name,
        date_added=today,
        date_modified=now,
        mastery_level=0,
        next_review=today,
    )

    result: dict = {"entry": entry}
    if cross_book_occurrences:
        result["cross_book_occurrences"] = cross_book_occurrences

    return result



def lookup_word(conn: sqlite3.Connection, word: str) -> list[dict]:
    """Look up a word across all books and chapters.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    word : str
        The word to look up (exact, case-insensitive match).

    Returns
    -------
    list[dict]
        Each dict contains: ``word``, ``meaning``, ``synonyms``,
        ``context``, ``book_name``, ``chapter_name``.
    """
    rows = conn.execute(
        """
        SELECT w.word, w.meaning, w.synonyms, w.context,
               b.name AS book_name, c.name AS chapter_name
        FROM word_entries w
        JOIN books b ON w.book_id = b.id
        JOIN chapters c ON w.chapter_id = c.id
        WHERE LOWER(w.word) = LOWER(?)
        ORDER BY b.name, c.chapter_number
        """,
        (word,),
    ).fetchall()

    return [
        {
            "word": r["word"],
            "meaning": r["meaning"],
            "synonyms": r["synonyms"],
            "context": r["context"],
            "book_name": r["book_name"],
            "chapter_name": r["chapter_name"],
        }
        for r in rows
    ]


def search_words(conn: sqlite3.Connection, query: str) -> list[dict]:
    """Full-text search across word, meaning, synonyms, and context.

    Uses the FTS5 virtual table ``word_entries_fts`` for efficient
    full-text matching.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    query : str
        The search query string.

    Returns
    -------
    list[dict]
        Each dict contains: ``word``, ``meaning``, ``synonyms``,
        ``context``, ``book_name``, ``chapter_name``.
    """
    if not query or not query.strip():
        return []

    rows = conn.execute(
        """
        SELECT w.word, w.meaning, w.synonyms, w.context,
               b.name AS book_name, c.name AS chapter_name
        FROM word_entries_fts fts
        JOIN word_entries w ON fts.rowid = w.id
        JOIN books b ON w.book_id = b.id
        JOIN chapters c ON w.chapter_id = c.id
        WHERE word_entries_fts MATCH ?
        ORDER BY rank
        """,
        (query,),
    ).fetchall()

    return [
        {
            "word": r["word"],
            "meaning": r["meaning"],
            "synonyms": r["synonyms"],
            "context": r["context"],
            "book_name": r["book_name"],
            "chapter_name": r["chapter_name"],
        }
        for r in rows
    ]


def export_words(conn: sqlite3.Connection) -> dict:
    """Export all word entries as a JSON-serializable dict.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.

    Returns
    -------
    dict
        A dict with key ``"entries"`` containing a list of dicts, each
        with: ``word``, ``meaning``, ``synonyms``, ``context``,
        ``book_name``, ``chapter_name``, ``date_added``,
        ``mastery_level``.
    """
    rows = conn.execute(
        """
        SELECT w.word, w.meaning, w.synonyms, w.context,
               w.date_added, w.mastery_level,
               b.name AS book_name, c.name AS chapter_name
        FROM word_entries w
        JOIN books b ON w.book_id = b.id
        JOIN chapters c ON w.chapter_id = c.id
        ORDER BY b.name, c.chapter_number, w.word
        """
    ).fetchall()

    entries = [
        {
            "word": r["word"],
            "meaning": r["meaning"],
            "synonyms": r["synonyms"],
            "context": r["context"],
            "book_name": r["book_name"],
            "chapter_name": r["chapter_name"],
            "date_added": r["date_added"],
            "mastery_level": r["mastery_level"],
        }
        for r in rows
    ]

    return {"entries": entries}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _regenerate_chapter_markdown(
    conn: sqlite3.Connection,
    vault_dir: str,
    chapter_id: int,
) -> None:
    """Regenerate the Markdown file for a chapter from SQLite data.

    Queries all word entries for the chapter, builds a Chapter object,
    calls :func:`generate_chapter_markdown`, and writes the result to
    disk.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    vault_dir : str
        Path to the vault root directory.
    chapter_id : int
        The chapter whose Markdown file should be regenerated.
    """
    # Get chapter info
    chapter_row = conn.execute(
        """
        SELECT c.id, c.book_id, c.name, c.chapter_number, c.filename,
               b.name AS book_name, b.folder_name
        FROM chapters c
        JOIN books b ON c.book_id = b.id
        WHERE c.id = ?
        """,
        (chapter_id,),
    ).fetchone()

    if chapter_row is None:
        return

    # Build Chapter object
    chapter = Chapter(
        id=chapter_row["id"],
        book_id=chapter_row["book_id"],
        name=chapter_row["name"],
        chapter_number=chapter_row["chapter_number"],
        filename=chapter_row["filename"],
    )
    # Attach book_name for markdown generation
    chapter.book_name = chapter_row["book_name"]  # type: ignore[attr-defined]

    # Get all word entries for this chapter
    entry_rows = conn.execute(
        """
        SELECT id, word, meaning, synonyms, context, book_id, chapter_id,
               date_added, date_modified, mastery_level, next_review
        FROM word_entries
        WHERE chapter_id = ?
        ORDER BY date_added, word
        """,
        (chapter_id,),
    ).fetchall()

    entries = [
        WordEntry(
            id=r["id"],
            word=r["word"],
            meaning=r["meaning"],
            synonyms=r["synonyms"],
            context=r["context"],
            book_id=r["book_id"],
            chapter_id=r["chapter_id"],
            book_name=chapter_row["book_name"],
            chapter_name=chapter_row["name"],
            date_added=date.fromisoformat(r["date_added"]),
            mastery_level=r["mastery_level"],
        )
        for r in entry_rows
    ]

    # Generate markdown content
    md_content = generate_chapter_markdown(chapter, entries)

    # Write to disk
    chapter_path = os.path.join(
        vault_dir,
        chapter_row["folder_name"],
        chapter_row["filename"],
    )
    os.makedirs(os.path.dirname(chapter_path), exist_ok=True)
    with open(chapter_path, "w", encoding="utf-8") as f:
        f.write(md_content)


def _row_to_word_entry(
    row: sqlite3.Row,
    book_name: str,
    chapter_name: str,
) -> WordEntry:
    """Convert a sqlite3.Row from word_entries into a WordEntry."""
    return WordEntry(
        id=row["id"],
        word=row["word"],
        meaning=row["meaning"],
        synonyms=row["synonyms"],
        context=row["context"],
        book_id=row["book_id"],
        chapter_id=row["chapter_id"],
        book_name=book_name,
        chapter_name=chapter_name,
        date_added=date.fromisoformat(row["date_added"]),
        mastery_level=row["mastery_level"],
    )
