"""Spaced repetition review engine for ReadLoot.

Provides the logic functions for selecting due words, processing answers,
blanking words in context sentences, and querying the next review date.
The interactive review session is wired in the CLI layer since it needs
user I/O.

See also: models.py, gamification.py, db.py
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta

from readloot.models import WordEntry

# SM-2 inspired intervals: days until next review by mastery level.
REVIEW_INTERVALS = {0: 1, 1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def get_due_words(
    conn: sqlite3.Connection,
    scope: dict | None = None,
) -> list[WordEntry]:
    """Select words due for review (next_review <= today).

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialized.
    scope : dict | None
        Optional filter:
        - ``{"book": "name"}`` — only words from that book
        - ``{"chapter": "name", "book": "name"}`` — only words from that chapter
        - ``None`` — all words in the vault

    Returns
    -------
    list[WordEntry]
        Word entries due for review, with ``book_name`` and
        ``chapter_name`` populated.
    """
    today = date.today().isoformat()

    query = """
        SELECT w.id, w.word, w.meaning, w.synonyms, w.context,
               w.book_id, w.chapter_id, w.date_added, w.date_modified,
               w.mastery_level, w.next_review,
               b.name AS book_name, c.name AS chapter_name
        FROM word_entries w
        JOIN books b ON w.book_id = b.id
        JOIN chapters c ON w.chapter_id = c.id
        WHERE w.next_review <= ?
    """
    params: list = [today]

    if scope is not None:
        if "book" in scope:
            query += " AND b.name = ?"
            params.append(scope["book"])
        if "chapter" in scope:
            query += " AND c.name = ?"
            params.append(scope["chapter"])

    query += " ORDER BY w.next_review, w.mastery_level"

    rows = conn.execute(query, params).fetchall()

    return [_row_to_word_entry(r) for r in rows]


def process_answer(
    conn: sqlite3.Connection,
    word_id: int,
    correct: bool,
) -> tuple[int, date]:
    """Update mastery level and schedule the next review.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    word_id : int
        The word entry to update.
    correct : bool
        Whether the user answered correctly.

    Returns
    -------
    tuple[int, date]
        ``(new_mastery_level, next_review_date)``
    """
    row = conn.execute(
        "SELECT mastery_level FROM word_entries WHERE id = ?",
        (word_id,),
    ).fetchone()

    mastery_before = row["mastery_level"]
    today = date.today()

    if correct:
        new_mastery = min(mastery_before + 1, 5)
        next_review = today + timedelta(days=REVIEW_INTERVALS[new_mastery])
    else:
        new_mastery = 1
        next_review = today + timedelta(days=1)

    # Update the word entry
    conn.execute(
        """
        UPDATE word_entries
        SET mastery_level = ?, next_review = ?, date_modified = datetime('now')
        WHERE id = ?
        """,
        (new_mastery, next_review.isoformat(), word_id),
    )

    # Insert review history record
    conn.execute(
        """
        INSERT INTO review_history
            (word_id, review_date, correct, mastery_before, mastery_after)
        VALUES (?, ?, ?, ?, ?)
        """,
        (word_id, today.isoformat(), int(correct), mastery_before, new_mastery),
    )

    conn.commit()

    return (new_mastery, next_review)


def blank_word_in_context(word: str, context: str) -> str:
    """Replace *word* in *context* with ``"_____"`` (case-insensitive).

    Uses word-boundary matching so partial words are not replaced.
    If the word is not found in the context, returns the context unchanged.

    Parameters
    ----------
    word : str
        The vocabulary word to blank out.
    context : str
        The context sentence.

    Returns
    -------
    str
        The context with the word replaced by ``"_____"``.
    """
    # Escape the word for safe regex usage, then do case-insensitive replace
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    return pattern.sub("_____", context)


def get_next_review_date(conn: sqlite3.Connection) -> date | None:
    """Return the earliest next_review date across all word entries.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.

    Returns
    -------
    date | None
        The earliest scheduled review date, or ``None`` if no words exist.
    """
    row = conn.execute(
        "SELECT MIN(next_review) AS earliest FROM word_entries"
    ).fetchone()

    if row is None or row["earliest"] is None:
        return None

    return date.fromisoformat(row["earliest"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_word_entry(row: sqlite3.Row) -> WordEntry:
    """Convert a sqlite3.Row from the due-words query into a WordEntry."""
    return WordEntry(
        id=row["id"],
        word=row["word"],
        meaning=row["meaning"],
        synonyms=row["synonyms"],
        context=row["context"],
        book_id=row["book_id"],
        chapter_id=row["chapter_id"],
        book_name=row["book_name"],
        chapter_name=row["chapter_name"],
        date_added=date.fromisoformat(row["date_added"]),
        mastery_level=row["mastery_level"],
        next_review=date.fromisoformat(row["next_review"]),
    )
