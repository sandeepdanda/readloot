"""Local dictionary lookup for word meaning and synonym suggestions."""

import json
from pathlib import Path

# Module-level cache: loaded lazily on first lookup call
_dictionary_cache: dict[str, dict] | None = None


def _get_dictionary_path() -> Path:
    """Return the path to the bundled dictionary JSON file."""
    return Path(__file__).parent / "data" / "dictionary.json"


def _load_dictionary() -> dict[str, dict]:
    """Load the dictionary from the bundled JSON file.

    Returns a dict mapping lowercase words to {meaning, synonyms}.
    Caches the result after the first call. Returns an empty dict
    if the file is missing or malformed.
    """
    global _dictionary_cache
    if _dictionary_cache is not None:
        return _dictionary_cache

    path = _get_dictionary_path()
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        # Normalize all keys to lowercase for case-insensitive lookup
        _dictionary_cache = {k.lower(): v for k, v in raw.items()}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _dictionary_cache = {}

    return _dictionary_cache


def lookup_word(word: str) -> dict | None:
    """Look up a word in the local dictionary.

    Args:
        word: The word to look up (case-insensitive).

    Returns:
        A dict with "meaning" and "synonyms" keys, or None if not found.
    """
    dictionary = _load_dictionary()
    return dictionary.get(word.strip().lower())
