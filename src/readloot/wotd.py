"""Word of the Day service for ReadLoot.

Selects a daily word from the vault using a date-seeded random generator,
weighted toward lower mastery levels. Tracks banner display state via
user_stats.wotd_last_shown.

See also: models.py, db.py, gamification.py
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date

from readloot.models import WordEntry


def get_word_of_the_day(
    conn: sqlite3.Connection,
    today: date | None = None,
) -> WordEntry | None:
    """Select a deterministic Word of the Day, weighted toward lower mastery.

    Uses ``random.Random(today.isoformat())`` so the same word is returned
    for every call on the same date with the same vault contents.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialized.
    today : date | None
        The date seed. Defaults to ``date.today()`` when *None*.

    Returns
    -------
    WordEntry | None
        The selected word with ``book_name`` and ``chapter_name`` populated,
        or *None* if the vault is empty.
    """
    if today is None:
        today = date.today()

    rows = conn.execute(
        """
        SELECT w.id, w.word, w.meaning, w.synonyms, w.context,
               w.book_id, w.chapter_id, w.date_added, w.date_modified,
               w.mastery_level, w.next_review,
               b.name AS book_name, c.name AS chapter_name
        FROM word_entries w
        JOIN books b ON w.book_id = b.id
        JOIN chapters c ON w.chapter_id = c.id
        """,
    ).fetchall()

    if not rows:
        return None

    weights = [(6 - r["mastery_level"]) for r in rows]
    rng = random.Random(today.isoformat())
    chosen = rng.choices(rows, weights=weights, k=1)[0]

    return WordEntry(
        id=chosen["id"],
        word=chosen["word"],
        meaning=chosen["meaning"],
        synonyms=chosen["synonyms"],
        context=chosen["context"],
        book_id=chosen["book_id"],
        chapter_id=chosen["chapter_id"],
        book_name=chosen["book_name"],
        chapter_name=chosen["chapter_name"],
        date_added=date.fromisoformat(chosen["date_added"]),
        mastery_level=chosen["mastery_level"],
    )


def should_show_banner(
    conn: sqlite3.Connection,
    today: date | None = None,
) -> bool:
    """Return True if the WOTD banner has not been shown today.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    today : date | None
        Override for the current date. Defaults to ``date.today()``.
    """
    if today is None:
        today = date.today()

    row = conn.execute(
        "SELECT wotd_last_shown FROM user_stats WHERE id = 1",
    ).fetchone()

    if row is None or row["wotd_last_shown"] is None:
        return True

    return row["wotd_last_shown"] != today.isoformat()


def mark_banner_shown(
    conn: sqlite3.Connection,
    today: date | None = None,
) -> None:
    """Record that the WOTD banner was shown today.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    today : date | None
        Override for the current date. Defaults to ``date.today()``.
    """
    if today is None:
        today = date.today()

    conn.execute(
        "UPDATE user_stats SET wotd_last_shown = ? WHERE id = 1",
        (today.isoformat(),),
    )
    conn.commit()
