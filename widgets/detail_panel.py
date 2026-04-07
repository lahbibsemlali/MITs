"""widgets/detail_panel.py — renders details of the selected item."""
from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class DetailPanel(Container):
    DEFAULT_CSS = """
    DetailPanel {
        width: 1fr;
        height: 100%;
        background: $background;
        border-left: tall $primary;
        padding: 0 2;
    }
    #dp_title {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }
    #dp_meta {
        color: $text-muted;
        margin-bottom: 1;
        height: auto;
    }
    #dp_notes {
        color: $foreground;
        height: auto;
    }
    #dp_empty {
        color: $text-muted;
        align: center middle;
        height: 100%;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="dp_title")
        yield Static("", id="dp_meta")
        yield Static("", id="dp_notes")
        yield Static("[dim]no details[/]", id="dp_empty")

    def on_mount(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.query_one("#dp_title", Static).update("")
        self.query_one("#dp_meta", Static).update("")
        self.query_one("#dp_notes", Static).update("")
        self.query_one("#dp_title", Static).display = False
        self.query_one("#dp_meta", Static).display = False
        self.query_one("#dp_notes", Static).display = False
        self.query_one("#dp_empty", Static).display = True

    def show_task(self, task: dict | None) -> None:
        if not task:
            self.clear()
            return

        self.query_one("#dp_empty", Static).display = False

        title = escape(task.get("title", ""))
        self.query_one("#dp_title", Static).update(title)
        self.query_one("#dp_title", Static).display = True

        # Render metadata as stacked lines to keep details readable.
        chips: list[str] = []
        schedule: list[str] = []

        if task.get("project"):
            chips.append(f"project: [bold]#{escape(task['project'])}[/]")

        lst = task.get("list", "")
        if lst:
            chips.append(f"list: [bold]{escape(lst)}[/]")

        if task.get("done"):
            chips.append("status: [$success]done ✓[/]")
        elif task.get("is_mit"):
            chips.append("status: [$accent]MIT ★[/]")
        else:
            chips.append("status: [dim]active[/]")

        if task.get("due"):
            schedule.append(f"due: [bold]{escape(task['due'])}[/]")

        if task.get("recur"):
            schedule.append(f"recur: [bold]{escape(task['recur'])}[/]")

        if task.get("created"):
            chips.append(f"created: [bold]{escape(task['created'])}[/]")

        lines: list[str] = []
        if chips:
            lines.extend(chips)
        if schedule:
            lines.append("")
            lines.append("[dim]schedule[/]")
            lines.extend(schedule)

        meta_str = "\n".join(lines)
        meta_wid = self.query_one("#dp_meta", Static)
        meta_wid.update(meta_str)
        meta_wid.display = bool(meta_str)

        notes = task.get("notes", "").strip()
        notes_wid = self.query_one("#dp_notes", Static)
        if notes:
            notes_wid.update(
                "\n[dim]notes[/]\n"
                f"{escape(notes)}"
            )
            notes_wid.display = True
        else:
            notes_wid.update("")
            notes_wid.display = False

    def show_project(self, project_name: str | None, project_tasks: list[dict]) -> None:
        if not project_name:
            self.clear()
            return
            
        self.query_one("#dp_empty", Static).display = False

        self.query_one("#dp_title", Static).update(f"#[bold]{escape(project_name)}[/]")
        self.query_one("#dp_title", Static).display = True
        
        total = len(project_tasks)
        done  = sum(1 for t in project_tasks if t.get("done"))
        mits  = sum(1 for t in project_tasks if t.get("is_mit"))
        
        parts = [
            f"{done}/{total} tasks done",
        ]
        if mits:
            parts.append(f"[$accent]{mits} MITs[/]")
            
        meta_str = " • ".join(parts)
        self.query_one("#dp_meta", Static).update(meta_str)
        self.query_one("#dp_meta", Static).display = True
        
        if project_tasks:
            lines = ["\n[dim]── tasks ───────────────────[/]\n"]
            incomplete = [t for t in project_tasks if not t.get("done")]
            for t in incomplete:
                prefix = "[$accent]★[/]" if t.get("is_mit") else "○"
                lines.append(f"{prefix} {escape(t.get('title', ''))}")
                
            completed = [t for t in project_tasks if t.get("done")]
            if completed:
                if incomplete:
                    lines.append("")
                for t in completed:
                    lines.append(f"[dim]✓ {escape(t.get('title', ''))}[/]")
            
            self.query_one("#dp_notes", Static).update("\n".join(lines))
            self.query_one("#dp_notes", Static).display = True
        else:
            self.query_one("#dp_notes", Static).display = False
