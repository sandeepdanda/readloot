"""SQLite database connection and schema management for ReadLoot."""

import sqlite3

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    folder_name TEXT NOT NULL UNIQUE,
    date_created TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    filename TEXT NOT NULL,
    date_created TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE(book_id, chapter_number)
);

CREATE TABLE IF NOT EXISTS word_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    meaning TEXT NOT NULL,
    synonyms TEXT DEFAULT '',
    context TEXT DEFAULT '',
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    date_added TEXT NOT NULL DEFAULT (date('now')),
    date_modified TEXT NOT NULL DEFAULT (datetime('now')),
    mastery_level INTEGER NOT NULL DEFAULT 0
        CHECK(mastery_level >= 0 AND mastery_level <= 5),
    next_review TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE(word, chapter_id)
);

CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL REFERENCES word_entries(id) ON DELETE CASCADE,
    review_date TEXT NOT NULL DEFAULT (date('now')),
    correct INTEGER NOT NULL,
    mastery_before INTEGER NOT NULL,
    mastery_after INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_stats (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    total_xp INTEGER NOT NULL DEFAULT 0,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    last_activity_date TEXT,
    wotd_last_shown TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS word_entries_fts USING fts5(
    word, meaning, synonyms, context,
    content='word_entries',
    content_rowid='id'
);

CREATE TABLE IF NOT EXISTS achievements (
    key TEXT PRIMARY KEY,
    earned_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Tracks which chapters the user has marked as read. A chapter's auto-extracted
-- words stay locked (far-future next_review) until a row appears here.
CREATE TABLE IF NOT EXISTS reading_progress (
    chapter_id INTEGER PRIMARY KEY REFERENCES chapters(id) ON DELETE CASCADE,
    read_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Local cache of Gutenberg/Gutendex metadata for imported books. Distinct from
-- the per-user `books` table: this is catalog data keyed by Gutenberg id.
CREATE TABLE IF NOT EXISTS book_catalog (
    gutenberg_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    cover_url TEXT NOT NULL DEFAULT '',
    download_url TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT 'en',
    cached_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO user_stats (id) VALUES (1);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply guarded, idempotent column additions.

    ``ALTER TABLE ADD COLUMN`` cannot use ``IF NOT EXISTS``, and this runs on
    every connection, so each add is gated on a ``PRAGMA table_info`` check.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(word_entries)")}
    if "source" not in cols:
        # Existing rows are manual entries; auto-extracted words set 'auto'.
        conn.execute(
            "ALTER TABLE word_entries ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'"
        )


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist, then apply migrations."""
    conn.executescript(_SCHEMA_SQL)
    _migrate(conn)
    conn.commit()


def get_db_connection(db_path: str = "vault.db") -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode, foreign keys, and Row factory.

    Automatically initialises the schema on every connection so callers never
    need to worry about missing tables.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn
