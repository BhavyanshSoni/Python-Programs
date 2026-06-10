"""Fast checkout and sales processing interface."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from config import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL
from database import Database, DatabaseError
from ui.components import SectionHeader, TreeviewFrame, format_currency, show_toast, validate_integer


class SalesView(ctk.CTkFrame):
    """Point-of-sale checkout with live stock updates."""

    SALE_COLUMNS = ("sku", "name", "price", "qty", "revenue", "profit", "sold_at", "by")
    SALE_HEADINGS = {
        "sku": ("SKU", 80),
        "name": ("Product", 160),
        "price": ("Unit Price", 80),
        "qty": ("Qty", 50),
        "revenue": ("Revenue", 90),
        "profit": ("Profit", 80),
        "sold_at": ("Timestamp", 140),
        "by": ("Sold By", 80),
    }

    STOCK_COLUMNS = ("sku", "name", "price", "qty")
    STOCK_HEADINGS = {
        "sku": ("SKU", 80),
        "name": ("Product", 180),
        "price": ("Price", 80),
        "qty": ("In Stock", 70),
    }

    def __init__(self, master, db: Database, user: dict, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db = db
        self.user = user
        self._owner_id = user["id"]
        self._selected_product_id: int | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self, "Sales & Checkout", "Process transactions with automatic stock deduction",
        )
        header.pack(fill="x", padx=24, pady=(24, 16))
        header.add_button("Refresh", self.refresh, style="secondary")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Left — recent sales
        left = ctk.CTkFrame(
            body, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ctk.CTkLabel(
            left, text="Recent Transactions", font=FONT_BODY, text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(12, 8))
        self._sales_tree = TreeviewFrame(left, self.SALE_COLUMNS, self.SALE_HEADINGS)
        self._sales_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Right — checkout panel
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        checkout = ctk.CTkFrame(
            right, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        checkout.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            checkout, text="⚡ Quick Checkout", font=FONT_HEADING, text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=16, pady=(16, 8))

        search_row = ctk.CTkFrame(checkout, fg_color="transparent")
        search_row.pack(fill="x", padx=16, pady=(0, 8))
        self._search = ctk.CTkEntry(
            search_row, placeholder_text="Search product…", height=36,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self._search.pack(fill="x")
        self._search.bind("<KeyRelease>", lambda _: self._load_stock())

        stock_frame = ctk.CTkFrame(checkout, fg_color="transparent", height=160)
        stock_frame.pack(fill="x", padx=8, pady=(0, 8))
        stock_frame.pack_propagate(False)
        self._stock_tree = TreeviewFrame(stock_frame, self.STOCK_COLUMNS, self.STOCK_HEADINGS)
        self._stock_tree.pack(fill="both", expand=True)
        self._stock_tree.tree.bind("<<TreeviewSelect>>", self._on_product_select)

        self._selected_label = ctk.CTkLabel(
            checkout, text="No product selected", font=FONT_SMALL,
            text_color=COLORS["text_muted"],
        )
        self._selected_label.pack(anchor="w", padx=16, pady=(4, 4))

        qty_row = ctk.CTkFrame(checkout, fg_color="transparent")
        qty_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            qty_row, text="Quantity:", font=FONT_SMALL, text_color=COLORS["text_secondary"]
        ).pack(side="left")
        self._qty_entry = ctk.CTkEntry(
            qty_row, width=80, height=36, font=FONT_BODY,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self._qty_entry.insert(0, "1")
        self._qty_entry.pack(side="left", padx=(8, 0))

        self._total_label = ctk.CTkLabel(
            checkout, text="Total: ₹0.00", font=(FONT_HEADING[0], 20, "bold"),
            text_color=COLORS["accent_emerald"],
        )
        self._total_label.pack(anchor="w", padx=16, pady=(4, 8))

        ctk.CTkButton(
            checkout, text="Complete Sale", height=48, font=FONT_BODY,
            fg_color=COLORS["accent_emerald"], hover_color=COLORS["accent_emerald_hover"],
            command=self._complete_sale,
        ).pack(fill="x", padx=16, pady=(0, 16))

        self._qty_entry.bind("<KeyRelease>", lambda _: self._update_total())

        # Summary card
        summary = ctk.CTkFrame(
            right, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        summary.pack(fill="both", expand=True)
        ctk.CTkLabel(
            summary, text="Session Info", font=FONT_BODY, text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(12, 8))
        self._session_info = ctk.CTkLabel(
            summary,
            text=f"Logged in as: {self.user['username']} ({self.user['role'].title()})\n\n"
                 "Select a product, enter quantity, and click Complete Sale.\n"
                 "Stock levels update instantly upon checkout.",
            font=FONT_SMALL,
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=280,
        )
        self._session_info.pack(anchor="w", padx=16, pady=(0, 16))

        self._selected_price: float = 0.0

    def refresh(self) -> None:
        self._load_sales()
        self._load_stock()

    def _load_sales(self) -> None:
        tree = self._sales_tree.tree
        tree.clear()
        for i, s in enumerate(self.db.get_recent_sales(self._owner_id, limit=100)):
            tree.insert(
                "",
                "end",
                values=(
                    s["product_id"],
                    s["name"],
                    format_currency(s["total_revenue"] / s["quantity_sold"]),
                    s["quantity_sold"],
                    format_currency(s["total_revenue"]),
                    format_currency(s["profit"]),
                    s["sold_at"],
                    s["sold_by"],
                ),
                tags=("even" if i % 2 == 0 else "odd",),
            )

    def _load_stock(self) -> None:
        tree = self._stock_tree.tree
        tree.clear()
        products = self.db.get_products(self._owner_id, search=self._search.get())
        for i, p in enumerate(products):
            if p["quantity"] <= 0:
                continue
            tags = ("low_stock",) if p["quantity"] <= 5 else ()
            tree.insert(
                "",
                "end",
                iid=str(p["id"]),
                values=(
                    p["product_id"],
                    p["name"],
                    format_currency(p["selling_price"]),
                    p["quantity"],
                ),
                tags=tags + ("even" if i % 2 == 0 else "odd",),
            )

    def _on_product_select(self, _event=None) -> None:
        selection = self._stock_tree.tree.selection()
        if not selection:
            return
        self._selected_product_id = int(selection[0])
        product = self.db.get_product_by_id(self._owner_id, self._selected_product_id)
        if product:
            self._selected_price = product["selling_price"]
            self._selected_label.configure(
                text=f"{product['name']} — {format_currency(product['selling_price'])} each "
                     f"({product['quantity']} in stock)",
                text_color=COLORS["text_primary"],
            )
            self._update_total()

    def _update_total(self) -> None:
        qty_str = self._qty_entry.get().strip()
        if validate_integer(qty_str) and self._selected_product_id:
            total = self._selected_price * int(qty_str)
            self._total_label.configure(text=f"Total: {format_currency(total)}")
        else:
            self._total_label.configure(text="Total: ₹0.00")

    def _complete_sale(self) -> None:
        if not self._selected_product_id:
            messagebox.showwarning("Selection", "Select a product to sell.")
            return
        qty_str = self._qty_entry.get().strip()
        if not validate_integer(qty_str) or int(qty_str) <= 0:
            messagebox.showwarning("Validation", "Enter a valid quantity greater than zero.")
            return

        quantity = int(qty_str)
        try:
            result = self.db.process_sale(
                self._owner_id, self._selected_product_id, quantity, self.user["username"]
            )
            show_toast(
                self.winfo_toplevel(),
                f"Sale complete: {result['product_name']} x{quantity} — "
                f"{format_currency(result['total_revenue'])}",
            )
            self._qty_entry.delete(0, "end")
            self._qty_entry.insert(0, "1")
            self._selected_product_id = None
            self._selected_label.configure(text="No product selected", text_color=COLORS["text_muted"])
            self._total_label.configure(text="Total: ₹0.00")
            self.refresh()
        except DatabaseError as exc:
            messagebox.showerror("Sale Failed", str(exc))
