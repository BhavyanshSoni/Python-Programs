"""Inventory management view with CRUD operations."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from config import COLORS, FONT_BODY, FONT_SMALL, LOW_STOCK_THRESHOLD
from database import Database, DatabaseError
from ui.components import SectionHeader, TreeviewFrame, format_currency, show_toast, validate_integer, validate_numeric


class InventoryView(ctk.CTkFrame):
    """Product inventory table with add/update/delete forms."""

    COLUMNS = ("sku", "name", "category", "cost", "price", "qty", "value")
    HEADINGS = {
        "sku": ("SKU", 90),
        "name": ("Product Name", 200),
        "category": ("Category", 120),
        "cost": ("Cost", 80),
        "price": ("Price", 80),
        "qty": ("Qty", 60),
        "value": ("Stock Value", 100),
    }

    def __init__(self, master, db: Database, user: dict, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db = db
        self.user = user
        self._selected_id: int | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self, "Inventory", "Manage product catalog and stock levels",
        )
        header.pack(fill="x", padx=24, pady=(24, 16))
        header.add_button("Refresh", self.refresh, style="secondary")
        if self.user["role"] == "admin":
            header.add_button("Delete", self._delete_product, style="danger")
        header.add_button("Update", self._update_product, style="primary")
        header.add_button("Add Product", self._add_product, style="success")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(body, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            search_frame, text="Search:", font=FONT_SMALL, text_color=COLORS["text_secondary"]
        ).pack(side="left")
        self._search = ctk.CTkEntry(
            search_frame, placeholder_text="SKU, name, or category…", width=280, height=36,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self._search.pack(side="left", padx=(8, 0))
        self._search.bind("<KeyRelease>", lambda _: self.refresh())

        table_frame = ctk.CTkFrame(
            body, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        table_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        self._tree_frame = TreeviewFrame(table_frame, self.COLUMNS, self.HEADINGS)
        self._tree_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self._tree_frame.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ctk.CTkFrame(
            body, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        form.grid(row=0, column=1, rowspan=2, sticky="nsew")
        ctk.CTkLabel(
            form, text="Product Details", font=FONT_BODY, text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=16, pady=(16, 12))

        self._fields: dict[str, ctk.CTkEntry] = {}
        field_defs = [
            ("product_id", "Product ID (SKU)"),
            ("name", "Product Name"),
            ("category", "Category"),
            ("cost_price", "Cost Price (₹)"),
            ("selling_price", "Selling Price (₹)"),
            ("quantity", "Quantity"),
        ]
        for key, label in field_defs:
            ctk.CTkLabel(
                form, text=label, font=FONT_SMALL, text_color=COLORS["text_secondary"]
            ).pack(anchor="w", padx=16, pady=(4, 0))
            entry = ctk.CTkEntry(
                form, height=36, font=FONT_BODY,
                fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            )
            entry.pack(fill="x", padx=16, pady=(2, 4))
            self._fields[key] = entry

        ctk.CTkButton(
            form, text="Clear Form", height=36, font=FONT_SMALL,
            fg_color=COLORS["bg_input"], hover_color=COLORS["bg_hover"],
            command=self._clear_form,
        ).pack(fill="x", padx=16, pady=(12, 16))

        legend = ctk.CTkFrame(form, fg_color=COLORS["danger_soft"], corner_radius=8)
        legend.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkLabel(
            legend,
            text=f"Rows highlighted red = low stock (≤{LOW_STOCK_THRESHOLD})",
            font=(FONT_SMALL[0], 10),
            text_color=COLORS["text_secondary"],
        ).pack(padx=10, pady=8)

    def refresh(self) -> None:
        tree = self._tree_frame.tree
        tree.clear()
        products = self.db.get_products(self.user["id"], search=self._search.get())

        for i, p in enumerate(products):
            tags = []
            if p["quantity"] <= LOW_STOCK_THRESHOLD:
                tags.append("low_stock")
            tags.append("even" if i % 2 == 0 else "odd")

            tree.insert(
                "",
                "end",
                iid=str(p["id"]),
                values=(
                    p["product_id"],
                    p["name"],
                    p["category"],
                    format_currency(p["cost_price"]),
                    format_currency(p["selling_price"]),
                    p["quantity"],
                    format_currency(p["cost_price"] * p["quantity"]),
                ),
                tags=tuple(tags),
            )

    def _on_select(self, _event=None) -> None:
        selection = self._tree_frame.tree.selection()
        if not selection:
            return
        self._selected_id = int(selection[0])
        product = self.db.get_product_by_id(self.user["id"], self._selected_id)
        if not product:
            return
        self._fields["product_id"].delete(0, "end")
        self._fields["product_id"].insert(0, product["product_id"])
        self._fields["name"].delete(0, "end")
        self._fields["name"].insert(0, product["name"])
        self._fields["category"].delete(0, "end")
        self._fields["category"].insert(0, product["category"])
        self._fields["cost_price"].delete(0, "end")
        self._fields["cost_price"].insert(0, str(product["cost_price"]))
        self._fields["selling_price"].delete(0, "end")
        self._fields["selling_price"].insert(0, str(product["selling_price"]))
        self._fields["quantity"].delete(0, "end")
        self._fields["quantity"].insert(0, str(product["quantity"]))

    def _clear_form(self) -> None:
        self._selected_id = None
        self._tree_frame.tree.selection_remove(self._tree_frame.tree.selection())
        for field in self._fields.values():
            field.delete(0, "end")

    def _parse_form(self) -> dict | None:
        product_id = self._fields["product_id"].get().strip()
        name = self._fields["name"].get().strip()
        category = self._fields["category"].get().strip()
        cost_str = self._fields["cost_price"].get().strip()
        price_str = self._fields["selling_price"].get().strip()
        qty_str = self._fields["quantity"].get().strip()

        if not all([product_id, name, category, cost_str, price_str, qty_str]):
            messagebox.showwarning("Validation", "All fields are required.")
            return None
        if not validate_numeric(cost_str):
            messagebox.showwarning("Validation", "Cost price must be a valid non-negative number.")
            return None
        if not validate_numeric(price_str):
            messagebox.showwarning("Validation", "Selling price must be a valid non-negative number.")
            return None
        if not validate_integer(qty_str):
            messagebox.showwarning("Validation", "Quantity must be a valid non-negative integer.")
            return None

        return {
            "product_id": product_id,
            "name": name,
            "category": category,
            "cost_price": float(cost_str),
            "selling_price": float(price_str),
            "quantity": int(qty_str),
        }

    def _add_product(self) -> None:
        data = self._parse_form()
        if not data:
            return
        try:
            self.db.add_product(self.user["id"], **data)
            show_toast(self.winfo_toplevel(), f"Added {data['name']} to inventory.")
            self._clear_form()
            self.refresh()
        except DatabaseError as exc:
            messagebox.showerror("Error", str(exc))

    def _update_product(self) -> None:
        if not self._selected_id:
            messagebox.showwarning("Selection", "Select a product to update.")
            return
        data = self._parse_form()
        if not data:
            return
        try:
            self.db.update_product(self.user["id"], self._selected_id, **data)
            show_toast(self.winfo_toplevel(), f"Updated {data['name']}.")
            self.refresh()
        except DatabaseError as exc:
            messagebox.showerror("Error", str(exc))

    def _delete_product(self) -> None:
        if self.user["role"] != "admin":
            messagebox.showwarning("Permission", "Only admins can delete products.")
            return
        if not self._selected_id:
            messagebox.showwarning("Selection", "Select a product to delete.")
            return
        product = self.db.get_product_by_id(self.user["id"], self._selected_id)
        if not product:
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete '{product['name']}'?"):
            return
        try:
            self.db.delete_product(self.user["id"], self._selected_id)
            show_toast(self.winfo_toplevel(), "Product deleted.", success=False)
            self._clear_form()
            self.refresh()
        except DatabaseError as exc:
            messagebox.showerror("Error", str(exc))
