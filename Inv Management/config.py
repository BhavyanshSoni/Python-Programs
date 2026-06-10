"""Application-wide configuration, theme palette, and constants."""

from pathlib import Path

# Paths
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "inventory.db"
EXPORT_DIR = DATA_DIR / "exports"

# Currency
CURRENCY_SYMBOL = "₹"

# Inventory thresholds
LOW_STOCK_THRESHOLD = 5
REORDER_LOOKBACK_DAYS = 30

# Theme — dark-mode-first enterprise palette
COLORS = {
    "bg_dark": "#0f1419",
    "bg_sidebar": "#151b23",
    "bg_card": "#1c2430",
    "bg_input": "#252f3d",
    "bg_hover": "#2a3544",
    "text_primary": "#f0f4f8",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "accent_blue": "#3b82f6",
    "accent_blue_hover": "#2563eb",
    "accent_emerald": "#10b981",
    "accent_emerald_hover": "#059669",
    "accent_amber": "#f59e0b",
    "danger": "#ef4444",
    "danger_soft": "#3d2020",
    "success": "#22c55e",
    "border": "#2d3748",
    "chart_line": "#3b82f6",
    "chart_bar": "#10b981",
    "chart_grid": "#334155",
}

# Typography
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 24, "bold")
FONT_HEADING = (FONT_FAMILY, 18, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 13)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 12)

# Window defaults
WINDOW_TITLE = "InvManager Pro — Enterprise Inventory System"
WINDOW_MIN_SIZE = (1200, 720)
LOGIN_SIZE = (480, 620)

# Navigation
NAV_ITEMS = [
    ("dashboard", "Dashboard", "📊"),
    ("inventory", "Inventory", "📦"),
    ("sales", "Sales", "🛒"),
    ("insights", "Insights", "💡"),
]
