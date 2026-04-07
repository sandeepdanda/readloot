"""Achievement system for Vocabulary Vault.

Tracks milestones like word counts, streaks, review performance, and
book collection. Each achievement is unlocked once and persisted in the
``achievements`` table.

See also: gamification.py, db.py, cli.py
"""

from __future__ import annotations

import sqlite3

ACHIEVEMENTS = {
    "first_word":     ("🌱", "First Steps",       "Added your first word"),
    "ten_words":      ("📖", "Bookworm Begins",   "Collected 10 words"),
    "fifty_words":    ("🧠", "Word Hoarder",      "Collected 50 words"),
    "hundred_words":  ("⚔️",  "Lexicon Warrior",   "Collected 100 words"),
    "streak_7":       ("🔥", "Week Warrior",       "7-day streak"),
    "streak_30":      ("💎", "Monthly Master",     "30-day streak"),
    "first_review":   ("🎯", "Quiz Apprentice",    "Completed first review"),
    "perfect_review": ("✨", "Flawless Victory",   "Perfect review session"),
    "five_books":     ("📚", "Library Builder",    "Added words from 5 books"),
    "mastery_5":      ("👑", "Word Master",        "Mastered a word to level 5"),
}


def check_achievements(
    conn: sqlite3.Connection,
    context: dict | None = None,
) -> list[str]:
    """Check for newly unlocked achievements and persist them.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection with schema initialized.
    context : dict | None
        Optional flags from the calling context:
        - ``first_review`` (bool): True if this was the user's first review
        - ``perfect_review`` (bool): True if the user got all answers correct
        - ``mastery_5`` (bool): True if a word just reached mastery level 5

    Returns
    -------
    list[str]
        Keys of achievements that were newly unlocked during this call.
    """
    if context is None:
        context = {}

    # Fetch already-earned achievement keys
    earned_rows = conn.execute("SELECT key FROM achievements").fetchall()
    earned_keys = {r["key"] for r in earned_rows}

    newly_unlocked: list[str] = []

    # --- Word count milestones ---
    word_count = conn.execute("SELECT COUNT(*) FROM word_entries").fetchone()[0]

    if word_count >= 1 and "first_word" not in earned_keys:
        newly_unlocked.append("first_word")
    if word_count >= 10 and "ten_words" not in earned_keys:
        newly_unlocked.append("ten_words")
    if word_count >= 50 and "fifty_words" not in earned_keys:
        newly_unlocked.append("fifty_words")
    if word_count >= 100 and "hundred_words" not in earned_keys:
        newly_unlocked.append("hundred_words")

    # --- Streak milestones ---
    streak_row = conn.execute(
        "SELECT current_streak, longest_streak FROM user_stats WHERE id = 1"
    ).fetchone()
    if streak_row:
        best_streak = max(streak_row["current_streak"], streak_row["longest_streak"])
        if best_streak >= 7 and "streak_7" not in earned_keys:
            newly_unlocked.append("streak_7")
        if best_streak >= 30 and "streak_30" not in earned_keys:
            newly_unlocked.append("streak_30")

    # --- Book count milestones ---
    book_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    if book_count >= 5 and "five_books" not in earned_keys:
        newly_unlocked.append("five_books")

    # --- Context-driven achievements ---
    if context.get("first_review") and "first_review" not in earned_keys:
        newly_unlocked.append("first_review")
    if context.get("perfect_review") and "perfect_review" not in earned_keys:
        newly_unlocked.append("perfect_review")
    if context.get("mastery_5") and "mastery_5" not in earned_keys:
        newly_unlocked.append("mastery_5")

    # Persist newly unlocked achievements
    for key in newly_unlocked:
        conn.execute(
            "INSERT OR IGNORE INTO achievements (key) VALUES (?)", (key,)
        )
    if newly_unlocked:
        conn.commit()

    return newly_unlocked


def show_achievement_toast(key: str) -> None:
    """Display a Rich Panel toast for a newly unlocked achievement.

    Falls back to plain click.echo if Rich is not available.

    Parameters
    ----------
    key : str
        The achievement key from :data:`ACHIEVEMENTS`.
    """
    if key not in ACHIEVEMENTS:
        return

    emoji, title, description = ACHIEVEMENTS[key]

    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        content = f"{emoji}  [bold]{title}[/bold]\n{description}"
        console.print(Panel(
            content,
            title="🏆 ACHIEVEMENT UNLOCKED",
            border_style="yellow",
            expand=False,
        ))
    except ImportError:
        import click
        click.echo(f"🏆 ACHIEVEMENT UNLOCKED: {emoji} {title} — {description}")


def list_achievements(conn: sqlite3.Connection) -> list[dict]:
    """Return all achievements with their earned status.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.

    Returns
    -------
    list[dict]
        Each dict has keys: ``key``, ``emoji``, ``title``, ``description``,
        ``earned`` (bool), ``earned_at`` (str or None).
    """
    earned_rows = conn.execute("SELECT key, earned_at FROM achievements").fetchall()
    earned_map = {r["key"]: r["earned_at"] for r in earned_rows}

    result = []
    for key, (emoji, title, description) in ACHIEVEMENTS.items():
        result.append({
            "key": key,
            "emoji": emoji,
            "title": title,
            "description": description,
            "earned": key in earned_map,
            "earned_at": earned_map.get(key),
        })
    return result
