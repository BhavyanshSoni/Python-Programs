"""Reusable UI components for InvManager Pro."""

from __future__ import annotations

from tkinter import ttk
from typing import Callable

import customtkinter as ctk

from config import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL, FONT_SUBHEADING


class MetricCard(ctk.CTkFrame):
    """Dashboard KPI card with title, value, and optional subtitle."""

    def __init__(
        self,
        master,
        title: str,
        value: str = "—",
        subtitle: str = "",
        accent: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        accent = accent or COLORS["accent_blue"]
        self._accent_bar = ctk.CTkFrame(self, fg_color=accent, height=4, corner_radius=2)
        self._accent_bar.pack(fill="x", padx=16, pady=(14, 0))

        self._title = ctk.CTkLabel(
            self, text=title, font=FONT_SMALL, text_color=COLORS["text_secondary"]
        )
        self._title.pack(anchor="w", padx=16, pady=(10, 0))

        self._value = ctk.CTkLabel(
            self, text=value, font=(FONT_HEADING[0], 28, "bold"), text_color=COLORS["text_primary"]
        )
        self._value.pack(anchor="w", padx=16, pady=(4, 0))

        self._subtitle = ctk.CTkLabel(
            self, text=subtitle, font=FONT_SMALL, text_color=COLORS["text_muted"]
        )
        self._subtitle.pack(anchor="w", padx=16, pady=(2, 16))

    def update_values(self, value: str, subtitle: str = "") -> None:
        self._value.configure(text=value)
        if subtitle:
            self._subtitle.configure(text=subtitle)


class StyledTreeview(ttk.Treeview):
    """Dark-themed Treeview with low-stock row highlighting."""

    COLUMNS: tuple[str, ...] = ()

    def __init__(self, master, columns: tuple[str, ...], **kwargs) -> None:
        self.COLUMNS = columns
        super().__init__(
            master,
            columns=columns,
            show="headings",
            selectmode="browse",
            **kwargs,
        )
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Inv.Treeview",
            background=COLORS["bg_card"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_card"],
            borderwidth=0,
            rowheight=32,
            font=FONT_BODY,
        )
        style.configure(
            "Inv.Treeview.Heading",
            background=COLORS["bg_input"],
            foreground=COLORS["text_secondary"],
            font=FONT_SUBHEADING,
            relief="flat",
        )
        style.map(
            "Inv.Treeview",
            background=[("selected", COLORS["accent_blue"])],
            foreground=[("selected", COLORS["text_primary"])],
        )
        self.configure(style="Inv.Treeview")
        self.tag_configure("low_stock", background=COLORS["danger_soft"])
        self.tag_configure("even", background=COLORS["bg_card"])
        self.tag_configure("odd", background=COLORS["bg_hover"])

    def setup_headings(self, headings: dict[str, tuple[str, int]]) -> None:
        """headings: {column_id: (display_name, width)}"""
        for col, (text, width) in headings.items():
            self.heading(col, text=text)
            self.column(col, width=width, anchor="center" if col != "name" else "w")

    def clear(self) -> None:
        for item in self.get_children():
            self.delete(item)


class TreeviewFrame(ctk.CTkFrame):
    """Scrollable Treeview wrapper."""

    def __init__(self, master, columns: tuple[str, ...], headings: dict[str, tuple[str, int]], **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.tree = StyledTreeview(self, columns=columns)
        self.tree.setup_headings(headings)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")


class SectionHeader(ctk.CTkFrame):
    """Page title with optional action buttons."""

    def __init__(
        self,
        master,
        title: str,
        subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(left, text=title, font=FONT_HEADING, text_color=COLORS["text_primary"]).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                left, text=subtitle, font=FONT_SMALL, text_color=COLORS["text_secondary"]
            ).pack(anchor="w", pady=(2, 0))

        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.pack(side="right")

    def add_button(
        self,
        text: str,
        command: Callable,
        style: str = "primary",
        **kwargs,
    ) -> ctk.CTkButton:
        colors = {
            "primary": (COLORS["accent_blue"], COLORS["accent_blue_hover"]),
            "success": (COLORS["accent_emerald"], COLORS["accent_emerald_hover"]),
            "danger": (COLORS["danger"], "#dc2626"),
            "secondary": (COLORS["bg_input"], COLORS["bg_hover"]),
        }
        fg, hover = colors.get(style, colors["primary"])
        btn = ctk.CTkButton(
            self.actions,
            text=text,
            command=command,
            fg_color=fg,
            hover_color=hover,
            font=FONT_BODY,
            height=36,
            **kwargs,
        )
        btn.pack(side="left", padx=(8, 0))
        return btn


def show_toast(parent: ctk.CTk, message: str, success: bool = True) -> None:
    """Brief notification banner at bottom of window."""
    color = COLORS["accent_emerald"] if success else COLORS["danger"]
    toast = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
    toast.place(relx=0.5, rely=0.97, anchor="s")
    ctk.CTkLabel(toast, text=message, font=FONT_BODY, text_color="white").pack(padx=20, pady=10)
    parent.after(3000, toast.destroy)


def validate_numeric(value: str, allow_negative: bool = False) -> bool:
    """Return True if value is a valid decimal number."""
    if not value.strip():
        return False
    try:
        num = float(value)
        return allow_negative or num >= 0
    except ValueError:
        return False


def validate_integer(value: str, allow_negative: bool = False) -> bool:
    """Return True if value is a valid integer."""
    if not value.strip():
        return False
    try:
        num = int(value)
        return allow_negative or num >= 0
    except ValueError:
        return False


def format_currency(amount: float) -> str:
    from config import CURRENCY_SYMBOL
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"
