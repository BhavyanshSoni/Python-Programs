"""Main application shell with sidebar navigation."""

from __future__ import annotations

import customtkinter as ctk

from config import COLORS, FONT_BODY, FONT_SMALL, FONT_SUBHEADING, NAV_ITEMS, WINDOW_MIN_SIZE, WINDOW_TITLE
from database import Database
from ui.dashboard import DashboardView
from ui.insights import InsightsView
from ui.inventory import InventoryView
from ui.sales import SalesView


class AppShell(ctk.CTk):
    """Primary application window with sidebar navigation."""

    def __init__(self, db: Database, user: dict) -> None:
        super().__init__()
        self.db = db
        self.user = user
        self._current_view: str | None = None
        self._views: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_MIN_SIZE[0]}x{WINDOW_MIN_SIZE[1]}")
        self.minsize(*WINDOW_MIN_SIZE)
        self.configure(fg_color=COLORS["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_layout()
        self._show_view("dashboard")
        self._center_window()

    def _center_window(self) -> None:
        self.update_idletasks()
        w = WINDOW_MIN_SIZE[0]
        h = WINDOW_MIN_SIZE[1]
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            self, width=220, fg_color=COLORS["bg_sidebar"], corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="📦 InvManager", font=FONT_SUBHEADING, text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=20, pady=(24, 4))
        ctk.CTkLabel(
            sidebar, text="Pro Edition", font=FONT_SMALL, text_color=COLORS["text_muted"]
        ).pack(anchor="w", padx=20, pady=(0, 24))

        for key, label, icon in NAV_ITEMS:
            btn = ctk.CTkButton(
                sidebar,
                text=f"  {icon}  {label}",
                anchor="w",
                height=42,
                font=FONT_BODY,
                fg_color="transparent",
                hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_secondary"],
                command=lambda k=key: self._show_view(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = btn

        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        user_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_card"], corner_radius=10)
        user_frame.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(
            user_frame,
            text=f"👤 {self.user['username']}",
            font=FONT_BODY,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(
            user_frame,
            text=self.user["role"].title(),
            font=FONT_SMALL,
            text_color=COLORS["accent_blue"],
        ).pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkButton(
            sidebar,
            text="Sign Out",
            height=36,
            font=FONT_SMALL,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["danger"],
            command=self._sign_out,
        ).pack(fill="x", padx=12, pady=(0, 20))

        self._content = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

    def _show_view(self, key: str) -> None:
        if self._current_view == key:
            return

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(
                    fg_color=COLORS["accent_blue"],
                    text_color=COLORS["text_primary"],
                )
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_secondary"])

        if key not in self._views:
            self._views[key] = self._create_view(key)

        for view in self._views.values():
            view.grid_forget()

        self._views[key].grid(row=0, column=0, sticky="nsew")
        if hasattr(self._views[key], "refresh"):
            self._views[key].refresh()

        self._current_view = key

    def _create_view(self, key: str) -> ctk.CTkFrame:
        factories = {
            "dashboard": lambda: DashboardView(self._content, self.db, self.user),
            "inventory": lambda: InventoryView(self._content, self.db, self.user),
            "sales": lambda: SalesView(self._content, self.db, self.user),
            "insights": lambda: InsightsView(self._content, self.db, self.user),
        }
        return factories[key]()

    def _sign_out(self) -> None:
        self.destroy()
