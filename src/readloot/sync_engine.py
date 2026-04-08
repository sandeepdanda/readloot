"""Bidirectional sync engine for ReadLoot.

Reconciles the Markdown store (``vault/`` directory) with the SQLite
database so that manual edits to either side are reflected in both.

Sync strategy:
1. Scan all ``.md`` files in ``vault/`` subdirectories.
2. Parse each file and compare with SQLite entries.
3. Entries only in Markdown → import to SQLite (mastery=0), update FTS.
4. Entries only in SQLite → regenerate Markdown file.
5. Entries in both but different → use most recently modified source.
6. Malformed files → log warning, skip, continue processing.

See also: markdown.py, word_service.py, book_service.py, models.py
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime

from readloot.book_service import create_book, create_chapter, sanitize_name
from readloot.markdown import generate_chapter_markdown, parse_chapter_markdown
from readloot.models import Chapter, WordEntry
from readloot.word_service import _regenerate_chapter_markdown


@dataclass
class SyncResult:
    """Summary of a sync operation."""

    added: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)


def sync(conn: sqlite3.Connection, vault_dir: str = "vault") -> SyncResult:
    """Full bidirectional sync between Markdown store and SQLite.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialised.
    vault_dir : str
        Path to the vault root directory (e.g. ``"vault"``).

    Returns
    -------
    SyncResult
        Counts of added, updated, and unchanged entries plus any errors.
    """
    result = SyncResult()

    # ------------------------------------------------------------------
    # Phase 1: Markdown → SQLite  (import / update from .md files)
    # ------------------------------------------------------------------
    md_seen_chapters: set[int] = set()  # chapter IDs we touched from MD side

    for md_path in _iter_md_files(vault_dir):
        try:
            _process_md_file(conn, vault_dir, md_path, result, md_seen_chapters)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"{md_path}: {exc}")

    # ------------------------------------------------------------------
    # Phase 2: SQLite → Markdown  (export entries missing from MD store)
    # ------------------------------------------------------------------
    _export_sqlite_only_entries(conn, vault_dir, md_seen_chapters, result)

    return result


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _iter_md_files(vault_dir: str):
    """Yield absolute paths to all ``.md`` files inside *vault_dir* subdirectories."""
    if not os.path.isdir(vault_dir):
        return
    for book_folder in sorted(os.listdir(vault_dir)):
        book_path = os.path.join(vault_dir, book_folder)
        if not os.path.isdir(book_path):
            continue
        for fname in sorted(os.listdir(book_path)):
            if fname.lower().endswith(".md"):
                yield os.path.join(book_path, fname)


def _process_md_file(
    conn: sqlite3.Connection,
    vault_dir: str,
    md_path: str,
    result: SyncResult,
    md_seen_chapters: set[int],
) -> None:
    """Parse a single Markdown file and reconcile with SQLite."""
    with open(md_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    metadata, md_entries = parse_chapter_markdown(content)

    book_name = metadata.get("book", "")
    chapter_name = metadata.get("chapter", "")
    chapter_number = metadata.get("chapter_number", 0)
    if isinstance(chapter_number, str):
        try:
            chapter_number = int(chapter_number)
        except ValueError:
            chapter_number = 0

    if not book_name or not chapter_name:
        result.errors.append(f"{md_path}: missing book or chapter in front matter")
        return

    # Ensure book exists in DB (create if needed)
    book_row = conn.execute(
        "SELECT id, folder_name FROM books WHERE name = ?", (book_name,)
    ).fetchone()
    if book_row is None:
        book = create_book(conn, vault_dir, book_name)
        book_id = book.id
    else:
        book_id = book_row["id"]

    # Ensure chapter exists in DB (create if needed)
    chapter_row = conn.execute(
        "SELECT id FROM chapters WHERE book_id = ? AND name = ?",
        (book_id, chapter_name),
    ).fetchone()
    if chapter_row is None:
        chapter = create_chapter(conn, vault_dir, book_name, chapter_name, chapter_number or 1)
        chapter_id = chapter.id
    else:
        chapter_id = chapter_row["id"]

    md_seen_chapters.add(chapter_id)

    # Get file mtime for conflict resolution
    file_mtime = datetime.fromtimestamp(os.path.getmtime(md_path))

    # Build lookup of existing DB entries for this chapter keyed by word
    db_entries = _get_db_entries_for_chapter(conn, chapter_id)

    # Build lookup of MD entries keyed by word
    md_lookup: dict[str, WordEntry] = {}
    for entry in md_entries:
        md_lookup[entry.word] = entry

    all_words = set(db_entries.keys()) | set(md_lookup.keys())

    for word in all_words:
        in_md = word in md_lookup
        in_db = word in db_entries

        if in_md and not in_db:
            # Markdown-only → import to SQLite
            _import_md_entry(conn, md_lookup[word], book_id, chapter_id)
            result.added += 1

        elif in_db and not in_md:
            # DB-only → will be handled in phase 2 (regenerate MD)
            # We still count it as unchanged from the MD perspective;
            # phase 2 handles the actual file regeneration.
            pass

        elif in_md and in_db:
            # Both exist — check for differences
            md_entry = md_lookup[word]
            db_row = db_entries[word]

            if _entries_match(md_entry, db_row):
                result.unchanged += 1
            else:
                # Conflict: compare timestamps
                db_modified = datetime.fromisoformat(db_row["date_modified"])
                if file_mtime > db_modified:
                    # Markdown is newer → update SQLite
                    _update_db_from_md(conn, md_entry, db_row["id"])
                    result.updated += 1
                else:
                    # SQLite is newer (or equal) → regenerate MD later
                    # Mark as updated since the MD file will be rewritten
                    result.updated += 1

    # After processing all words, regenerate the MD file so it reflects
    # the authoritative state (handles DB-newer conflicts + DB-only words
    # that belong to this chapter).
    _regenerate_chapter_markdown(conn, vault_dir, chapter_id)
    conn.commit()


def _get_db_entries_for_chapter(
    conn: sqlite3.Connection, chapter_id: int
) -> dict[str, sqlite3.Row]:
    """Return a dict mapping word → Row for all entries in a chapter."""
    rows = conn.execute(
        """
        SELECT id, word, meaning, synonyms, context, book_id, chapter_id,
               date_added, date_modified, mastery_level, next_review
        FROM word_entries
        WHERE chapter_id = ?
        """,
        (chapter_id,),
    ).fetchall()
    return {row["word"]: row for row in rows}


def _entries_match(md_entry: WordEntry, db_row: sqlite3.Row) -> bool:
    """Check whether a parsed MD entry matches the DB row on content fields."""
    return (
        md_entry.meaning == db_row["meaning"]
        and md_entry.synonyms == (db_row["synonyms"] or "")
        and md_entry.context == (db_row["context"] or "")
        and md_entry.date_added.isoformat() == db_row["date_added"]
    )


def _import_md_entry(
    conn: sqlite3.Connection,
    entry: WordEntry,
    book_id: int,
    chapter_id: int,
) -> None:
    """Insert a Markdown-only entry into SQLite with mastery=0 and update FTS."""
    now = datetime.now()
    today = date.today()
    cursor = conn.execute(
        """
        INSERT INTO word_entries
            (word, meaning, synonyms, context, book_id, chapter_id,
             date_added, date_modified, mastery_level, next_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            entry.word,
            entry.meaning,
            entry.synonyms,
            entry.context,
            book_id,
            chapter_id,
            entry.date_added.isoformat(),
            now.isoformat(),
            today.isoformat(),
        ),
    )
    word_id = cursor.lastrowid

    # Update FTS index
    conn.execute(
        """
        INSERT INTO word_entries_fts(rowid, word, meaning, synonyms, context)
        VALUES (?, ?, ?, ?, ?)
        """,
        (word_id, entry.word, entry.meaning, entry.synonyms, entry.context),
    )


