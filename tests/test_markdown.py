"""Unit tests for Markdown generation and parsing."""

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from vocabulary_vault.markdown import generate_chapter_markdown, parse_chapter_markdown
from vocabulary_vault.models import Chapter, WordEntry


def _make_chapter(book_name: str = "Sapiens", name: str = "The Cognitive Revolution",
                  chapter_number: int = 1) -> Chapter:
    """Create a Chapter with an attached book_name for testing."""
    ch = Chapter(name=name, chapter_number=chapter_number)
    ch.book_name = book_name  # type: ignore[attr-defined]
    return ch


def _make_entry(word: str = "ephemeral", meaning: str = "lasting for a very short time",
                synonyms: str = "transient, fleeting, momentary",
                context: str = "The ephemeral nature of Sapiens' earliest settlements left few traces.",
                date_added: date | None = None) -> WordEntry:
    return WordEntry(
        word=word,
        meaning=meaning,
        synonyms=synonyms,
        context=context,
        date_added=date_added or date(2025, 1, 15),
    )


class TestGenerateChapterMarkdown:
    """Tests for generate_chapter_markdown."""

    def test_yaml_front_matter_present(self):
        chapter = _make_chapter()
        entries = [_make_entry()]
        md = generate_chapter_markdown(chapter, entries)
        assert md.startswith("---\n")
        assert '\nbook: "Sapiens"\n' in md
        assert '\nchapter: "The Cognitive Revolution"\n' in md
        assert "\nchapter_number: 1\n" in md
        assert "\nword_count: 1\n" in md

    def test_word_section_format(self):
        chapter = _make_chapter()
        entry = _make_entry()
        md = generate_chapter_markdown(chapter, [entry])
        assert "## ephemeral" in md
        assert "- **Meaning:** lasting for a very short time" in md
        assert "- **Synonyms:** transient, fleeting, momentary" in md
        assert '- **Context:** "The ephemeral nature' in md
        assert "- **Date Added:** 2025-01-15" in md

    def test_multiple_entries(self):
        chapter = _make_chapter()
        entries = [
            _make_entry(word="ephemeral"),
            _make_entry(word="ubiquitous", meaning="present everywhere",
                        synonyms="omnipresent, pervasive", context="Technology is ubiquitous.",
                        date_added=date(2025, 2, 1)),
        ]
        md = generate_chapter_markdown(chapter, entries)
        assert "word_count: 2" in md
        assert "## ephemeral" in md
        assert "## ubiquitous" in md

    def test_empty_entries(self):
        chapter = _make_chapter()
        md = generate_chapter_markdown(chapter, [])
        assert "word_count: 0" in md
        assert "## " not in md

    def test_empty_synonyms(self):
        chapter = _make_chapter()
        entry = _make_entry(synonyms="")
        md = generate_chapter_markdown(chapter, [entry])
        assert "- **Synonyms:** \n" in md or "- **Synonyms:** " in md

    def test_book_name_from_entries(self):
        """When chapter has no book_name, fall back to first entry's book_name."""
        chapter = Chapter(name="Ch1", chapter_number=1)
        entry = _make_entry()
        entry.book_name = "Sapiens"
        md = generate_chapter_markdown(chapter, [entry])
        assert 'book: "Sapiens"' in md

    def test_yaml_escaping_quotes(self):
        chapter = _make_chapter(book_name='A "Great" Book')
        md = generate_chapter_markdown(chapter, [])
        assert 'book: "A \\"Great\\" Book"' in md


class TestParseChapterMarkdown:
    """Tests for parse_chapter_markdown."""

    def test_parse_basic(self):
        content = (
            '---\n'
            'book: "Sapiens"\n'
            'chapter: "The Cognitive Revolution"\n'
            'chapter_number: 1\n'
            'word_count: 1\n'
            '---\n'
            '\n'
            '## ephemeral\n'
            '\n'
            '- **Meaning:** lasting for a very short time\n'
            '- **Synonyms:** transient, fleeting, momentary\n'
            '- **Context:** "The ephemeral nature of early settlements."\n'
            '- **Date Added:** 2025-01-15\n'
        )
        metadata, entries = parse_chapter_markdown(content)
        assert metadata["book"] == "Sapiens"
        assert metadata["chapter"] == "The Cognitive Revolution"
        assert metadata["chapter_number"] == 1
        assert metadata["word_count"] == 1
        assert len(entries) == 1
        assert entries[0].word == "ephemeral"
        assert entries[0].meaning == "lasting for a very short time"
        assert entries[0].synonyms == "transient, fleeting, momentary"
        assert entries[0].context == "The ephemeral nature of early settlements."
        assert entries[0].date_added == date(2025, 1, 15)

    def test_parse_multiple_entries(self):
        content = (
            '---\n'
            'book: "Sapiens"\n'
            'chapter: "Ch1"\n'
            'chapter_number: 1\n'
            'word_count: 2\n'
            '---\n'
            '\n'
            '## ephemeral\n'
            '\n'
            '- **Meaning:** short-lived\n'
            '- **Synonyms:** transient\n'
            '- **Context:** "An ephemeral moment."\n'
            '- **Date Added:** 2025-01-15\n'
            '\n'
            '## ubiquitous\n'
            '\n'
            '- **Meaning:** present everywhere\n'
            '- **Synonyms:** omnipresent\n'
            '- **Context:** "Technology is ubiquitous."\n'
            '- **Date Added:** 2025-02-01\n'
        )
        metadata, entries = parse_chapter_markdown(content)
        assert len(entries) == 2
        assert entries[0].word == "ephemeral"
        assert entries[1].word == "ubiquitous"

    def test_parse_no_front_matter(self):
        content = "## hello\n\n- **Meaning:** a greeting\n"
        metadata, entries = parse_chapter_markdown(content)
        assert metadata == {}
        assert len(entries) == 1
        assert entries[0].word == "hello"

    def test_parse_empty_content(self):
        metadata, entries = parse_chapter_markdown("")
        assert metadata == {}
        assert entries == []


