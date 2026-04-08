"""Achievements API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.db import get_user_db
from app.schemas import AchievementResponse

from readloot import achievements as ach_module

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("", response_model=list[AchievementResponse])
def list_achievements(user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        all_achs = ach_module.list_achievements(conn)
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
        ]
    finally:
        conn.close()
