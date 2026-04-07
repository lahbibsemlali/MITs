"""app.py — ForgeApp: full UX system with focus, j/k, context bar, feedback"""
from __future__ import annotations

import copy
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import ContentSwitcher, ListView, Static

from data import (
    load_data, load_config, save_data, save_config,
    make_task, parse_quick_input, process_recurring, update_streak,
    is_overdue, MIT_LIMIT,
)
from help_text import HELP_TEXT
from themes import THEMES, get_next_theme
from widgets.sidebar import Sidebar, VIEWS
from widgets.task_panel import TaskPanel, TaskRow
from widgets.project_panel import ProjectPanel, ProjectRow
from widgets.detail_panel import DetailPanel
from textual import on
from widgets.modals import (
    AddTaskModal, EditTaskModal, HelpModal, NoteModal,
    ConfirmModal, GlobalSearchModal, ProjectAddModal, ReviewScreen,
)


# ── Context-sensitive keybinding bar ─────────────────────────────────────────

def _kb(bindings: list[tuple[str, str]]) -> str:
    """Build a keybinding bar string: [(key, label), ...]."""
    parts = []
    for key, label in bindings:
        # Use \[ to render literal [ in Rich markup
        parts.append(f"[$accent]\\[{key}][/][dim]{label}[/]")
    return "  ".join(parts)


KB: dict[str, str] = {
    "sidebar": _kb([
        ("j/k", " move"), ("o", " open"), ("a", "dd"), ("ff", " search"),
        ("/", " search"), ("^j/k", " tasks↔"), ("?", " help"), ("q", "uit"),
    ]),
    "tasklist": _kb([
        ("j/k", " move"), ("space", " done"), ("m", "it★"), ("a", "dd"),
        ("e", "dit"), ("n", "otes"), ("D", "el"), ("u", "ndo"),
        ("ff", " search"), ("/", " search"), ("^j/k", " tasks↔"), ("h", " back"),
    ]),
    "tasklist_mit_full": _kb([
        ("j/k", " move"), ("space", " done"), ("m", " unset★"), ("a", "dd"),
        ("e", "dit"), ("n", "otes"), ("D", "el"), ("u", "ndo"),
        ("ff", " search"), ("/", " search"), ("^j/k", " tasks↔"), ("h", " back"),
    ]),
    "tasklist_empty": _kb([
        ("a", "dd task"), ("ff", " search"), ("/", " search"), ("^j/k", " tasks↔"),
        ("h", " back"), ("?", " help"), ("q", "uit"),
    ]),
    "projects": _kb([
        ("j/k", " move"), ("N", "ew"), ("D", "el"), ("ff", " search"),
        ("/", " search"), ("^j/k", " tasks↔"), ("h", " back"), ("?", " help"),
    ]),
}

