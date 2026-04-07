"""widgets/modals.py — minimal terminal-native modals (no buttons)"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static, TextArea

from data import parse_quick_input
from help_text import HELP_TEXT as HELP_TEXT_BUILTIN

ESC = "\\"  # single backslash — Rich sees \[ as a literal [

# ── Shared Input CSS (injected into every modal) ──────────────────────────────
# Fixes invisible text: explicit foreground + slightly-raised background

_INPUT_CSS = """
    Input {
        background: $boost;
        color: $foreground;
        border: tall $primary;
        height: 3;
        margin: 0;
    }
    Input:focus {
        border: tall $accent;
        background: $boost;
    }
"""


# ── Add Task (single-field smart input) ──────────────────────────────────────

from textual import on
from textual.events import Key

class AddTaskModal(ModalScreen):
    DEFAULT_CSS = _INPUT_CSS + """
    AddTaskModal { align: center middle; }
    #dialog {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    #modal_title { height: 1; margin-bottom: 1; }
    .hint        { height: 1; color: $text-muted; }
    #modal_hints { height: 1; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, current_list: str = "inbox") -> None:
        super().__init__()
        self.current_list = current_list

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static("[bold $accent]add task[/]", id="modal_title")
            yield Input(
                placeholder="fix the bug  +project  due:fri  recur:daily  ★",
                id="inp_quick",
            )
            yield Static(
                "[dim]+project  due:fri  recur:daily  ★ = MIT  today: …[/]",
                classes="hint",
            )
            yield Static(
                f"[$accent]{ESC}[enter][/][dim] add[/]   "
                f"[$accent]{ESC}[esc][/][dim] cancel[/]",
                id="modal_hints",
            )

    def on_mount(self) -> None:
        self.query_one("#inp_quick", Input).focus()

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)

    @on(Input.Submitted, "#inp_quick")
    def _submit(self, event) -> None:
        raw = self.query_one("#inp_quick", Input).value.strip()
        if not raw:
            return
        default = self.current_list if self.current_list in ("today", "inbox", "someday") else "inbox"
        result  = parse_quick_input(raw, default)
        if not result["title"]:
            return
        self.dismiss(result)


# ── Edit Task ─────────────────────────────────────────────────────────────────

