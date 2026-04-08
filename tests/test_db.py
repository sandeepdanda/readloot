"""Property-based tests for the database layer."""

import sqlite3
from datetime import date

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from readloot.db import init_schema


# Feature: readloot, Property 8: Referential Integrity Enforcement
# Validates: Requirements 4.6
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    book_id=st.integers(min_value=1001, max_value=999999),
    chapter_id=st.integers(min_value=1001, max_value=999999),
)
def test_referential_integrity_enforcement(db_conn, book_id, chapter_id):
    """For any attempt to insert a word entry with a non-existent book_id or
    chapter_id, the database should raise an integrity error."""
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            """
            INSERT INTO word_entries (word, meaning, book_id, chapter_id)
            VALUES (?, ?, ?, ?)
            """,
            ("testword", "a test meaning", book_id, chapter_id),
        )
    db_conn.rollback()


# Feature: readloot, Property 29: New Word Entry Defaults
# Validates: Requirements 2.3
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    word=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
    meaning=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "Z"))),
)
def test_new_word_entry_defaults(db_conn, word, meaning):
    """For any newly added word entry, the mastery_level should be 0 and the
    next_review date should be today."""
    # Create a valid book and chapter for foreign key constraints
    db_conn.execute(
        "INSERT OR IGNORE INTO books (id, name, folder_name) VALUES (1, 'TestBook', 'testbook')"
    )
    db_conn.execute(
        "INSERT OR IGNORE INTO chapters (id, book_id, name, chapter_number, filename) "
        "VALUES (1, 1, 'Chapter 1', 1, '01_chapter_1.md')"
    )

    # Delete any prior word entry to avoid UNIQUE constraint violations
    db_conn.execute("DELETE FROM word_entries WHERE word = ? AND chapter_id = 1", (word,))

    # Insert a word entry with only required fields — let defaults apply
    db_conn.execute(
        "INSERT INTO word_entries (word, meaning, book_id, chapter_id) VALUES (?, ?, 1, 1)",
        (word, meaning),
    )

    row = db_conn.execute(
        "SELECT mastery_level, next_review FROM word_entries WHERE word = ? AND chapter_id = 1",
        (word,),
    ).fetchone()

    assert row is not None, "Inserted word entry should be queryable"
    assert row["mastery_level"] == 0, f"Default mastery_level should be 0, got {row['mastery_level']}"
    assert row["next_review"] == date.today().isoformat(), (
        f"Default next_review should be today ({date.today().isoformat()}), got {row['next_review']}"
    )

    # Clean up for next hypothesis iteration
    db_conn.execute("DELETE FROM word_entries WHERE word = ? AND chapter_id = 1", (word,))
    db_conn.commit()
