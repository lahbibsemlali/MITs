#!/usr/bin/env python3
"""
Drop leading events from an asciicast v2/v3 file until the MITs TUI first appears.

Use when a recording includes typing `make run` / shell noise before the app.

  python scripts/trim_asciicast_start.py mit-demo.cast mit-demo-trimmed.cast

Optional: --first-delay SECONDS sets the time field on the first kept event (default 0.05).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _is_mit_main_frame(ev: list) -> bool:
    if len(ev) < 3 or ev[1] != "o":
        return False
    data = ev[2]
    if "VIEWS" not in data:
        return False
    # Current branding "MITs"; older casts used "mit ⚡"
    return "MITs" in data or "mit ⚡" in data


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument(
        "--first-delay",
        type=float,
        default=0.05,
        metavar="SEC",
        help="delay (seconds) on first kept event (default: 0.05)",
    )
    args = p.parse_args()

    raw = args.input.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if not lines:
        print("empty file", file=sys.stderr)
        sys.exit(1)

    header = json.loads(lines[0])
    events: list[list] = []
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        events.append(json.loads(line))

    start = 0
    for i, ev in enumerate(events):
        if _is_mit_main_frame(ev):
            start = i
            break
    else:
        print(
            "trim_asciicast_start: no MITs main UI found (expected output with VIEWS + MITs)",
            file=sys.stderr,
        )
        sys.exit(1)

    kept = events[start:]
    if not kept:
        sys.exit(1)
    kept[0] = [args.first_delay, kept[0][1], kept[0][2]]

    out_lines = [json.dumps(header, ensure_ascii=False)]
    for ev in kept:
        out_lines.append(json.dumps(ev, ensure_ascii=False))

    args.output.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"trimmed: dropped {start} events, {len(kept)} kept → {args.output}")


if __name__ == "__main__":
    main()
