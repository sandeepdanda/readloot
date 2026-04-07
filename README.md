# Vocabulary Vault 📚⚔️

A Python CLI tool that turns reading into a vocabulary RPG. Every word you save earns XP. Every review session strengthens your memory. Your vault grows book by book, chapter by chapter — and you level up along the way.

Words are stored in two places: **Markdown files** (browsable on GitHub, diffable, human-readable) and a **SQLite database** (searchable, stats-ready, powers spaced repetition). They stay in sync.

## Features

- **Dual storage** — SQLite for power, Markdown for readability. Both always in sync.
- **Spaced repetition** — SM-2 inspired review system with mastery levels 0–5 and increasing intervals.
- **Gamification** — Earn XP, maintain streaks, and climb from Novice to Vocabulary Vault Master.
- **Word of the Day** — A daily word from your vault, weighted toward words you know least.
- **Full-text search** — Search across words, meanings, synonyms, and context sentences.
- **Organize by book & chapter** — Trace every word back to where you found it.
- **Markdown sync** — Edit Markdown files by hand, then sync back to the database.
- **JSON export** — Export your entire vault for backup or analysis.

## Installation

```bash
git clone https://github.com/your-username/vocabulary-vault.git
cd vocabulary-vault
pip install -e ".[dev]"
```

This installs the `vault` CLI command and dev dependencies (pytest, hypothesis).

## Quick Start

### Add a word

```bash
# Inline — fast, no prompts
vault add "ephemeral" --book "Sapiens" --chapter "The Cognitive Revolution" \
  --meaning "lasting for a very short time" \
  --synonyms "transient, fleeting, momentary" \
  --context "The ephemeral nature of early settlements left few traces."

# Interactive — just run add and follow the prompts
vault add
```

If you skip `--meaning` or `--synonyms`, the CLI suggests definitions from a built-in dictionary.

### Look up a word

```bash
vault lookup ephemeral
```

Shows the meaning, synonyms, and every occurrence across all books with context.

### Review words

```bash
# Review all due words
vault review

# Scope to a specific book
vault review --book "Sapiens"

# Scope to a specific chapter
vault review --book "Sapiens" --chapter "The Cognitive Revolution"
```

The review shows context sentences with the word blanked out. Type the word to answer. Correct answers increase mastery; incorrect answers reset it.

### Check your stats

```bash
vault stats
```

Displays your Reader Level, XP, streak, word count, and a progress bar to the next level.

### Browse your books

```bash
# List all books
vault books

# Show chapters and word counts for a book
vault books "Sapiens"
```

### Sync Markdown and SQLite

```bash
vault sync
```

Reconciles differences between your Markdown files and the database. Edit a `.md` file by hand, run sync, and the database picks up the changes (and vice versa).

### Export to JSON

```bash
vault export
vault export --output my_words.json
```

### Word of the Day

```bash
vault wotd
```

Same word all day (date-seeded), weighted toward words you haven't mastered yet. Also appears as a banner when you run any command.

## Project Structure

```
vocabulary-vault/
├── src/vocabulary_vault/
│   ├── cli.py              # Click commands (vault add, lookup, review, ...)
│   ├── db.py               # SQLite connection, schema, FTS5
│   ├── models.py           # Dataclasses: WordEntry, Book, Chapter, UserStats
│   ├── markdown.py         # Markdown generation and parsing
│   ├── word_service.py     # Add, lookup, search, export words
│   ├── book_service.py     # Book/chapter CRUD and filesystem management
│   ├── review_engine.py    # Spaced repetition logic and review sessions
│   ├── gamification.py     # XP, levels, streaks
│   ├── sync_engine.py      # Markdown ↔ SQLite reconciliation
│   ├── wotd.py             # Word of the Day selection
│   ├── dictionary.py       # Local dictionary lookup
│   └── data/
│       └── dictionary.json # Bundled dictionary for suggestions
├── tests/                  # Unit + property-based tests (Hypothesis)
├── vault/                  # Default Markdown store (your word files live here)
├── examples/               # Sample content to see the format
│   └── sapiens/
│       ├── 01_the_cognitive_revolution.md
│       └── 02_the_agricultural_revolution.md
└── pyproject.toml
```

## How It Works

### Dual Storage Philosophy

All writes go through **SQLite first** — it's the primary store with foreign keys, FTS5 search, and gamification state. After every write, the corresponding **Markdown file is regenerated** from the database.

The Markdown files are the human-friendly layer: organized by `vault/{book}/{chapter}.md`, with YAML front matter and clean formatting. They're meant to be browsed on GitHub and tracked in version control.

The `vault sync` command handles the reverse direction — if you edit a Markdown file by hand (or add one manually), sync imports it into SQLite.

### Chapter File Format

```markdown
---
book: "Sapiens"
chapter: "The Cognitive Revolution"
chapter_number: 1
word_count: 5
---

## ephemeral

- **Meaning:** lasting for a very short time
- **Synonyms:** transient, fleeting, momentary
- **Context:** "The ephemeral nature of early settlements left few traces."
- **Date Added:** 2025-01-15
```

### Gamification

| XP Threshold | Reader Level            |
| ------------ | ----------------------- |
| 0            | Novice                  |
| 100          | Page Turner             |
| 500          | Bookworm                |
| 1,500        | Word Smith              |
| 5,000        | Lexicon Lord            |
| 15,000       | Vocabulary Vault Master |

- **+10 XP** for every word added
- **+5 XP** per correct review answer
- Streaks track consecutive days of activity

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Open a pull request

Tests use [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing alongside standard pytest unit tests.

## License

MIT
