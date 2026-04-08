"""Stats/profile API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_user_db
from app.schemas import ProfileResponse

from readloot import gamification
from readloot.gamification import READER_LEVELS

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        profile = gamification.get_profile(conn)

        # Compute current and next level thresholds for the progress bar
        total_xp = profile["total_xp"]
        current_threshold = 0
        next_threshold = None
        for threshold, _name in READER_LEVELS:
            if total_xp >= threshold:
                current_threshold = threshold
            else:
                next_threshold = threshold
                break

        return ProfileResponse(
            total_xp=profile["total_xp"],
            reader_level=profile["reader_level"],
            current_streak=profile["current_streak"],
            longest_streak=profile["longest_streak"],
            total_words=profile["total_words"],
            total_books=profile["total_books"],
            next_level_name=profile["next_level_name"],
            xp_to_next_level=profile["xp_to_next_level"],
            current_level_threshold=current_threshold,
            next_level_threshold=next_threshold,
        )
    finally:
        conn.close()
