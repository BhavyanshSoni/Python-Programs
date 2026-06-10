"""SQLite database layer with schema initialization, auth, and data operations."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

from config import DB_PATH, DATA_DIR, LOW_STOCK_THRESHOLD


class DatabaseError(Exception):
    """Raised when a database operation fails validation or integrity checks."""


class Database:
    """Thread-safe SQLite access wrapper for the inventory system."""

    def __init__(self, db_path: str | None = None) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path or DB_PATH)
        self._init_schema()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'staff')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            self._ensure_tenant_schema(conn)

    def _ensure_tenant_schema(self, conn: sqlite3.Connection) -> None:
        """Ensure products/sales are scoped per user; migrate away legacy shared data."""
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "products" in tables:
            product_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(products)").fetchall()
            }
            if "owner_id" not in product_cols:
                if "sales" in tables:
                    conn.execute("DELETE FROM sales")
                conn.execute("DELETE FROM products")
                conn.executescript(
                    """
                    DROP TABLE IF EXISTS sales;
                    DROP TABLE IF EXISTS products;
                    """
                )

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                cost_price REAL NOT NULL CHECK(cost_price >= 0),
                selling_price REAL NOT NULL CHECK(selling_price >= 0),
                quantity INTEGER NOT NULL CHECK(quantity >= 0),
                owner_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(product_id, owner_id)
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity_sold INTEGER NOT NULL CHECK(quantity_sold > 0),
                unit_cost REAL NOT NULL CHECK(unit_cost >= 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                total_revenue REAL NOT NULL CHECK(total_revenue >= 0),
                total_cost REAL NOT NULL CHECK(total_cost >= 0),
                profit REAL NOT NULL,
                sold_at TEXT NOT NULL DEFAULT (datetime('now')),
                sold_by TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_products_owner ON products(owner_id);
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
            CREATE INDEX IF NOT EXISTS idx_products_quantity ON products(quantity);
            CREATE INDEX IF NOT EXISTS idx_sales_owner ON sales(owner_id);
            CREATE INDEX IF NOT EXISTS idx_sales_sold_at ON sales(sold_at);
            CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);
            """
        )

    @staticmethod
    def _hash_password(password: str, salt: str | None = None) -> str:
        salt = salt or secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}${digest}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt, digest = stored_hash.split("$", 1)
        except ValueError:
            return False
        return secrets.compare_digest(
            digest, hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        )

    def _create_user(
        self, conn: sqlite3.Connection, username: str, password: str, role: str
    ) -> int:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, self._hash_password(password), role),
        )
        return cursor.lastrowid

    # ------------------------------------------------------------------ Auth
    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            if row and self._verify_password(password, row["password_hash"]):
                return {"id": row["id"], "username": row["username"], "role": row["role"]}
        return None

    def register_user(self, username: str, password: str, role: str = "staff") -> int:
        if len(username.strip()) < 3:
            raise DatabaseError("Username must be at least 3 characters.")
        if len(password) < 6:
            raise DatabaseError("Password must be at least 6 characters.")
        if role not in ("admin", "staff"):
            raise DatabaseError("Invalid role specified.")

        with self._connection() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if user_count == 0:
                role = "admin"

            try:
                return self._create_user(conn, username.strip(), password, role)
            except sqlite3.IntegrityError as exc:
                raise DatabaseError("Username already exists.") from exc

    # -------------------------------------------------------------- Products
    def get_products(self, owner_id: int, search: str = "") -> list[dict[str, Any]]:
        query = """
            SELECT id, product_id, name, category, cost_price, selling_price,
                   quantity, owner_id, created_at, updated_at
            FROM products
            WHERE owner_id = ?
        """
        params: list[Any] = [owner_id]
        if search.strip():
            query += " AND (product_id LIKE ? OR name LIKE ? OR category LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term])
        query += " ORDER BY name COLLATE NOCASE"

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_product_by_id(self, owner_id: int, product_db_id: int) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE id = ? AND owner_id = ?",
                (product_db_id, owner_id),
            ).fetchone()
            return dict(row) if row else None

    def add_product(
        self,
        owner_id: int,
        product_id: str,
        name: str,
        category: str,
        cost_price: float,
        selling_price: float,
        quantity: int,
    ) -> int:
        self._validate_product_fields(product_id, name, category, cost_price, selling_price, quantity)
        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO products
                        (product_id, name, category, cost_price, selling_price, quantity, owner_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_id.strip().upper(),
                        name.strip(),
                        category.strip(),
                        round(cost_price, 2),
                        round(selling_price, 2),
                        quantity,
                        owner_id,
                    ),
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError as exc:
                raise DatabaseError(f"Product ID '{product_id}' already exists.") from exc

    def update_product(
        self,
        owner_id: int,
        db_id: int,
        product_id: str,
        name: str,
        category: str,
        cost_price: float,
        selling_price: float,
        quantity: int,
    ) -> None:
        self._validate_product_fields(product_id, name, category, cost_price, selling_price, quantity)
        with self._connection() as conn:
            existing = conn.execute(
                "SELECT id FROM products WHERE id = ? AND owner_id = ?", (db_id, owner_id)
            ).fetchone()
            if not existing:
                raise DatabaseError("Product not found.")

            try:
                conn.execute(
                    """
                    UPDATE products SET
                        product_id = ?, name = ?, category = ?,
                        cost_price = ?, selling_price = ?, quantity = ?,
                        updated_at = datetime('now')
                    WHERE id = ? AND owner_id = ?
                    """,
                    (
                        product_id.strip().upper(),
                        name.strip(),
                        category.strip(),
                        round(cost_price, 2),
                        round(selling_price, 2),
                        quantity,
                        db_id,
                        owner_id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DatabaseError(f"Product ID '{product_id}' already exists.") from exc

    def delete_product(self, owner_id: int, db_id: int) -> None:
        with self._connection() as conn:
            product = conn.execute(
                "SELECT id FROM products WHERE id = ? AND owner_id = ?", (db_id, owner_id)
            ).fetchone()
            if not product:
                raise DatabaseError("Product not found.")

            sales_count = conn.execute(
                "SELECT COUNT(*) FROM sales WHERE product_id = ? AND owner_id = ?",
                (db_id, owner_id),
            ).fetchone()[0]
            if sales_count > 0:
                raise DatabaseError(
                    "Cannot delete product with sales history. Set quantity to 0 instead."
                )
            conn.execute(
                "DELETE FROM products WHERE id = ? AND owner_id = ?", (db_id, owner_id)
            )

    @staticmethod
    def _validate_product_fields(
        product_id: str,
        name: str,
        category: str,
        cost_price: float,
        selling_price: float,
        quantity: int,
    ) -> None:
        if not product_id.strip():
            raise DatabaseError("Product ID is required.")
        if not name.strip():
            raise DatabaseError("Product name is required.")
        if not category.strip():
            raise DatabaseError("Category is required.")
        if cost_price < 0:
            raise DatabaseError("Cost price cannot be negative.")
        if selling_price < 0:
            raise DatabaseError("Selling price cannot be negative.")
        if quantity < 0:
            raise DatabaseError("Quantity cannot be negative.")

    # ------------------------------------------------------------------ Sales
    def process_sale(
        self, owner_id: int, product_db_id: int, quantity: int, sold_by: str
    ) -> dict[str, Any]:
        if quantity <= 0:
            raise DatabaseError("Sale quantity must be greater than zero.")

        with self._connection() as conn:
            product = conn.execute(
                "SELECT * FROM products WHERE id = ? AND owner_id = ?",
                (product_db_id, owner_id),
            ).fetchone()
            if not product:
                raise DatabaseError("Product not found.")
            if product["quantity"] < quantity:
                raise DatabaseError(
                    f"Insufficient stock. Available: {product['quantity']}, requested: {quantity}."
                )

            unit_cost = product["cost_price"]
            unit_price = product["selling_price"]
            total_revenue = round(unit_price * quantity, 2)
            total_cost = round(unit_cost * quantity, 2)
            profit = round(total_revenue - total_cost, 2)

            conn.execute(
                """
                UPDATE products SET quantity = quantity - ?, updated_at = datetime('now')
                WHERE id = ? AND owner_id = ?
                """,
                (quantity, product_db_id, owner_id),
            )
            cursor = conn.execute(
                """
                INSERT INTO sales
                    (product_id, quantity_sold, unit_cost, unit_price,
                     total_revenue, total_cost, profit, sold_by, owner_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_db_id,
                    quantity,
                    unit_cost,
                    unit_price,
                    total_revenue,
                    total_cost,
                    profit,
                    sold_by,
                    owner_id,
                ),
            )
            return {
                "sale_id": cursor.lastrowid,
                "product_name": product["name"],
                "quantity": quantity,
                "total_revenue": total_revenue,
                "profit": profit,
            }

    def get_recent_sales(self, owner_id: int, limit: int = 50) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT s.id, p.product_id, p.name, s.quantity_sold,
                       s.total_revenue, s.profit, s.sold_at, s.sold_by
                FROM sales s
                JOIN products p ON p.id = s.product_id
                WHERE s.owner_id = ?
                ORDER BY s.sold_at DESC
                LIMIT ?
                """,
                (owner_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_sales_for_period(self, owner_id: int, days: int = 30) -> list[dict[str, Any]]:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*, p.name AS product_name, p.product_id AS sku
                FROM sales s
                JOIN products p ON p.id = s.product_id
                WHERE s.owner_id = ? AND s.sold_at >= ?
                ORDER BY s.sold_at ASC
                """,
                (owner_id, since),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_low_stock_products(self, owner_id: int) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM products
                WHERE owner_id = ? AND quantity <= ?
                ORDER BY quantity ASC, name ASC
                """,
                (owner_id, LOW_STOCK_THRESHOLD),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_categories(self, owner_id: int) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT category FROM products
                WHERE owner_id = ?
                ORDER BY category COLLATE NOCASE
                """,
                (owner_id,),
            ).fetchall()
            return [row[0] for row in rows]