class EditTaskModal(ModalScreen):
    DEFAULT_CSS = _INPUT_CSS + """
    EditTaskModal { align: center middle; }
    #edit_dialog {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    #edit_title  { height: 1; margin-bottom: 1; }
    .hint        { height: 1; color: $text-muted; }
    #edit_hints  { height: 1; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, task: dict) -> None:
        super().__init__()
        self.task_data = task

    def _compile_to_string(self) -> str:
        t = self.task_data
        parts = [t["title"]]
        if t.get("project"):
            parts.append(f"+{t['project']}")
        if t.get("list"):
            parts.append(f"{t['list']}:")
        if t.get("due"):
            parts.append(f"due:{t['due']}")
        if t.get("recur"):
            parts.append(f"recur:{t['recur']}")
        if t.get("is_mit"):
            parts.append("★")
        return "  ".join(parts)

    def compose(self) -> ComposeResult:
        with Container(id="edit_dialog"):
            yield Static("[bold $accent]edit task[/]", id="edit_title")
            yield Input(
                value=self._compile_to_string(),
                id="inp_quick",
                select_on_focus=False,
            )
            yield Static(
                "[dim]+project  due:fri  recur:daily  ★ = MIT  today: …[/]",
                classes="hint",
            )
            yield Static(
                f"[$accent]{ESC}[enter][/][dim] save[/]   "
                f"[$accent]{ESC}[esc][/][dim] cancel[/]",
                id="edit_hints",
            )

    def on_mount(self) -> None:
        inp = self.query_one("#inp_quick", Input)
        inp.focus()
        inp.cursor_position = len(inp.value)

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)

    @on(Input.Submitted, "#inp_quick")
    def _submit(self, event) -> None:
        raw = self.query_one("#inp_quick", Input).value.strip()
        if not raw:
            return

        old_list = self.task_data.get("list", "inbox")
        result  = parse_quick_input(raw, old_list)
        
        if not result["title"]:
            return
            
        # Add id so caller knows which task to update
        result["id"] = self.task_data["id"]
        
        self.dismiss(result)


class SearchResultRow(ListItem):
    """Single search result row for global search."""

    def __init__(self, result: dict) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        yield Static(self.result.get("label", ""))


class GlobalSearchModal(ModalScreen):
    DEFAULT_CSS = _INPUT_CSS + """
    GlobalSearchModal { align: center middle; }
    #search_dialog {
        width: 84;
        height: 26;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    #search_title { height: 1; margin-bottom: 1; }
    #search_summary { height: 1; color: $text-muted; }
    #search_list  { height: 1fr; border: none; margin-top: 1; }
    #search_hint  { height: 1; color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("enter", "choose", show=False),
        Binding("j,down", "move_down", show=False),
        Binding("k,up", "move_up", show=False),
    ]

    def __init__(self, tasks: list[dict], projects: list[str]) -> None:
        super().__init__()
        self._tasks = tasks
        self._projects = projects
        self._results: list[dict] = []

    def compose(self) -> ComposeResult:
        with Container(id="search_dialog"):
            yield Static("[bold $accent]global search[/]", id="search_title")
            yield Input(placeholder="search tasks, projects, tags, list...", id="search_input")
            yield Static("", id="search_summary")
            yield ListView(id="search_list")
            yield Static(
                "[dim]type to filter   •   j/k or ↑↓ move   •   Enter open   •   Esc cancel[/]",
                id="search_hint",
            )

    def on_mount(self) -> None:
        self.query_one("#search_input", Input).focus()
        self._render_results("")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search_input":
            self._render_results(event.value)

    @on(Input.Submitted, "#search_input")
    def _submit_search(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_choose()

    def _render_results(self, query: str) -> None:
        q = query.strip().lower()
        results: list[dict] = []
        proj_counts: dict[str, int] = {}

        for t in self._tasks:
            p = t.get("project", "")
            if p:
                proj_counts[p] = proj_counts.get(p, 0) + 1

        for t in self._tasks:
            title = t.get("title", "")
            project = t.get("project", "")
            lst = t.get("list", "")
            due = str(t.get("due") or "")
            recur = str(t.get("recur") or "")
            hay = f"{title} {project} {lst} {due} {recur}".lower()
            if q and q not in hay:
                continue

            mit = "[$accent]★[/] " if t.get("is_mit") and not t.get("done") else ""
            done = " [dim]✓ done[/]" if t.get("done") else ""
            proj = f"  [dim]#{project}[/]" if project else ""
            due_part = f"  [dim]due:{due}[/]" if due else ""
            recur_part = f"  [dim]↺ {recur}[/]" if recur else ""
            score = 0
            title_l = title.lower()
            if q:
                if title_l == q:
                    score += 100
                elif title_l.startswith(q):
                    score += 60
                elif q in title_l:
                    score += 40
                if project and project.lower().startswith(q):
                    score += 20
                if lst.startswith(q):
                    score += 10
            else:
                score += 1
            results.append({
                "kind": "task",
                "task_id": t.get("id"),
                "list": lst,
                "score": score,
                "label": f"[bold]task[/]  {mit}{title}{proj}  [dim]↳ {lst}[/]{due_part}{recur_part}{done}",
            })

        for p in self._projects:
            if q and q not in p.lower():
                continue
            count = proj_counts.get(p, 0)
            score = 0
            if q:
                if p.lower() == q:
                    score += 80
                elif p.lower().startswith(q):
                    score += 45
                else:
                    score += 25
            else:
                score += 1
            results.append({
                "kind": "project",
                "project": p,
                "score": score + min(count, 20),
                "label": f"[bold]project[/]  [bold]#{p}[/]  [dim]({count} task{'s' if count != 1 else ''})[/]",
            })

        results.sort(
            key=lambda r: (
                -int(r.get("score", 0)),
                r.get("kind", ""),
                r.get("label", ""),
            )
        )
        self._results = results[:120]
        lv = self.query_one("#search_list", ListView)
        lv.clear()

        if not self._results:
            lv.append(SearchResultRow({"label": "[dim]no results[/]"}))
        else:
            for r in self._results:
                lv.append(SearchResultRow(r))

        if lv.children:
            lv.index = 0
        self.query_one("#search_summary", Static).update(
            f"[dim]{len(self._results)} result{'s' if len(self._results) != 1 else ''}[/]"
        )

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_move_down(self) -> None:
        lv = self.query_one("#search_list", ListView)
        if not lv.children:
            return
        if lv.index is None:
            lv.index = 0
            return
        lv.action_cursor_down()

    def action_move_up(self) -> None:
        lv = self.query_one("#search_list", ListView)
        if not lv.children:
            return
        if lv.index is None:
            lv.index = 0
            return
        lv.action_cursor_up()

    def action_choose(self) -> None:
        lv = self.query_one("#search_list", ListView)
        child = lv.highlighted_child
        if isinstance(child, SearchResultRow) and child.result.get("kind"):
            self.dismiss(child.result)

    @on(ListView.Selected, "#search_list")
    def _select_from_list(self, event: ListView.Selected) -> None:
        event.stop()
        if isinstance(event.item, SearchResultRow) and event.item.result.get("kind"):
            self.dismiss(event.item.result)
# ── Help ──────────────────────────────────────────────────────────────────────

class HelpModal(ModalScreen):
    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    #help_box {
        width: 78;
        height: auto;
        max-height: 90%;
        border: solid $primary;
        background: $background;
        padding: 1 3;
        margin: 1 2;
    }
    #help_static {
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, help_text: str = "") -> None:
        super().__init__()
        self._help_text = help_text

    def compose(self) -> ComposeResult:
        body = self._help_text or HELP_TEXT_BUILTIN
        text = f"[bold $accent]MITs · help[/]\n\n{body}"
        with Container(id="help_box"):
            yield Static(text, id="help_static", markup=True)

    def on_key(self, event) -> None:
        event.stop()
        self.dismiss()


