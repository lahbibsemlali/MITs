"""widgets/sidebar.py — navigable sidebar with j/k support"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

VIEWS       = ["today", "inbox", "someday", "projects"]
VIEW_LABELS = {
    "today":    "Today",
    "inbox":    "Inbox",
    "someday":  "Someday",
    "projects": "Projects",
}


class Sidebar(Container):
    DEFAULT_CSS = """
    Sidebar {
        width: 22;
        height: 100%;
        border-right: solid $boost;
        background: $background;
        padding: 0 0 0 1;
    }
    Sidebar.--active {
        border-right: solid $accent;
    }
    Sidebar Static { height: 1; }
    #sb_logo      { height: 2; padding: 1 0 0 0; }
    #sb_proj_list { height: auto; }
    #sb_stats     { height: auto; margin-top: 1; }
    #sb_focus_tip { height: auto; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, projects: list[str]) -> None:
        super().__init__()
        self._projects: list[str]     = projects
        self._counts:   dict[str, int] = {}
        self._overdue:  int            = 0
        self._project_counts: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Static("[bold $accent]mit ⚡[/]",  id="sb_logo")
        yield Static("[dim]VIEWS[/]",            id="sb_views_hdr")
        yield Static("[dim]─────[/]",            id="sb_views_div")
        yield Static("", id="nav_today")
        yield Static("", id="nav_inbox")
        yield Static("", id="nav_someday")
        yield Static("", id="nav_projects")
        yield Static("",                         id="sb_gap")
        yield Static("[dim]PROJECTS[/]",         id="sb_proj_hdr")
        yield Static("[dim]─────────[/]",        id="sb_proj_div")
        yield Static("",                         id="sb_proj_list")
        yield Static("",                         id="sb_stats")
        yield Static("",                         id="sb_focus_tip")

    # ── Nav rendering ─────────────────────────────────────────────────────────

    def render_nav(
        self,
        active_view:    str,
        cursor_index:   int,
        sidebar_focused: bool,
    ) -> None:
        """Re-render all nav items based on current state."""
        od = f" [bold $error]!{self._overdue}[/]" if self._overdue else ""

        for i, view_key in enumerate(VIEWS):
            label  = VIEW_LABELS[view_key]
            count  = self._counts.get(view_key, 0)
            nav_id = f"#nav_{view_key}"
            extra  = od if view_key == "today" else ""

            is_cursor = sidebar_focused and i == cursor_index
            is_active = view_key == active_view

            if is_cursor:
                line = f"[bold $accent]> {label:<9} ({count}){extra}[/]"
            elif is_active:
                line = f"[bold]  {label:<9} ({count}){extra}[/]"
            else:
                line = f"[dim]  {label:<9} ({count}){extra}[/]"

            self.query_one(nav_id, Static).update(line)

    # ── Count / stats updates ─────────────────────────────────────────────────

    def update_counts(
        self,
        today:    int,
        inbox:    int,
        someday:  int,
        projects: int,
        overdue:  int = 0,
        project_counts: dict[str, int] | None = None,
    ) -> None:
        self._counts = {
            "today":    today,
            "inbox":    inbox,
            "someday":  someday,
            "projects": projects,
        }
        self._overdue = overdue
        self._project_counts = project_counts or {}
        self._render_projects()

    def update_stats(
        self,
        done_today:  int,
        total_today: int,
        mits_done:   int,
        mits_total:  int,
        streak:      int,
    ) -> None:
        parts = [f"[dim]✓ {done_today}/{total_today}[/]"]
        if mits_total:
            parts.append(f"[dim]★ {mits_done}/{mits_total}[/]")
        if streak > 0:
            parts.append(f"[dim]🔥{streak}d[/]")
        self.query_one("#sb_stats", Static).update("  ".join(parts))
        self.query_one(
            "#sb_focus_tip",
            Static,
        ).update("[dim]Tab to switch focus   •   / search all[/]")

    def set_projects(self, projects: list[str]) -> None:
        """Update the project list (called when projects are added/removed)."""
        self._projects = projects
        self._render_projects()

    def _render_projects(self) -> None:
        """Re-render the project list inside #sb_proj_list."""
        try:
            container = self.query_one("#sb_proj_list", Static)
        except Exception:
            return

        if not self._projects:
            container.update("[dim]  (none)[/]")
            return

        lines = []
        ordered = sorted(
            self._projects,
            key=lambda p: (-self._project_counts.get(p, 0), p),
        )
        visible = ordered[:6]
        for p in visible:
            n = self._project_counts.get(p, 0)
            if n:
                lines.append(f"[dim]  ◦ {p} ({n})[/]")
            else:
                lines.append(f"[dim]  ◦ {p}[/]")
        hidden = len(ordered) - len(visible)
        if hidden > 0:
            lines.append(f"[dim]  … +{hidden} more[/]")
        container.update("\n".join(lines))