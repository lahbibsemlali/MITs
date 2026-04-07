"""Single source for help screen content — aligned columns, short lines."""
from __future__ import annotations

from data import MIT_LIMIT

# Key column width (monospace); keeps keys + descriptions on one line in the modal.
_K = 18


def _row(key: str, desc: str) -> str:
    return f"  [dim]{key.ljust(_K)}[/] {desc}"


def build_help_text(mit_limit: int = MIT_LIMIT) -> str:
    """Rich markup for HelpModal / ? help."""
    return "\n".join(
        [
            "[bold]NAVIGATION[/]",
            "",
            _row("j k ↑↓", "move up / down"),
            _row("h · Esc", "back to sidebar"),
            _row("Enter · l · o", "open row [dim](sidebar)[/]"),
            _row("Tab", "sidebar ↔ task list"),
            _row("Ctrl+j", "focus list · else ↓"),
            _row("Ctrl+k", "focus sidebar · else ↑"),
            _row("1 … 4", "Today · Inbox · Someday · Projects"),
            "",
            "[bold]TASK ACTIONS[/]",
            "",
            _row("Space", "toggle done ✓"),
            _row("m", f"toggle MIT ★ [dim](max {mit_limit})[/]"),
            _row("e", "edit task"),
            _row("n", "notes"),
            _row("D", "delete · [dim]D again to confirm[/]"),
            _row("u", "undo"),
            "",
            "[bold]MOVEMENT[/]",
            "",
            _row("M", "→ Today"),
            _row("i", "→ Inbox"),
            _row("s", "→ Someday"),
            "",
            "[bold]PROJECTS[/]",
            "",
            _row("N", "new project"),
            _row("D", "delete project"),
            "",
            "[bold]ADD TASK[/]",
            "",
            _row("a", "open add prompt"),
            _row("line", "title +proj due:fri recur:daily today: ★"),
            _row("due", "today · weekday · +N · YYYY-MM-DD"),
            _row("recur", "daily · weekly · weekdays"),
            "",
            "[bold]APP[/]",
            "",
            _row("/", "global search"),
            _row("f f", "search [dim](double-tap f)[/]"),
            _row("W", "weekly review"),
            _row("t", "cycle theme"),
            _row("?", "this help"),
            _row("q", "quit"),
            "",
            "[dim]any key — close[/]",
        ]
    )


HELP_TEXT = build_help_text()