# ── Notes ─────────────────────────────────────────────────────────────────────

class QuickTextArea(TextArea):
    # We override _on_key to guarantee we intercept before TextArea's native binding
    async def _on_key(self, event) -> None:
        if event.key == "enter":
            self.screen.action_save()
            event.stop()
        elif event.key in ("shift+enter", "alt+enter"):
            # insert equivalent of enter directly
            self.insert("\n")
            event.stop()
        else:
            await super()._on_key(event)


class NoteModal(ModalScreen):
    DEFAULT_CSS = """
    NoteModal { align: center middle; }
    #note_box {
        width: 64;
        height: auto;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    #note_title { height: 1; margin-bottom: 1; }
    QuickTextArea {
        height: 11;
        margin: 0;
        background: $boost;
        color: $foreground;
    }
    #note_hints { height: 1; color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("ctrl+s", "save",   show=False),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, task: dict) -> None:
        super().__init__()
        self.task_data = task

    def compose(self) -> ComposeResult:
        with Container(id="note_box"):
            yield Static(
                f"[bold $accent]notes:[/] [dim]{self.task_data['title'][:44]}[/]",
                id="note_title",
            )
            yield QuickTextArea(self.task_data.get("notes", ""), id="note_area")
            yield Static(
                "  [b $accent]Enter[/] to save   •   [b $accent]Shift+Enter[/] for new line   •   [b $accent]Esc[/] to cancel",
                id="note_hints",
            )

    def on_mount(self) -> None:
        self.query_one("#note_area", QuickTextArea).focus()

    def action_save(self) -> None:
        self.dismiss(self.query_one("#note_area", QuickTextArea).text)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Confirm ───────────────────────────────────────────────────────────────────

class ConfirmModal(ModalScreen):
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    #confirm_box {
        width: 64;
        height: auto;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    #confirm_msg   { height: auto; margin-bottom: 1; }
    #confirm_hints { height: 1; color: $text-muted; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm_box"):
            yield Static(f"[$error]⚠[/]  {self.message}", id="confirm_msg")
            yield Static(
                f"[$accent]{ESC}[y/enter][/][dim] confirm[/]   "
                f"[$accent]{ESC}[n/esc][/][dim] cancel[/]",
                id="confirm_hints",
            )

    def on_key(self, event) -> None:
        event.stop()
        if event.key in ("y", "enter"):
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)


# ── Project Add ───────────────────────────────────────────────────────────────

class ProjectAddModal(ModalScreen):
    DEFAULT_CSS = _INPUT_CSS + """
    ProjectAddModal { align: center middle; }
    #proj_dialog {
        width: 46;
        height: auto;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    .fl         { height: 1; color: $text-muted; }
    #proj_hints { height: 1; color: $text-muted; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="proj_dialog"):
            yield Static("[bold $accent]new project[/]")
            yield Static("[dim]name  >[/]", classes="fl")
            yield Input(placeholder="project name", id="inp_proj_name")
            yield Static(
                f"[$accent]{ESC}[enter][/][dim] create[/]   "
                f"[$accent]{ESC}[esc][/][dim] cancel[/]",
                id="proj_hints",
            )

    def on_mount(self) -> None:
        self.query_one("#inp_proj_name", Input).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key == "enter":
            event.stop()
            self._submit()

    def _submit(self) -> None:
        name = self.query_one("#inp_proj_name", Input).value.strip()
        self.dismiss(name if name else None)


