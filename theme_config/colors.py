"""
Central Color Palette Configuration Module — WealthWise Executive Styling
=============================================================================

This file centralizes all theme colors for the entire application.
Exposes CSS custom properties (--color-*) for both Light Theme (:root)
and Dark Theme ([data-theme='dark']), using the Dark Emerald Green & Gold
footer palette for dark mode.
"""

# ============================================================
# LIGHT THEME NAMED COLOR CONSTANTS
# ============================================================

DEEP_ROYAL_PURPLE = "#000000"       # Primary headings & text
WARM_PEACH_CREAM = "#FFFFFF"        # Containers & Cards background
SOFT_LAVENDER = "#F8FAFC"           # Page Body Background
COOL_SLATE_GRAY = "#475569"         # Subtext & labels
SOFT_LAVENDER_BORDER = "#E2E8F0"    # Subtle Gray Border
VIBRANT_VIOLET = "#F1F5F9"          # Primary hover state
ULTRA_SOFT_PURPLE = "#F1F5F9"      # Form input fields background
FOREST_GREEN = "#15803D"            # Success notification text
SOFT_MINT = "#F0FDF4"               # Success alert pill background
DEEP_CRIMSON = "#B91C1C"            # Error alert text
SOFT_ROSE = "#FEF2F2"              # Error alert pill background
GOLDEN_AMBER = "#F59E0B"          # Golden Amber Accent
BRIGHT_CYAN = "#06B6D4"           # Bright Cyan Blue

# ============================================================
# DARK THEME NAMED COLOR CONSTANTS (Solid Dark Emerald & Gold Theme)
# ============================================================

CRISP_SILVER_WHITE = "#FFFFFF"       # Primary text
DEEP_EMERALD_CARD = "#0B1B13"        # Solid Dark Emerald Surface & Card background
DEEP_EMERALD_BG = "#050B08"          # Solid Ultra-Dark Emerald Page background
MIDNIGHT_EMERALD_BG = "#040806"      # Deepest Dark Emerald background
MUTED_EMERALD_SUBTEXT = "#c8d6ce"    # Subtext (Muted Emerald-Silver)
EMERALD_GLASS_BORDER = "rgba(197, 160, 89, 0.25)" # Gold subtle border
EMERALD_PRIMARY_HOVER = "#0F261B"    # Hover state
EMERALD_INPUT_BG = "#07120C"         # Solid Dark Input fields background
EMERALD_GREEN = "#34D399"           # Success text
EMERALD_PILL_BG = "rgba(16, 185, 129, 0.15)" # Success pill bg
BRIGHT_RED = "#F87171"               # Error text
RED_PILL_BG = "rgba(239, 68, 68, 0.15)" # Error pill bg
GOLD_ACCENT = "#C5A059"              # Gold accent
GOLD_LIGHT = "#E5C158"               # Gold light accent
GOLD_DARK = "#8F6B29"                # Gold dark accent
EMERALD_GLOW = "#34D399"             # Emerald glow accent


# ============================================================
# PALETTE ASSIGNMENTS
# ============================================================

# Light Theme
COLOR_PRIMARY = DEEP_ROYAL_PURPLE
COLOR_SECONDARY = WARM_PEACH_CREAM
COLOR_BG = SOFT_LAVENDER
COLOR_TEXT_SUB = COOL_SLATE_GRAY
COLOR_BORDER = SOFT_LAVENDER_BORDER
COLOR_PRIMARY_HOVER = VIBRANT_VIOLET
COLOR_INPUT_BG = ULTRA_SOFT_PURPLE
COLOR_SUCCESS = FOREST_GREEN
COLOR_SUCCESS_BG = SOFT_MINT
COLOR_ERROR = DEEP_CRIMSON
COLOR_ERROR_BG = SOFT_ROSE
COLOR_GOLD = GOLDEN_AMBER
COLOR_CYAN = BRIGHT_CYAN

# Dark Theme (Solid Dark Emerald Green & Gold)
DARK_COLOR_PRIMARY = CRISP_SILVER_WHITE
DARK_COLOR_SECONDARY = DEEP_EMERALD_CARD
DARK_COLOR_BG = DEEP_EMERALD_BG
DARK_COLOR_TEXT_SUB = MUTED_EMERALD_SUBTEXT
DARK_COLOR_BORDER = EMERALD_GLASS_BORDER
DARK_COLOR_PRIMARY_HOVER = EMERALD_PRIMARY_HOVER
DARK_COLOR_INPUT_BG = EMERALD_INPUT_BG
DARK_COLOR_SUCCESS = EMERALD_GREEN
DARK_COLOR_SUCCESS_BG = EMERALD_PILL_BG
DARK_COLOR_ERROR = BRIGHT_RED
DARK_COLOR_ERROR_BG = RED_PILL_BG
DARK_COLOR_GOLD = GOLD_ACCENT
DARK_COLOR_CYAN = EMERALD_GLOW


