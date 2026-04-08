# Vocabulary Vault - Project Reference

A vocabulary RPG that turns reading into a game. You read books, collect words you encounter, review them with spaced repetition, earn XP, level up, and unlock achievements.

## Architecture

Three layers, each independently usable:

```
┌─────────────────────────────────────────────┐
│  Frontend (Next.js 14)                      │
│  Pages, gamification UI, PWA                │
│  Talks to backend via REST + httpOnly JWT   │
├─────────────────────────────────────────────┤
│  Backend (FastAPI)                          │
│  Auth, routing, per-user DB isolation       │
│  Delegates business logic to CLI layer      │
├─────────────────────────────────────────────┤
│  CLI / Service Layer (Python package)       │
│  word_service, review_engine, gamification, │
│  book_service, achievements, wotd, sync     │
│  All state in SQLite + Markdown files       │
└─────────────────────────────────────────────┘
```

The backend does NOT reimplement business logic. It imports the CLI package (`vocabulary_vault`) and calls its service functions directly. Any fix to the service layer benefits both CLI and web.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| CLI | Python 3.10+, Click, Rich, SQLite, Markdown files |
| Backend | FastAPI, python-jose (JWT), passlib/bcrypt, pydantic-settings |
| Frontend | Next.js 14.2.29 (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Framer Motion, next-pwa |
| Database | SQLite per user (WAL mode, FTS5 full-text search) |
| CI | GitHub Actions (backend tests + frontend build on push) |
| Deployment | Render (render.yaml), Docker multi-stage (Dockerfile) |

## Directory Structure

```
vocabulary-vault/
├── src/vocabulary_vault/       # CLI package (service layer)
│   ├── cli.py                  # Click CLI commands
│   ├── models.py               # Dataclasses: Book, Chapter, WordEntry, ReviewRecord, UserStats
│   ├── db.py                   # SQLite schema init, connection factory
│   ├── word_service.py         # Add, lookup, search, export words
│   ├── book_service.py         # Create/list books and chapters
│   ├── review_engine.py        # SM-2 spaced repetition: due words, process answers
│   ├── gamification.py         # XP, reader levels, streaks
│   ├── achievements.py         # 10 milestone achievements
│   ├── wotd.py                 # Word of the Day (date-seeded, mastery-weighted)
│   ├── dictionary.py           # Local dictionary lookup from bundled JSON
│   ├── sync_engine.py          # Bidirectional Markdown <-> SQLite sync
│   ├── markdown.py             # Chapter Markdown generation and parsing
│   └── data/dictionary.json    # Bundled word dictionary
├── tests/                      # CLI service layer tests (47 tests)
│   ├── conftest.py
│   ├── test_db.py
│   ├── test_book_service.py
│   └── test_markdown.py
├── backend/                    # FastAPI web backend
│   ├── app/
│   │   ├── main.py             # App entry, CORS, router registration, generic error handler
│   │   ├── auth.py             # Register/login/logout, JWT (httpOnly cookies), get_current_user
│   │   ├── db.py               # Per-user SQLite resolver + get_db FastAPI dependency (auto-close)
│   │   ├── config.py           # Settings via pydantic-settings ConfigDict
│   │   ├── schemas.py          # Pydantic models with Field validation (min/max length)
│   │   ├── utils.py            # Shared helpers: word_entry_to_response, achievement_keys_to_responses
│   │   └── routes/
│   │       ├── words.py        # POST /api/words, GET /lookup, /search, /export
│   │       ├── books.py        # GET /api/books, /api/books/{name}
│   │       ├── review.py       # GET /due, POST /answer, POST /complete
│   │       ├── stats.py        # GET /api/stats/profile
│   │       ├── achievements.py # GET /api/achievements
│   │       ├── wotd.py         # GET /api/wotd
│   │       └── dictionary.py   # GET /api/dictionary/lookup/{word}
│   ├── tests/                  # Backend API tests (28 tests)
│   │   ├── conftest.py         # Isolated temp data dir, TestClient, auth fixtures
│   │   ├── test_auth.py        # Auth flow: register, login, logout, JWT, hashing
│   │   └── test_api.py         # All routes + 401 guards on all protected endpoints
│   └── requirements.txt
├── frontend/                   # Next.js 14 web frontend
│   ├── app/                    # App Router pages
│   │   ├── layout.tsx          # Root layout: ThemeProvider, QueryProvider, GamificationProvider
│   │   ├── page.tsx            # Dashboard: WOTD, stats grid, due review banner
│   │   ├── login/page.tsx      # Login/register form
│   │   ├── add/page.tsx        # Add word form with book/chapter selection
│   │   ├── review/page.tsx     # Review session: show meaning, type word, track score
│   │   ├── search/page.tsx     # Full-text search across vault
│   │   ├── books/page.tsx      # Book list
│   │   ├── books/[name]/page.tsx # Book detail with chapters
│   │   ├── stats/page.tsx      # XP, level, streak, progress ring
│   │   ├── achievements/page.tsx # Achievement grid (earned/locked)
│   │   └── settings/page.tsx   # Theme toggle, export vault, logout
│   ├── lib/
│   │   ├── api.ts              # Typed fetch wrapper, 16 API functions, 401 redirect
│   │   ├── types.ts            # TypeScript interfaces matching backend schemas
│   │   └── utils.ts            # cn() helper for Tailwind class merging
│   ├── components/
│   │   ├── navbar.tsx           # Desktop sidebar (8 items) + mobile bottom tab (5 items)
│   │   ├── app-shell.tsx        # Layout wrapper with navbar
│   │   ├── ui/                  # shadcn/ui primitives: button, card, input, badge, progress, textarea
│   │   └── gamification/        # XP popup, level-up overlay, achievement toast, streak display, XP ring
│   ├── providers/
│   │   ├── gamification-provider.tsx  # Queues XP -> level-up -> achievement animations
│   │   ├── query-provider.tsx         # TanStack Query client
│   │   └── theme-provider.tsx         # next-themes dark/light
│   ├── middleware.ts            # Auth guard: no token -> /login, has token on /login -> /
│   ├── public/
│   │   ├── manifest.json        # PWA manifest
│   │   └── icons/               # 192x192 and 512x512 PNG icons
│   └── next.config.js           # next-pwa config
├── research/                    # Feature research docs (see ROADMAP.md)
├── .github/workflows/ci.yml    # GitHub Actions: backend tests + frontend build
├── pyproject.toml               # CLI package config (pip install -e .)
├── Dockerfile                   # Multi-stage production container (Python 3.12 + Node 20)
├── render.yaml                  # Render.com deployment config
├── LICENSE                      # MIT
└── start.sh                     # Backend start script
```

## Database Schema

Single SQLite file per user at `data/vaults/{user_id}/vault.db`:

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `books` | Books being read | id, name, folder_name |
| `chapters` | Subdivisions of books | id, book_id, name, chapter_number, filename |
| `word_entries` | Vocabulary words | id, word, meaning, synonyms, context, book_id, chapter_id, mastery_level (0-5), next_review |
| `review_history` | Every review attempt | word_id, review_date, correct, mastery_before, mastery_after |
| `user_stats` | Single-row gamification state | total_xp, current_streak, longest_streak, last_activity_date |
| `achievements` | Earned achievements | key, earned_at |
| `word_entries_fts` | FTS5 virtual table for search | word, meaning, synonyms, context |

Separate `data/users.db` for auth (id, username, password_hash).

## API Endpoints

All routes except auth require a valid JWT in the `access_token` httpOnly cookie.

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/auth/register | Create user, set JWT cookie |
| POST | /api/auth/login | Authenticate, set JWT cookie |
| POST | /api/auth/logout | Clear JWT cookie |
| POST | /api/words | Add word (returns entry + XP + achievements) |
| GET | /api/words/lookup/{word} | Look up word across all books |
| GET | /api/words/search?q= | Full-text search |
| GET | /api/words/export | Export all words as JSON |
| GET | /api/books | List books with word/chapter counts |
| GET | /api/books/{name} | Book detail with chapters |
| GET | /api/review/due | Words due for review (optional book/chapter filter) |
| POST | /api/review/answer | Submit answer, get correct/incorrect + new mastery |
| POST | /api/review/complete | End session, award XP, check achievements |
| GET | /api/stats/profile | XP, level, streak, word/book counts |
| GET | /api/achievements | All 10 achievements with earned status |
| GET | /api/wotd | Word of the Day |
| GET | /api/dictionary/lookup/{word} | Local dictionary lookup |

## Gamification System

**XP and Levels:**
- Add word: +10 XP
- Review (per correct answer in session): +5 XP
- Levels: Novice (0) -> Page Turner (100) -> Bookworm (500) -> Word Smith (1500) -> Lexicon Lord (5000) -> Vocabulary Vault Master (15000)

**Streaks:**
- Consecutive daily activity tracked
- Yesterday = extend streak, today = no change, older = reset to 1

**Achievements (10 total):**
- first_word, ten_words, fifty_words, hundred_words (word count milestones)
- streak_7, streak_30 (streak milestones)
- first_review, perfect_review (review milestones)
- five_books (book collection)
- mastery_5 (master a word to level 5)

**Review System (SM-2 inspired):**
- Mastery levels 0-5, each with increasing review intervals: 1, 1, 3, 7, 14, 30 days
- Correct answer: mastery +1, schedule next review
- Wrong answer: reset mastery to 1, review tomorrow

## Security

- JWT auth via httpOnly cookies (not localStorage)
- Passwords hashed with bcrypt
- Password minimum 8 characters, username minimum 3 characters
- Input length limits on all word fields (word: 100, meaning: 1000, context: 2000)
- Generic error responses in production (no stack trace leaks)
- Per-user database isolation (separate SQLite files)

## Setup and Running

```bash
# 1. Install CLI package
cd vocabulary-vault
pip install -e .

# 2. CLI usage (standalone)
vault add          # Add a word interactively
vault review       # Start a review session
vault stats        # View your profile
vault books        # List your books

# 3. Backend
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload    # http://localhost:8000

# 4. Frontend
cd frontend && npm install && npm run dev       # http://localhost:3000

# 5. Run tests (run separately - shared conftest causes collision)
python -m pytest tests/ -v                      # CLI tests (47)
cd backend && python -m pytest tests/ -v        # Backend tests (28)
```

## Test Coverage

| Suite | Tests | What's covered |
|-------|-------|---------------|
| CLI (tests/) | 47 | Book/chapter CRUD, markdown generation/parsing/round-trip, DB schema, property-based tests |
| Backend auth (backend/tests/test_auth.py) | 9 | Register, login, logout, password hashing, JWT validation, 401 guards |
| Backend API (backend/tests/test_api.py) | 19 | All route handlers, gamification flow, duplicate detection, 401 on all protected endpoints |

## Known Issues

- `themeColor` in page metadata triggers Next.js 14 deprecation warnings (should use `viewport` export). Non-blocking.
- Running `pytest` from the project root with both `tests/` and `backend/tests/` causes a conftest import collision. Run them separately.
- 9 high-severity npm vulnerabilities remain in Next.js 14 transitive deps (unfixable without upgrading to Next.js 15).

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the prioritized feature plan and [research/](research/) for detailed technical research on each feature.
