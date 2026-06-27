"""Book catalog + auto-import API routes.

Search the curated public-domain catalog, import a book (fetch text, split
chapters, auto-extract gated vocabulary in the background), poll import status,
and mark a chapter read to unlock its words.
"""

from __future__ import annotations

import os
import threading

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.config import settings
from app.db import get_user_db
from app.schemas import (
    CatalogItem,
    ChapterProgressItem,
    ImportStatusResponse,
    MarkReadResponse,
)

from readloot import achievements, book_service, gamification, gutenberg, word_service
from readloot.vocab_extractor import extract_vocabulary

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

# In-process import status, keyed by (user_id, gutenberg_id). Fine for a
# single-worker personal app; a multi-worker deploy would move this to the DB.
_IMPORTS: dict[tuple[int, int], dict] = {}
_LOCK = threading.Lock()

_WORDS_PER_CHAPTER = 12


def _set_status(key, **fields):
    with _LOCK:
        _IMPORTS.setdefault(key, {}).update(fields)


@router.get("/search", response_model=list[CatalogItem])
def search(q: str = "", user: dict = Depends(get_current_user)):
    return [CatalogItem(**b) for b in gutenberg.search_catalog(q)]


def _run_import(user_id: int, gutenberg_id: int, title: str):
    """Background worker: fetch -> split -> extract gated vocab per chapter."""
    key = (user_id, gutenberg_id)
    vault_dir = os.path.join(settings.DATA_DIR, "vaults", str(user_id))
    os.makedirs(vault_dir, exist_ok=True)
    conn = get_user_db(user_id)
    try:
        _set_status(key, state="fetching", progress=0, total=0, words=0)
        text = gutenberg.fetch_book_text(gutenberg_id)
        chapters = gutenberg.split_chapters(text)
        _set_status(key, state="extracting", total=len(chapters))

        # Create the book if it doesn't exist yet.
        if conn.execute(
            "SELECT 1 FROM books WHERE name = ?", (title,)
        ).fetchone() is None:
            book_service.create_book(conn, vault_dir, title)

        total_words = 0
        for i, ch in enumerate(chapters, start=1):
            book_id = conn.execute(
                "SELECT id FROM books WHERE name = ?", (title,)
            ).fetchone()["id"]
            if conn.execute(
                "SELECT 1 FROM chapters WHERE book_id = ? AND name = ?",
                (book_id, ch["name"]),
            ).fetchone() is None:
                book_service.create_chapter(conn, vault_dir, title, ch["name"], i)

            vocab = extract_vocabulary(ch["text"], max_words=_WORDS_PER_CHAPTER)
            res = word_service.add_words_bulk(
                conn, vault_dir, title, ch["name"], vocab, source="auto", locked=True
            )
            total_words += res["inserted"]
            _set_status(key, progress=i, words=total_words)

        # Cache catalog metadata.
        entry = gutenberg._catalog_entry(gutenberg_id) or {}
        conn.execute(
            "INSERT OR REPLACE INTO book_catalog "
            "(gutenberg_id, title, author, language) VALUES (?, ?, ?, 'en')",
            (gutenberg_id, title, entry.get("author", "")),
        )
        conn.commit()
        _set_status(key, state="done", book_name=title)
    except Exception as exc:  # surface failure to the poller, don't crash worker
        _set_status(key, state="error", error=str(exc))
    finally:
        conn.close()


@router.post("/import/{gutenberg_id}", response_model=ImportStatusResponse)
def import_book(gutenberg_id: int, user: dict = Depends(get_current_user)):
    entry = gutenberg._catalog_entry(gutenberg_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Book not in catalog")
    key = (user["user_id"], gutenberg_id)
    with _LOCK:
        current = _IMPORTS.get(key, {}).get("state")
        if current in ("fetching", "extracting"):
            raise HTTPException(status_code=409, detail="Import already in progress")
        _IMPORTS[key] = {"state": "queued", "progress": 0, "total": 0, "words": 0}

    # Run in a daemon thread so the request returns immediately. (FastAPI
    # BackgroundTasks would also work; a thread keeps status pollable mid-run.)
    threading.Thread(
        target=_run_import,
        args=(user["user_id"], gutenberg_id, entry["title"]),
        daemon=True,
    ).start()
    return _status_response(gutenberg_id, key)


@router.get("/import/{gutenberg_id}/status", response_model=ImportStatusResponse)
def import_status(gutenberg_id: int, user: dict = Depends(get_current_user)):
    key = (user["user_id"], gutenberg_id)
    with _LOCK:
        if key not in _IMPORTS:
            raise HTTPException(status_code=404, detail="No import found")
    return _status_response(gutenberg_id, key)


def _status_response(gutenberg_id: int, key) -> ImportStatusResponse:
    with _LOCK:
        s = dict(_IMPORTS.get(key, {}))
    return ImportStatusResponse(
        gutenberg_id=gutenberg_id,
        state=s.get("state", "unknown"),
        progress=s.get("progress", 0),
        total=s.get("total", 0),
        words=s.get("words", 0),
        book_name=s.get("book_name"),
        error=s.get("error"),
    )


@router.get("/books/{book_name}/chapters", response_model=list[ChapterProgressItem])
def book_chapters(book_name: str, user: dict = Depends(get_current_user)):
    """Chapters for a book with id, word counts, and lock/read state.

    A chapter is locked when it has auto-words still parked at the far-future
    review date and no reading_progress row.
    """
    conn = get_user_db(user["user_id"])
    try:
        book = conn.execute(
            "SELECT id FROM books WHERE name = ?", (book_name,)
        ).fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.chapter_number,
                   COUNT(w.id) AS word_count,
                   SUM(CASE WHEN w.next_review = ? THEN 1 ELSE 0 END) AS locked_words,
                   (SELECT 1 FROM reading_progress rp WHERE rp.chapter_id = c.id) AS read_flag
            FROM chapters c
            LEFT JOIN word_entries w ON w.chapter_id = c.id
            WHERE c.book_id = ?
            GROUP BY c.id
            ORDER BY c.chapter_number
            """,
            (word_service.LOCKED_REVIEW_DATE, book["id"]),
        ).fetchall()
        return [
            ChapterProgressItem(
                id=r["id"],
                name=r["name"],
                chapter_number=r["chapter_number"],
                word_count=r["word_count"],
                is_read=bool(r["read_flag"]),
                is_locked=bool(r["locked_words"]) and not bool(r["read_flag"]),
            )
            for r in rows
        ]
    finally:
        conn.close()


@router.post("/chapters/{chapter_id}/mark-read", response_model=MarkReadResponse)
def mark_read(chapter_id: int, user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        if conn.execute(
            "SELECT 1 FROM chapters WHERE id = ?", (chapter_id,)
        ).fetchone() is None:
            raise HTTPException(status_code=404, detail="Chapter not found")

        res = word_service.mark_chapter_read(conn, chapter_id)

        xp_earned = 0
        new_xp = gamification.get_profile(conn)["total_xp"]
        # Reward only the first time a chapter is unlocked.
        if not res["already_read"] and res["newly_unlocked"] > 0:
            xp_earned = 15
            new_xp, _ = gamification.award_xp(conn, xp_earned)
            gamification.update_streak(conn)
            achievements.check_achievements(conn)

        return MarkReadResponse(
            chapter_id=chapter_id,
            newly_unlocked=res["newly_unlocked"],
            already_read=res["already_read"],
            xp_earned=xp_earned,
            new_total_xp=new_xp,
        )
    finally:
        conn.close()
