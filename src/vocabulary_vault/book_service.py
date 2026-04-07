"""Book and chapter management for Vocabulary Vault.

Handles creation, listing, and detail retrieval for books and chapters.
Book names are sanitized for filesystem safety while preserving the
original name in the database.

See also: models.py, markdown.py, db.py
"""

from __future__ import annotations

import os
import re
import sqlite3

from vocabulary_vault.markdown import generate_chapter_markdown
from vocabulary_vault.models import Book, Chapter


# Characters invalid in filesystem paths (Windows + common restrictions)
_INVALID_FS_CHARS = re.compile(r'[<>:"|?*]')


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a filesystem folder or file name.

    Replaces characters invalid for filesystem paths (<, >, :, ", |, ?, *)
    with underscores, then strips leading/trailing whitespace and dots.

    Parameters
    ----------
    name : str
        The original name to sanitize.

    Returns
    -------
    str
        A filesystem-safe version of the name.
    """
    sanitized = _INVALID_FS_CHARS.sub("_", name)
    sanitized = sanitized.strip().strip(".")
    return sanitized


def create_book(conn: sqlite3.Connection, vault_dir: str, name: str) -> Book:
    """Create a new book with a filesystem folder and database record.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialized.
    vault_dir : str
        Path to the vault root directory (e.g. ``"vault"``).
    name : str
        The original book name (may contain special characters).

    Returns
    -------
    Book
        The newly created Book with ``id`` populated.
    """
    folder_name = sanitize_name(name)

    # Create the folder on disk
    book_path = os.path.join(vault_dir, folder_name)
    os.makedirs(book_path, exist_ok=True)

    # Insert into database
    cursor = conn.execute(
        "INSERT INTO books (name, folder_name) VALUES (?, ?)",
        (name, folder_name),
    )
    conn.commit()

    row = conn.execute(
        "SELECT id, name, folder_name, date_created FROM books WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()

    return Book(
        id=row["id"],
        name=row["name"],
        folder_name=row["folder_name"],
    )


def create_chapter(
    conn: sqlite3.Connection,
    vault_dir: str,
    book_name: str,
    chapter_name: str,
    chapter_number: int,
) -> Chapter:
    """Create a new chapter with a Markdown file and database record.

    The chapter Markdown file is created at
    ``vault/{book_folder}/{chapter_number:02d}_{sanitized_chapter_name}.md``
    using :func:`generate_chapter_markdown` for the initial (empty) content.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialized.
    vault_dir : str
        Path to the vault root directory.
    book_name : str
        The original (unsanitized) book name — must already exist in the DB.
    chapter_name : str
        The chapter title.
    chapter_number : int
        The chapter number (used for ordering and filename prefix).

    Returns
    -------
    Chapter
        The newly created Chapter with ``id`` populated.
    """
    # Look up the book
    book_row = conn.execute(
        "SELECT id, folder_name FROM books WHERE name = ?",
        (book_name,),
    ).fetchone()
    if book_row is None:
        raise ValueError(f"Book not found: {book_name}")

    book_id = book_row["id"]
    book_folder = book_row["folder_name"]

    # Build the filename
    sanitized_chapter = sanitize_name(chapter_name)
    filename = f"{chapter_number:02d}_{sanitized_chapter}.md"

    # Create a Chapter object for markdown generation
    chapter = Chapter(
        book_id=book_id,
        name=chapter_name,
        chapter_number=chapter_number,
        filename=filename,
    )
    # Attach book_name so generate_chapter_markdown can resolve it
    chapter.book_name = book_name  # type: ignore[attr-defined]

    # Generate initial empty chapter markdown
    md_content = generate_chapter_markdown(chapter, [])

    # Write the file
    chapter_path = os.path.join(vault_dir, book_folder, filename)
    os.makedirs(os.path.dirname(chapter_path), exist_ok=True)
    with open(chapter_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Insert into database
    cursor = conn.execute(
        "INSERT INTO chapters (book_id, name, chapter_number, filename) VALUES (?, ?, ?, ?)",
        (book_id, chapter_name, chapter_number, filename),
    )
    conn.commit()

    row = conn.execute(
        "SELECT id, book_id, name, chapter_number, filename, date_created FROM chapters WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()

    return Chapter(
        id=row["id"],
        book_id=row["book_id"],
        name=row["name"],
        chapter_number=row["chapter_number"],
        filename=row["filename"],
    )


def list_books(conn: sqlite3.Connection) -> list[dict]:
    """List all books with their word counts and chapter counts.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.

    Returns
    -------
    list[dict]
        Each dict contains: ``name``, ``folder_name``, ``date_created``,
        ``word_count``, ``chapter_count``.
    """
    rows = conn.execute(
        """
        SELECT
            b.id,
            b.name,
            b.folder_name,
            b.date_created,
            COUNT(DISTINCT c.id) AS chapter_count,
            COUNT(w.id) AS word_count
        FROM books b
        LEFT JOIN chapters c ON c.book_id = b.id
        LEFT JOIN word_entries w ON w.book_id = b.id
        GROUP BY b.id
        ORDER BY b.name
        """
    ).fetchall()

    return [
        {
            "name": row["name"],
            "folder_name": row["folder_name"],
            "date_created": row["date_created"],
            "chapter_count": row["chapter_count"],
            "word_count": row["word_count"],
        }
        for row in rows
    ]


def get_book_details(conn: sqlite3.Connection, book_name: str) -> dict:
    """Get detailed information about a book including its chapters.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    book_name : str
        The original (unsanitized) book name.

    Returns
    -------
    dict
        Contains ``name``, ``folder_name``, ``date_created``,
        ``word_count``, ``chapter_count``, and ``chapters`` — a list of
        dicts each with ``name``, ``chapter_number``, ``filename``,
        ``date_created``, ``word_count``, ``earliest_entry``,
        ``latest_entry``.

    Raises
    ------
    ValueError
        If the book is not found.
    """
    book_row = conn.execute(
        "SELECT id, name, folder_name, date_created FROM books WHERE name = ?",
        (book_name,),
    ).fetchone()
    if book_row is None:
        raise ValueError(f"Book not found: {book_name}")

    book_id = book_row["id"]

    # Get chapters with per-chapter word counts and date ranges
    chapter_rows = conn.execute(
        """
        SELECT
            c.name,
            c.chapter_number,
            c.filename,
            c.date_created,
            COUNT(w.id) AS word_count,
            MIN(w.date_added) AS earliest_entry,
            MAX(w.date_added) AS latest_entry
        FROM chapters c
        LEFT JOIN word_entries w ON w.chapter_id = c.id
        WHERE c.book_id = ?
        GROUP BY c.id
        ORDER BY c.chapter_number
        """,
        (book_id,),
    ).fetchall()

    chapters = [
        {
            "name": row["name"],
            "chapter_number": row["chapter_number"],
            "filename": row["filename"],
            "date_created": row["date_created"],
            "word_count": row["word_count"],
            "earliest_entry": row["earliest_entry"],
            "latest_entry": row["latest_entry"],
        }
        for row in chapter_rows
    ]

    total_words = sum(ch["word_count"] for ch in chapters)

    return {
        "name": book_row["name"],
        "folder_name": book_row["folder_name"],
        "date_created": book_row["date_created"],
        "word_count": total_words,
        "chapter_count": len(chapters),
        "chapters": chapters,
    }
