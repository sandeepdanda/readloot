"""Click CLI layer for ReadLoot — Rich-enhanced edition.

Wires all service modules together into the ``vault`` command group.
Registered as the ``vault`` entry point in ``pyproject.toml``.

Uses Rich for beautiful terminal output with graceful fallback to
plain click.echo when Rich is not installed.

See also: word_service.py, book_service.py, review_engine.py,
          gamification.py, sync_engine.py, wotd.py, dictionary.py,
          achievements.py
"""

from __future__ import annotations

import json
import os

import click

from readloot.db import get_db_connection
from readloot.wotd import get_word_of_the_day, mark_banner_shown, should_show_banner

# Graceful Rich imports — fall back to None if unavailable
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress_bar import ProgressBar
    from rich.table import Table
    from rich.text import Text

    _RICH = True
    _console = Console()
except ImportError:
    _RICH = False
    _console = None  # type: ignore[assignment]

# Graceful pyfiglet import
try:
    import pyfiglet

    _FIGLET = True
except ImportError:
    _FIGLET = False

SESSION_FILE = ".vault_session.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_session_defaults() -> dict:
    """Load last-used book/chapter from session file in current directory."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_session_defaults(book: str, chapter: str) -> None:
    """Persist book/chapter as session defaults."""
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"book": book, "chapter": chapter}, f, indent=2)


def _show_banner() -> None:
    """Show the ASCII art banner using pyfiglet + Rich."""
    if _FIGLET and _RICH:
        banner = pyfiglet.figlet_format("Vocab Vault", font="slant")
        _console.print(f"[cyan]{banner}[/cyan]", end="")
        _console.print("[bold]⚔️  A Vocabulary RPG for Readers[/bold]\n")
    elif _FIGLET:
        banner = pyfiglet.figlet_format("Vocab Vault", font="slant")
        click.echo(click.style(banner, fg="cyan"), nl=False)
        click.echo("⚔️  A Vocabulary RPG for Readers\n")
    else:
        click.echo(click.style("=== Vocab Vault ===", fg="cyan", bold=True))
        click.echo("⚔️  A Vocabulary RPG for Readers\n")


def _display_wotd_banner(conn) -> None:
    """Show the Word of the Day banner."""
    entry = get_word_of_the_day(conn)
    if entry is None:
        return

    if _RICH:
        lines = [f"[bold cyan]{entry.word}[/bold cyan] — {entry.meaning}"]
        if entry.synonyms:
            lines.append(f"Synonyms: {entry.synonyms}")
        if entry.context:
            lines.append(f'"{entry.context}"')
        lines.append(f"[cyan]From: {entry.book_name} / {entry.chapter_name}[/cyan]")
        _console.print(Panel(
            "\n".join(lines),
            title="📖 Word of the Day",
            border_style="cyan",
            expand=False,
        ))
    else:
        click.echo()
        click.echo(click.style("📖 Word of the Day", fg="cyan", bold=True))
        click.echo(click.style(f"  {entry.word}", fg="cyan", bold=True) +
                   f" — {entry.meaning}")
        if entry.synonyms:
            click.echo(f"  Synonyms: {entry.synonyms}")
        if entry.context:
            click.echo(f'  "{entry.context}"')
        click.echo(click.style(f"  From: {entry.book_name} / {entry.chapter_name}", fg="cyan"))
        click.echo()


def _display_word_detail(entry: dict) -> None:
    """Display a single word lookup result."""
    if _RICH:
        lines = [f"[bold]Meaning:[/bold]  {entry['meaning']}"]
        if entry.get("synonyms"):
            lines.append(f"[bold]Synonyms:[/bold] {entry['synonyms']}")
        if entry.get("context"):
            lines.append(f'[bold]Context:[/bold]  "{entry["context"]}"')
        lines.append(f"[bold]Source:[/bold]   {entry['book_name']} / {entry['chapter_name']}")
        _console.print(Panel(
            "\n".join(lines),
            title=f"[bold cyan]{entry['word']}[/bold cyan]",
            border_style="cyan",
            expand=False,
        ))
    else:
        click.echo(click.style(f"  {entry['word']}", fg="cyan", bold=True))
        click.echo(f"    Meaning:  {entry['meaning']}")
        if entry.get("synonyms"):
            click.echo(f"    Synonyms: {entry['synonyms']}")
        if entry.get("context"):
            click.echo(f'    Context:  "{entry["context"]}"')
        click.echo(f"    Source:   {entry['book_name']} / {entry['chapter_name']}")


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------


@click.group(invoke_without_command=True)
@click.pass_context
def vault(ctx):
    """ReadLoot — your reading companion."""
    ctx.ensure_object(dict)
    db_path = os.environ.get("VAULT_DB_PATH", "vault.db")
    vault_dir = os.environ.get("VAULT_DIR", "vault")
    conn = get_db_connection(db_path)
    ctx.obj["db"] = conn
    ctx.obj["vault_dir"] = vault_dir

    # Show WOTD banner if not seen today
    if should_show_banner(conn):
        _display_wotd_banner(conn)
        mark_banner_shown(conn)

    # Show ASCII banner when invoked with no subcommand
    if ctx.invoked_subcommand is None:
        _show_banner()


# ---------------------------------------------------------------------------
# vault add
# ---------------------------------------------------------------------------

@vault.command()
@click.argument("word", required=False)
@click.option("--book", default=None, help="Book name")
@click.option("--chapter", default=None, help="Chapter name")
@click.option("--meaning", default=None, help="Word meaning/definition")
@click.option("--synonyms", default=None, help="Comma-separated synonyms")
@click.option("--context", default=None, help="Context sentence from the book")
@click.pass_context
def add(ctx, word, book, chapter, meaning, synonyms, context):
    """Add a word to your vault."""
    from readloot import dictionary, gamification, word_service
    from readloot.achievements import check_achievements, show_achievement_toast
    from readloot.book_service import create_book, create_chapter

    conn = ctx.obj["db"]
    vault_dir = ctx.obj["vault_dir"]

    # Load session defaults for book/chapter
    session = _load_session_defaults()

    # Interactive mode: prompt for missing fields
    if word is None:
        word = click.prompt("Word")

    word = word.strip()
    if not word:
        click.echo(click.style("Word cannot be empty.", fg="red"))
        return

    # Suggest meaning/synonyms from dictionary if not provided
    suggestion = dictionary.lookup_word(word)

    if book is None:
        default_book = session.get("book", "")
        book = click.prompt("Book", default=default_book or None)

    if chapter is None:
        default_chapter = session.get("chapter", "")
        chapter = click.prompt("Chapter", default=default_chapter or None)

    if meaning is None:
        default_meaning = suggestion["meaning"] if suggestion else ""
        if default_meaning:
            meaning = click.prompt("Meaning", default=default_meaning)
        else:
            meaning = click.prompt("Meaning")

    if synonyms is None:
        default_synonyms = suggestion.get("synonyms", "") if suggestion else ""
        if default_synonyms:
            synonyms = click.prompt("Synonyms (comma-separated)", default=default_synonyms)
        else:
            synonyms = click.prompt("Synonyms (comma-separated)", default="")

    if context is None:
        context = click.prompt("Context sentence", default="")

    # Ensure book exists
    book_row = conn.execute(
        "SELECT id FROM books WHERE name = ?", (book,)
    ).fetchone()
    if book_row is None:
        click.echo(click.style(f'Creating new book: "{book}"', fg="yellow"))
        create_book(conn, vault_dir, book)

    # Ensure chapter exists
    book_row = conn.execute(
        "SELECT id FROM books WHERE name = ?", (book,)
    ).fetchone()
    chapter_row = conn.execute(
        "SELECT id FROM chapters WHERE book_id = ? AND name = ?",
        (book_row["id"], chapter),
    ).fetchone()
    if chapter_row is None:
        # Determine next chapter number
        max_num = conn.execute(
            "SELECT COALESCE(MAX(chapter_number), 0) AS m FROM chapters WHERE book_id = ?",
            (book_row["id"],),
        ).fetchone()["m"]
        click.echo(click.style(f'Creating new chapter: "{chapter}"', fg="yellow"))
        create_chapter(conn, vault_dir, book, chapter, max_num + 1)

    # Add the word
    result = word_service.add_word(
        conn, vault_dir, word, meaning, synonyms, context, book, chapter,
    )

    if result.get("duplicate"):
        existing = result["existing"]
        click.echo(click.style(
            f'⚠ Duplicate: "{word}" already exists in this chapter.',
            fg="yellow",
        ))
        click.echo(f"  Existing meaning: {existing.meaning}")
        return

    # Cross-book notification
    cross = result.get("cross_book_occurrences", [])
    if cross:
        click.echo(click.style(
            f'ℹ Note: "{word}" also appears in:', fg="yellow",
        ))
        for occ in cross:
            click.echo(f"  • {occ['book_name']} / {occ['chapter_name']}")

    # Award XP and update streak
    new_xp, level_up = gamification.award_xp(conn, 10)
    streak = gamification.update_streak(conn)

    entry = result["entry"]
    click.echo(click.style(f'✓ Added "{entry.word}" to {book} / {chapter}', fg="green"))
    click.echo(click.style(f"  +10 XP (total: {new_xp})", fg="magenta"))

    if streak > 1:
        click.echo(click.style(f"  🔥 {streak}-day streak!", fg="magenta"))

    if level_up:
        click.echo(click.style(
            f"  🎉 Level up! You are now a {level_up}!", fg="magenta", bold=True,
        ))

    # Save session defaults
    _save_session_defaults(book, chapter)

    # Check and show achievements
    unlocked = check_achievements(conn)
    for key in unlocked:
        show_achievement_toast(key)


# ---------------------------------------------------------------------------
# vault lookup
# ---------------------------------------------------------------------------

@vault.command()
@click.argument("word")
@click.pass_context
def lookup(ctx, word):
    """Look up a word in your vault."""
    from readloot import word_service

    conn = ctx.obj["db"]
    results = word_service.lookup_word(conn, word)

    if not results:
        click.echo(click.style(f'No entries found for "{word}".', fg="yellow"))
        return

    click.echo(click.style(f'Found {len(results)} occurrence(s) of "{word}":', fg="green"))
    click.echo()
    for entry in results:
        _display_word_detail(entry)
        if not _RICH:
            click.echo()


# ---------------------------------------------------------------------------
# vault review
# ---------------------------------------------------------------------------

@vault.command()
@click.option("--book", default=None, help="Scope review to a specific book")
@click.option("--chapter", default=None, help="Scope review to a specific chapter (requires --book)")
@click.pass_context
def review(ctx, book, chapter):
    """Start a spaced repetition review session."""
    from readloot import gamification
    from readloot.achievements import check_achievements, show_achievement_toast
    from readloot.review_engine import (
        blank_word_in_context,
        get_due_words,
        get_next_review_date,
        process_answer,
    )

    conn = ctx.obj["db"]

    # Build scope filter
    scope = None
    if book:
        scope = {"book": book}
        if chapter:
            scope["chapter"] = chapter

    due_words = get_due_words(conn, scope)

    if not due_words:
        next_date = get_next_review_date(conn)
        if next_date:
            click.echo(click.style(
                f"No words due for review. Next review: {next_date.isoformat()}",
                fg="yellow",
            ))
        else:
            click.echo(click.style(
                "No words in your vault yet. Add some words first!",
                fg="yellow",
            ))
        click.echo("Try " + click.style("vault wotd", bold=True) +
                   " for your Word of the Day.")
        return

    click.echo(click.style(
        f"📝 Review session: {len(due_words)} word(s) due", fg="cyan", bold=True,
    ))
    click.echo()

    correct_count = 0
    total = len(due_words)
    mastery_5_hit = False

    for i, entry in enumerate(due_words, 1):
        blanked = blank_word_in_context(entry.word, entry.context)
        click.echo(f"[{i}/{total}] {click.style(entry.book_name, fg='cyan')} / "
                   f"{entry.chapter_name}")
        if blanked != entry.context:
            click.echo(f'  "{blanked}"')
        else:
            click.echo(f"  Meaning: {entry.meaning}")

        answer = click.prompt("  Your answer").strip()
        is_correct = answer.lower() == entry.word.lower()

        if is_correct:
            correct_count += 1
            new_mastery, next_rev = process_answer(conn, entry.id, True)
            click.echo(click.style("  ✓ Correct!", fg="green") +
                       f" Mastery: {new_mastery}/5, next review: {next_rev}")
            if new_mastery >= 5:
                mastery_5_hit = True
        else:
            new_mastery, next_rev = process_answer(conn, entry.id, False)
            click.echo(click.style(f"  ✗ The word was: {entry.word}", fg="red") +
                       f" — Mastery: {new_mastery}/5, next review: {next_rev}")
        click.echo()

    # Session summary
    click.echo(click.style("─" * 40, fg="cyan"))
    click.echo(click.style(
        f"Session complete: {correct_count}/{total} correct", fg="green" if correct_count == total else "yellow",
    ))

    # Award XP for correct answers
    if correct_count > 0:
        xp_earned = correct_count * 5
        new_xp, level_up = gamification.award_xp(conn, xp_earned)
        streak = gamification.update_streak(conn)

        click.echo(click.style(f"  +{xp_earned} XP (total: {new_xp})", fg="magenta"))

        if streak > 1:
            click.echo(click.style(f"  🔥 {streak}-day streak!", fg="magenta"))

        if level_up:
            click.echo(click.style(
                f"  🎉 Level up! You are now a {level_up}!", fg="magenta", bold=True,
            ))

    # Check achievements with review context
    # Determine if this is the user's first-ever review
    review_count = conn.execute("SELECT COUNT(*) FROM review_history").fetchone()[0]
    is_first_review = review_count <= total  # only entries from this session

    achievement_ctx = {
        "first_review": is_first_review,
        "perfect_review": correct_count == total and total > 0,
        "mastery_5": mastery_5_hit,
    }
    unlocked = check_achievements(conn, achievement_ctx)
    for key in unlocked:
        show_achievement_toast(key)


# ---------------------------------------------------------------------------
# vault stats
# ---------------------------------------------------------------------------

@vault.command()
@click.pass_context
def stats(ctx):
    """Display your vocabulary profile and stats."""
    from readloot import gamification
    from readloot.achievements import list_achievements
    from readloot.gamification import READER_LEVELS

    conn = ctx.obj["db"]
    profile = gamification.get_profile(conn)

    if _RICH:
        # Build stats table (no header, no box)
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column(style="bold")
        stats_table.add_column()

        stats_table.add_row("📊 Reader Level", f"[bold magenta]{profile['reader_level']}[/bold magenta]")
        stats_table.add_row("⭐ Total XP", f"[magenta]{profile['total_xp']}[/magenta]")
        stats_table.add_row("📝 Total Words", str(profile["total_words"]))
        stats_table.add_row("📚 Total Books", str(profile["total_books"]))
        stats_table.add_row("🔥 Current Streak", f"[magenta]{profile['current_streak']} days[/magenta]")
        stats_table.add_row("🏆 Longest Streak", f"{profile['longest_streak']} days")

        # XP progress bar
        xp_line = ""
        if profile["next_level_name"]:
            current_threshold = 0
            next_threshold = 0
            for threshold, name in READER_LEVELS:
                if threshold <= profile["total_xp"]:
                    current_threshold = threshold
                if threshold > profile["total_xp"]:
                    next_threshold = threshold
                    break

            if next_threshold > current_threshold:
                progress = profile["total_xp"] - current_threshold
                span = next_threshold - current_threshold
                pct = int(100 * progress / span)
                bar_width = 20
                filled = int(bar_width * progress / span)
                bar = "█" * filled + "░" * (bar_width - filled)
                xp_line = (
                    f"\n[bold]Next:[/bold] [magenta]{profile['next_level_name']}[/magenta] "
                    f"({profile['xp_to_next_level']} XP to go)\n"
                    f"[{bar}] {pct}%"
                )
        else:
            xp_line = "\n[bold magenta]🏆 Max level reached![/bold magenta]"

        # Earned achievements line
        all_achievements = list_achievements(conn)
        earned = [a for a in all_achievements if a["earned"]]
        if earned:
            badges = " ".join(a["emoji"] for a in earned)
            xp_line += f"\n\n[bold]Achievements:[/bold] {badges}"

        _console.print(Panel(
            stats_table,
            title="[bold cyan]📊 ReadLoot Profile[/bold cyan]",
            subtitle=xp_line if xp_line else None,
            border_style="cyan",
            expand=False,
        ))
    else:
        # Plain fallback
        click.echo()
        click.echo(click.style("📊 ReadLoot Profile", fg="cyan", bold=True))
        click.echo(click.style("─" * 35, fg="cyan"))
        click.echo(f"  Reader Level:  {click.style(profile['reader_level'], fg='magenta', bold=True)}")
        click.echo(f"  Total XP:      {click.style(str(profile['total_xp']), fg='magenta')}")
        click.echo(f"  Total Words:   {profile['total_words']}")
        click.echo(f"  Total Books:   {profile['total_books']}")
        click.echo(f"  Current Streak: {click.style(str(profile['current_streak']) + ' days', fg='magenta')}")
        click.echo(f"  Longest Streak: {profile['longest_streak']} days")

        if profile["next_level_name"]:
            xp_to_next = profile["xp_to_next_level"]
            current_threshold = 0
            next_threshold = 0
            for threshold, name in READER_LEVELS:
                if threshold <= profile["total_xp"]:
                    current_threshold = threshold
                if threshold > profile["total_xp"]:
                    next_threshold = threshold
                    break

            if next_threshold > current_threshold:
                progress = profile["total_xp"] - current_threshold
                span = next_threshold - current_threshold
                bar_width = 20
                filled = int(bar_width * progress / span)
                bar = "█" * filled + "░" * (bar_width - filled)
                pct = int(100 * progress / span)
                click.echo()
                click.echo(f"  Next: {click.style(profile['next_level_name'], fg='magenta')} "
                           f"({xp_to_next} XP to go)")
                click.echo(f"  [{bar}] {pct}%")
        else:
            click.echo()
            click.echo(click.style("  🏆 Max level reached!", fg="magenta", bold=True))

        click.echo()


# ---------------------------------------------------------------------------
# vault books
# ---------------------------------------------------------------------------

@vault.command()
@click.argument("book_name", required=False)
@click.pass_context
def books(ctx, book_name):
    """List books or show details for a specific book."""
    from readloot import book_service

    conn = ctx.obj["db"]

    if book_name is None:
        # List all books
        book_list = book_service.list_books(conn)
        if not book_list:
            click.echo(click.style("No books in your vault yet.", fg="yellow"))
            return

        if _RICH:
            table = Table(title="📚 Your Books", border_style="cyan")
            table.add_column("Book", style="bold cyan")
            table.add_column("Chapters", justify="right")
            table.add_column("Words", justify="right")

            for b in book_list:
                table.add_row(b["name"], str(b["chapter_count"]), str(b["word_count"]))

            _console.print(table)
        else:
            click.echo(click.style("📚 Your Books", fg="cyan", bold=True))
            click.echo()
            for b in book_list:
                click.echo(f"  {click.style(b['name'], fg='cyan', bold=True)}")
                click.echo(f"    Chapters: {b['chapter_count']}  |  Words: {b['word_count']}")
            click.echo()
    else:
        # Show book details
        try:
            details = book_service.get_book_details(conn, book_name)
        except ValueError:
            click.echo(click.style(f'Book not found: "{book_name}"', fg="red"))
            return

        click.echo(click.style(f"📖 {details['name']}", fg="cyan", bold=True))
        click.echo(f"  Total words: {details['word_count']}  |  "
                   f"Chapters: {details['chapter_count']}")
        click.echo()

        for ch in details["chapters"]:
            click.echo(f"  Ch. {ch['chapter_number']}: {click.style(ch['name'], fg='cyan')}")
            click.echo(f"    Words: {ch['word_count']}", nl=False)
            if ch.get("earliest_entry"):
                click.echo(f"  |  {ch['earliest_entry']} → {ch['latest_entry']}", nl=False)
            click.echo()
        click.echo()


# ---------------------------------------------------------------------------
# vault sync
# ---------------------------------------------------------------------------

@vault.command(name="sync")
@click.pass_context
def sync_cmd(ctx):
    """Sync Markdown files with the SQLite database."""
    from readloot.sync_engine import sync

    conn = ctx.obj["db"]
    vault_dir = ctx.obj["vault_dir"]

    if _RICH:
        with _console.status("[bold cyan]Syncing...[/bold cyan]", spinner="dots"):
            result = sync(conn, vault_dir)

        # Show results in a small Rich Table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="bold")
        table.add_column(justify="right")
        table.add_row("Added", f"[green]{result.added}[/green]")
        table.add_row("Updated", f"[yellow]{result.updated}[/yellow]")
        table.add_row("Unchanged", str(result.unchanged))

        _console.print("[bold green]✓ Sync complete[/bold green]")
        _console.print(table)

        if result.errors:
            _console.print(f"[yellow]  Errors: {len(result.errors)}[/yellow]")
            for err in result.errors:
                _console.print(f"[yellow]    • {err}[/yellow]")
    else:
        click.echo("Syncing Markdown ↔ SQLite...")
        result = sync(conn, vault_dir)

        click.echo(click.style("✓ Sync complete", fg="green"))
        click.echo(f"  Added:     {result.added}")
        click.echo(f"  Updated:   {result.updated}")
        click.echo(f"  Unchanged: {result.unchanged}")

        if result.errors:
            click.echo(click.style(f"  Errors:    {len(result.errors)}", fg="yellow"))
            for err in result.errors:
                click.echo(click.style(f"    • {err}", fg="yellow"))


# ---------------------------------------------------------------------------
# vault achievements
# ---------------------------------------------------------------------------

@vault.command()
@click.pass_context
def achievements(ctx):
    """Show all achievements and your progress."""
    from readloot.achievements import list_achievements

    conn = ctx.obj["db"]
    all_achievements = list_achievements(conn)

    if _RICH:
        table = Table(title="🏆 Achievements", border_style="yellow")
        table.add_column("", justify="center")
        table.add_column("Achievement")
        table.add_column("Description")
        table.add_column("Status", justify="center")

        for a in all_achievements:
            if a["earned"]:
                table.add_row(
                    a["emoji"],
                    f"[bold green]{a['title']}[/bold green]",
                    a["description"],
                    f"[green]✓ {a['earned_at'][:10]}[/green]",
                )
            else:
                table.add_row(
                    f"[dim]{a['emoji']}[/dim]",
                    f"[dim]{a['title']}[/dim]",
                    f"[dim]{a['description']}[/dim]",
                    "[dim]🔒[/dim]",
                )

        _console.print(table)
    else:
        click.echo(click.style("🏆 Achievements", fg="yellow", bold=True))
        click.echo()
        for a in all_achievements:
            if a["earned"]:
                click.echo(click.style(
                    f"  {a['emoji']} {a['title']} — {a['description']}  ✓ {a['earned_at'][:10]}",
                    fg="green",
                ))
            else:
                click.echo(f"  {a['emoji']} {a['title']} — {a['description']}  🔒")
        click.echo()


# ---------------------------------------------------------------------------
# vault export
# ---------------------------------------------------------------------------

@vault.command()
@click.option("--output", "-o", default="vault_export.json",
              help="Output file path (default: vault_export.json)")
@click.pass_context
def export(ctx, output):
    """Export all words to a JSON file."""
    from readloot import word_service

    conn = ctx.obj["db"]
    data = word_service.export_words(conn)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    count = len(data.get("entries", []))
    click.echo(click.style(f"✓ Exported {count} word(s) to {output}", fg="green"))


# ---------------------------------------------------------------------------
# vault wotd
# ---------------------------------------------------------------------------

@vault.command()
@click.pass_context
def wotd(ctx):
    """Show the Word of the Day."""
    conn = ctx.obj["db"]
    entry = get_word_of_the_day(conn)

    if entry is None:
        click.echo(click.style(
            "No words in your vault yet. Add some words first!",
            fg="yellow",
        ))
        return

    if _RICH:
        lines = [
            f"[bold cyan]{entry.word}[/bold cyan]",
            f"[bold]Meaning:[/bold]  {entry.meaning}",
        ]
        if entry.synonyms:
            lines.append(f"[bold]Synonyms:[/bold] {entry.synonyms}")
        if entry.context:
            lines.append(f'[bold]Context:[/bold]  "{entry.context}"')
        lines.append(f"[cyan]Source: {entry.book_name} / {entry.chapter_name}[/cyan]")
        _console.print(Panel(
            "\n".join(lines),
            title="📖 Word of the Day",
            border_style="cyan",
            expand=False,
        ))
    else:
        click.echo()
        click.echo(click.style("📖 Word of the Day", fg="cyan", bold=True))
        click.echo(click.style("─" * 30, fg="cyan"))
        click.echo(f"  {click.style(entry.word, fg='cyan', bold=True)}")
        click.echo(f"  Meaning:  {entry.meaning}")
        if entry.synonyms:
            click.echo(f"  Synonyms: {entry.synonyms}")
        if entry.context:
            click.echo(f'  Context:  "{entry.context}"')
        click.echo(f"  Source:   {entry.book_name} / {entry.chapter_name}")
        click.echo()
