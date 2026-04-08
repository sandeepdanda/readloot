# Vocabulary Vault - Roadmap

Prioritized feature plan. Each phase builds on the previous one. Detailed research for each feature is in `research/`.

## Phase 1: Auto-Vocabulary from Books (MVP)

The core new feature. When a user adds a book, the system auto-generates vocabulary for every chapter.

**User flow:** User searches for a book -> adds it to library -> system extracts vocabulary per chapter in background -> chapters are locked by default -> user marks chapters as "read" to unlock words -> unlocked words enter the spaced repetition review queue.

**Technical approach:**
- Book source: Project Gutenberg (70k+ public domain books, fully legal, free API via Gutendex)
- NLP pipeline: spaCy tokenization -> wordfreq frequency scoring (Zipf < 4.0) -> cefrpy CEFR level (B2+) -> filter proper nouns -> take top 10-15 per chapter
- Definitions: WordNet via NLTK (offline, 155k words) with Free Dictionary API as fallback
- Spoiler prevention: chapter-gated visibility (words locked until chapter marked as read)
- Processing: FastAPI BackgroundTasks (a 300-page book processes in ~5-8 seconds)

**New dependencies:** spacy, wordfreq, cefrpy, ebooklib, beautifulsoup4, nltk

**Schema changes:**
- Add `reading_progress` table (user_id, chapter_id, read_at)
- Add `source` column to word_entries ('manual' or 'auto')
- Add `book_catalog` table for caching Gutenberg metadata

**New API endpoints:**
- GET /api/catalog/search?q= (search Gutenberg books)
- POST /api/catalog/import/{gutenberg_id} (trigger auto-extraction)
- POST /api/chapters/{id}/mark-read (unlock chapter words)

**New frontend pages/components:**
- Book catalog search page
- Chapter progress view with lock/unlock state
- "Mark as Read" button per chapter

**Research:** `research/auto-vocab-research.md`, `research/auto-vocab-ux-design.md`, `research/technical-architecture.md`

---

## Phase 2: Word Rarity and Evolution

Make the collection feel alive with RPG-style word rarity and visual evolution.

**Word rarity tiers** (based on real frequency data):
- Common (gray) - Zipf >= 5.0 - 1x XP
- Uncommon (green) - Zipf 4.0-4.9 - 2x XP
- Rare (blue) - Zipf 3.0-3.9 - 3x XP
- Epic (purple) - Zipf 2.0-2.9 - 4x XP
- Legendary (gold) - Zipf < 2.0 - 5x XP

**Word evolution** (visual stages as mastery increases):
- Mastery 0: Seed
- Mastery 1: Sprout
- Mastery 2: Sapling
- Mastery 3: Tree
- Mastery 4: Ancient Oak
- Mastery 5: Crystal Tree

Each stage gets a different icon/color in the UI. Users get attached to "growing" their words.

**Implementation:** Mostly frontend work. Add rarity tier calculation to word_service.py (one wordfreq lookup). Add evolution stage to WordResponse. Update frontend word cards with rarity colors and evolution icons.

**Research:** `research/gamification-deep-dive.md` (sections 1 and 4)

---

## Phase 3: FSRS Spaced Repetition

Replace SM-2 with the FSRS algorithm for 20-30% fewer reviews at the same retention rate.

**What FSRS does differently:** Uses a DSR model (Difficulty, Stability, Retrievability) with 19 parameters that adapt to the individual user's memory patterns. Instead of fixed intervals per mastery level, it calculates optimal review timing based on actual performance history.

**Migration path:**
- Add `fsrs_stability` and `fsrs_difficulty` columns to word_entries
- Bootstrap initial values from existing mastery levels
- Expand answer grading from binary (correct/wrong) to 4 levels (Again/Hard/Good/Easy)
- Run FSRS and SM-2 in parallel initially, switch when confident

**Research:** `research/smart-reading-companion.md` (section 5, includes full Python implementation)

---

## Phase 4: Smart Reading Companion

Turn the app from a vocabulary tracker into an intelligent reading partner.

**Vocabulary gap analysis:** Compare user's known words against a book's word index. "You know 94% of words in Sapiens but only 78% of Thinking Fast and Slow - read that next for maximum learning." Uses the i+1 comprehension hypothesis (95-98% coverage is the sweet spot).

**Cross-book concordance:** "You learned 'ephemeral' in Sapiens Chapter 3. It also appears in The Great Gatsby Chapter 5." Shows the same word across different books and contexts.

**Reading analytics:** Vocabulary acquisition rate, reading patterns, words per day graphs. Derived from existing timestamps in word_entries and review_history.

**Reading level assessment:** Map user's vocabulary count to CEFR bands (A1 ~500 words through C2 ~14,000 words). Suggest books at their level or slightly above.

**Research:** `research/smart-reading-companion.md`

---

## Phase 5: Advanced Gamification

**Boss battles:** Timed review sessions against themed bosses. "The Vocabulary Dragon" throws 20 words in 60 seconds. Beat it for rare achievements.

**Morpheme alchemy:** Show word roots, let users "craft" predictions. "pre" + "dict" = ? Teaches etymology through gameplay.

**Skill trees:** Three branches - Etymology Expert, Context Master, Speed Reader. Each unlocks different review modes and bonuses.

**Seasonal events:** Halloween vocabulary challenge, Spring Bloom reading marathon, etc.

**Research:** `research/gamification-deep-dive.md`

---

## Phase 6: Community and Growth

**Community vocabulary lists:** Users create and share vocabulary lists per book (like Quizlet sets but organized by chapter with spoiler protection). This becomes the content moat.

**Programmatic SEO:** Public vocabulary pages for every book targeting "[book name] vocabulary words" searches. SparkNotes built a business on this pattern.

**Epub upload:** User uploads their own epub files for copyrighted/modern books. Processed server-side, text never stored (only extracted word lists + dictionary definitions).

**Browser extension:** Highlight any word while reading online, one click to add to vault with context auto-captured.

**Monetization (if desired):** Freemium - free for 3 books, Pro ($4.99/mo) for unlimited. Don't gate spaced repetition behind paywall.

**Research:** `research/growth-and-monetization.md`

---

## Research Files Index

| File | Contents |
|------|----------|
| `research/auto-vocab-research.md` | Book content APIs, NLP pipeline, spoiler-free context, chapter detection, code examples |
| `research/auto-vocab-ux-design.md` | User flow design, spoiler prevention strategies, word quality filtering, legal analysis |
| `research/technical-architecture.md` | NLP benchmarks, book catalog search, difficulty scoring algorithm, definition sourcing, epub processing, offline-first design |
| `research/gamification-deep-dive.md` | RPG mechanics, social features, AI-powered features, reward systems, psychology principles, implementation priority matrix |
| `research/smart-reading-companion.md` | Reading analytics, vocabulary gap analysis, word relationship graphs, FSRS algorithm, reading level assessment |
| `research/growth-and-monetization.md` | Freemium model, community features, content partnerships, SEO strategy, open source community, platform expansion |
