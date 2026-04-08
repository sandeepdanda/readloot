"""Shared helpers for route handlers."""

from __future__ import annotations

import sqlite3

from app.schemas import AchievementResponse, WordResponse
from vocabulary_vault import achievements


def word_entry_to_response(entry) -> WordResponse:
    """Convert a WordEntry dataclass to a WordResponse schema."""
    return WordResponse(
        id=entry.id,
        word=entry.word,
        meaning=entry.meaning,
        synonyms=entry.synonyms,
        context=entry.context,
        book_name=entry.book_name,
        chapter_name=entry.chapter_name,
        date_added=str(entry.date_added),
        mastery_level=entry.mastery_level,
    )


def achievement_keys_to_responses(conn: sqlite3.Connection, keys: list[str]) -> list[AchievementResponse]:
    """Convert newly unlocked achievement keys to AchievementResponse list."""
    all_achs = achievements.list_achievements(conn)
    return [
        AchievementResponse(
            key=a["key"],
            emoji=a["emoji"],
            title=a["title"],
            description=a["description"],
            earned=a["earned"],
            earned_at=a["earned_at"],
        )
        for a in all_achs
        if a["key"] in keys
    ]
