"""Review session API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import get_user_db
from app.schemas import (
    ReviewAnswerRequest,
    ReviewAnswerResponse,
    ReviewSessionSummary,
    WordResponse,
)
from app.utils import achievement_keys_to_responses, word_entry_to_response

from vocabulary_vault import achievements, gamification, review_engine

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewCompleteRequest(BaseModel):
    correct_count: int
    total_count: int


@router.get("/due", response_model=list[WordResponse])
def get_due_words(
    book: str | None = Query(None),
    chapter: str | None = Query(None),
    user: dict = Depends(get_current_user),
):
    conn = get_user_db(user["user_id"])
    try:
        scope = None
        if book:
            scope = {"book": book}
            if chapter:
                scope["chapter"] = chapter

        due = review_engine.get_due_words(conn, scope)
        return [word_entry_to_response(w) for w in due]
    finally:
        conn.close()


@router.post("/answer", response_model=ReviewAnswerResponse)
def submit_answer(body: ReviewAnswerRequest, user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        # Look up the word to get the correct answer
        row = conn.execute(
            "SELECT word FROM word_entries WHERE id = ?", (body.word_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Word not found")

        correct_word = row["word"]
        is_correct = body.answer.strip().lower() == correct_word.strip().lower()

        new_mastery, next_review = review_engine.process_answer(
            conn, body.word_id, is_correct
        )

        return ReviewAnswerResponse(
            correct=is_correct,
            correct_word=correct_word,
            new_mastery=new_mastery,
            next_review=next_review.isoformat(),
        )
    finally:
        conn.close()


@router.post("/complete", response_model=ReviewSessionSummary)
def complete_review(body: ReviewCompleteRequest, user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        xp_earned = body.correct_count * 5
        new_xp, level_up = gamification.award_xp(conn, xp_earned)
        streak = gamification.update_streak(conn)

        # Build achievement context flags
        review_count = conn.execute("SELECT COUNT(*) FROM review_history").fetchone()[0]
        first_review = review_count <= body.total_count  # this batch is the first

        perfect_review = (
            body.correct_count == body.total_count and body.total_count > 0
        )

        # Check if any word reached mastery 5 in this session
        mastery_5 = False
        if body.correct_count > 0:
            m5_row = conn.execute(
                "SELECT COUNT(*) FROM word_entries WHERE mastery_level = 5"
            ).fetchone()
            mastery_5 = m5_row[0] > 0

        context = {
            "first_review": first_review,
            "perfect_review": perfect_review,
            "mastery_5": mastery_5,
        }
        unlocked_keys = achievements.check_achievements(conn, context)
        unlocked = achievement_keys_to_responses(conn, unlocked_keys)

        return ReviewSessionSummary(
            correct_count=body.correct_count,
            total_count=body.total_count,
            xp_earned=xp_earned,
            new_total_xp=new_xp,
            level_up=level_up,
            streak=streak,
            achievements_unlocked=unlocked,
        )
    finally:
        conn.close()
