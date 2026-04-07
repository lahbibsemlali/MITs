"""data.py — persistence layer for mit ⚡

Paths follow XDG Base Directory spec:
  data:   $XDG_DATA_HOME/mit/data.json   (~/.local/share/mit/data.json)
  config: $XDG_CONFIG_HOME/mit/config.json (~/.config/mit/config.json)

Override via env: MIT_DATA=/path/to/data.json
"""
from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

__version__ = "0.1.0"

# ── Paths (XDG + env override) ────────────────────────────────────────────────

_LEGACY_DATA = Path.home() / ".forge" / "data.json"


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_data_path() -> Path:
    if "MIT_DATA" in os.environ:
        return Path(os.environ["MIT_DATA"])
    return _xdg_data_home() / "mit" / "data.json"


def get_config_path() -> Path:
    return _xdg_config_home() / "mit" / "config.json"


DATA_PATH   = get_data_path()
CONFIG_PATH = get_config_path()

VALID_LISTS = ("today", "inbox", "someday")
MIT_LIMIT   = int(os.environ.get("MIT_MIT_LIMIT", "3"))


# ── Migration from legacy path ────────────────────────────────────────────────

def _maybe_migrate() -> None:
    """Migrate ~/.forge/data.json → XDG path if legacy exists and XDG doesn't."""
    if "MIT_DATA" in os.environ:
        return
    if _LEGACY_DATA.exists() and not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_LEGACY_DATA, DATA_PATH)


# ── Storage ───────────────────────────────────────────────────────────────────

def load_data() -> dict:
    _maybe_migrate()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        default: dict = {
            "tasks":      [],
            "projects":   [],
            "streaks":    {"last_date": "", "count": 0},
            "onboarding": {"first_task_added": False, "first_mit_set": False},
        }
        DATA_PATH.write_text(json.dumps(default, indent=2))
        return default

    data = json.loads(DATA_PATH.read_text())

    # ── Schema migrations — always forward-compatible ────────────────────────
    data.setdefault("streaks",  {"last_date": "", "count": 0})
    data.setdefault("projects", [])

    has_tasks = bool(data.get("tasks"))
    data.setdefault("onboarding", {
        "first_task_added": has_tasks,
        "first_mit_set":    any(t.get("is_mit") for t in data.get("tasks", [])),
    })

    for task in data.get("tasks", []):
        task.setdefault("due",    None)
        task.setdefault("recur",  None)
        task.setdefault("notes",  "")
        task.setdefault("is_mit", False)
        task.setdefault("done",   False)

    return data


def save_data(data: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2))


def load_config() -> dict:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        default = {"theme": "dark"}
        CONFIG_PATH.write_text(json.dumps(default, indent=2))
        return default
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


# ── Task factory ──────────────────────────────────────────────────────────────

def make_task(
    title:     str,
    list_name: str           = "inbox",
    project:   str           = "",
    due:       Optional[str] = None,
    recur:     Optional[str] = None,
) -> dict:
    return {
        "id":      str(uuid.uuid4())[:8],
        "title":   title,
        "list":    list_name,
        "project": project,
        "is_mit":  False,
        "done":    False,
        "created": str(date.today()),
        "due":     due,
        "recur":   recur,
        "notes":   "",
    }


# ── Inline tag parsing ────────────────────────────────────────────────────────

def parse_inline_project(title: str) -> tuple[str, str]:
    """Extract +project from title. Returns (clean_title, project)."""
    match = re.search(r'\s*\+(\w+)\s*', title)
    if match:
        project = match.group(1)
        clean   = (title[:match.start()] + title[match.end():]).strip()
        return clean, project
    return title.strip(), ""


