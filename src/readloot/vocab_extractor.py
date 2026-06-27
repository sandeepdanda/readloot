"""Auto-vocabulary extraction from book text.

Given a chapter's plain text, pick the words most worth learning: rare,
B2-and-above, real dictionary words (not proper nouns or stopwords). Each
candidate gets an offline WordNet definition.

Pipeline: spaCy tokenize+lemmatize -> filter by part-of-speech and shape ->
score difficulty (CEFR-J/Octanove level, falling back to wordfreq Zipf) ->
take the top N rarest per chapter.

The NLP model and wordlists load once on first use. spaCy runs with the
parser and NER excluded — vocab extraction needs only the tokenizer, tagger,
and lemmatizer, and dropping the other two is the main speed/memory win.

See also: word_service.add_words_bulk (the batch insert path this feeds).
"""

from __future__ import annotations

import functools
import json
import os
import re
from importlib import resources

# CEFR levels we treat as "worth learning". A1-B1 are everyday words.
_LEARN_LEVELS = {"B2", "C1", "C2"}
# Words absent from the CEFR profile are judged by frequency: a Zipf below
# this (log10 occurrences per billion words) reads as uncommon enough to keep.
_ZIPF_KEEP_BELOW = 4.0
# spaCy parts of speech that carry learnable vocabulary.
_KEEP_POS = {"NOUN", "VERB", "ADJ", "ADV"}
_MIN_LEN = 3
_ALPHA = re.compile(r"^[a-z]+$")


@functools.lru_cache(maxsize=1)
def _nlp():
    """Load en_core_web_sm once, without the parser/NER (faster, lighter)."""
    import spacy

    return spacy.load("en_core_web_sm", exclude=["parser", "ner"])


@functools.lru_cache(maxsize=1)
def _cefr_levels() -> dict[str, str]:
    """Combined CEFR-J + Octanove headword -> level map (bundled JSON)."""
    with resources.files("readloot.data").joinpath("cefr_levels.json").open(
        encoding="utf-8"
    ) as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def _wordnet():
    """NLTK WordNet corpus reader, loaded once."""
    from nltk.corpus import wordnet

    # Force the lazy corpus to initialise so failures surface here, not mid-loop.
    wordnet.ensure_loaded()
    return wordnet


def _difficulty_rank(lemma: str) -> float | None:
    """Lower rank == harder/rarer == higher learning priority.

    Returns ``None`` for words that are too common to bother with. CEFR level
    decides when known; otherwise wordfreq Zipf is the tie-breaker so rarer
    words sort first.
    """
    from wordfreq import zipf_frequency

    zipf = zipf_frequency(lemma, "en")
    level = _cefr_levels().get(lemma)
    if level is not None:
        if level not in _LEARN_LEVELS:
            return None
        # C2 hardest -> smallest rank. Blend in Zipf to break ties within a level.
        level_weight = {"B2": 3.0, "C1": 2.0, "C2": 1.0}[level]
        return level_weight + zipf / 100.0
    # Not in the CEFR profile: keep only if genuinely uncommon by frequency.
    if zipf == 0.0 or zipf >= _ZIPF_KEEP_BELOW:
        return None
    # Map onto the same scale, just above the CEFR band so graded words win ties.
    return 3.5 + zipf / 100.0


# Rarity tiers by wordfreq Zipf (log10 occurrences per billion words). Lower
# Zipf == rarer. Boundaries are inclusive at the lower edge of each band.
_RARITY_BANDS = (
    (5.0, "common"),
    (4.0, "uncommon"),
    (3.0, "rare"),
    (2.0, "epic"),
)

# Mastery level (0-5) -> visual evolution stage name.
_EVOLUTION_STAGES = (
    "seed",        # 0
    "sprout",      # 1
    "sapling",     # 2
    "tree",        # 3
    "ancient oak", # 4
    "crystal tree",# 5
)


def rarity_tier(word: str) -> str:
    """Map a word to an RPG rarity tier from its wordfreq Zipf frequency.

    Tiers: common (Zipf >= 5.0), uncommon (4.0-4.9), rare (3.0-3.9),
    epic (2.0-2.9), legendary (< 2.0). Unknown words (Zipf 0.0) read as
    legendary — they are the rarest of all.
    """
    from wordfreq import zipf_frequency

    zipf = zipf_frequency(word, "en")
    for threshold, tier in _RARITY_BANDS:
        if zipf >= threshold:
            return tier
    return "legendary"


def evolution_stage(mastery_level: int) -> str:
    """Map a mastery level (0-5) to its visual evolution stage.

    Values are clamped to the 0-5 range so out-of-band input degrades to the
    nearest stage rather than raising.
    """
    idx = max(0, min(mastery_level, len(_EVOLUTION_STAGES) - 1))
    return _EVOLUTION_STAGES[idx]


def define(word: str) -> str:
    """First WordNet gloss for a word, or '' if none. Offline, no network."""
    try:
        synsets = _wordnet().synsets(word)
    except Exception:
        return ""
    if not synsets:
        return ""
    return synsets[0].definition()


def synonyms_for(word: str, limit: int = 5) -> str:
    """Comma-separated WordNet synonyms (lemma names), excluding the word itself."""
    try:
        synsets = _wordnet().synsets(word)
    except Exception:
        return ""
    seen: list[str] = []
    for syn in synsets:
        for lemma in syn.lemmas():
            name = lemma.name().replace("_", " ")
            if name.lower() != word.lower() and name not in seen:
                seen.append(name)
            if len(seen) >= limit:
                return ", ".join(seen)
    return ", ".join(seen)


def extract_vocabulary(text: str, max_words: int = 12) -> list[dict]:
    """Pick the top vocabulary candidates from a block of chapter text.

    Parameters
    ----------
    text : str
        The chapter's plain text.
    max_words : int
        Cap on candidates returned (the rarest ``max_words``).

    Returns
    -------
    list[dict]
        Each: ``{"word", "meaning", "synonyms", "cefr", "rank"}``. ``word`` is
        the lemma in lower case. Sorted hardest/rarest first. Words with no
        WordNet definition are dropped (nothing to teach).
    """
    if not text or not text.strip():
        return []

    nlp = _nlp()
    levels = _cefr_levels()
    # best candidate per lemma: keep the lowest (hardest) rank seen
    best: dict[str, float] = {}
    for token in nlp(text):
        if token.pos_ not in _KEEP_POS or token.is_stop:
            continue
        lemma = token.lemma_.lower().strip()
        if len(lemma) < _MIN_LEN or not _ALPHA.match(lemma):
            continue
        rank = _difficulty_rank(lemma)
        if rank is None:
            continue
        if lemma not in best or rank < best[lemma]:
            best[lemma] = rank

    ranked = sorted(best.items(), key=lambda kv: kv[1])

    out: list[dict] = []
    for lemma, rank in ranked:
        meaning = define(lemma)
        if not meaning:
            continue  # no definition -> can't teach it
        out.append(
            {
                "word": lemma,
                "meaning": meaning,
                "synonyms": synonyms_for(lemma),
                "cefr": levels.get(lemma, ""),
                "rank": round(rank, 3),
            }
        )
        if len(out) >= max_words:
            break
    return out
