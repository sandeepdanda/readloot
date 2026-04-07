"""Gamification engine for Vocabulary Vault — XP, levels, streaks."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

READER_LEVELS = [
    (0, "Novice"),
    (100, "Page Turner"),
    (500, "Bookworm"),
    (1500, "Word Smith"),
    (5000, "Lexicon Lord"),
    (15000, "Vocabulary Vault Master"),
]


def get_reader_level(xp: int) -> str:
    """Return the Reader_Level name for a given XP total.

    Returns the highest level whose threshold is ≤ *xp*.
    """
    level_name = READER_LEVELS[0][1]
    for threshold, name in READER_LEVELS:
        if xp >= threshold:
            level_name = name
        else:
            break
    return level_name


def award_xp(conn: sqlite3.Connection, amount: int) -> tuple[int, str | None]:
    """Award *amount* XP and return ``(new_total_xp, new_level_name_or_None)``.

    *new_level_name* is only returned when the award causes a level-up;
    otherwise the second element is ``None``.
    """
    row = conn.execute("SELECT total_xp FROM user_stats WHERE id = 1").fetchone()
    old_xp = row["total_xp"]
    new_xp = old_xp + amount

    conn.execute("UPDATE user_stats SET total_xp = ? WHERE id = 1", (new_xp,))
    conn.commit()

    old_level = get_reader_level(old_xp)
    new_level = get_reader_level(new_xp)

    leveled_up = new_level != old_level
    return (new_xp, new_level if leveled_up else None)


def update_streak(conn: sqlite3.Connection) -> int:
    """Update the activity streak based on the current calendar day.

    Rules:
    * last_activity_date is yesterday → increment current_streak
    * last_activity_date is today → no change
    * last_activity_date is older or ``None`` → reset current_streak to 1
      (a new streak starts), after preserving longest_streak

    Always sets last_activity_date to today.  Returns the resulting
    current_streak value.
    """
    row = conn.execute(
        "SELECT current_streak, longest_streak, last_activity_date "
        "FROM user_stats WHERE id = 1"
    ).fetchone()

    current_streak: int = row["current_streak"]
    longest_streak: int = row["longest_streak"]
    last_activity: str | None = row["last_activity_date"]

    today = date.today()

    if last_activity is not None:
        last_date = date.fromisoformat(last_activity)
        if last_date == today:
            # Already active today — nothing to change.
            return current_streak
        elif last_date == today - timedelta(days=1):
            # Consecutive day — extend the streak.
            current_streak += 1
        else:
            # Missed at least one day — preserve longest, then reset.
            longest_streak = max(longest_streak, current_streak)
            current_streak = 1
    else:
        # First ever activity.
        current_streak = 1

    # longest_streak should always reflect the running max.
    longest_streak = max(longest_streak, current_streak)

    conn.execute(
        "UPDATE user_stats "
        "SET current_streak = ?, longest_streak = ?, last_activity_date = ? "
        "WHERE id = 1",
        (current_streak, longest_streak, today.isoformat()),
    )
    conn.commit()

    return current_streak


def get_profile(conn: sqlite3.Connection) -> dict:
    """Return the full user profile for display.

    Keys: total_xp, reader_level, current_streak, longest_streak,
    last_activity_date, total_words, total_books, next_level_name,
    xp_to_next_level.
    """
    row = conn.execute(
        "SELECT total_xp, current_streak, longest_streak, last_activity_date "
        "FROM user_stats WHERE id = 1"
    ).fetchone()

    total_xp: int = row["total_xp"]
    current_streak: int = row["current_streak"]
    longest_streak: int = row["longest_streak"]
    last_activity: str | None = row["last_activity_date"]

    reader_level = get_reader_level(total_xp)

    # Determine next level info.
    next_level_name: str | None = None
    xp_to_next: int = 0
    for threshold, name in READER_LEVELS:
        if threshold > total_xp:
            next_level_name = name
            xp_to_next = threshold - total_xp
            break

    # Aggregate counts from the database.
    total_words = conn.execute("SELECT COUNT(*) FROM word_entries").fetchone()[0]
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    return {
        "total_xp": total_xp,
        "reader_level": reader_level,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "last_activity_date": last_activity,
        "total_words": total_words,
        "total_books": total_books,
        "next_level_name": next_level_name,
        "xp_to_next_level": xp_to_next,
    }