def parse_quick_input(raw: str, default_list: str = "inbox") -> dict:
    """
    Parse a single-line task input with optional inline tags:
      "fix SSR bug +work due:today *"
      → title="fix SSR bug", project="work", due="<today>", is_mit=True, list="inbox"
    """
    is_mit  = False
    project = ""
    due     = None
    lst     = default_list

    # MIT marker: trailing ★ or " *"
    if "★" in raw:
        is_mit = True
        raw    = raw.replace("★", "").strip()
    elif re.search(r'\s\*\s*$', raw):
        is_mit = True
        raw    = re.sub(r'\s\*\s*$', '', raw).strip()

    # list:xxx
    m = re.search(r'\b(today|inbox|someday):', raw)
    if m:
        lst = m.group(1)
        raw = (raw[:m.start()] + raw[m.end():]).strip()

    # +project (normalized to match stored project names)
    m = re.search(r'\s*\+(\w+)', raw)
    if m:
        project = m.group(1).lower()
        raw     = (raw[:m.start()] + raw[m.end():]).strip()

    # due:xxx
    m = re.search(r'\bdue:(\S+)', raw)
    if m:
        due = parse_due(m.group(1))
        if not due:
            # If parse failed, keep the raw text
            due = m.group(1)
        raw = (raw[:m.start()] + raw[m.end():]).strip()

    # recur:xxx
    recur = None
    m = re.search(r'\brecur:(\S+)', raw)
    if m:
        recur = m.group(1).lower()
        raw = (raw[:m.start()] + raw[m.end():]).strip()

    title = " ".join(raw.split())
    return {
        "title": title,
        "project": project,
        "due": due,
        "recur": recur,
        "is_mit": is_mit,
        "list": lst,
    }


# ── Typo suggestions ──────────────────────────────────────────────────────────

def suggest_list(given: str) -> Optional[str]:
    from difflib import get_close_matches
    matches = get_close_matches(given.lower(), VALID_LISTS, n=1, cutoff=0.5)
    return matches[0] if matches else None


# ── Due date helpers ──────────────────────────────────────────────────────────

def parse_due(raw: str) -> Optional[str]:
    raw   = raw.strip().lower()
    today = date.today()

    if raw in ("", "none", "-", "n"):
        return None
    if raw == "today":
        return str(today)
    if raw in ("tomorrow", "tmr", "tom"):
        return str(today + timedelta(days=1))

    day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    if raw[:3] in day_map:
        delta = (day_map[raw[:3]] - today.weekday()) % 7 or 7
        return str(today + timedelta(days=delta))

    # +N days
    m = re.match(r'^\+(\d+)$', raw)
    if m:
        return str(today + timedelta(days=int(m.group(1))))

    # ISO date
    try:
        date.fromisoformat(raw)
        return raw
    except ValueError:
        return None


def is_overdue(task: dict) -> bool:
    if not task.get("due") or task.get("done"):
        return False
    try:
        return date.fromisoformat(task["due"]) < date.today()
    except ValueError:
        return False


def due_label(task: dict) -> str:
    """Return a Rich-markup due-date label, or empty string."""
    due = task.get("due")
    if not due:
        return ""
    try:
        d     = date.fromisoformat(due)
        today = date.today()
        delta = (d - today).days
        if delta < 0:
            return f"[bold $error](overdue {abs(delta)}d)[/]"
        if delta == 0:
            return "[bold $warning](due today)[/]"
        if delta == 1:
            return "[dim](tomorrow)[/]"
        return f"[dim](in {delta}d)[/]"
    except ValueError:
        return ""


# ── Recurring task logic ──────────────────────────────────────────────────────

def process_recurring(data: dict) -> bool:
    """Respawn done recurring tasks. Returns True if data changed."""
    today_str  = str(date.today())
    today      = date.today()
    new_tasks: list[dict] = []
    remove_ids: set[str]  = set()

    for task in data["tasks"]:
        if not (task.get("done") and task.get("recur")):
            continue
        created_str = task.get("created", today_str)
        if created_str >= today_str:
            continue  # completed today, not yet time to respawn

        recur        = task["recur"]
        weekday      = today.weekday()
        should_spawn = False

        if recur == "daily":
            should_spawn = True
        elif recur == "weekly":
            try:
                orig_wd      = date.fromisoformat(created_str).weekday()
                should_spawn = weekday == orig_wd
            except ValueError:
                should_spawn = True
        elif recur == "weekdays":
            should_spawn = weekday < 5

        if should_spawn:
            new_task = make_task(
                task["title"],
                task["list"],
                task.get("project", ""),
                task.get("due"),
                recur,
            )
            new_tasks.append(new_task)
            remove_ids.add(task["id"])

    if remove_ids:
        data["tasks"] = [t for t in data["tasks"] if t["id"] not in remove_ids]
        data["tasks"].extend(new_tasks)
        return True
    return False


# ── Streak tracking ───────────────────────────────────────────────────────────

