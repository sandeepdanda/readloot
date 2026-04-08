"""Data models for ReadLoot."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Book:
    """A book being read, stored as a folder in the Markdown structure."""

    id: int | None = None
    name: str = ""
    folder_name: str = ""  # sanitized filesystem name
    date_created: date = field(default_factory=date.today)


@dataclass
class Chapter:
    """A subdivision of a Book, stored as a single Markdown file."""

    id: int | None = None
    book_id: int = 0
    name: str = ""
    chapter_number: int = 0
    filename: str = ""  # e.g., "01_the_cognitive_revolution.md"
    date_created: date = field(default_factory=date.today)


@dataclass
class WordEntry:
    """A single vocabulary record with word, meaning, context, and metadata."""

    id: int | None = None
    word: str = ""
    meaning: str = ""
    synonyms: str = ""  # comma-separated
    context: str = ""
    book_id: int = 0
    chapter_id: int = 0
    book_name: str = ""
    chapter_name: str = ""
    date_added: date = field(default_factory=date.today)
    date_modified: datetime = field(default_factory=datetime.now)
    mastery_level: int = 0
    next_review: date = field(default_factory=date.today)


@dataclass
class ReviewRecord:
    """A record of a single word review attempt."""

    id: int | None = None
    word_id: int = 0
    review_date: date = field(default_factory=date.today)
    correct: bool = False
    mastery_before: int = 0
    mastery_after: int = 0


@dataclass
class UserStats:
    """Aggregate user statistics for gamification."""

    total_xp: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: date | None = None
    wotd_last_shown: date | None = None
