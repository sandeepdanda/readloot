"""Tests for book_service module — book/chapter CRUD and listing."""

import os

import pytest

from readloot.book_service import (
    create_book,
    create_chapter,
    get_book_details,
    list_books,
    sanitize_name,
)


# ---------------------------------------------------------------------------
# sanitize_name
# ---------------------------------------------------------------------------

class TestSanitizeName:
    def test_plain_name_unchanged(self):
        assert sanitize_name("Sapiens") == "Sapiens"

    def test_replaces_invalid_chars_with_underscore(self):
        assert sanitize_name('Book: "A Tale"') == "Book_ _A Tale_"

    def test_strips_leading_trailing_whitespace(self):
        assert sanitize_name("  Sapiens  ") == "Sapiens"

    def test_strips_leading_trailing_dots(self):
        assert sanitize_name("..hidden..") == "hidden"

    def test_all_invalid_chars(self):
        result = sanitize_name('<>:"|?*')
        assert result == "_______"

    def test_mixed_valid_and_invalid(self):
        result = sanitize_name("My Book: Chapter 1?")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result


# ---------------------------------------------------------------------------
# create_book
# ---------------------------------------------------------------------------

class TestCreateBook:
    def test_creates_folder_on_disk(self, db_conn, vault_dir):
        book = create_book(db_conn, vault_dir, "Sapiens")
        assert os.path.isdir(os.path.join(vault_dir, "Sapiens"))

    def test_returns_book_with_id(self, db_conn, vault_dir):
        book = create_book(db_conn, vault_dir, "Sapiens")
        assert book.id is not None
        assert book.name == "Sapiens"
        assert book.folder_name == "Sapiens"

    def test_sanitizes_folder_name(self, db_conn, vault_dir):
        book = create_book(db_conn, vault_dir, 'Book: "Quotes"')
        assert book.name == 'Book: "Quotes"'
        assert book.folder_name == "Book_ _Quotes_"
        assert os.path.isdir(os.path.join(vault_dir, "Book_ _Quotes_"))

    def test_inserts_db_record(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        row = db_conn.execute("SELECT name, folder_name FROM books WHERE name = ?", ("Sapiens",)).fetchone()
        assert row is not None
        assert row["name"] == "Sapiens"
        assert row["folder_name"] == "Sapiens"

    def test_duplicate_book_raises(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        with pytest.raises(Exception):
            create_book(db_conn, vault_dir, "Sapiens")


# ---------------------------------------------------------------------------
# create_chapter
# ---------------------------------------------------------------------------

class TestCreateChapter:
    def test_creates_markdown_file(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        chapter = create_chapter(db_conn, vault_dir, "Sapiens", "The Cognitive Revolution", 1)
        expected_path = os.path.join(vault_dir, "Sapiens", "01_The Cognitive Revolution.md")
        assert os.path.isfile(expected_path)

    def test_returns_chapter_with_id(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        chapter = create_chapter(db_conn, vault_dir, "Sapiens", "The Cognitive Revolution", 1)
        assert chapter.id is not None
        assert chapter.name == "The Cognitive Revolution"
        assert chapter.chapter_number == 1
        assert chapter.filename == "01_The Cognitive Revolution.md"

    def test_chapter_file_has_yaml_front_matter(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        create_chapter(db_conn, vault_dir, "Sapiens", "The Cognitive Revolution", 1)
        path = os.path.join(vault_dir, "Sapiens", "01_The Cognitive Revolution.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "---" in content
        assert 'book: "Sapiens"' in content
        assert 'chapter: "The Cognitive Revolution"' in content
        assert "chapter_number: 1" in content
        assert "word_count: 0" in content

    def test_inserts_db_record(self, db_conn, vault_dir):
        book = create_book(db_conn, vault_dir, "Sapiens")
        create_chapter(db_conn, vault_dir, "Sapiens", "The Cognitive Revolution", 1)
        row = db_conn.execute(
            "SELECT name, chapter_number, filename FROM chapters WHERE book_id = ?",
            (book.id,),
        ).fetchone()
        assert row is not None
        assert row["name"] == "The Cognitive Revolution"
        assert row["chapter_number"] == 1

    def test_nonexistent_book_raises(self, db_conn, vault_dir):
        with pytest.raises(ValueError, match="Book not found"):
            create_chapter(db_conn, vault_dir, "Nonexistent", "Ch1", 1)

    def test_chapter_number_formatting(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        ch = create_chapter(db_conn, vault_dir, "Sapiens", "Intro", 3)
        assert ch.filename == "03_Intro.md"


# ---------------------------------------------------------------------------
# list_books
# ---------------------------------------------------------------------------

class TestListBooks:
    def test_empty_vault(self, db_conn):
        result = list_books(db_conn)
        assert result == []

    def test_single_book_no_words(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        result = list_books(db_conn)
        assert len(result) == 1
        assert result[0]["name"] == "Sapiens"
        assert result[0]["chapter_count"] == 0
        assert result[0]["word_count"] == 0

    def test_book_with_chapters_and_words(self, db_conn, vault_dir):
        book = create_book(db_conn, vault_dir, "Sapiens")
        ch = create_chapter(db_conn, vault_dir, "Sapiens", "Ch1", 1)
        # Insert a word entry directly
        db_conn.execute(
            "INSERT INTO word_entries (word, meaning, book_id, chapter_id) VALUES (?, ?, ?, ?)",
            ("ephemeral", "short-lived", book.id, ch.id),
        )
        db_conn.commit()
        result = list_books(db_conn)
        assert result[0]["chapter_count"] == 1
        assert result[0]["word_count"] == 1

    def test_multiple_books(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        create_book(db_conn, vault_dir, "Atomic Habits")
        result = list_books(db_conn)
        assert len(result) == 2
        names = [r["name"] for r in result]
        assert "Sapiens" in names
        assert "Atomic Habits" in names


# ---------------------------------------------------------------------------
# get_book_details
# ---------------------------------------------------------------------------

class TestGetBookDetails:
    def test_book_not_found(self, db_conn):
        with pytest.raises(ValueError, match="Book not found"):
            get_book_details(db_conn, "Nonexistent")

    def test_book_with_no_chapters(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        details = get_book_details(db_conn, "Sapiens")
        assert details["name"] == "Sapiens"
        assert details["chapter_count"] == 0
        assert details["word_count"] == 0
        assert details["chapters"] == []

    def test_book_with_chapters_and_words(self, db_conn, vault_dir):
        book = create_book(db_conn, vault_dir, "Sapiens")
        ch1 = create_chapter(db_conn, vault_dir, "Sapiens", "Ch1", 1)
        ch2 = create_chapter(db_conn, vault_dir, "Sapiens", "Ch2", 2)
        # Add words
        db_conn.execute(
            "INSERT INTO word_entries (word, meaning, book_id, chapter_id, date_added) VALUES (?, ?, ?, ?, ?)",
            ("ephemeral", "short-lived", book.id, ch1.id, "2025-01-10"),
        )
        db_conn.execute(
            "INSERT INTO word_entries (word, meaning, book_id, chapter_id, date_added) VALUES (?, ?, ?, ?, ?)",
            ("ubiquitous", "everywhere", book.id, ch1.id, "2025-01-15"),
        )
        db_conn.execute(
            "INSERT INTO word_entries (word, meaning, book_id, chapter_id, date_added) VALUES (?, ?, ?, ?, ?)",
            ("cogent", "clear", book.id, ch2.id, "2025-02-01"),
        )
        db_conn.commit()

        details = get_book_details(db_conn, "Sapiens")
        assert details["chapter_count"] == 2
        assert details["word_count"] == 3

        ch1_detail = details["chapters"][0]
        assert ch1_detail["word_count"] == 2
        assert ch1_detail["earliest_entry"] == "2025-01-10"
        assert ch1_detail["latest_entry"] == "2025-01-15"

        ch2_detail = details["chapters"][1]
        assert ch2_detail["word_count"] == 1
        assert ch2_detail["earliest_entry"] == "2025-02-01"
        assert ch2_detail["latest_entry"] == "2025-02-01"

    def test_chapters_ordered_by_number(self, db_conn, vault_dir):
        create_book(db_conn, vault_dir, "Sapiens")
        create_chapter(db_conn, vault_dir, "Sapiens", "Later", 3)
        create_chapter(db_conn, vault_dir, "Sapiens", "First", 1)
        create_chapter(db_conn, vault_dir, "Sapiens", "Middle", 2)

        details = get_book_details(db_conn, "Sapiens")
        numbers = [ch["chapter_number"] for ch in details["chapters"]]
        assert numbers == [1, 2, 3]


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

import sqlite3
import tempfile

from hypothesis import given, settings, strategies as st

from readloot.book_service import sanitize_name, create_book, create_chapter, list_books
from readloot.db import init_schema


def _fresh_db():
    """Return a fresh in-memory SQLite connection with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


# Strategy: generate book names that contain at least one letter character,
# ensuring the sanitized result is non-empty.
_book_name_alphabet = st.characters(
    whitelist_categories=("L", "N", "P", "Z"),
    blacklist_characters="\x00/\\",
)
book_names_with_letters = st.text(
    alphabet=_book_name_alphabet, min_size=1, max_size=80
).filter(lambda s: any(c.isalpha() for c in s) and len(sanitize_name(s)) > 0)


# Feature: readloot, Property 4: Book Name Sanitization Preserves Original
class TestPropertyBookNameSanitization:
    """**Validates: Requirements 1.5**

    For any string containing characters invalid for filesystem paths, the
    sanitization function should produce a valid filesystem folder name, and
    the original unsanitized name should be stored in the Vault's ``name``
    field while the sanitized version is stored in ``folder_name``.
    """

    @given(name=book_names_with_letters)
    @settings(max_examples=100)
    def test_sanitized_name_is_filesystem_safe_and_original_preserved(self, name):
        """Sanitized folder name has no invalid FS chars; original name is kept."""
        invalid_chars = set('<>:"|?*')

        sanitized = sanitize_name(name)
        # The sanitized name must not contain any invalid filesystem characters
        assert not any(ch in invalid_chars for ch in sanitized), (
            f"Sanitized name {sanitized!r} still contains invalid chars"
        )
        # The sanitized name must not be empty (guaranteed by strategy filter)
        assert len(sanitized) > 0

        # When we create a book, the original name is stored in `name`
        # and the sanitized version in `folder_name`.
        conn = _fresh_db()
        try:
            with tempfile.TemporaryDirectory() as vault_dir:
                book = create_book(conn, vault_dir, name)
                assert book.name == name, "Original name must be preserved in book.name"
                assert book.folder_name == sanitized, (
                    "folder_name must equal the sanitized version"
                )

                # Verify the DB record matches
                row = conn.execute(
                    "SELECT name, folder_name FROM books WHERE id = ?", (book.id,)
                ).fetchone()
                assert row["name"] == name
                assert row["folder_name"] == sanitized
        finally:
            conn.close()


# Feature: readloot, Property 3: Book and Chapter Dual Creation
class TestPropertyBookChapterDualCreation:
    """**Validates: Requirements 1.1, 1.2**

    For any valid book name, creating a book should produce both a filesystem
    folder and a DB record. For any valid chapter added to an existing book,
    both a Markdown file and a chapters table record should be created.
    """

    @given(
        book_name=book_names_with_letters,
        chapter_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=1,
            max_size=60,
        ).filter(lambda s: s.strip() and any(c.isalpha() for c in s)),
        chapter_number=st.integers(min_value=1, max_value=99),
    )
    @settings(max_examples=100)
    def test_book_creates_folder_and_db_record_chapter_creates_file_and_db_record(
        self, book_name, chapter_name, chapter_number
    ):
        """Book creation → folder + DB row; chapter creation → .md file + DB row."""
        conn = _fresh_db()
        try:
            with tempfile.TemporaryDirectory() as vault_dir:
                # --- Book creation ---
                book = create_book(conn, vault_dir, book_name)

                # Filesystem folder must exist
                folder_path = os.path.join(vault_dir, book.folder_name)
                assert os.path.isdir(folder_path), f"Folder {folder_path} was not created"

                # DB record must exist
                book_row = conn.execute(
                    "SELECT id, name, folder_name FROM books WHERE id = ?", (book.id,)
                ).fetchone()
                assert book_row is not None, "Book DB record missing"
                assert book_row["name"] == book_name

                # --- Chapter creation ---
                chapter = create_chapter(
                    conn, vault_dir, book_name, chapter_name, chapter_number
                )

                # Markdown file must exist
                md_path = os.path.join(vault_dir, book.folder_name, chapter.filename)
                assert os.path.isfile(md_path), f"Chapter file {md_path} was not created"

                # DB record must exist
                ch_row = conn.execute(
                    "SELECT id, name, chapter_number, filename FROM chapters WHERE id = ?",
                    (chapter.id,),
                ).fetchone()
                assert ch_row is not None, "Chapter DB record missing"
                assert ch_row["name"] == chapter_name
                assert ch_row["chapter_number"] == chapter_number
        finally:
            conn.close()


# Feature: readloot, Property 27: Book and Chapter Count Accuracy
class TestPropertyBookChapterCountAccuracy:
    """**Validates: Requirements 1.3, 1.4**

    For any vault state, the book listing should report word counts and
    chapter counts that exactly match the actual number of word entries and
    chapters in the database for each book.
    """

    @given(
        num_chapters=st.integers(min_value=0, max_value=5),
        words_per_chapter=st.lists(
            st.integers(min_value=0, max_value=5), min_size=0, max_size=5
        ),
    )
    @settings(max_examples=100)
    def test_list_books_counts_match_actual_db_counts(
        self, num_chapters, words_per_chapter
    ):
        """list_books() word_count and chapter_count match actual DB rows."""
        conn = _fresh_db()
        try:
            with tempfile.TemporaryDirectory() as vault_dir:
                book = create_book(conn, vault_dir, "TestBook")

                # Create chapters (up to num_chapters)
                chapter_ids = []
                for i in range(num_chapters):
                    ch = create_chapter(
                        conn, vault_dir, "TestBook", f"Chapter {i + 1}", i + 1
                    )
                    chapter_ids.append(ch.id)

                # Insert words into chapters round-robin
                for idx, count in enumerate(words_per_chapter):
                    if not chapter_ids:
                        break
                    ch_id = chapter_ids[idx % len(chapter_ids)]
                    for w in range(count):
                        conn.execute(
                            "INSERT INTO word_entries (word, meaning, book_id, chapter_id) "
                            "VALUES (?, ?, ?, ?)",
                            (f"word_{idx}_{w}", f"meaning_{idx}_{w}", book.id, ch_id),
                        )
                conn.commit()

                # Verify via list_books
                books = list_books(conn)
                assert len(books) == 1
                reported = books[0]

                # Actual counts from DB
                actual_chapter_count = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM chapters WHERE book_id = ?", (book.id,)
                ).fetchone()["cnt"]
                actual_word_count = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM word_entries WHERE book_id = ?", (book.id,)
                ).fetchone()["cnt"]

                assert reported["chapter_count"] == actual_chapter_count, (
                    f"chapter_count mismatch: reported {reported['chapter_count']} "
                    f"vs actual {actual_chapter_count}"
                )
                assert reported["word_count"] == actual_word_count, (
                    f"word_count mismatch: reported {reported['word_count']} "
                    f"vs actual {actual_word_count}"
                )
        finally:
            conn.close()
