"""themes.py — terminal-native colour palettes for MITs"""
from __future__ import annotations

from textual.theme import Theme

THEME_NAMES = ["dark", "gruvbox", "nord", "tokyo-night", "light"]

THEMES: dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        primary="#444444",
        accent="#d4a017",
        foreground="#c8c8c8",
        background="#1c1c1c",
        surface="#1c1c1c",
        panel="#1c1c1c",
        boost="#2a2a2a",
        success="#5a7a5a",
        warning="#d4a017",
        error="#8b3a3a",
        dark=True,
    ),
    "gruvbox": Theme(
        name="gruvbox",
        primary="#504945",
        accent="#d79921",
        foreground="#ebdbb2",
        background="#1d2021",
        surface="#1d2021",
        panel="#1d2021",
        boost="#3c3836",
        success="#689d6a",
        warning="#d79921",
        error="#cc241d",
        dark=True,
    ),
    "nord": Theme(
        name="nord",
        primary="#4c566a",
        accent="#ebcb8b",
        foreground="#d8dee9",
        background="#2e3440",
        surface="#2e3440",
        panel="#2e3440",
        boost="#3b4252",
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
        dark=True,
    ),
    "tokyo-night": Theme(
        name="tokyo-night",
        primary="#3b4261",
        accent="#e0af68",
        foreground="#c0caf5",
        background="#1a1b26",
        surface="#1a1b26",
        panel="#1a1b26",
        boost="#24283b",
        success="#9ece6a",
        warning="#e0af68",
        error="#f7768e",
        dark=True,
    ),
    "light": Theme(
        name="light",
        primary="#c0c0c0",
        accent="#8a6d00",
        foreground="#2e2e2e",
        background="#f0f0f0",
        surface="#f0f0f0",
        panel="#f0f0f0",
        boost="#e0e0e0",
        success="#3a6a3a",
        warning="#8a6d00",
        error="#8b3a3a",
        dark=False,
    ),
}


def get_next_theme(current: str) -> str:
    idx = THEME_NAMES.index(current) if current in THEME_NAMES else 0
    return THEME_NAMES[(idx + 1) % len(THEME_NAMES)]