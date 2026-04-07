# MITs ⚡

[![PyPI version](https://img.shields.io/pypi/v/mits-cli.svg)](https://pypi.org/project/mits-cli/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/mits-cli.svg)](https://pypi.org/project/mits-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A terminal task manager built around the **3 Most Important Tasks** method — focus on what actually matters today.

<p align="center">
  <img src="assets/demos/demo-main.gif" alt="MITs main UI" width="720">
</p>

<p align="center">
  <img src="assets/demos/demo-search.gif" alt="MITs global search" width="720">
</p>

---

## Install

```bash
pip install mits-cli
mits
```

**From source:**

```bash
git clone https://github.com/lahbibsemlali/MITs.git
cd MITs
make install
make launch
```

---

## What it does

Each day you pick **up to 3 Most Important Tasks** (★). Everything else lives in your inbox or someday list. At the end of the day you know exactly what you shipped.

| | |
|---|---|
| **★ MIT limit** | Max 3 active starred tasks per day — forces real prioritisation |
| **Due dates** | `due:today`, weekday names, `+3` (days from now), ISO dates |
| **Recurring** | `recur:daily`, `weekly`, `weekdays` — auto-reschedules on completion |
| **Projects** | `+tag` syntax, project overview panel, per-project progress bars |
| **Global search** | Fuzzy search across all tasks and projects |
| **Undo** | Full undo stack (`u`) |
| **Weekly review** | `W` — see everything outstanding across all lists |
| **Themes** | `t` to cycle through palettes, persisted in config |
| **CLI capture** | Add tasks without opening the TUI |
| **Shell greeting** | One-liner summary for your `.zshrc` / `.bashrc` |

---

## CLI quick capture

Add tasks directly from the shell — no need to open the TUI:

```bash
mits "fix the rlinks bug"              # → inbox
mits "fix SSR bug +work"               # → inbox, tagged #work
mits today "read x86 calling conv"     # → today
mits someday "learn heap exploit"      # → someday
mits "deploy hotfix +work due:today *" # → today, MIT-starred
```

**Inline syntax** (also works in the TUI add/edit prompt):

```
title  +project  due:fri  recur:daily  ★ (or *)
```

| Token | Example | Effect |
|---|---|---|
| `+project` | `+work` | Tag with a project |
| `due:` | `due:mon`, `due:+3`, `due:2026-05-01` | Set due date |
| `recur:` | `recur:daily`, `recur:weekdays` | Recurring task |
| `★` or trailing `*` | `fix bug *` | Mark as MIT |
| `today:` / `inbox:` / `someday:` | `today: plan sprint` | Set target list |

---

## Shell greeting

Print today's MITs and stats every time you open a terminal. Add to `~/.zshrc` or `~/.bashrc`:

```bash
mits --summary
```

Example output:

```
╔╗╔╗ ╦ ╔╦╗ ╔═╗
║╚╝║ ║  ║  ╚═╗
╩  ╩ ╩  ╩  ╚═╝

⚡ MITs — Monday, April 07

  MITs (2/3)
  ★ fix rlinks_client SSR bug     #work
  ★ solve Rainfall level3         #rainfall

  today: 4   inbox: 7   streak: 🔥4d
```

Machine-readable version for scripts:

```bash
mits --summary --json | jq .mit_count
```

---

## Keybindings

| Key | Action |
|---|---|
| `a` | Add task |
| `e` | Edit task |
| `n` | Notes |
| `m` | Toggle MIT ★ |
| `Space` | Toggle done |
| `u` | Undo |
| `D` | Delete task |
| `/` or `ff` | Global search |
| `Tab` / `Ctrl+j` / `Ctrl+k` | Switch sidebar ↔ list |
| `h` | Back to sidebar |
| `W` | Weekly review |
| `t` | Cycle theme |
| `?` | Full help |
| `q` | Quit |

---

## Data & config

| | Path |
|---|---|
| Tasks | `~/.local/share/mits/data.json` |
| Config | `~/.config/mits/config.json` |

Override with `MITS_DATA=/path/to/data.json`.

---

## Development

```bash
make install    # create venv + install deps
make launch     # run TUI
make dev        # run with Textual devtools
make build      # build sdist + wheel → dist/
make report     # print weekly markdown report
make demo-gifs  # regenerate README demo GIFs
make reset      # wipe local data (careful)
make clean      # remove .venv and caches
```

**Publishing:**

```bash
# 1. bump version in pyproject.toml
make build
python -m twine upload dist/*
```

---

## Repository layout

```
MITs/
├── mits.py             # CLI entry point
├── app.py              # TUI application
├── data.py             # persistence, parsing, migrations
├── logo.py             # ASCII art logo
├── help_text.py        # in-app help content
├── themes.py           # colour palettes
├── widgets/            # sidebar, task panel, modals, search
├── assets/demos/       # README GIFs
├── pyproject.toml
├── Makefile
└── LICENSE
```

---

## License

[MIT](LICENSE)
