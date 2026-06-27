"""Tests for auto-vocabulary extraction and the gated bulk-insert path."""

from __future__ import annotations

import pytest

from readloot import book_service, review_engine, word_service
from readloot.vocab_extractor import (
    define,
    evolution_stage,
    extract_vocabulary,
    rarity_tier,
)

SAMPLE = (
    "The intricate machinery bewildered the apprentice, whose ephemeral "
    "patience dwindled with every recalcitrant cog. The melancholy fog "
    "enveloped the village. A cat slept and the happy children played."
) * 2


def test_extract_prioritizes_rare_words():
    res = extract_vocabulary(SAMPLE, max_words=8)
    words = {r["word"] for r in res}
    # Hard words kept; everyday words dropped.
    assert "ephemeral" in words or "melancholy" in words
    assert "cat" not in words
    assert "happy" not in words


def test_extract_results_have_definitions_and_are_ranked():
    res = extract_vocabulary(SAMPLE, max_words=8)
    assert all(r["meaning"] for r in res), "every result must carry a definition"
    ranks = [r["rank"] for r in res]
    assert ranks == sorted(ranks), "results sorted hardest/rarest first"


def test_extract_respects_max_words():
    assert len(extract_vocabulary(SAMPLE, max_words=3)) <= 3


def test_extract_empty_text_returns_empty():
    assert extract_vocabulary("", max_words=5) == []
    assert extract_vocabulary("   ", max_words=5) == []


def test_define_known_word():
    assert define("ephemeral")  # non-empty WordNet gloss


# --- Phase 2: rarity tiers ---

@pytest.mark.parametrize(
    "zipf, expected",
    [
        (7.0, "common"),     # very frequent
        (5.0, "common"),     # lower boundary of common (inclusive)
        (4.9, "uncommon"),
        (4.0, "uncommon"),   # lower boundary of uncommon
        (3.9, "rare"),
        (3.0, "rare"),       # lower boundary of rare
        (2.9, "epic"),
        (2.0, "epic"),       # lower boundary of epic
        (1.9, "legendary"),
        (0.0, "legendary"),  # unknown word -> rarest
    ],
)
def test_rarity_tier_boundaries(monkeypatch, zipf, expected):
    monkeypatch.setattr("wordfreq.zipf_frequency", lambda *a, **k: zipf)
    assert rarity_tier("anything") == expected


def test_rarity_tier_real_words():
    # Sanity check against real frequency data: 'the' is common, a rare word
    # is not. (Exact tier of rare words can shift with wordfreq data, so only
    # assert the unambiguous common case and ordering.)
    assert rarity_tier("the") == "common"


# --- Phase 2: evolution stages ---

@pytest.mark.parametrize(
    "mastery, expected",
    [
        (0, "seed"),
        (1, "sprout"),
        (2, "sapling"),
        (3, "tree"),
        (4, "ancient oak"),
        (5, "crystal tree"),
    ],
)
def test_evolution_stage_mapping(mastery, expected):
    assert evolution_stage(mastery) == expected


def test_evolution_stage_clamps_out_of_range():
    assert evolution_stage(-1) == "seed"
    assert evolution_stage(99) == "crystal tree"


@pytest.fixture
def vault(tmp_path):
    """A vault with one book + chapter, ready for bulk insert."""
    from readloot.db import get_db_connection

    vault_dir = str(tmp_path / "vault")
    db_path = str(tmp_path / "vault.db")
    conn = get_db_connection(db_path)
    book_service.create_book(conn, vault_dir, "Test Book")
    book_service.create_chapter(conn, vault_dir, "Test Book", "Chapter One", 1)
    chapter_id = conn.execute("SELECT id FROM chapters").fetchone()["id"]
    yield conn, vault_dir, chapter_id
    conn.close()


def test_bulk_insert_inserts_and_dedups(vault):
    conn, vault_dir, _ = vault
    words = [
        {"word": "ephemeral", "meaning": "short-lived"},
        {"word": "melancholy", "meaning": "thoughtful sadness"},
        {"word": "ephemeral", "meaning": "dup"},  # duplicate in same chapter
        {"word": "", "meaning": "no word"},        # invalid
    ]
    res = word_service.add_words_bulk(
        conn, vault_dir, "Test Book", "Chapter One", words
    )
    assert res == {"inserted": 2, "skipped": 2}
    count = conn.execute("SELECT COUNT(*) FROM word_entries").fetchone()[0]
    assert count == 2


def test_auto_words_are_locked_out_of_review(vault):
    conn, vault_dir, _ = vault
    word_service.add_words_bulk(
        conn, vault_dir, "Test Book", "Chapter One",
        [{"word": "ephemeral", "meaning": "short-lived"}],
    )
    # Locked auto-word must not be due for review.
    due = review_engine.get_due_words(conn)
    assert due == []
    row = conn.execute(
        "SELECT next_review, source FROM word_entries WHERE word = 'ephemeral'"
    ).fetchone()
    assert row["next_review"] == word_service.LOCKED_REVIEW_DATE
    assert row["source"] == "auto"


def test_mark_chapter_read_unlocks_words(vault):
    conn, vault_dir, chapter_id = vault
    word_service.add_words_bulk(
        conn, vault_dir, "Test Book", "Chapter One",
        [{"word": "ephemeral", "meaning": "short-lived"},
         {"word": "melancholy", "meaning": "thoughtful sadness"}],
    )
    res = word_service.mark_chapter_read(conn, chapter_id)
    assert res["newly_unlocked"] == 2
    assert res["already_read"] is False
    # Now both words are due.
    due = review_engine.get_due_words(conn)
    assert len(due) == 2


def test_mark_chapter_read_is_idempotent(vault):
    conn, vault_dir, chapter_id = vault
    word_service.add_words_bulk(
        conn, vault_dir, "Test Book", "Chapter One",
        [{"word": "ephemeral", "meaning": "short-lived"}],
    )
    word_service.mark_chapter_read(conn, chapter_id)
    res2 = word_service.mark_chapter_read(conn, chapter_id)
    assert res2["newly_unlocked"] == 0
    assert res2["already_read"] is True


def test_manual_words_unaffected_by_locking(vault):
    conn, vault_dir, _ = vault
    # A manual add goes through the existing path -> due immediately.
    word_service.add_word(
        conn, vault_dir, "serendipity", "luck", "", "", "Test Book", "Chapter One"
    )
    due = review_engine.get_due_words(conn)
    assert any(w.word == "serendipity" for w in due)