THEME_PALETTE = {
    # Light
    "COLOR_PRIMARY": COLOR_PRIMARY,
    "COLOR_SECONDARY": COLOR_SECONDARY,
    "COLOR_BG": COLOR_BG,
    "COLOR_TEXT_SUB": COLOR_TEXT_SUB,
    "COLOR_BORDER": COLOR_BORDER,
    "COLOR_PRIMARY_HOVER": COLOR_PRIMARY_HOVER,
    "COLOR_INPUT_BG": COLOR_INPUT_BG,
    "COLOR_SUCCESS": COLOR_SUCCESS,
    "COLOR_SUCCESS_BG": COLOR_SUCCESS_BG,
    "COLOR_ERROR": COLOR_ERROR,
    "COLOR_ERROR_BG": COLOR_ERROR_BG,
    "COLOR_GOLD": COLOR_GOLD,
    "COLOR_CYAN": COLOR_CYAN,
    # Dark
    "DARK_COLOR_PRIMARY": DARK_COLOR_PRIMARY,
    "DARK_COLOR_SECONDARY": DARK_COLOR_SECONDARY,
    "DARK_COLOR_BG": DARK_COLOR_BG,
    "DARK_COLOR_TEXT_SUB": DARK_COLOR_TEXT_SUB,
    "DARK_COLOR_BORDER": DARK_COLOR_BORDER,
    "DARK_COLOR_PRIMARY_HOVER": DARK_COLOR_PRIMARY_HOVER,
    "DARK_COLOR_INPUT_BG": DARK_COLOR_INPUT_BG,
    "DARK_COLOR_SUCCESS": DARK_COLOR_SUCCESS,
    "DARK_COLOR_SUCCESS_BG": DARK_COLOR_SUCCESS_BG,
    "DARK_COLOR_ERROR": DARK_COLOR_ERROR,
    "DARK_COLOR_ERROR_BG": DARK_COLOR_ERROR_BG,
    "DARK_COLOR_GOLD": DARK_COLOR_GOLD,
    "DARK_COLOR_CYAN": DARK_COLOR_CYAN,
}


def get_css_variables():
    """
    Generates CSS custom property declarations for both light and dark themes.
    Dark theme uses the Solid Dark Emerald Green & Gold palette.
    """
    light_vars = [
        f"--color-primary: {COLOR_PRIMARY};",
        f"--color-secondary: {COLOR_SECONDARY};",
        f"--color-card-bg: {COLOR_SECONDARY};",
        f"--color-bg: {COLOR_BG};",
        f"--color-subtext: {COLOR_TEXT_SUB};",
        f"--color-border: {COLOR_BORDER};",
        f"--color-primary-hover: {COLOR_PRIMARY_HOVER};",
        f"--color-input-bg: {COLOR_INPUT_BG};",
        f"--color-success: {COLOR_SUCCESS};",
        f"--color-success-bg: {COLOR_SUCCESS_BG};",
        f"--color-success-border: rgba(21, 128, 61, 0.25);",
        f"--color-error: {COLOR_ERROR};",
        f"--color-error-bg: {COLOR_ERROR_BG};",
        f"--color-error-border: rgba(185, 28, 28, 0.25);",
        f"--color-info: {COLOR_CYAN};",
        f"--color-info-bg: #ECFEFF;",
        f"--color-info-border: rgba(6, 182, 212, 0.2);",
        f"--color-focus-ring: rgba(212, 175, 55, 0.28);",
        f"--color-avatar-shadow: rgba(212, 175, 55, 0.15);",
        f"--color-gold: {COLOR_GOLD};",
        f"--color-gold-deep: #B45309;",
        f"--color-cyan: {COLOR_CYAN};",
        f"--color-glass-bg: rgba(255, 255, 255, 0.85);",
        f"--color-glass-border: rgba(255, 255, 255, 0.5);",
        f"--color-body-gradient: {COLOR_BG};",
    ]

    dark_vars = [
        f"--color-primary: {DARK_COLOR_PRIMARY};",
        f"--color-secondary: {DARK_COLOR_SECONDARY};",
        f"--color-card-bg: {DARK_COLOR_SECONDARY};",
        f"--color-bg: {DARK_COLOR_BG};",
        f"--color-subtext: {DARK_COLOR_TEXT_SUB};",
        f"--color-border: {DARK_COLOR_BORDER};",
        f"--color-primary-hover: {DARK_COLOR_PRIMARY_HOVER};",
        f"--color-input-bg: {DARK_COLOR_INPUT_BG};",
        f"--color-success: {DARK_COLOR_SUCCESS};",
        f"--color-success-bg: {DARK_COLOR_SUCCESS_BG};",
        f"--color-success-border: rgba(52, 211, 153, 0.25);",
        f"--color-error: {DARK_COLOR_ERROR};",
        f"--color-error-bg: {DARK_COLOR_ERROR_BG};",
        f"--color-error-border: rgba(248, 113, 113, 0.25);",
        f"--color-info: #34D399;",
        f"--color-info-bg: rgba(52, 211, 153, 0.15);",
        f"--color-info-border: rgba(52, 211, 153, 0.25);",
        f"--color-focus-ring: rgba(197, 160, 89, 0.3);",
        f"--color-avatar-shadow: rgba(0, 0, 0, 0.5);",
        f"--color-gold: {DARK_COLOR_GOLD};",
        f"--color-gold-deep: {GOLD_DARK};",
        f"--color-cyan: {DARK_COLOR_CYAN};",
        f"--color-glass-bg: rgba(11, 27, 19, 0.85);",
        f"--color-glass-border: rgba(197, 160, 89, 0.22);",
        f"--color-body-gradient: radial-gradient(circle at 50% 10%, rgba(197, 160, 89, 0.08) 0%, rgba(5, 11, 8, 0.98) 75%), linear-gradient(180deg, #091710 0%, #040806 100%);",
    ]

    light_str = "\n  ".join(light_vars)
    dark_str = "\n  ".join(dark_vars)

    return f":root {{\n  {light_str}\n}}\n\n[data-theme='dark'] {{\n  {dark_str}\n}}"



