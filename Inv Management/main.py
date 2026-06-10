"""
InvManager Pro — Enterprise Desktop Inventory Management System

Entry point for the application. Handles login flow and launches the main shell.
"""

from __future__ import annotations

import sys

import customtkinter as ctk

from database import Database
from ui.app import AppShell
from ui.login import LoginView


def launch_app(user: dict, db: Database) -> None:
    """Open the main application after successful authentication."""
    app = AppShell(db, user)
    app.mainloop()


def main() -> None:
    db = Database()

    def on_login_success(user: dict) -> None:
        launch_app(user, db)

    login = LoginView(db, on_login_success)
    login.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
