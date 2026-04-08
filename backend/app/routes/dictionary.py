"""Dictionary lookup API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user

from readloot import dictionary

router = APIRouter(prefix="/api/dictionary", tags=["dictionary"])


@router.get("/lookup/{word}")
def lookup_word(word: str, _user: dict = Depends(get_current_user)):
    result = dictionary.lookup_word(word)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Word not found in dictionary: {word}")
    return result
