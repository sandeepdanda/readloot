<div align="center">

# 📚⚔️ ReadLoot

**A vocabulary RPG that turns reading into a game.**

Collect words from books you read, review them with spaced repetition,
earn XP, level up, and unlock achievements.

[![CI](https://github.com/sandeepdanda/readloot/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeepdanda/readloot/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

[Web App](#-web-app) · [CLI](#-cli) · [How It Works](#-how-it-works) · [Roadmap](ROADMAP.md)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

🧠 **Spaced Repetition** - SM-2 review system with mastery levels 0-5

⚔️ **Gamification** - XP, streaks, levels from Novice to Vault Master

🏆 **10 Achievements** - First Steps, Week Warrior, Flawless Victory...

🔍 **Full-Text Search** - Search words, meanings, synonyms, context

</td>
<td width="50%">

✨ **Word of the Day** - Daily word, weighted toward least mastered

📚 **Book & Chapter** - Trace every word to where you found it

🌙 **Dark/Light Theme** - System-aware with manual toggle

📱 **PWA** - Install on your phone as a native app

</td>
</tr>
</table>

## 🌐 Web App

### Quick Start

```bash
git clone https://github.com/sandeepdanda/readloot.git
cd readloot

# Backend
pip install -e .
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload    # http://localhost:8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev       # http://localhost:3000
```

### Pages

| | Page | What it does |
|---|------|-------------|
| 🏠 | **Dashboard** | XP stats, streak, Word of the Day, due review count |
| ➕ | **Add Word** | Add words with book/chapter, auto-creates books |
| 🔄 | **Review** | Type-the-word sessions with score tracking |
| 🔍 | **Search** | Full-text search across your vault |
| 📚 | **Books** | Browse books and chapters with word counts |
| 📊 | **Stats** | XP progress ring, level, streak history |
| 🏆 | **Achievements** | Grid of 10 achievements (earned/locked) |
| ⚙️ | **Settings** | Theme toggle, export vault as JSON, logout |

## 💻 CLI

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

## 🔧 How It Works

```
┌──────────────────────────────────────────┐
│  Frontend (Next.js 14)                   │
│  Pages, gamification UI, PWA             │
├──────────────────────────────────────────┤
│  Backend (FastAPI)                       │
│  Auth, routing, per-user DB isolation    │
├──────────────────────────────────────────┤
│  CLI / Service Layer (Python)            │
│  All business logic lives here           │
│  SQLite + Markdown dual storage          │
└──────────────────────────────────────────┘
```

The backend imports the CLI package directly - no duplicated logic. Fixes to the service layer benefit both CLI and web.

> **Dual storage:** All writes go through SQLite first (FTS5 search, gamification state). After every write, the Markdown file is regenerated. `vault sync` handles the reverse direction.

### ⚔️ Gamification

| XP | Level |
|:---|:------|
| 0 | 🌱 Novice |
| 100 | 📖 Page Turner |
| 500 | 🐛 Bookworm |
| 1,500 | 🔨 Word Smith |
| 5,000 | 👑 Lexicon Lord |
| 15,000 | 🏰 ReadLoot Master |

> +10 XP per word added · +5 XP per correct review · Streaks track daily activity

### 🧠 Review System

Mastery levels 0-5 with increasing intervals: **1, 1, 3, 7, 14, 30 days**. Correct answers increase mastery. Wrong answers reset to level 1.

## 🛠 Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Framer Motion |
| **Backend** | FastAPI, JWT auth (httpOnly cookies), per-user SQLite vaults |
| **CLI** | Python, Click, Rich |
| **Database** | SQLite (WAL mode, FTS5), Markdown files |
| **CI/CD** | GitHub Actions |
| **Deploy** | Render.com, Docker |

## 🧪 Tests

```bash
python -m pytest tests/ -v              # CLI tests (47)
cd backend && python -m pytest tests/ -v # Backend tests (28)
```

## 🗺 What's Next

See [ROADMAP.md](ROADMAP.md) for the full feature plan, including:
- 📖 **Auto-vocabulary extraction** from books (Project Gutenberg + epub upload)
- 💎 **Word rarity tiers** (Common to Legendary with XP multipliers)
- 🌱 **Word evolution** (visual stages as mastery increases)
- 🧠 **FSRS algorithm** (smarter spaced repetition)
- 📊 **Vocabulary gap analysis** (book recommendations based on what you'd learn)
- 🐉 **Boss battles** (timed review sessions)

See [PROJECT.md](PROJECT.md) for full architecture details.

## 📄 License

MIT - The most popular open-source license in the world, originally written at MIT in 1987. It fits in a tweet: "Do whatever you want with this, just keep the copyright notice, and don't blame me if it breaks." ([Full text](LICENSE))
