"""widgets/task_panel.py — TaskRow, TaskPanel with search and ▶ cursor"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ListItem, ListView, Static

from data import is_overdue, due_label, MIT_LIMIT

ESC = "\\"
RECUR_ICON = {"daily": "↻", "weekly": "↺", "weekdays": "↺"}


def _highlight(text: str, query: str) -> str:
    """Highlight matching substring in amber."""
    if not query:
        return text
    lower = text.lower()
    q     = query.lower()
    idx   = lower.find(q)
    if idx == -1:
        return text
    return (
        text[:idx]
        + f"[bold $accent]{text[idx : idx + len(q)]}[/]"
        + text[idx + len(q):]
    )


class TaskRow(ListItem):
    DEFAULT_CSS = """
    TaskRow { padding: 0 1; height: 1; }
    TaskRow > Static { width: 1fr; }
    """

    def __init__(self, task: dict, search: str = "") -> None:
        super().__init__()
        self.task_data = task
        self._search   = search

    def compose(self) -> ComposeResult:
        yield Static(self._render_text())

    def _render_text(self) -> str:
        t       = self.task_data
        overdue = is_overdue(t)
        q       = self._search

        # ★ column (3 chars wide)
        star = "[bold $accent]★[/] " if t["is_mit"] else "  "

        # recur icon (1 char wide)
        rec = f"[dim]{RECUR_ICON[t['recur']]}[/]" if t.get("recur") in RECUR_ICON else " "

        # checkbox
        check = "[dim][✓][/]" if t["done"] else "[ ]"

        # title styling
        raw = t["title"]
        hl  = _highlight(raw, q) if q else raw

        if t["done"]:
            title = f"[dim]{hl}[/]"
        elif overdue:
            title = f"[$error]{hl}[/]"
        elif t["is_mit"]:
            title = f"[bold]{hl}[/]"
        else:
            title = hl

        # due date label
        due = f" {due_label(t)}" if t.get("due") else ""

        # project tag
        proj = ""
        if t.get("project"):
            pt   = f"#{t['project']}"
            proj = f"  [dim]{_highlight(pt, q) if q else pt}[/]"

        # notes indicator
        notes = " [dim]¬[/]" if t.get("notes") else ""

        return f"{star}{rec}{check} {title}{due}{proj}{notes}"

    def refresh_label(self) -> None:
        self.query_one(Static).update(self._render_text())


class TaskPanel(Container):
    DEFAULT_CSS = """
    TaskPanel {
        width: 1fr;
        height: 1fr;
        background: $background;
        padding: 0 1;
    }
    #panel_title { height: 1; padding: 1 0 0 0; }
    #mit_status  { height: 1; color: $text-muted; }

    #task_list   { height: 1fr; border: none; }
    #empty_hint  { color: $text-muted; padding: 1 0; }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="panel_title")
        yield Static("", id="mit_status")
        yield ListView(id="task_list")
        yield Static("", id="empty_hint")

    # ── Load / render ─────────────────────────────────────────────────────────

    def load(self, tasks: list[dict], title: str) -> int:
        self.query_one("#panel_title", Static).update(title)

        # Bucket tasks
        mits    = [t for t in tasks if     t["is_mit"] and not t["done"]]
        regular = [t for t in tasks if not t["is_mit"] and not t["done"]]
        done    = [t for t in tasks if     t["done"]]

        n = len(mits)
        E = ESC
        if n == 0:
            mit_line = f"[dim]no MITs — {E}[m] to mark[/]"
        elif n < MIT_LIMIT:
            mit_line = f"[dim]MITs: {n}/{MIT_LIMIT} — add {MIT_LIMIT - n} more[/]"
        else:
            mit_line = f"[$accent]MITs: {MIT_LIMIT}/{MIT_LIMIT}[/]"

        self.query_one("#mit_status", Static).update(mit_line)

        lv = self.query_one("#task_list", ListView)
        lv.clear()
        
        all_tasks = mits + regular + done
        for t in all_tasks:
            lv.append(TaskRow(t))

        # Empty state hint
        hint = self.query_one("#empty_hint", Static)
        if not all_tasks:
            # Pass-through: app.py will update this with onboarding-aware text
            hint.update(f"[dim]  nothing here.  {E}[a] to add a task.[/]")
        else:
            hint.update("")
            
        return len(all_tasks)