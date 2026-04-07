"""widgets/project_panel.py — project overview with progress bars"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ListView, ListItem, Static

ESC = "\\"


def _bar(done: int, total: int, width: int = 12) -> str:
    """ASCII progress bar."""
    if total == 0:
        return f"[dim]{'─' * width}[/]"
    filled = round(done / total * width)
    return (
        f"[$success]{'█' * filled}[/]"
        f"[dim]{'░' * (width - filled)}[/]"
    )


class ProjectRow(ListItem):
    DEFAULT_CSS = """
    ProjectRow { height: 1; padding: 0 1; }
    ProjectRow > Static { width: 1fr; }
    """

    def __init__(self, name: str, total: int, done: int, mit_count: int) -> None:
        super().__init__()
        self.proj_name = name
        self.total     = total
        self.done      = done
        self.mit_count = mit_count

    def compose(self) -> ComposeResult:
        bar  = _bar(self.done, self.total)
        pct  = f"{self.done}/{self.total}" if self.total else "—"
        mits = f" [$accent]★{self.mit_count}[/]" if self.mit_count else ""
        yield Static(
            f"  ◦ {self.proj_name:<16} {bar} [dim]{pct}[/]{mits}"
        )


class ProjectPanel(Container):
    DEFAULT_CSS = """
    ProjectPanel {
        width: 1fr;
        height: 1fr;
        background: $background;
        padding: 0 1;
    }
    #proj_header { height: 1; padding: 1 0 0 0; }
    #proj_list   { height: 1fr; border: none; }
    #proj_empty  { color: $text-muted; padding: 1 0; }
    #proj_hints  { color: $text-muted; height: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Static("[bold]PROJECTS[/]", id="proj_header")
        yield ListView(id="proj_list")
        yield Static("", id="proj_empty")
        yield Static(
            f"[dim]{ESC}[N] new project   {ESC}[D] delete[/]",
            id="proj_hints",
        )

    def load(self, data: dict) -> int:
        projects = data.get("projects", [])
        tasks    = data.get("tasks", [])

        lv = self.query_one("#proj_list", ListView)
        lv.clear()

        rows: list[tuple[str, int, int, int]] = []
        for pname in projects:
            pt = [t for t in tasks if t.get("project") == pname]
            total = len(pt)
            done = sum(1 for t in pt if t.get("done"))
            mits = sum(1 for t in pt if t.get("is_mit") and not t.get("done"))
            rows.append((pname, total, done, mits))

        # Most actionable projects first: more open tasks, then MITs.
        rows.sort(key=lambda r: (-(r[1] - r[2]), -r[3], r[0]))
        for pname, total, done, mits in rows:
            lv.append(ProjectRow(pname, total, done, mits))

        empty = self.query_one("#proj_empty", Static)
        if not projects:
            empty.update(f"[dim]  no projects yet.  {ESC}[N] to add one.[/]")
        else:
            empty.update("")
            
        return len(rows)