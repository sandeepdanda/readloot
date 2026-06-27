# ReadLoot — North Star

Futuristic goals for this project. What it is today, where it's going, and the
next moves that take it to the next level. Update this as phases ship.

## What it is today

A vocabulary RPG that turns reading into a game. Three layers, each usable on
its own: a Python CLI service layer (`src/readloot/`), a FastAPI backend that
imports those services (per-user SQLite + JWT cookies), and a Next.js 14
frontend (TanStack Query, Tailwind, shadcn/ui, Framer Motion).

Shipped:
- v1: add words by hand, SM-2 spaced repetition, XP/levels/streaks, 10
  achievements, word-of-the-day, full-text search, gamified web UI.
- **Phase 1 (Auto-Vocab from Books):** import a public-domain book from a
  curated catalog, fetch real text from Project Gutenberg, split into chapters,
  auto-extract ~12 rare/B2+ words per chapter (spaCy + CEFR-J/Octanove 8,653
  graded words + wordfreq + offline WordNet definitions). Words are **locked**
  until the chapter is marked read, then flow into the review queue and award
  XP. Auto words read as `✨ Suggested`, manual as `🔖 Saved`.

Tests: 56 CLI + 34 API. One known pre-existing flake (`test_new_word_entry_defaults`,
UTC-vs-local date) left untouched.

## The vision

The reading companion that makes building a vocabulary feel like leveling a
character. You read anything, it quietly turns the words you meet into a
collection worth growing — spaced-repetition under the hood, RPG on the surface.
No subscriptions, no API bills: the NLP runs locally.

## Next level — roadmap (highest value first)

1. **Word rarity + evolution (ROADMAP Phase 2).** Zipf-derived rarity tiers
   (common→legendary, XP multipliers) and mastery evolution stages
   (seed→crystal tree). Mostly frontend; add a `rarity` field off the existing
   wordfreq lookup. Encode tier as a small corner gem, glow only on legendary.
2. **Live Gutendex search.** Replace the bundled catalog with the real Gutendex
   API once reachable (or self-host). One function swap: `gutenberg.search_catalog`.
3. **FSRS review engine (ROADMAP Phase 3).** Move from binary SM-2 to 4-level
   grading (Again/Hard/Good/Easy). Touches schema, `review_engine`, the answer
   route, and the review UI — plan as its own vertical slice.
4. **Definition quality.** WordNet is terse; add a richer offline source
   (self-hosted Wiktextract/kaikki.org JSONL) behind the existing fallback.
5. **Chapter-structure robustness.** Gutenberg `.txt` headings are noisy; harden
   `split_chapters` for books with parts/sections/none, strip license boilerplate
   better.

## Constraints that don't change

- No git commit/push — left to the human.
- Every external API must stay free. Verify before adding.
- Migrations are additive + idempotent (guarded `ALTER`, `CREATE IF NOT EXISTS`)
  — there is no migration framework; schema runs on every connect.
- Backend imports the CLI service layer; never reimplement business logic.
- Ship one roadmap phase at a time, evidence-first, before/after report on localhost.

## Working agreement (how to build here)

Mirror the proven loop: understand the seams → additive migration → service
layer first → backend → frontend → tests → browser-verify → localhost report.
Surgical changes, match existing idiom, reduced-motion-safe animations.
