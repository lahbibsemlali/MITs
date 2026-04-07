"""logo.py — ASCII art logo for MITs.

Box-drawing block letters. Width: 14 chars, 3 lines.

  ╔╗╔╗ ╦ ╔╦╗ ╔═╗
  ║╚╝║ ║  ║  ╚═╗
  ╩  ╩ ╩  ╩  ╚═╝
"""

_L1 = "╔╗╔╗ ╦ ╔╦╗ ╔═╗"
_L2 = "║╚╝║ ║  ║  ╚═╗"
_L3 = "╩  ╩ ╩  ╩  ╚═╝"

# ── TUI / Textual ─────────────────────────────────────────────────────────────
# Uses $accent CSS variable (resolved by Textual at render time).

LOGO_SIDEBAR = (
    f"[bold $accent]{_L1}[/]\n"
    f"[bold $accent]{_L2}[/]\n"
    f"[bold $accent]{_L3}[/]"
)

# ── CLI / Rich console ────────────────────────────────────────────────────────
# Uses hardcoded yellow so it looks right without Textual's theme engine.

LOGO_CLI_LINES = [
    f"[bold yellow]{_L1}[/]",
    f"[bold yellow]{_L2}[/]",
    f"[bold yellow]{_L3}[/]",
]

LOGO_CLI = "\n".join(LOGO_CLI_LINES)


def print_logo(console=None) -> None:
    """Print the MITs logo to stdout via Rich (or a supplied Console)."""
    from rich.console import Console
    from rich.text import Text

    c = console or Console()
    c.print(LOGO_CLI)