def _update_db_from_md(
    conn: sqlite3.Connection,
    md_entry: WordEntry,
    db_id: int,
) -> None:
    """Update an existing SQLite entry with values from the Markdown file."""
    # Read old values for FTS content-sync delete
    old_row = conn.execute(
        "SELECT word, meaning, synonyms, context FROM word_entries WHERE id = ?",
        (db_id,),
    ).fetchone()

    now = datetime.now()
    conn.execute(
        """
        UPDATE word_entries
        SET meaning = ?, synonyms = ?, context = ?, date_modified = ?
        WHERE id = ?
        """,
        (md_entry.meaning, md_entry.synonyms, md_entry.context, now.isoformat(), db_id),
    )

    # Update FTS index — content-sync tables require the special delete syntax
    if old_row is not None:
        conn.execute(
            """
            INSERT INTO word_entries_fts(word_entries_fts, rowid, word, meaning, synonyms, context)
            VALUES ('delete', ?, ?, ?, ?, ?)
            """,
            (db_id, old_row["word"], old_row["meaning"], old_row["synonyms"], old_row["context"]),
        )
    conn.execute(
        """
        INSERT INTO word_entries_fts(rowid, word, meaning, synonyms, context)
        VALUES (?, ?, ?, ?, ?)
        """,
        (db_id, md_entry.word, md_entry.meaning, md_entry.synonyms, md_entry.context),
    )


def _export_sqlite_only_entries(
    conn: sqlite3.Connection,
    vault_dir: str,
    md_seen_chapters: set[int],
    result: SyncResult,
) -> None:
    """Regenerate Markdown for chapters that have DB entries but no MD file.

    Any chapter whose entries were *not* encountered during the MD scan
    needs its Markdown file (re)generated.
    """
    all_chapter_rows = conn.execute(
        """
        SELECT DISTINCT c.id
        FROM chapters c
        JOIN word_entries w ON w.chapter_id = c.id
        """
    ).fetchall()

    for row in all_chapter_rows:
        chapter_id = row["id"]
        if chapter_id not in md_seen_chapters:
            # This chapter has DB entries but was not seen in any MD file
            _regenerate_chapter_markdown(conn, vault_dir, chapter_id)
            # Count each word in this chapter as "added" (to the MD side)
            count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM word_entries WHERE chapter_id = ?",
                (chapter_id,),
            ).fetchone()["cnt"]
            result.added += count
    conn.commit()
