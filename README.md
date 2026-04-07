# Vocabulary Vault 📚⚔️

A CLI tool that turns reading into a vocabulary RPG. Track new words from books you read, review them with spaced repetition, and level up your vocabulary.

## Features

- Organize vocabulary by **book** and **chapter**
- Store words with meanings, synonyms, and context
- **Spaced repetition** review system with mastery levels (0–5)
- Full-text search across your word collection
- XP tracking, streaks, and gamification stats
- SQLite-backed with Markdown vault export

## Installation

```bash
pip install -e .
```

## Usage

```bash
vault --help
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Tech Stack

- Python 3.10+
- Click (CLI framework)
- SQLite with FTS5 full-text search
- Hypothesis (property-based testing)

## License

MIT
