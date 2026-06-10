"""Business analytics, KPI calculations, and reorder forecasting."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from config import REORDER_LOOKBACK_DAYS
from database import Database


def calculate_dashboard_metrics(db: Database, owner_id: int) -> dict[str, float | int]:
    """
    Compute high-level KPIs for the dashboard (scoped to one user account).

    Formulas:
        Total Revenue     = SUM(sale total_revenue)
        Net Profit        = SUM(sale profit)  [Revenue - COGS per transaction]
        Total Capital     = SUM(product cost_price * quantity)  [current inventory value at cost]
        Products Sold     = SUM(sale quantity_sold)
    """
    products = db.get_products(owner_id)
    sales = db.get_recent_sales(owner_id, limit=100_000)

    total_revenue = sum(s["total_revenue"] for s in sales)
    net_profit = sum(s["profit"] for s in sales)
    total_capital = sum(p["cost_price"] * p["quantity"] for p in products)
    products_sold = sum(s["quantity_sold"] for s in sales)
    inventory_value_retail = sum(p["selling_price"] * p["quantity"] for p in products)
    low_stock_count = len(db.get_low_stock_products(owner_id))
    total_skus = len(products)

    return {
        "total_revenue": round(total_revenue, 2),
        "net_profit": round(net_profit, 2),
        "total_capital": round(total_capital, 2),
        "products_sold": products_sold,
        "inventory_value_retail": round(inventory_value_retail, 2),
        "low_stock_count": low_stock_count,
        "total_skus": total_skus,
        "profit_margin_pct": round((net_profit / total_revenue * 100) if total_revenue else 0, 1),
    }


def get_profit_trend(db: Database, owner_id: int, days: int = 14) -> list[tuple[str, float]]:
    """Daily profit totals for charting."""
    sales = db.get_sales_for_period(owner_id, days=days)
    daily: dict[str, float] = defaultdict(float)

    for sale in sales:
        day = sale["sold_at"][:10]
        daily[day] += sale["profit"]

    result: list[tuple[str, float]] = []
    start = datetime.now() - timedelta(days=days - 1)
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        result.append((day, round(daily.get(day, 0.0), 2)))
    return result


def get_top_selling_products(db: Database, owner_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """Aggregate sales by product for bar chart and insights."""
    sales = db.get_sales_for_period(owner_id, days=REORDER_LOOKBACK_DAYS)
    totals: dict[str, dict[str, Any]] = {}

    for sale in sales:
        key = sale["product_name"]
        if key not in totals:
            totals[key] = {"name": key, "units": 0, "revenue": 0.0, "profit": 0.0}
        totals[key]["units"] += sale["quantity_sold"]
        totals[key]["revenue"] += sale["total_revenue"]
        totals[key]["profit"] += sale["profit"]

    ranked = sorted(totals.values(), key=lambda x: x["units"], reverse=True)
    return ranked[:limit]


def get_reorder_recommendations(db: Database, owner_id: int) -> list[dict[str, Any]]:
    """
    Smart reorder suggestions based on sales velocity.

    Velocity = units sold in lookback period / lookback days.
    Days until stockout = current quantity / velocity (if velocity > 0).
    """
    products = db.get_products(owner_id)
    sales = db.get_sales_for_period(owner_id, days=REORDER_LOOKBACK_DAYS)
    velocity_map: dict[int, int] = defaultdict(int)

    for sale in sales:
        velocity_map[sale["product_id"]] += sale["quantity_sold"]

    recommendations: list[dict[str, Any]] = []
    for product in products:
        sold = velocity_map.get(product["id"], 0)
        daily_velocity = sold / REORDER_LOOKBACK_DAYS if sold else 0.0
        qty = product["quantity"]

        if qty <= 0 and sold > 0:
            priority, message = "critical", "Out of stock — reorder immediately."
        elif qty <= 5 and daily_velocity > 0:
            days_left = qty / daily_velocity
            if days_left <= 7:
                priority, message = "high", f"Stock may run out in ~{days_left:.0f} days."
            else:
                priority, message = "medium", f"Low stock with steady demand ({sold} sold/30d)."
        elif daily_velocity > 0:
            days_left = qty / daily_velocity
            if days_left <= 14:
                priority = "medium"
                message = f"Reorder suggested — ~{days_left:.0f} days of stock remaining."
            else:
                continue
        elif qty <= 5:
            priority, message = "low", "Below minimum stock threshold."
        else:
            continue

        suggested_qty = max(int(daily_velocity * 30) - qty, 10) if daily_velocity else 20
        recommendations.append(
            {
                "product_id": product["product_id"],
                "name": product["name"],
                "current_qty": qty,
                "sold_30d": sold,
                "daily_velocity": round(daily_velocity, 2),
                "priority": priority,
                "message": message,
                "suggested_reorder": suggested_qty,
            }
        )

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda r: (priority_order[r["priority"]], r["current_qty"]))
    return recommendations
