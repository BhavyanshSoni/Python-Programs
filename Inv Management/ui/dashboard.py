"""Dashboard view with KPI cards, charts, and export actions."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from analytics import calculate_dashboard_metrics, get_profit_trend, get_top_selling_products
from config import COLORS, FONT_BODY, FONT_SMALL, LOW_STOCK_THRESHOLD
from database import Database
from export import export_financial_csv, export_inventory_csv, export_inventory_excel
from ui.components import MetricCard, SectionHeader, format_currency, show_toast


class DashboardView(ctk.CTkFrame):
    """Analytics dashboard with embedded Matplotlib charts."""

    def __init__(self, master, db: Database, user: dict, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db = db
        self.user = user
        self._owner_id = user["id"]
        self._chart_canvas: FigureCanvasTkAgg | None = None
        self._bar_canvas: FigureCanvasTkAgg | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = SectionHeader(
            self,
            "Dashboard",
            "Real-time business metrics and performance analytics",
        )
        header.pack(fill="x", padx=24, pady=(24, 16))
        header.add_button("Export CSV", self._export_csv, style="secondary")
        header.add_button("Export Excel", self._export_excel, style="success")

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=24, pady=(0, 16))
        cards.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        self._card_revenue = MetricCard(
            cards, "Total Revenue", accent=COLORS["accent_blue"]
        )
        self._card_revenue.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._card_profit = MetricCard(
            cards, "Net Profit", accent=COLORS["accent_emerald"]
        )
        self._card_profit.grid(row=0, column=1, sticky="nsew", padx=4)

        self._card_capital = MetricCard(
            cards, "Total Capital Invested", accent=COLORS["accent_amber"]
        )
        self._card_capital.grid(row=0, column=2, sticky="nsew", padx=4)

        self._card_sold = MetricCard(
            cards, "Products Sold", accent=COLORS["accent_blue"]
        )
        self._card_sold.grid(row=0, column=3, sticky="nsew", padx=(8, 0))

        charts = ctk.CTkFrame(self, fg_color="transparent")
        charts.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        charts.grid_columnconfigure(0, weight=3)
        charts.grid_columnconfigure(1, weight=2)
        charts.grid_rowconfigure(0, weight=1)

        self._profit_frame = ctk.CTkFrame(
            charts, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        self._profit_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            self._profit_frame, text="Profit Trend (14 Days)", font=FONT_BODY,
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(12, 0))
        self._profit_chart_host = ctk.CTkFrame(self._profit_frame, fg_color="transparent")
        self._profit_chart_host.pack(fill="both", expand=True, padx=8, pady=8)

        self._top_frame = ctk.CTkFrame(
            charts, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        self._top_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(
            self._top_frame, text="Top Selling Products", font=FONT_BODY,
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(12, 0))
        self._bar_chart_host = ctk.CTkFrame(self._top_frame, fg_color="transparent")
        self._bar_chart_host.pack(fill="both", expand=True, padx=8, pady=8)

        self._alert_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"],
        )
        self._alert_frame.pack(fill="x", padx=24, pady=(0, 24))
        self._alert_label = ctk.CTkLabel(
            self._alert_frame, text="", font=FONT_SMALL, text_color=COLORS["text_secondary"],
            wraplength=900, justify="left",
        )
        self._alert_label.pack(anchor="w", padx=16, pady=12)

    def refresh(self) -> None:
        metrics = calculate_dashboard_metrics(self.db, self._owner_id)
        self._card_revenue.update_values(
            format_currency(metrics["total_revenue"]),
            f"Retail inventory value: {format_currency(metrics['inventory_value_retail'])}",
        )
        self._card_profit.update_values(
            format_currency(metrics["net_profit"]),
            f"Margin: {metrics['profit_margin_pct']}%",
        )
        self._card_capital.update_values(
            format_currency(metrics["total_capital"]),
            f"{metrics['total_skus']} SKUs in stock",
        )
        self._card_sold.update_values(
            str(metrics["products_sold"]),
            f"{metrics['low_stock_count']} items low stock (≤{LOW_STOCK_THRESHOLD})",
        )

        low_stock = self.db.get_low_stock_products(self._owner_id)
        products = self.db.get_products(self._owner_id)
        if not products:
            self._alert_label.configure(
                text="Welcome! Your account is fresh — add products in Inventory to get started.",
                text_color=COLORS["accent_blue"],
            )
        elif low_stock:
            names = ", ".join(f"{p['name']} ({p['quantity']})" for p in low_stock[:5])
            extra = f" +{len(low_stock) - 5} more" if len(low_stock) > 5 else ""
            self._alert_label.configure(
                text=f"⚠ Low Stock Alert: {names}{extra}",
                text_color=COLORS["accent_amber"],
            )
        else:
            self._alert_label.configure(
                text="✓ All products above minimum stock threshold.",
                text_color=COLORS["accent_emerald"],
            )

        self._render_profit_chart()
        self._render_top_products_chart()

    def _styled_figure(self, size: tuple[float, float]) -> Figure:
        fig = Figure(figsize=size, dpi=100, facecolor=COLORS["bg_card"])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.18)
        return fig

    def _render_profit_chart(self) -> None:
        for widget in self._profit_chart_host.winfo_children():
            widget.destroy()

        data = get_profit_trend(self.db, self._owner_id, days=14)
        labels = [d[5:] for d, _ in data]
        values = [v for _, v in data]

        fig = self._styled_figure((6, 2.8))
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        ax.plot(labels, values, color=COLORS["chart_line"], linewidth=2, marker="o", markersize=4)
        ax.fill_between(range(len(values)), values, alpha=0.15, color=COLORS["chart_line"])
        ax.tick_params(colors=COLORS["text_muted"], labelsize=8)
        ax.set_ylabel("Profit (₹)", color=COLORS["text_secondary"], fontsize=9)
        ax.grid(True, alpha=0.2, color=COLORS["chart_grid"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self._profit_chart_host)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _render_top_products_chart(self) -> None:
        for widget in self._bar_chart_host.winfo_children():
            widget.destroy()

        top = get_top_selling_products(self.db, self._owner_id, limit=5)
        if not top:
            ctk.CTkLabel(
                self._bar_chart_host, text="No sales data yet", font=FONT_SMALL,
                text_color=COLORS["text_muted"],
            ).pack(expand=True)
            return

        names = [p["name"][:14] + "…" if len(p["name"]) > 14 else p["name"] for p in top]
        units = [p["units"] for p in top]

        fig = self._styled_figure((4, 2.8))
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        bars = ax.barh(names, units, color=COLORS["chart_bar"], height=0.6)
        ax.tick_params(colors=COLORS["text_muted"], labelsize=8)
        ax.set_xlabel("Units Sold", color=COLORS["text_secondary"], fontsize=9)
        ax.grid(True, axis="x", alpha=0.2, color=COLORS["chart_grid"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])
        for bar, val in zip(bars, units):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", color=COLORS["text_secondary"], fontsize=8)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self._bar_chart_host)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _export_csv(self) -> None:
        try:
            inv_path = export_inventory_csv(self.db, self._owner_id)
            fin_path = export_financial_csv(self.db, self._owner_id)
            show_toast(self.winfo_toplevel(), f"Exported to {inv_path.parent.name}/")
            messagebox.showinfo(
                "Export Complete",
                f"Files saved:\n{inv_path}\n{fin_path}",
            )
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _export_excel(self) -> None:
        try:
            path = export_inventory_excel(self.db, self._owner_id)
            show_toast(self.winfo_toplevel(), "Excel report exported successfully.")
            messagebox.showinfo("Export Complete", f"File saved:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))
