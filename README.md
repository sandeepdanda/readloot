<div align="center">

# 📚⚔️ ReadLoot

### A vocabulary RPG that turns reading into a game.

Collect words from books. Review with spaced repetition. Earn XP. Level up. Unlock achievements.

[![CI](https://github.com/sandeepdanda/readloot/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeepdanda/readloot/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

</div>

---

## The Loop

```mermaid
graph LR
    A["📖 Read a book"] --> B["✍️ Collect words"]
    B --> C["🧠 Review"]
    C --> D["⚔️ Earn XP"]
    D --> E["📈 Level up"]
    E --> F["🏆 Achievements"]
    F --> A

    style A fill:#7c3aed,color:#fff,stroke:none
    style B fill:#7c3aed,color:#fff,stroke:none
    style C fill:#7c3aed,color:#fff,stroke:none
    style D fill:#7c3aed,color:#fff,stroke:none
    style E fill:#7c3aed,color:#fff,stroke:none
    style F fill:#7c3aed,color:#fff,stroke:none
```

Words come back at increasing intervals (1, 1, 3, 7, 14, 30 days) as you master them. Every correct answer earns XP, builds streaks, and unlocks achievements.

## Features

| | | |
|---|---|---|
| 🧠 **Spaced Repetition** | 6 mastery levels with SM-2 intervals | Words come back when you're about to forget |
| ⚔️ **XP & Levels** | Novice → Page Turner → Bookworm → Word Smith → Lexicon Lord → Master | +10 XP per word, +5 XP per correct review |
| 🔥 **Streaks** | Daily activity tracking | Consecutive days keep your streak alive |
| 🏆 **10 Achievements** | Word milestones, streak goals, perfect reviews | Animated toasts when you unlock them |
| ✨ **Word of the Day** | Date-seeded, mastery-weighted | Resurfaces words you haven't seen in a while |
| 📚 **Book Organization** | Words grouped by book and chapter | Browse your vocabulary by source |
| 🔍 **Full-text Search** | SQLite FTS5 | Search across words, meanings, synonyms, context |
| 🌙 **Dark/Light/System** | Three theme modes | PWA installable on mobile |

## Architecture

```mermaid
graph LR
    A["🖥️ Next.js 14\nTypeScript · Tailwind"] -->|REST + JWT| B["⚙️ FastAPI\n16 endpoints"] --> C["📦 Python Service Layer\nReview · XP · Achievements"] --> D[("💾 SQLite\nper user")]

    style A fill:#1e1b4b,color:#c4b5fd,stroke:#7c3aed
    style B fill:#1e1b4b,color:#c4b5fd,stroke:#7c3aed
    style C fill:#1e1b4b,color:#c4b5fd,stroke:#7c3aed
    style D fill:#7c3aed,color:#fff,stroke:none
```

Three layers, each independently usable. The backend imports the CLI package directly - one fix benefits both web and CLI.

## Gamification

```mermaid
graph LR
    L1["Novice\n0 XP"] --> L2["Page Turner\n100 XP"] --> L3["Bookworm\n500 XP"] --> L4["Word Smith\n1,500 XP"] --> L5["Lexicon Lord\n5,000 XP"] --> L6["ReadLoot Master\n15,000 XP"]

    style L1 fill:#6b7280,color:#fff,stroke:none
    style L2 fill:#3b82f6,color:#fff,stroke:none
    style L3 fill:#8b5cf6,color:#fff,stroke:none
    style L4 fill:#a855f7,color:#fff,stroke:none
    style L5 fill:#d946ef,color:#fff,stroke:none
    style L6 fill:#f59e0b,color:#fff,stroke:none
```

## Quick Start

```bash
git clone https://github.com/sandeepdanda/readloot.git
cd readloot

# Backend
pip install -e . && pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload    # http://localhost:8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev       # http://localhost:3000
```

Or use the CLI standalone:

```bash
pip install -e .
vault add "ephemeral" --book "Sapiens" --chapter "Ch 1" --meaning "lasting a short time"
vault review          # spaced repetition quiz
vault stats           # XP, level, streak
```

## What's Next

Auto-vocabulary extraction from books, word rarity tiers, FSRS algorithm, boss battles, and more. See [ROADMAP.md](ROADMAP.md).

For full architecture, API docs, schema, and security details: [PROJECT.md](PROJECT.md)

## License

MIT ([Full text](LICENSE))
