#!/usr/bin/env python3
"""
Generate README demo GIFs: Rich → SVG → PNG (cairosvg) → GIF (Pillow).

Terminal-style panels, borders, and markup — higher quality than raw PIL text.
Requires: rich, pillow, cairosvg
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import cairosvg
from PIL import Image
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.terminal_theme import TerminalTheme
from rich.text import Text

MIT_THEME = TerminalTheme(
    (28, 28, 28),
    (200, 200, 200),
    [
        (42, 42, 42),
        (180, 70, 70),
        (90, 130, 90),
        (212, 160, 23),
        (100, 140, 190),
        (160, 100, 140),
        (100, 180, 180),
        (160, 160, 160),
    ],
    [
        (120, 120, 120),
        (220, 90, 90),
        (120, 200, 120),
        (230, 190, 80),
        (130, 170, 230),
        (220, 120, 180),
        (140, 220, 220),
        (230, 230, 230),
    ],
)

CONSOLE_W = 98
DPI = 144


def _svg_to_png(svg: str) -> Image.Image:
    png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"), dpi=DPI)
    im = Image.open(io.BytesIO(png_bytes))
    return im.convert("RGB")


def _pad_to_size(images: list[Image.Image], bg: tuple[int, int, int] = (28, 28, 28)) -> list[Image.Image]:
    mw = max(im.width for im in images)
    mh = max(im.height for im in images)
    out: list[Image.Image] = []
    for im in images:
        canvas = Image.new("RGB", (mw, mh), bg)
        x = (mw - im.width) // 2
        y = (mh - im.height) // 2
        canvas.paste(im, (x, y))
        out.append(canvas)
    return out


def _render_main(highlight: int) -> str:
    """highlight 0 or 1 = selected task row."""
    c = Console(record=True, width=CONSOLE_W, file=io.StringIO(), force_terminal=True)

    sb = Table(show_header=False, box=box.MINIMAL, pad_edge=False)
    sb.add_column("sb", width=22)
    sb.add_row(Text.from_markup("[dim]VIEWS[/]"))
    sb.add_row(Text.from_markup("[bold yellow]>[/] [bold]Today[/]  [dim](3)[/]"))
    sb.add_row(Text.from_markup("  Inbox   [dim](7)[/]"))
    sb.add_row(Text.from_markup("  Someday [dim](2)[/]"))
    sb.add_row(Text.from_markup("  Projects[dim](4)[/]"))

    def task_cell(i: int, markup: str) -> Text:
        if i == highlight:
            return Text.from_markup(f"[on rgb(48,44,28)]{markup}[/]")
        return Text.from_markup(markup)

    tk = Table(show_header=False, box=box.MINIMAL, pad_edge=False)
    tk.add_column("tk")
    tk.add_row(
        task_cell(
            0,
            "  [bold yellow]★[/] [ ]  Fix SSR bug in client          [dim]#work[/]",
        )
    )
    tk.add_row(task_cell(1, "      [ ]  Buy groceries"))
    tk.add_row(task_cell(2, "      [dim][✓][/]  Email team"))

    dt = Table(show_header=False, box=box.MINIMAL, pad_edge=False)
    dt.add_column("dt", width=24)
    dt.add_row(Text.from_markup("[bold]Fix SSR bug in client[/]"))
    dt.add_row(Text.from_markup("[dim]project[/]  [bold]#work[/]"))
    dt.add_row(Text.from_markup("[dim]list[/]    today"))
    dt.add_row(Text.from_markup("[dim]due[/]     2026-04-10"))

    body = Table(
        show_header=False,
        box=box.ROUNDED,
        border_style="dim",
        pad_edge=False,
        padding=(0, 1),
    )
    body.add_column("sidebar", width=24)
    body.add_column("tasks", min_width=40)
    body.add_column("detail", width=26)
    body.add_row(sb, tk, dt)

    foot = Text.from_markup(
        "[dim]tasks:12  done:4  MITs:2/3  🔥4d[/]   "
        "[dim][[/][yellow]j/k[/][dim]][/] [dim]move[/]  "
        "[dim][[/][yellow]space[/][dim]][/] [dim]done[/]  "
        "[dim][[/][yellow]a[/][dim]][/] [dim]add[/]  "
        "[dim][[/][yellow]/[/][dim]][/] [dim]search[/]  "
        "[dim][[/][yellow]?[/][dim]][/] [dim]help[/]"
    )

    root = Panel(
        Group(body, Rule(style="dim"), foot),
        title="[bold yellow]MITs[/]  [bold]Today[/]  [dim]· Monday, April 7[/]",
        border_style="yellow",
        padding=(0, 1),
    )
    c.print(root)
    return c.export_svg(title="MITs", theme=MIT_THEME, clear=True)


def _render_search(phase: int) -> str:
    c = Console(record=True, width=CONSOLE_W, file=io.StringIO(), force_terminal=True)
    query = "" if phase == 0 else "fix"
    cursor = "▌" if phase < 2 else ""

    results = Table(show_header=False, box=None, padding=(0, 0))
    if phase >= 1:
        if phase >= 2:
            results.add_row(
                Text.from_markup(
                    "[on rgb(48,44,28)]  [bold]task[/]  Fix SSR bug in client  [dim]#work  ↳ today[/]"
                )
            )
            results.add_row(Text.from_markup("  [dim]task[/]  Fix typo in README     [dim]↳ inbox[/]"))
        else:
            results.add_row(Text.from_markup("  [dim]task[/]  Fix SSR bug in client  [dim]#work  ↳ today[/]"))

    inner = Group(
        Text.from_markup("[bold yellow]global search[/]"),
        Text(""),
        Text.from_markup(f"  [bold]{query}[/][yellow]{cursor}[/]  [dim]…[/]"),
        Text.from_markup("[dim]type to filter  ·  Enter open  ·  Esc cancel[/]"),
        Text(""),
        results,
    )

    modal = Panel(
        inner,
        border_style="yellow",
        padding=(1, 2),
        width=72,
    )
    c.print(Align.center(modal, vertical="middle"))
    return c.export_svg(title="MITs — search", theme=MIT_THEME, clear=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "assets" / "demos"
    out.mkdir(parents=True, exist_ok=True)

    svgs_main = [_render_main(0), _render_main(0), _render_main(1), _render_main(1)]
    pngs_main = _pad_to_size([_svg_to_png(s) for s in svgs_main])
    main_path = out / "demo-main.gif"
    pngs_main[0].save(
        main_path,
        save_all=True,
        append_images=pngs_main[1:],
        duration=700,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {main_path}", file=sys.stderr)

    svgs_search = [_render_search(0), _render_search(1), _render_search(2), _render_search(2)]
    pngs_s = _pad_to_size([_svg_to_png(s) for s in svgs_search])
    search_path = out / "demo-search.gif"
    pngs_s[0].save(
        search_path,
        save_all=True,
        append_images=pngs_s[1:],
        duration=600,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {search_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