class TestRoundTrip:
    """Test that generate → parse produces equivalent data."""

    def test_round_trip_single_entry(self):
        chapter = _make_chapter()
        original = _make_entry()
        md = generate_chapter_markdown(chapter, [original])
        metadata, parsed = parse_chapter_markdown(md)

        assert metadata["book"] == "Sapiens"
        assert metadata["chapter"] == "The Cognitive Revolution"
        assert metadata["chapter_number"] == 1
        assert metadata["word_count"] == 1

        assert len(parsed) == 1
        p = parsed[0]
        assert p.word == original.word
        assert p.meaning == original.meaning
        assert p.synonyms == original.synonyms
        assert p.context == original.context
        assert p.date_added == original.date_added

    def test_round_trip_multiple_entries(self):
        chapter = _make_chapter()
        entries = [
            _make_entry(word="ephemeral", date_added=date(2025, 1, 15)),
            _make_entry(word="ubiquitous", meaning="present everywhere",
                        synonyms="omnipresent, pervasive",
                        context="Technology is ubiquitous.",
                        date_added=date(2025, 2, 1)),
        ]
        md = generate_chapter_markdown(chapter, entries)
        _, parsed = parse_chapter_markdown(md)

        assert len(parsed) == len(entries)
        for orig, p in zip(entries, parsed):
            assert p.word == orig.word
            assert p.meaning == orig.meaning
            assert p.synonyms == orig.synonyms
            assert p.context == orig.context
            assert p.date_added == orig.date_added

    def test_round_trip_empty_synonyms(self):
        chapter = _make_chapter()
        entry = _make_entry(synonyms="")
        md = generate_chapter_markdown(chapter, [entry])
        _, parsed = parse_chapter_markdown(md)
        assert parsed[0].synonyms == ""

    def test_round_trip_empty_entries(self):
        chapter = _make_chapter()
        md = generate_chapter_markdown(chapter, [])
        metadata, parsed = parse_chapter_markdown(md)
        assert metadata["word_count"] == 0
        assert parsed == []


# Feature: vocabulary-vault, Property 1: Markdown Round-Trip
# **Validates: Requirements 3.6, 3.5**

# Strategy: letters only, no Markdown-breaking chars for word headings
_letters = st.characters(whitelist_categories=("L",))

_word_strategy = st.text(alphabet=_letters, min_size=1, max_size=40)

_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Z"),
        blacklist_characters='#-*"`\\',
    ),
    min_size=1,
    max_size=100,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

_synonyms_strategy = st.one_of(
    st.just(""),
    st.lists(
        st.text(alphabet=_letters, min_size=1, max_size=20),
        min_size=1,
        max_size=5,
    ).map(", ".join),
)

_context_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Z"),
        blacklist_characters='"\\#-*',
    ),
    min_size=1,
    max_size=200,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

_word_entry_strategy = st.builds(
    WordEntry,
    word=_word_strategy,
    meaning=_safe_text,
    synonyms=_synonyms_strategy,
    context=_context_strategy,
    date_added=st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31)),
)


class TestMarkdownRoundTripProperty:
    """Property-based test: generate → parse round-trip preserves WordEntry fields."""

    @given(entry=_word_entry_strategy)
    @settings(max_examples=100)
    def test_round_trip_property(self, entry: WordEntry):
        """For any valid WordEntry, generate then parse should produce an equivalent entry."""
        chapter = Chapter(name="Test Chapter", chapter_number=1)
        chapter.book_name = "Test Book"  # type: ignore[attr-defined]

        md = generate_chapter_markdown(chapter, [entry])
        _metadata, parsed = parse_chapter_markdown(md)

        assert len(parsed) == 1
        p = parsed[0]
        assert p.word == entry.word
        assert p.meaning == entry.meaning
        assert p.synonyms == entry.synonyms
        assert p.context == entry.context
        assert p.date_added == entry.date_added


# Feature: vocabulary-vault, Property 5: Markdown Generation Completeness
# **Validates: Requirements 3.1, 3.2**


class TestMarkdownGenerationCompletenessProperty:
    """Property-based test: generated Markdown contains complete YAML front matter and all word entry sections."""

    @given(
        book_name=_safe_text,
        chapter_name=_safe_text,
        chapter_number=st.integers(min_value=0, max_value=9999),
        entries=st.lists(_word_entry_strategy, min_size=1, max_size=10),
    )
    @settings(max_examples=100)
    def test_markdown_generation_completeness(
        self,
        book_name: str,
        chapter_name: str,
        chapter_number: int,
        entries: list,
    ):
        """For any chapter with 1+ entries, generated Markdown has complete front matter and word sections."""
        chapter = Chapter(name=chapter_name, chapter_number=chapter_number)
        chapter.book_name = book_name  # type: ignore[attr-defined]

        md = generate_chapter_markdown(chapter, entries)

        # Assert YAML front matter contains required fields
        assert f'book: "{book_name}"' in md or f"book:" in md
        assert f'chapter: "{chapter_name}"' in md or f"chapter:" in md
        assert f"chapter_number: {chapter_number}" in md
        assert f"word_count: {len(entries)}" in md

        # Assert each word entry section is present with all required fields
        for entry in entries:
            assert f"## {entry.word}" in md
            assert "**Meaning:**" in md
            assert "**Synonyms:**" in md
            assert "**Context:**" in md
            assert "**Date Added:**" in md
