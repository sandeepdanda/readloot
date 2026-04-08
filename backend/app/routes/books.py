"""Books API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.db import get_user_db
from app.schemas import BookDetailResponse, BookListItem, ChapterResponse

from readloot import book_service

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("", response_model=list[BookListItem])
def list_books(user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        books = book_service.list_books(conn)
        return [
            BookListItem(
                name=b["name"],
                chapter_count=b["chapter_count"],
                word_count=b["word_count"],
            )
            for b in books
        ]
    finally:
        conn.close()


@router.get("/{book_name}", response_model=BookDetailResponse)
def get_book_details(book_name: str, user: dict = Depends(get_current_user)):
    conn = get_user_db(user["user_id"])
    try:
        details = book_service.get_book_details(conn, book_name)
        return BookDetailResponse(
            name=details["name"],
            word_count=details["word_count"],
            chapter_count=details["chapter_count"],
            chapters=[
                ChapterResponse(
                    name=ch["name"],
                    chapter_number=ch["chapter_number"],
                    word_count=ch["word_count"],
                    earliest_entry=ch["earliest_entry"],
                    latest_entry=ch["latest_entry"],
                )
                for ch in details["chapters"]
            ],
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Book not found: {book_name}")
    finally:
        conn.close()
