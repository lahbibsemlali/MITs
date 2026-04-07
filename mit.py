#!/usr/bin/env python3
"""
mit ⚡ — terminal task manager enforcing the 3 Most Important Tasks method.

CLIG-compliant CLI. See https://clig.dev/
"""
from __future__ import annotations

import argparse
import signal
import sys


# ── Ctrl+C — clean exit, no traceback ────────────────────────────────────────

def _handle_sigint(_sig, _frame) -> None:
    print(file=sys.stderr)
    sys.exit(0)


signal.signal(signal.SIGINT, _handle_sigint)


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mit",
        description="Terminal task manager — 3 Most Important Tasks per day.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  mit                          launch the TUI
  mit "fix the bug"            add to inbox
  mit today "fix the bug"      add to today
  mit today "fix +work"        add to today, tag project #work
  mit inbox "idea +gcmedia"    add to inbox with project tag
  mit --summary                print today's MITs and exit
  mit --summary --json         machine-readable summary (pipe to jq)
  mit --report                 print weekly markdown report
  mit --report > week.md       save report to file

inline task syntax (works in TUI add/edit prompts too):
  "today: title +project due:fri recur:daily ★"
  due values: today, tomorrow, mon-sun, +3 (days), 2026-04-10
  recur values: daily, weekly, weekdays
  list prefix: today: / inbox: / someday:  (at start or after title tokens)

environment variables:
  MIT_DATA        override data file path
  MIT_MIT_LIMIT   override MIT limit (default: 3)
  NO_COLOR        disable color output (https://no-color.org/)

paths:
  data:   $XDG_DATA_HOME/mit/data.json     (~/.local/share/mit/data.json)
  config: $XDG_CONFIG_HOME/mit/config.json (~/.config/mit/config.json)

shell greeting — add to .zshrc / .bashrc:
  python /path/to/mit.py --summary

feedback & issues: https://github.com/lahbibsemlali/mit
""",
    )

    parser.add_argument(
        "list_or_title",
        nargs="?",
        metavar="LIST|TITLE",
        help="list name (today/inbox/someday) or task title to add to inbox",
    )
    parser.add_argument(
        "title",
        nargs="?",
        metavar="TITLE",
        help="task title (when first arg is a list name)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print today's MITs and stats, then exit (use in .zshrc)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="print weekly markdown report to stdout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output --summary in JSON format (machine-readable)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="mit 0.1.0",
    )
    return parser


# ── CLI commands ──────────────────────────────────────────────────────────────

def cmd_summary(json_mode: bool = False) -> None:
    from data import load_data, generate_summary, generate_summary_json

    data = load_data()
    if json_mode:
        print(generate_summary_json(data))
    else:
        print(generate_summary(data))
    sys.exit(0)


def cmd_report() -> None:
    from data import load_data, generate_report

    data = load_data()
    print(generate_report(data))
    sys.exit(0)


def cmd_add(list_or_title: str, extra_title: str | None) -> None:
    from data import (
        load_data, save_data, make_task,
        parse_quick_input, suggest_list, VALID_LISTS,
    )

    low = list_or_title.lower()

    if low in VALID_LISTS and extra_title:
        lst         = low
        final_title = extra_title

    elif low in VALID_LISTS and not extra_title:
        print(f"mit: error: list '{low}' given but no task title", file=sys.stderr)
        print(f'usage: mit {low} "task title"', file=sys.stderr)
        sys.exit(2)

    elif extra_title is not None:
        # Two args but first is not a valid list — typo?
        suggestion = suggest_list(list_or_title)
        print(f"mit: '{list_or_title}' is not a valid list.", file=sys.stderr)
        if suggestion:
            print(f"did you mean '{suggestion}'?", file=sys.stderr)
            print(f'  mit {suggestion} "{extra_title}"', file=sys.stderr)
        else:
            print("valid lists: today, inbox, someday", file=sys.stderr)
        sys.exit(2)

    else:
        # Single arg — treat as task title, add to inbox
        lst         = "inbox"
        final_title = list_or_title

    # Use the unified parser
    result = parse_quick_input(final_title, default_list=lst)
    
    data = load_data()

    project_name = result.get("project", "")
    if project_name:
        projects = data.setdefault("projects", [])
        if project_name not in projects:
            if sys.stdin.isatty():
                try:
                    ans = input(
                        f"mit: project '+{project_name}' is not in your list. Create it? [Y/n] "
                    ).strip().lower()
                except EOFError:
                    ans = "y"
                if ans in ("", "y", "yes"):
                    projects.append(project_name)
                else:
                    project_name = ""
                    result["project"] = ""
            else:
                print(
                    f"mit: creating new project '+{project_name}' (non-interactive)",
                    file=sys.stderr,
                )
                projects.append(project_name)
            
    # Enforce MIT limits
    if result.get("is_mit"):
        active_mits = sum(1 for t in data.get("tasks", []) if t.get("is_mit") and not t.get("done"))
        from data import MIT_LIMIT
        if active_mits >= MIT_LIMIT:
            result["is_mit"] = False
            print(f"mit: limit of {MIT_LIMIT} MITs reached — task added without ★", file=sys.stderr)

    task = make_task(
        result["title"],
        result["list"],
        project_name,
        result.get("due"),
        result.get("recur"),
    )
    task["is_mit"] = result.get("is_mit", False)

    data["tasks"].append(task)
    save_data(data)

    proj_tag = f"  +{project_name}" if project_name else ""
    print(f"⚡ added to {result['list']}: {result['title']}{proj_tag}")
    sys.exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    if args.summary:
        cmd_summary(json_mode=args.json)

    elif args.report:
        cmd_report()

    elif args.list_or_title:
        cmd_add(args.list_or_title, args.title)

    else:
        # Launch TUI only when stdin is an interactive terminal
        if not sys.stdin.isatty():
            parser.print_help(sys.stderr)
            sys.exit(1)
        from app import ForgeApp
        ForgeApp().run()


if __name__ == "__main__":
    main()