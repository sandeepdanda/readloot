"""Word of the Day API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_user_db
from app.schemas import WotdResponse

from readloot import wotd

router = APIRouter(prefix="/api/wotd", tags=["wotd"])


@router.get("", response_model=WotdResponse | None)
def get_word_of_the_day(user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        entry = wotd.get_word_of_the_day(conn)
        if entry is None:
            return None
        return WotdResponse(
            word=entry.word,
            meaning=entry.meaning,
            synonyms=entry.synonyms,
            context=entry.context,
            book_name=entry.book_name,
            chapter_name=entry.chapter_name,
        )
    finally:
        conn.close()
