"""Word management API routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.config import settings
from app.db import get_user_db
from app.schemas import AddWordResponse, WordCreateRequest
from app.utils import achievement_keys_to_responses, word_entry_to_response

from readloot import achievements, book_service, gamification, word_service

router = APIRouter(prefix="/api/words", tags=["words"])


@router.post("", response_model=AddWordResponse)
def add_word(body: WordCreateRequest, user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    vault_dir = os.path.join(settings.DATA_DIR, "vaults", str(user["user_id"]))
    os.makedirs(vault_dir, exist_ok=True)

    try:
        # Ensure book exists
        book_row = conn.execute(
            "SELECT id FROM books WHERE name = ?", (body.book_name,)
        ).fetchone()
        if book_row is None:
            book_service.create_book(conn, vault_dir, body.book_name)

        # Ensure chapter exists
        chapter_row = conn.execute(
            "SELECT c.id FROM chapters c JOIN books b ON c.book_id = b.id "
            "WHERE b.name = ? AND c.name = ?",
            (body.book_name, body.chapter_name),
        ).fetchone()
        if chapter_row is None:
            # Determine next chapter number
            book_row = conn.execute(
                "SELECT id FROM books WHERE name = ?", (body.book_name,)
            ).fetchone()
            max_num = conn.execute(
                "SELECT COALESCE(MAX(chapter_number), 0) FROM chapters WHERE book_id = ?",
                (book_row["id"],),
            ).fetchone()[0]
            book_service.create_chapter(
                conn, vault_dir, body.book_name, body.chapter_name, max_num + 1
            )

        result = word_service.add_word(
            conn,
            vault_dir,
            body.word,
            body.meaning,
            body.synonyms,
            body.context,
            body.book_name,
            body.chapter_name,
        )

        if result.get("duplicate"):
            existing = result["existing"]
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate word '{body.word}' already exists in this chapter",
            )

        entry = result["entry"]
        entry_resp = word_entry_to_response(entry)

        # Gamification
        new_xp, level_up = gamification.award_xp(conn, 10)
        streak = gamification.update_streak(conn)
        unlocked_keys = achievements.check_achievements(conn)
        unlocked = achievement_keys_to_responses(conn, unlocked_keys)

        return AddWordResponse(
            entry=entry_resp,
            xp_earned=10,
            new_total_xp=new_xp,
            level_up=level_up,
            streak=streak,
            achievements_unlocked=unlocked,
        )
    finally:
        conn.close()


@router.get("/lookup/{word}")
def lookup_word(word: str, user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        results = word_service.lookup_word(conn, word)
        return results
    finally:
        conn.close()


@router.get("/search")
def search_words(q: str = Query(""), user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        results = word_service.search_words(conn, q)
        return results
    finally:
        conn.close()


@router.get("/export")
def export_words(user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        return word_service.export_words(conn)
    finally:
        conn.close()
