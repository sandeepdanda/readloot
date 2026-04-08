# Vocabulary Vault 📚⚔️

A vocabulary RPG that turns reading into a game. Collect words from books you read, review them with spaced repetition, earn XP, level up, and unlock achievements.

Available as a **web app** (Next.js + FastAPI) and a **CLI tool** (Python).

## Features

- **Spaced repetition** - SM-2 inspired review system with mastery levels 0-5 and increasing intervals
- **Gamification** - Earn XP, maintain streaks, climb from Novice to Vocabulary Vault Master
- **10 achievements** - First Steps, Bookworm Begins, Week Warrior, Flawless Victory, and more
- **Word of the Day** - Daily word from your vault, weighted toward words you know least
- **Full-text search** - Search across words, meanings, synonyms, and context sentences
- **Organize by book and chapter** - Trace every word back to where you found it
- **Dual storage** - SQLite for power, Markdown for readability, both always in sync
- **JSON export** - Export your entire vault for backup or analysis
- **Dark/light theme** - System-aware with manual toggle
- **PWA** - Install on your phone as a native-feeling app

## Web App

### Setup

```bash
git clone https://github.com/sandeepdanda/vocabulary-vault.git
cd vocabulary-vault

# Backend
pip install -e .
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload    # http://localhost:8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev       # http://localhost:3000
```

### Pages

| Page | What it does |
|------|-------------|
| Dashboard | XP stats, streak, Word of the Day, due review count |
| Add Word | Add words with book/chapter, auto-creates books |
| Review | Type-the-word review sessions with score tracking |
| Search | Full-text search across your vault |
| Books | Browse books and chapters with word counts |
| Stats | XP progress ring, level, streak history |
| Achievements | Grid of 10 achievements (earned/locked) |
| Settings | Theme toggle, export vault as JSON, logout |

## CLI

```bash
pip install -e ".[dev]"
```

```bash
vault add "ephemeral" --book "Sapiens" --chapter "The Cognitive Revolution" \
  --meaning "lasting for a very short time" \
  --synonyms "transient, fleeting" \
  --context "The ephemeral nature of early settlements left few traces."

vault review                    # Review all due words
vault review --book "Sapiens"   # Scope to a book
vault stats                     # XP, level, streak
vault books                     # List books
vault sync                      # Markdown <-> SQLite sync
vault export                    # JSON export
vault wotd                      # Word of the Day
```

## How It Works

All writes go through **SQLite first** (primary store with FTS5 search and gamification state). After every write, the corresponding **Markdown file is regenerated**. The `vault sync` command handles the reverse - edit a Markdown file by hand, sync imports it into SQLite.

The web backend doesn't reimplement business logic. It imports the CLI package directly and calls its service functions, so fixes to the service layer benefit both CLI and web.

### Gamification

| XP Threshold | Reader Level |
|-------------|-------------|
| 0 | Novice |
| 100 | Page Turner |
| 500 | Bookworm |
| 1,500 | Word Smith |
| 5,000 | Lexicon Lord |
| 15,000 | Vocabulary Vault Master |

+10 XP per word added, +5 XP per correct review answer. Streaks track consecutive days of activity.

### Review System

Mastery levels 0-5 with increasing review intervals (1, 1, 3, 7, 14, 30 days). Correct answers increase mastery. Wrong answers reset to level 1 with a review tomorrow.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Framer Motion |
| Backend | FastAPI, JWT auth (httpOnly cookies), per-user SQLite vaults |
| CLI | Python, Click, Rich |
| Database | SQLite (WAL mode, FTS5), Markdown files |

## Tests

```bash
python -m pytest tests/ -v              # CLI tests (47)
cd backend && python -m pytest tests/ -v # Backend tests (28)
```

## Deployment

Configured for Render.com (`render.yaml`) and Docker (`Dockerfile`). See [PROJECT.md](PROJECT.md) for full architecture details.

## License

MIT - The most popular open-source license in the world, originally written at MIT in 1987. It fits in a tweet: "Do whatever you want with this, just keep the copyright notice, and don't blame me if it breaks." ([Full text](LICENSE))