class ForgeApp(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }
    #main_row {
        height: 1fr;
    }
    ContentSwitcher {
        width: 2fr;
        height: 100%;
    }
    ListView {
        background: $background;
        border: none;
    }
    /* Unfocused highlight — subtle */
    ListView > ListItem.--highlight {
        background: $boost;
    }
    /* Focused highlight — clear active row */
    ListView:focus > ListItem.--highlight {
        background: $primary;
    }
    #status_divider {
        height: 1;
        color: $primary;
        background: $background;
    }
    #status_bar {
        height: 1;
        color: $text-muted;
        background: $background;
        padding: 0 1;
    }
    #keybind_bar {
        height: 1;
        background: $background;
        padding: 0 1;
    }
    """
    TITLE = "mit"

    # All bindings hidden — context bar replaces the footer
    BINDINGS = [
        Binding("q",             "quit",           show=False),
        Binding("question_mark", "show_help",      show=False),
        Binding("1",             "view_today",     show=False),
        Binding("2",             "view_inbox",     show=False),
        Binding("3",             "view_someday",   show=False),
        Binding("4",             "view_projects",  show=False),
        Binding("t",             "cycle_theme",    show=False),
        Binding("W",             "weekly_review",  show=False),
    ]

    current_view: reactive[str] = reactive("today")
    focus_area:   reactive[str] = reactive("sidebar")

    def __init__(self) -> None:
        super().__init__()
        self.data    = load_data()
        self.config  = load_config()
        self.history: list[dict] = []

        self._status_msg: str            = ""
        self._status_timer               = None
        self._sidebar_index: int         = 0
        self._pending_delete_id: str | None  = None
        self._pending_delete_timer       = None
        self._pending_f: bool = False
        self._f_timer = None

        # Run startup logic
        changed = process_recurring(self.data)
        update_streak(self.data)
        if changed:
            save_data(self.data)

    # ── Compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal(id="main_row"):
            yield Sidebar(self.data.get("projects", []))
            with ContentSwitcher(initial="task-panel"):
                yield TaskPanel(id="task-panel")
                yield ProjectPanel(id="project-panel")
            yield DetailPanel(id="detail-panel")
        yield Static("", id="status_divider")
        yield Static("", id="status_bar")
        yield Static("", id="keybind_bar")

    def on_mount(self) -> None:
        # Restore saved theme
        saved = self.config.get("theme", "dark")
        if saved in THEMES:
            self.register_theme(THEMES[saved])
            self.theme = saved

        self._refresh()

        # Auto-focus tasklist if there are tasks today, otherwise sidebar
        today_tasks = [
            t for t in self.data["tasks"]
            if t["list"] == "today" and not t["done"]
        ]
        if today_tasks:
            self._enter_tasklist()
        else:
            self._enter_sidebar()

    # ── Focus system ──────────────────────────────────────────────────────────

    def _enter_sidebar(self) -> None:
        self.focus_area = "sidebar"
        if self.current_view in VIEWS:
            self._sidebar_index = VIEWS.index(self.current_view)
        self.query_one(Sidebar).add_class("--active")
        self.screen.set_focus(None)  # Remove native focus from task list
        self._render_sidebar()
        self._update_keybind_bar()

    def _enter_tasklist(self) -> None:
        self.focus_area = "tasklist"
        self.query_one(Sidebar).remove_class("--active")
        lv_id = "#proj_list" if self.current_view == "projects" else "#task_list"
        try:
            lv = self.query_one(lv_id, ListView)
            lv.focus()
            # Only set index if it's genuinely unset
            if lv.index is None and len(lv.children) > 0:
                lv.index = 0
        except Exception:
            pass
        self._render_sidebar()
        self._update_keybind_bar()

    def _sidebar_move(self, delta: int) -> None:
        self._sidebar_index = max(0, min(len(VIEWS) - 1, self._sidebar_index + delta))
        self._render_sidebar()

    def _sidebar_activate(self) -> None:
        """Open sidebar-selected view and move focus to tasklist."""
        view = VIEWS[self._sidebar_index]
        if self.current_view != view:
            self.current_view = view
            self._refresh(preserve_cursor=False)
        self._enter_tasklist()

    def _render_sidebar(self) -> None:
        sb = self.query_one(Sidebar)
        sb.render_nav(
            self.current_view,
            self._sidebar_index,
            self.focus_area == "sidebar",
        )

    # ── Snapshot / undo ───────────────────────────────────────────────────────

    def _snapshot(self) -> None:
        self.history.append(copy.deepcopy(self.data))
        if len(self.history) > 20:
            self.history.pop(0)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self._status_msg = msg
        if self._status_timer:
            self._status_timer.stop()
        self._status_timer = self.set_timer(2.5, self._clear_status)
        self._refresh_bars()

    def _clear_status(self) -> None:
        self._status_msg   = ""
        self._status_timer = None
        self._refresh_bars()

    def _cancel_f_pending(self) -> None:
        """Clear double-tap `f` state (used for `ff` → search)."""
        self._pending_f = False
        if self._f_timer:
            self._f_timer.stop()
            self._f_timer = None

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _tasks_for_view(self) -> tuple[list[dict], str]:
        v  = self.current_view
        ts = self.data["tasks"]
        wd = date.today().strftime("%A, %B %d")
        if v == "today":
            return ([t for t in ts if t["list"] == "today"],
                    f"[bold]TODAY[/]  [dim]— {wd}[/]")
        if v == "inbox":
            return ([t for t in ts if t["list"] == "inbox"],
                    "[bold]INBOX[/]  [dim]— capture everything, sort later[/]")
        if v == "someday":
            return ([t for t in ts if t["list"] == "someday"],
                    "[bold]SOMEDAY[/]  [dim]— ideas & future tasks[/]")
        return [], ""

    def _active_mit_count(self) -> int:
        return sum(1 for t in self.data["tasks"] if t["is_mit"] and not t["done"])

    # ── Refresh — preserves cursor position ───────────────────────────────────

    def _refresh(self, preserve_cursor: bool = True) -> None:
        # ── Save cursor before any DOM changes ──────────────────────────────
        saved_index: int | None = None
        saved_task_id: str | None = None
        if preserve_cursor and self.focus_area == "tasklist":
            try:
                lv_id = "#proj_list" if self.current_view == "projects" else "#task_list"
                lv = self.query_one(lv_id, ListView)
                saved_index = lv.index
                
                # If we are in task_list, grab the task ID
                if lv_id == "#task_list" and saved_index is not None:
                    child = lv.children[saved_index]
                    saved_task_id = getattr(child, "task_data", {}).get("id")
            except Exception:
                pass

        # ── Render correct panel ─────────────────────────────────────────────
        switcher = self.query_one(ContentSwitcher)
        if self.current_view == "projects":
            switcher.current = "project-panel"
            n_items = self.query_one(ProjectPanel).load(self.data)
        else:
            switcher.current = "task-panel"
            tasks, title     = self._tasks_for_view()
            n_items = self.query_one(TaskPanel).load(tasks, title)

            # First-launch onboarding hint
            if not tasks:
                ob = self.data.get("onboarding", {})
                if not ob.get("first_task_added"):
                    hint = "  no tasks yet.\n\n  \\[a] add your first task\n  \\[?] see all keybindings"
                elif not ob.get("first_mit_set"):
                    hint = "  nothing here.\n\n  tip: press \\[m] on a task to mark it as a Most Important Task"
                else:
                    hint = "  nothing here.  \\[a] to add a task."
                try:
                    self.query_one("#empty_hint", Static).update(hint)
                except Exception:
                    pass

        # ── Restore cursor (clamp to new list length) ────────────────────────
        if self.focus_area == "tasklist":
            try:
                lv_id = "#proj_list" if self.current_view == "projects" else "#task_list"
                lv    = self.query_one(lv_id, ListView)
                
                # We use `.call_after_refresh` because nodes are appended asynchronously.
                def restore() -> None:
                    try:
                        if n_items == 0:
                            lv.index = None
                        else:
                            # If we saved a task ID, try to find it first
                            target_idx = None
                            if saved_task_id and self.current_view != "projects":
                                for i, child in enumerate(lv.children):
                                    if getattr(child, "task_data", {}).get("id") == saved_task_id:
                                        target_idx = i
                                        break
                                        
                            if target_idx is not None:
                                lv.index = target_idx
                            elif saved_index is not None:
                                lv.index = min(saved_index, n_items - 1)
                            elif lv.index is None:
                                lv.index = 0
                    except Exception:
                        pass
                    
                    # Update details with the restored cursor index
                    self._update_detail_panel()
                        
                self.call_after_refresh(restore)
            except Exception:
                pass

        # ── Sidebar counts ───────────────────────────────────────────────────
        ts      = self.data["tasks"]
        overdue = sum(1 for t in ts if is_overdue(t))
        sb      = self.query_one(Sidebar)
        sb.set_projects(self.data.get("projects", []))
        sb.update_counts(
            today    = sum(1 for t in ts if t["list"] == "today"   and not t["done"]),
            inbox    = sum(1 for t in ts if t["list"] == "inbox"   and not t["done"]),
            someday  = sum(1 for t in ts if t["list"] == "someday" and not t["done"]),
            projects = len(self.data.get("projects", [])),
            overdue  = overdue,
            project_counts = {
                p: sum(
                    1 for t in ts
                    if t.get("project") == p and not t.get("done")
                )
                for p in self.data.get("projects", [])
            },
        )

        today_all  = [t for t in ts if t["list"] == "today"]
        today_done = sum(1 for t in today_all if t["done"])
        mits       = [t for t in ts if t["is_mit"]]
        mits_done  = sum(1 for t in mits if t["done"])
        streak     = self.data.get("streaks", {}).get("count", 0)
        sb.update_stats(today_done, len(today_all), mits_done, len(mits), streak)

        self._render_sidebar()
        self._refresh_bars()

    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted) -> None:
        """Triggered when task or project selection changes."""
        self._update_detail_panel()
        
    def _update_detail_panel(self) -> None:
        try:
            dp = self.query_one(DetailPanel)
        except Exception:
            return

        lv_id = "#proj_list" if self.current_view == "projects" else "#task_list"
        try:
            lv = self.query_one(lv_id, ListView)
            if lv.index is None or not lv.children:
                dp.clear()
                return
            child = lv.children[lv.index]
        except Exception:
            dp.clear()
            return

        if self.current_view == "projects":
            name = getattr(child, "proj_name", None)
            p_tasks = [t for t in self.data.get("tasks", []) if t.get("project") == name]
            dp.show_project(name, p_tasks)
        else:
            task_data = getattr(child, "task_data", {})
            dp.show_task(task_data)

    def _refresh_bars(self) -> None:
        ts      = self.data["tasks"]
        total   = len(ts)
        done    = sum(1 for t in ts if t["done"])
        mit_act = self._active_mit_count()
        overdue = sum(1 for t in ts if is_overdue(t))
        streak  = self.data.get("streaks", {}).get("count", 0)

        parts = [f"tasks:{total}", f"done:{done}", f"MITs:{mit_act}/{MIT_LIMIT}"]
        if streak > 0:
            parts.append(f"🔥{streak}d")
        if overdue > 0:
            parts.append(f"[$error]!{overdue} overdue[/]")

        stats_line = "[dim]  " + "  ".join(parts) + "[/]"

        # Status message overrides stats for 2.5 s
        display = f"  [$accent]{self._status_msg}[/]" if self._status_msg else stats_line

        cols = self.size.width
        self.query_one("#status_divider", Static).update("─" * cols)
        self.query_one("#status_bar",     Static).update(display)
        self._update_keybind_bar()

    def _update_keybind_bar(self) -> None:
        if self.focus_area == "sidebar":
            key = "sidebar"
        elif self.current_view == "projects":
            key = "projects"
        else:
            tasks, _ = self._tasks_for_view()
            if not tasks:
                key = "tasklist_empty"
            elif self._active_mit_count() >= MIT_LIMIT:
                key = "tasklist_mit_full"
            else:
                key = "tasklist"

        self.query_one("#keybind_bar", Static).update(KB[key])

    # ── Selected item helpers ─────────────────────────────────────────────────

    def _selected_task(self) -> dict | None:
        if self.current_view == "projects":
            return None
        try:
            lv    = self.query_one("#task_list", ListView)
            child = lv.highlighted_child
            return child.task_data if isinstance(child, TaskRow) else None
        except Exception:
            return None

    def _selected_project(self) -> str | None:
        try:
            lv    = self.query_one("#proj_list", ListView)
            child = lv.highlighted_child
            return child.proj_name if isinstance(child, ProjectRow) else None
        except Exception:
            return None

    # ── Master key handler ────────────────────────────────────────────────────

    def on_key(self, event) -> None:  # noqa: C901  (complexity is intentional here)
        key  = event.key
        char = event.character or ""

        if key == "slash":
            self.action_global_search()
            event.stop()
            return

        # ── ff → global search (double-tap f, vim-style) ─────────────────────
        if self._pending_f:
            if char == "f":
                self._cancel_f_pending()
                self.action_global_search()
                event.stop()
                return
            self._cancel_f_pending()
            # Fall through so the current key is handled normally

        if key == "ctrl+j":
            if self.focus_area == "sidebar":
                self._enter_tasklist()
            else:
                self._list_move(+1)
            event.stop()
            return
        if key == "ctrl+k":
            if self.focus_area == "tasklist":
                self._enter_sidebar()
            else:
                self._sidebar_move(-1)
            event.stop()
            return

        if char == "f" and self.focus_area in ("sidebar", "tasklist"):
            self._pending_f = True
            self._f_timer = self.set_timer(0.4, self._cancel_f_pending)
            event.stop()
            return

        # ── Cancel pending delete on any key that isn't D ────────────────────
        if self._pending_delete_id and char != "D":
            self._cancel_pending_delete()
            # Don't stop the event — let the key do its normal thing

        # ── SIDEBAR ───────────────────────────────────────────────────────────
        if self.focus_area == "sidebar":
            if key == "j":
                self._sidebar_move(+1); event.stop(); return
            if key == "k":
                self._sidebar_move(-1); event.stop(); return
            if key in ("enter", "l") or char == "o":
                self._sidebar_activate(); event.stop(); return
            if key == "tab":
                self._enter_tasklist(); event.stop(); return
            if char == "a":
                self._do_add_task(); event.stop(); return
            if char == "N" and self.current_view == "projects":
                self._do_add_project(); event.stop(); return
            # All other keys: let Textual handle them (e.g. q, ?)
            return

        # ── TASKLIST / PROJECTS ───────────────────────────────────────────────
        # Navigation
        if key == "j":
            self._list_move(+1); event.stop(); return
        if key == "k":
            self._list_move(-1); event.stop(); return
        if key in ("h", "escape"):
            self._enter_sidebar(); event.stop(); return
        if key == "tab":
            self._enter_sidebar(); event.stop(); return

        # Task-specific actions (not in projects view)
        if self.current_view != "projects":
            if key == "space":
                self._do_toggle_done(); event.stop(); return
            if char == "m":
                self._do_toggle_mit(); event.stop(); return
            if char == "D":
                self._do_delete_task(); event.stop(); return
            if char == "e":
                self._do_edit_task(); event.stop(); return
            if char == "n":
                self._do_edit_notes(); event.stop(); return
            if char == "u":
                self._do_undo(); event.stop(); return
            if char == "a":
                self._do_add_task(); event.stop(); return
            if char == "M":
                self._do_move("today"); event.stop(); return
            if char == "i":
                self._do_move("inbox"); event.stop(); return
            if char == "s":
                self._do_move("someday"); event.stop(); return

        # Project-view actions
        if self.current_view == "projects":
            if char == "N":
                self._do_add_project(); event.stop(); return
            if char == "D":
                self._do_delete_project(); event.stop(); return

    def _list_move(self, delta: int) -> None:
        lv_id = "#proj_list" if self.current_view == "projects" else "#task_list"
        try:
            lv = self.query_one(lv_id, ListView)
            if not lv.children:
                return
            if lv.index is None:
                lv.index = 0
                return
            if delta > 0:
                lv.action_cursor_down()
            else:
                lv.action_cursor_up()
        except Exception:
            pass

    # ── View switch actions (bound to 1-4) ────────────────────────────────────

    def action_view_today(self) -> None:
        self.current_view   = "today"
        self._sidebar_index = 0
        self._refresh(preserve_cursor=False)
        self._enter_tasklist()

    def action_view_inbox(self) -> None:
        self.current_view   = "inbox"
        self._sidebar_index = 1
        self._refresh(preserve_cursor=False)
        self._enter_tasklist()

    def action_view_someday(self) -> None:
        self.current_view   = "someday"
        self._sidebar_index = 2
        self._refresh(preserve_cursor=False)
        self._enter_tasklist()

    def action_view_projects(self) -> None:
        self.current_view   = "projects"
        self._sidebar_index = 3
        self._refresh(preserve_cursor=False)
        self._enter_tasklist()

    # ── Task operations ───────────────────────────────────────────────────────

    def _do_add_task(self) -> None:
        def on_result(result: dict | None) -> None:
            if not result:
                return

            project_name = result.get("project", "")

            def finalize_add() -> None:
                self._snapshot()

                # parse_quick_input already ran inside the modal;
                # result contains: title, project, due, is_mit, list, recur
                task = make_task(
                    result["title"],
                    result["list"],
                    result.get("project", ""),
                    result.get("due"),
                    result.get("recur"),
                )

                # Enforce MIT limit on add
                if result.get("is_mit"):
                    if self._active_mit_count() < MIT_LIMIT:
                        task["is_mit"] = True
                    else:
                        self._set_status(
                            f"★ MIT limit reached — task added without MIT flag"
                        )

                self.data["tasks"].append(task)

                # Onboarding tracking
                ob = self.data.setdefault("onboarding", {})
                if not ob.get("first_task_added"):
                    ob["first_task_added"] = True

                save_data(self.data)

                # Switch to target view if different
                if (result["list"] in ("today", "inbox", "someday")
                        and result["list"] != self.current_view):
                    self.current_view   = result["list"]
                    self._sidebar_index = ["today", "inbox", "someday", "projects"].index(
                        self.current_view
                    )

                self._refresh(preserve_cursor=False)
                self._enter_tasklist()

                # Position cursor on the newly added task asynchronously
                def select_new_task() -> None:
                    try:
                        lv = self.query_one("#task_list", ListView)
                        # New task is appended — find its row index
                        for i, child in enumerate(lv.children):
                            if getattr(child, "task_data", {}).get("id") == task["id"]:
                                lv.index = i
                                break
                    except Exception:
                        pass

                self.call_after_refresh(select_new_task)

                proj_tag = f"  +{task['project']}" if task.get("project") else ""
                self._set_status(f"⚡ added to {result['list']}: {task['title']}{proj_tag}")

            if project_name:
                projects = self.data.setdefault("projects", [])
                if project_name not in projects:
                    def on_confirm(confirm: bool | None) -> None:
                        if confirm:
                            projects.append(project_name)
                            save_data(self.data)
                        else:
                            result["project"] = ""
                        finalize_add()

                    self.push_screen(
                        ConfirmModal(
                            f"Project [bold]#{project_name}[/] is not in your list yet.\n\n"
                            f"[dim]Create it and tag this task?[/]"
                        ),
                        on_confirm,
                    )
                    return

            finalize_add()

        self.push_screen(AddTaskModal(self.current_view), on_result)

    def _do_toggle_done(self) -> None:
        task = self._selected_task()
        if not task:
            self._set_status("no task selected")
            return
        self._snapshot()
        task["done"] = not task["done"]
        if task["done"]:
            task["is_mit"] = False
            self._set_status("✓ done")
        else:
            self._set_status("○ marked undone")
        save_data(self.data)
        self._refresh()

    def _do_toggle_mit(self) -> None:
        task = self._selected_task()
        if not task:
            self._set_status("no task selected")
            return
        self._snapshot()
        if not task["is_mit"]:
            active = self._active_mit_count()
            if active >= MIT_LIMIT:
                self._set_status(f"★ already {MIT_LIMIT} MITs — complete one first")
                return
            task["is_mit"] = True
            n = active + 1
            if task["list"] != "today":
                task["list"] = "today"
                self._set_status(f"★ MIT set ({n}/{MIT_LIMIT}) — moved to today")
            else:
                self._set_status(f"★ MIT set ({n}/{MIT_LIMIT})")
            # Onboarding
            ob = self.data.setdefault("onboarding", {})
            if not ob.get("first_mit_set"):
                ob["first_mit_set"] = True
        else:
            task["is_mit"] = False
            self._set_status("★ MIT removed")
        save_data(self.data)
        self._refresh()

    def _do_delete_task(self) -> None:
        task = self._selected_task()
        if not task:
            self._set_status("no task selected")
            return

        if self._pending_delete_id == task["id"]:
            # ── Second D — confirmed ─────────────────────────────────────────
            self._snapshot()
            self.data["tasks"] = [
                t for t in self.data["tasks"] if t["id"] != task["id"]
            ]
            save_data(self.data)
            self._pending_delete_id = None
            if self._pending_delete_timer:
                self._pending_delete_timer.stop()
                self._pending_delete_timer = None
            self._refresh()
            self._set_status("✗ deleted  \\[u] to undo")
        else:
            # ── First D — arm deletion ───────────────────────────────────────
            self._pending_delete_id = task["id"]
            self._set_status(
                "✗ press \\[D] again to confirm delete, any other key to cancel"
            )
            if self._pending_delete_timer:
                self._pending_delete_timer.stop()
            self._pending_delete_timer = self.set_timer(
                3.0, self._cancel_pending_delete
            )

    def _cancel_pending_delete(self) -> None:
        if self._pending_delete_id:
            self._pending_delete_id    = None
            self._pending_delete_timer = None
            self._set_status("")

    def _do_edit_task(self) -> None:
        task = self._selected_task()
        if not task:
            self._set_status("no task selected")
            return

        def on_result(result: dict | None) -> None:
            if not result:
                return

            project_name = result.get("project", "")

            def finalize_edit() -> None:
                self._snapshot()
                for t in self.data["tasks"]:
                    if t["id"] == result["id"]:
                        t["title"]   = result["title"]
                        t["project"] = result["project"]
                        t["list"]    = result["list"]
                        t["due"]     = result["due"]
                        t["recur"]   = result["recur"]
                        t["is_mit"]  = result["is_mit"]
                        break
                save_data(self.data)
                self._set_status("task updated")
                self._refresh()

            if project_name:
                projects = self.data.setdefault("projects", [])
                if project_name not in projects:
                    def on_confirm(confirm: bool | None) -> None:
                        if confirm:
                            projects.append(project_name)
                            save_data(self.data)
                        else:
                            result["project"] = ""
                        finalize_edit()

                    self.push_screen(
                        ConfirmModal(
                            f"Project [bold]#{project_name}[/] is not in your list yet.\n\n"
                            f"[dim]Create it and keep this tag on the task?[/]"
                        ),
                        on_confirm,
                    )
                    return

            finalize_edit()

        self.push_screen(EditTaskModal(task), on_result)

    def _do_edit_notes(self) -> None:
        task = self._selected_task()
        if not task:
            self._set_status("no task selected")
            return

        def on_result(notes: str | None) -> None:
            if notes is not None:
                self._snapshot()
                task["notes"] = notes
                save_data(self.data)
                indicator = "  ¬" if notes.strip() else ""
                self._set_status(f"notes saved{indicator}")
                self._refresh()

        self.push_screen(NoteModal(task), on_result)

    def _do_move(self, target: str) -> None:
        task = self._selected_task()
        if not task:
            self._set_status("no task selected")
            return
        if task["list"] == target:
            self._set_status(f"already in {target}")
            return
        self._snapshot()
        task["list"] = target
        save_data(self.data)
        self._set_status(f"→ moved to {target}")
        self._refresh()

    def _do_undo(self) -> None:
        if not self.history:
            self._set_status("nothing to undo")
            return
        self.data = self.history.pop()
        save_data(self.data)
        self._set_status("↩ undone")
        self._refresh(preserve_cursor=False)

    def _do_search(self) -> None:
        self.action_global_search()

    def action_global_search(self) -> None:
        tasks = self.data.get("tasks", [])
        projects = self.data.get("projects", [])

        def on_result(result: dict | None) -> None:
            if not result:
                return

            kind = result.get("kind")
            if kind == "project":
                project = result.get("project")
                if not project:
                    return
                self.current_view = "projects"
                self._sidebar_index = 3
                self._refresh(preserve_cursor=False)
                self._enter_tasklist()

                def select_project() -> None:
                    try:
                        lv = self.query_one("#proj_list", ListView)
                        for i, child in enumerate(lv.children):
                            if getattr(child, "proj_name", None) == project:
                                lv.index = i
                                break
                    except Exception:
                        pass

                self.call_after_refresh(select_project)
                return

            if kind == "task":
                task_id = result.get("task_id")
                if not task_id:
                    return
                task = next((t for t in tasks if t.get("id") == task_id), None)
                if not task:
                    self._set_status("search result no longer exists")
                    return
                target_view = task.get("list", "today")
                if target_view not in ("today", "inbox", "someday"):
                    target_view = "today"
                self.current_view = target_view
                self._sidebar_index = ["today", "inbox", "someday", "projects"].index(target_view)
                self._refresh(preserve_cursor=False)
                self._enter_tasklist()

                def select_task() -> None:
                    try:
                        lv = self.query_one("#task_list", ListView)
                        for i, child in enumerate(lv.children):
                            if getattr(child, "task_data", {}).get("id") == task_id:
                                lv.index = i
                                break
                    except Exception:
                        pass

                self.call_after_refresh(select_task)

        self.push_screen(GlobalSearchModal(tasks, projects), on_result)

    # ── Project operations ────────────────────────────────────────────────────

    def _do_add_project(self) -> None:
        def on_result(name: str | None) -> None:
            if not name:
                return
            name     = name.strip().lower()
            projects = self.data.setdefault("projects", [])
            if name in projects:
                self._set_status(f"'{name}' already exists")
                return
            self._snapshot()
            projects.append(name)
            save_data(self.data)
            self._set_status(f"project '{name}' created")
            self._refresh()

        self.push_screen(ProjectAddModal(), on_result)

    def _do_delete_project(self) -> None:
        pname = self._selected_project()
        if not pname:
            self._set_status("no project selected")
            return

        count = sum(1 for t in self.data["tasks"] if t.get("project") == pname)
        msg   = (
            f'delete "{pname}"? ({count} task{"s" if count != 1 else ""} will lose tag)'
            if count else
            f'delete "{pname}"?'
        )

        def on_confirm(ok: bool | None) -> None:
            if ok:
                self._snapshot()
                self.data["projects"] = [
                    p for p in self.data.get("projects", []) if p != pname
                ]
                save_data(self.data)
                self._set_status(f"'{pname}' deleted")
                self._refresh()

        self.push_screen(ConfirmModal(msg), on_confirm)

    # ── Weekly review ─────────────────────────────────────────────────────────

    def action_weekly_review(self) -> None:
        order   = {"inbox": 0, "today": 1, "someday": 2}
        pending = sorted(
            [t for t in self.data["tasks"] if not t.get("done")],
            key=lambda t: order.get(t["list"], 3),
        )
        if not pending:
            self._set_status("no pending tasks to review")
            return

        def on_result(changes: list | None) -> None:
            if not changes:
                self._set_status("review cancelled")
                self._refresh()
                return
            self._snapshot()
            remove_ids: set[str] = set()
            for task_id, action in changes:
                if action == "delete":
                    remove_ids.add(task_id)
                else:
                    for t in self.data["tasks"]:
                        if t["id"] == task_id:
                            t["list"] = action
            if remove_ids:
                self.data["tasks"] = [
                    t for t in self.data["tasks"] if t["id"] not in remove_ids
                ]
            save_data(self.data)
            n_del   = len(remove_ids)
            n_moved = sum(1 for _, a in changes if a != "delete")
            self._set_status(
                f"✓ review done — {n_moved} moved, {n_del} deleted"
            )
            self._refresh()

        self.push_screen(ReviewScreen(pending), on_result)

    # ── Theme cycling ─────────────────────────────────────────────────────────

    def action_cycle_theme(self) -> None:
        current    = self.config.get("theme", "dark")
        next_theme = get_next_theme(current)
        if next_theme in THEMES:
            self.register_theme(THEMES[next_theme])
            self.theme = next_theme
        self.config["theme"] = next_theme
        save_config(self.config)
        self._set_status(f"theme: {next_theme}")

    # ── Help ──────────────────────────────────────────────────────────────────

    def action_show_help(self) -> None:
        self.push_screen(HelpModal(HELP_TEXT))