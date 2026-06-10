"""Smart insights, reorder forecasts, and inventory intelligence."""

from __future__ import annotations

import customtkinter as ctk

from analytics import get_reorder_recommendations
from config import COLORS, FONT_BODY, FONT_SMALL, REORDER_LOOKBACK_DAYS
from database import Database
from ui.components import MetricCard, SectionHeader, TreeviewFrame


class InsightsView(ctk.CTkFrame):
    """Forecast panel with reorder recommendations and velocity metrics."""

    COLUMNS = ("priority", "sku", "name", "qty", "sold", "velocity", "suggest", "message")
    HEADINGS = {
        "priority": ("Priority", 80),
        "sku": ("SKU", 80),
        "name": ("Product", 160),
        "qty": ("Stock", 60),
        "sold": ("Sold 30d", 70),
        "velocity": ("Daily Vel.", 80),
        "suggest": ("Reorder Qty", 90),
        "message": ("Insight", 260),
    }

    PRIORITY_COLORS = {
        "critical": COLORS["danger"],
        "high": COLORS["accent_amber"],
        "medium": COLORS["accent_blue"],
        "low": COLORS["text_muted"],
    }

    def __init__(self, master, db: Database, user: dict, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db = db
        self._owner_id = user["id"]
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self,
            "Smart Insights",
            f"Automated reorder suggestions based on {REORDER_LOOKBACK_DAYS}-day sales velocity",
        )
        header.pack(fill="x", padx=24, pady=(24, 16))
        header.add_button("Refresh Analysis", self.refresh, style="primary")

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=24, pady=(0, 16))
        cards.grid_columnconfigure((0, 1, 2), weight=1, uniform="insight")

        self._card_critical = MetricCard(cards, "Critical Items", accent=COLORS["danger"])
        self._card_critical.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._card_reorder = MetricCard(cards, "Reorder Suggested", accent=COLORS["accent_amber"])
        self._card_reorder.grid(row=0, column=1, sticky="nsew", padx=4)

        self._card_healthy = MetricCard(cards, "Healthy Stock", accent=COLORS["accent_emerald"])
        self._card_healthy.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        table_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        ctk.CTkLabel(
            table_frame,
            text="📋 Reorder Recommendations",
            font=FONT_BODY,
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self._tree_frame = TreeviewFrame(table_frame, self.COLUMNS, self.HEADINGS)
        self._tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._empty_label = ctk.CTkLabel(
            table_frame,
            text="No products yet. Add inventory from the Inventory tab to get insights.",
            font=FONT_SMALL,
            text_color=COLORS["text_muted"],
        )

    def refresh(self) -> None:
        recommendations = get_reorder_recommendations(self.db, self._owner_id)
        all_products = self.db.get_products(self._owner_id)

        critical = sum(1 for r in recommendations if r["priority"] == "critical")
        reorder = len(recommendations) - critical
        healthy = len(all_products) - len({r["product_id"] for r in recommendations})

        self._card_critical.update_values(str(critical), "Out of stock with demand")
        self._card_reorder.update_values(str(reorder), "Items needing attention")
        self._card_healthy.update_values(str(max(healthy, 0)), "Adequate stock levels")

        tree = self._tree_frame.tree
        tree.clear()

        if not all_products:
            self._empty_label.configure(
                text="No products yet. Add inventory from the Inventory tab to get insights.",
                text_color=COLORS["text_muted"],
            )
            self._empty_label.pack(pady=20)
            return

        if not recommendations:
            self._empty_label.configure(
                text="All inventory levels are healthy. No reorder actions needed.",
                text_color=COLORS["accent_emerald"],
            )
            self._empty_label.pack(pady=20)
            return
        self._empty_label.pack_forget()

        for i, rec in enumerate(recommendations):
            tree.insert(
                "",
                "end",
                values=(
                    rec["priority"].upper(),
                    rec["product_id"],
                    rec["name"],
                    rec["current_qty"],
                    rec["sold_30d"],
                    rec["daily_velocity"],
                    rec["suggested_reorder"],
                    rec["message"],
                ),
                tags=("even" if i % 2 == 0 else "odd",),
            )
