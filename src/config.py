"""Configuration settings for Scrcpy Phone Farm Dashboard."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = BASE_DIR / "bin"
SCRCPY_EXE = str(BIN_DIR / "scrcpy.exe")
ADB_EXE = str(BIN_DIR / "adb.exe")
SCRCPY_SERVER = str(BIN_DIR / "scrcpy-server")

# Quality Presets (optimized for multi-device performance)
QUALITY_PRESETS = {
    "Balanced (5-12 HP)": {
        "max_size": 800,
        "max_fps": 30,
        "bitrate": "2M",
        "desc": "Resolusi 800px, 30 FPS, 2 Mbps (Optimal & Ringan)"
    },
    "Farm Max (13-20 HP)": {
        "max_size": 540,
        "max_fps": 25,
        "bitrate": "1.2M",
        "desc": "Resolusi 540px, 25 FPS, 1.2 Mbps (Paling Hemat Daya)"
    },
    "High Quality (1-4 HP)": {
        "max_size": 1080,
        "max_fps": 60,
        "bitrate": "4M",
        "desc": "Resolusi 1080px, 60 FPS, 4 Mbps (Jernih & Tajam)"
    }
}

DEFAULT_PRESET = "Balanced (5-12 HP)"

# Premium Cyber Slate Theme Colors
COLORS = {
    # Backgrounds
    "bg_root": "#0B0D14",         # Very deep obsidian
    "bg_header": "#121520",       # Header bar slate
    "bg_card": "#181C2B",         # Device card chassis
    "bg_card_inner": "#000000",   # Phone screen background
    "bg_card_hover": "#202538",   # Hover state
    "bg_surface": "#1E2235",      # Controls background
    "bg_input": "#10131E",        # Input fields

    # Borders & Dividers
    "border_subtle": "#23283E",   # Subtle card border
    "border_card": "#2B324D",     # Default card border
    "border_glow": "#38BDF8",     # Cyan focus glow
    "border_master": "#F59E0B",   # Gold Master border

    # Text
    "text_white": "#F8FAFC",      # Bright text
    "text_primary": "#E2E8F0",    # Main body
    "text_secondary": "#94A3B8",  # Secondary details
    "text_muted": "#64748B",      # Muted labels

    # Vibrant Accents
    "accent_cyan": "#06B6D4",     # Neon cyan
    "accent_blue": "#3B82F6",     # Electric blue
    "accent_green": "#10B981",    # Emerald green
    "accent_yellow": "#F59E0B",   # Amber / Gold
    "accent_red": "#EF4444",      # Crimson red
    "accent_purple": "#8B5CF6",   # Royal purple
    "accent_orange": "#F97316",   # Orange
}

# Grid & Layout Settings
DEFAULT_COLUMNS = 4
MAX_DEVICES = 20

# Standard smartphone cell dimensions (height fixed to 520px, width adapted per phone ratio)
CELL_HEIGHT = 520
DEFAULT_CELL_WIDTH = 245
POLL_INTERVAL_MS = 2500  # Device scan interval