# ── Weekly Review ─────────────────────────────────────────────────────────────

class ReviewScreen(ModalScreen):
    DEFAULT_CSS = """
    ReviewScreen { align: center middle; }
    #review_box {
        width: 66;
        height: auto;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }
    #review_header    { height: 1; margin-bottom: 1; }
    #review_task_box  { height: auto; padding: 0 0 1 0; }
    #review_task_name { height: 1; }
    #review_task_meta { height: 1; color: $text-muted; }
    #review_actions   { height: 1; margin-top: 1; }
    #review_progress  { height: 1; color: $text-muted; margin-top: 1; }
    #review_summary   { height: auto; }
    """
    BINDINGS = [
        Binding("k",      "keep",         show=False),
        Binding("t",      "move_today",   show=False),
        Binding("i",      "move_inbox",   show=False),
        Binding("s",      "move_someday", show=False),
        Binding("d",      "delete_task",  show=False),
        Binding("escape", "stop_review",  show=False),
    ]

    def __init__(self, tasks: list[dict]) -> None:
        super().__init__()
        self.review_tasks = [dict(t) for t in tasks]
        self.idx          = 0
        self.changes: list[tuple[str, str]] = []
        self.stats:   dict[str, int]        = {
            "kept": 0, "today": 0, "inbox": 0, "someday": 0, "delete": 0
        }
        self._done = False

    def compose(self) -> ComposeResult:
        with Container(id="review_box"):
            yield Static("", id="review_header")
            with Container(id="review_task_box"):
                yield Static("", id="review_task_name")
                yield Static("", id="review_task_meta")
            yield Static("", id="review_actions")
            yield Static("", id="review_progress")
            yield Static("", id="review_summary")

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        total = len(self.review_tasks)
        E = ESC

        if self.idx >= total:
            self._show_summary()
            return

        task = self.review_tasks[self.idx]
        proj = f" [dim]#{task['project']}[/]" if task.get("project") else ""
        due  = f"  due:{task['due']}" if task.get("due") else ""
        rec  = f"  ↻{task['recur']}"  if task.get("recur") else ""

        self.query_one("#review_header",    Static).update(
            f"[bold $accent]weekly review[/]  [dim]({self.idx + 1}/{total})[/]"
        )
        self.query_one("#review_task_name", Static).update(
            f"[bold]{task['title']}[/]{proj}"
        )
        self.query_one("#review_task_meta", Static).update(
            f"[dim]{task['list']}{due}{rec}[/]"
        )
        self.query_one("#review_actions", Static).update(
            f"[$accent]{E}[k][/][dim]eep[/]  "
            f"[$accent]{E}[t][/][dim]oday[/]  "
            f"[$accent]{E}[i][/][dim]nbox[/]  "
            f"[$accent]{E}[s][/][dim]omeday[/]  "
            f"[$accent]{E}[d][/][dim]elete[/]  "
            f"[$accent]{E}[esc][/][dim] stop[/]"
        )

        width  = 22
        filled = round(self.idx / total * width) if total else 0
        bar    = f"[$success]{'█' * filled}[/][dim]{'░' * (width - filled)}[/]"
        self.query_one("#review_progress", Static).update(bar)

    def _show_summary(self) -> None:
        self._done = True
        self.query_one("#review_header",   Static).update("[bold $accent]review complete[/]")
        self.query_one("#review_task_box", Container).display = False
        self.query_one("#review_actions",  Static).update("")
        self.query_one("#review_progress", Static).update("")
        s = self.stats
        self.query_one("#review_summary", Static).update(
            f"[dim]kept:{s['kept']}  today:{s['today']}  "
            f"inbox:{s['inbox']}  someday:{s['someday']}  "
            f"deleted:{s['delete']}[/]\n\n"
            f"[dim]press any key to close[/]"
        )

    def _step(self, action: str) -> None:
        task = self.review_tasks[self.idx]
        if action != "kept":
            self.changes.append((task["id"], action))
        self.stats[action] = self.stats.get(action, 0) + 1
        self.idx += 1
        self._update_display()

    def action_keep(self)         -> None: self._step("kept")
    def action_move_today(self)   -> None: self._step("today")
    def action_move_inbox(self)   -> None: self._step("inbox")
    def action_move_someday(self) -> None: self._step("someday")
    def action_delete_task(self)  -> None: self._step("delete")

    def action_stop_review(self) -> None:
        self.dismiss(self.changes)

    def on_key(self, event) -> None:
        if self._done:
            event.stop()
            self.dismiss(self.changes)