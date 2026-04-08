"""FastAPI application entry point."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import init_users_db, router as auth_router
from app.config import settings
from app.routes import achievements, books, dictionary, review, stats, words, wotd

app = FastAPI(title="Vocabulary Vault API", version="0.1.0")

# CORS middleware - split comma-separated origins
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes (public)
app.include_router(auth_router)

# Include protected routes
app.include_router(words.router)
app.include_router(books.router)
app.include_router(review.router)
app.include_router(stats.router)
app.include_router(achievements.router)
app.include_router(wotd.router)
app.include_router(dictionary.router)

# Initialize users database on startup
init_users_db()


# Generic exception handler for consistent JSON error format
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Serve frontend static files in production
_frontend_out = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend", "out"
)
if os.path.isdir(_frontend_out):
    app.mount("/", StaticFiles(directory=_frontend_out, html=True), name="static")
