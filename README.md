# MITs

[![PyPI version](https://img.shields.io/pypi/v/mits.svg)](https://pypi.org/project/mits/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/mits.svg)](https://pypi.org/project/mits/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Terminal task manager built around the **3 Most Important Tasks (MIT)** method: star up to three tasks per day, track due dates, projects, recurring work, notes, global search, weekly review, undo, and themes.

<p align="center">
  <img src="assets/demos/demo-main.gif" alt="MITs main UI" width="720">
</p>

<p align="center">
  <img src="assets/demos/demo-search.gif" alt="MITs global search" width="720">
</p>

*GIFs are auto-generated mock UIs (`make demo-gifs`). For real terminal recordings, see [assets/demos/README.md](assets/demos/README.md).*

## Install

### From PyPI

```bash
pip install mits
mits
```

### From source

```bash
git clone https://github.com/lahbibsemlali/mit.git
cd mit
make install
make launch
```

Or with pip in a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python mits.py
```

### Editable install (development)

```bash
pip install -e .
mits --version
```

## CLI quick capture

```bash
mits "fix the rlinks bug"            # → inbox
mits "fix SSR bug +work"             # → inbox, tagged #work
mits today "read x86 calling conv"   # → today
mits someday "learn heap exploit"    # → someday
```

Use `+projectname` anywhere in the title for a project tag.

## Shell greeting (`--summary`)

Add to `~/.zshrc` or `~/.bashrc`:

```bash
python /path/to/mits.py --summary
```

Example output:

```
⚡ MITs — Monday, April 07

  MITs (2/3)
  ★ fix rlinks_client SSR bug            #work
  ★ solve Rainfall level3                #rainfall

  today: 4   inbox: 7   streak: 🔥4d
```

## Keybindings (short)

| Key | Action |
|-----|--------|
| `a` | Add task (inline syntax) |
| `e` | Edit task |
| `n` | Notes |
| `m` | Toggle MIT ★ |
| `Space` | Toggle done |
| `/` or `f` `f` | Global search (tasks + projects) |
| `Tab` / `Ctrl+j` / `Ctrl+k` | Sidebar ↔ list |
| `h` | Back to sidebar |
| `?` | Help |

Full list: press `?` in the app.

## Features

- **MIT limit** — max 3 active ★ tasks; optional move to Today
- **Global search** — `/` or double-tap `f`
- **Due dates** — `due:today`, weekdays, `+3`, ISO dates
- **Recurring** — `recur:daily`, `weekly`, `weekdays`
- **Projects** — `#tags`, project list, confirm when creating new tags
- **Undo** — stack of recent changes (`u`)
- **Weekly review** — `W`
- **Themes** — `t` (persisted in config)
- **CLI & JSON** — `mits --summary --json`, `mits --report`

## Data locations (XDG)

| | Path |
|---|------|
| Tasks | `$XDG_DATA_HOME/mits/data.json` (default: `~/.local/share/mits/data.json`) |
| Config | `$XDG_CONFIG_HOME/mits/config.json` (default: `~/.config/mits/config.json`) |

Override data file: `MITS_DATA=/path/to/data.json` (legacy: `MIT_DATA`).

On first run, if you previously used the `mit` app directory, data is copied from `~/.local/share/mit/` into `mits/` when the new files do not exist yet.

## Development

```bash
make install    # venv + deps
make launch     # run TUI (same as make run)
make dev        # Textual devtools
make build      # sdist + wheel → dist/
make report     # markdown report to stdout
make demo-gifs  # regenerate README demo GIFs (needs pillow)
make reset      # wipe local MITs data (careful)
make clean      # remove .venv and caches
```

## Publish to PyPI

1. Bump version in `pyproject.toml`.
2. `make build`
3. `pip install twine` and upload:

```bash
python -m twine upload dist/*
```

Use [TestPyPI](https://test.pypi.org/) first if you like: `twine upload --repository testpypi dist/*`.

Repository: [github.com/lahbibsemlali/mit](https://github.com/lahbibsemlali/mit).

## Repository layout

```
mit/
├── mits.py             # CLI entry
├── app.py              # TUI app
├── data.py             # storage & parsing
├── help_text.py        # help screen copy
├── themes.py
├── widgets/            # UI panels & modals
├── assets/demos/       # README GIFs
├── scripts/            # generate_demo_gifs.py (Pillow)
├── pyproject.toml
├── requirements.txt
├── Makefile
└── LICENSE
```

## License

MIT — see [LICENSE](LICENSE).