def update_streak(data: dict) -> None:
    """Update the daily MIT-completion streak counter. Call once on launch."""
    streaks       = data.setdefault("streaks", {"last_date": "", "count": 0})
    today         = date.today()
    today_str     = str(today)
    yesterday_str = str(today - timedelta(days=1))
    last          = streaks.get("last_date", "")

    if last == today_str:
        return  # already updated today

    yesterday_mits = [
        t for t in data["tasks"]
        if t.get("is_mit") and t.get("created") == yesterday_str
    ]
    yesterday_done = [t for t in yesterday_mits if t.get("done")]

    if (last == yesterday_str
            and yesterday_mits
            and len(yesterday_done) >= len(yesterday_mits)):
        streaks["count"] = streaks.get("count", 0) + 1
    elif last and last < yesterday_str:
        streaks["count"] = 0  # missed a day

    streaks["last_date"] = today_str


# ── Report generator ──────────────────────────────────────────────────────────

def generate_report(data: dict) -> str:
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    streak     = data.get("streaks", {}).get("count", 0)
    completed  = [t for t in data["tasks"] if t.get("done")]
    incomplete = [t for t in data["tasks"] if not t.get("done")]

    lines = [f"# Week of {week_start} — mit report\n"]

    lines.append(f"## ✓ Completed ({len(completed)})\n")
    for t in completed:
        proj = f"  #{t['project']}" if t.get("project") else ""
        lines.append(f"- [x] {t['title']}{proj}")
    if not completed:
        lines.append("_None_")

    lines.append(f"\n## ✗ Incomplete ({len(incomplete)})\n")
    for t in incomplete:
        proj = f"  #{t['project']}" if t.get("project") else ""
        due  = f"  due:{t['due']}" if t.get("due") else ""
        lines.append(f"- [ ] {t['title']}{proj}{due}")
    if not incomplete:
        lines.append("_None_")

    lines.append("\n## Stats\n")
    lines.append(f"- Tasks completed: {len(completed)}")
    if streak > 0:
        lines.append(f"- Streak: 🔥 {streak}d")

    return "\n".join(lines) + "\n"


# ── Shell summary ─────────────────────────────────────────────────────────────

def generate_summary(data: dict) -> str:
    """Plain-text summary for shell greeting — no Rich markup."""
    today       = date.today()
    weekday     = today.strftime("%A, %B %d")
    tasks       = data.get("tasks", [])
    mits        = [t for t in tasks if t.get("is_mit") and not t.get("done")]
    today_count = sum(1 for t in tasks if t["list"] == "today"  and not t.get("done"))
    inbox_count = sum(1 for t in tasks if t["list"] == "inbox"  and not t.get("done"))
    streak      = data.get("streaks", {}).get("count", 0)

    lines = [f"⚡ mit — {weekday}", ""]

    if mits:
        lines.append(f"  MITs ({len(mits)}/{MIT_LIMIT})")
        for t in mits:
            proj = f"  #{t['project']}" if t.get("project") else ""
            lines.append(f"  ★ {t['title']:<40}{proj}")
    else:
        lines.append(f"  MITs (0/{MIT_LIMIT})  — none set")

    lines.append("")
    parts = [f"today: {today_count}", f"inbox: {inbox_count}"]
    if streak > 0:
        parts.append(f"streak: 🔥{streak}d")
    lines.append("  " + "   ".join(parts))
    lines.append("")

    return "\n".join(lines)


def generate_summary_json(data: dict) -> str:
    """JSON summary for machine consumption."""
    import json as _json

    tasks       = data.get("tasks", [])
    mits        = [t for t in tasks if t.get("is_mit") and not t.get("done")]
    today_tasks = [t for t in tasks if t["list"] == "today" and not t.get("done")]
    streak      = data.get("streaks", {}).get("count", 0)

    output = {
        "date":        str(date.today()),
        "mits":        [{"title": t["title"], "project": t.get("project", "")} for t in mits],
        "mit_count":   len(mits),
        "mit_limit":   MIT_LIMIT,
        "today_count": len(today_tasks),
        "inbox_count": sum(1 for t in tasks if t["list"] == "inbox" and not t.get("done")),
        "total_tasks": len(tasks),
        "streak":      streak,
    }
    return _json.dumps(output, indent=2)