"""Login and registration screen."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from config import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL, FONT_TITLE, LOGIN_SIZE, WINDOW_TITLE
from database import Database, DatabaseError


class LoginView(ctk.CTk):
    """Secure login gate with separate Sign Up and Login actions."""

    def __init__(self, db: Database, on_success: Callable[[dict], None]) -> None:
        super().__init__()
        self.db = db
        self.on_success = on_success

        self.title(WINDOW_TITLE)
        self.geometry(f"{LOGIN_SIZE[0]}x{LOGIN_SIZE[1]}")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self._center_window()

    def _center_window(self) -> None:
        self.update_idletasks()
        w, h = LOGIN_SIZE
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=16)
        container.pack(expand=True, fill="both", padx=40, pady=40)

        ctk.CTkLabel(container, text="📦", font=(FONT_HEADING[0], 48)).pack(pady=(30, 0))
        ctk.CTkLabel(
            container, text="InvManager Pro", font=FONT_TITLE, text_color=COLORS["text_primary"]
        ).pack(pady=(8, 4))
        ctk.CTkLabel(
            container,
            text="Enterprise Inventory Management",
            font=FONT_SMALL,
            text_color=COLORS["text_secondary"],
        ).pack(pady=(0, 24))

        self._username = ctk.CTkEntry(
            container, placeholder_text="Username", height=44, font=FONT_BODY,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self._username.pack(fill="x", padx=32, pady=(0, 12))

        self._password = ctk.CTkEntry(
            container, placeholder_text="Password", show="•", height=44, font=FONT_BODY,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self._password.pack(fill="x", padx=32, pady=(0, 12))

        self._confirm = ctk.CTkEntry(
            container, placeholder_text="Confirm password (Sign Up only)", show="•",
            height=44, font=FONT_BODY,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self._confirm.pack(fill="x", padx=32, pady=(0, 12))
        self._confirm.bind("<Return>", lambda _: self._login())

        self._password.bind("<Return>", lambda _: self._login())

        self._error = ctk.CTkLabel(
            container, text="", font=FONT_SMALL, text_color=COLORS["danger"], wraplength=360
        )
        self._error.pack(pady=(0, 12))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", padx=32, pady=(0, 8))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_row,
            text="Login",
            height=44,
            font=FONT_BODY,
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            command=self._login,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Sign Up",
            height=44,
            font=FONT_BODY,
            fg_color=COLORS["accent_emerald"],
            hover_color=COLORS["accent_emerald_hover"],
            command=self._signup,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ctk.CTkLabel(
            container,
            text="Create an account with Sign Up, then use Login to enter.",
            font=(FONT_SMALL[0], 10),
            text_color=COLORS["text_muted"],
        ).pack(pady=(8, 20))

    def _clear_error(self) -> None:
        self._error.configure(text="", text_color=COLORS["danger"])

    def _get_credentials(self) -> tuple[str, str] | None:
        username = self._username.get().strip()
        password = self._password.get()

        if not username or not password:
            self._error.configure(text="Please enter username and password.")
            return None
        return username, password

    def _login(self) -> None:
        self._clear_error()
        creds = self._get_credentials()
        if not creds:
            return

        username, password = creds
        user = self.db.authenticate(username, password)
        if user:
            self.destroy()
            self.on_success(user)
        else:
            self._error.configure(text="Invalid username or password.")

    def _signup(self) -> None:
        self._clear_error()
        creds = self._get_credentials()
        if not creds:
            return

        username, password = creds
        confirm = self._confirm.get()

        if password != confirm:
            self._error.configure(text="Passwords do not match.")
            return

        try:
            self.db.register_user(username, password)
            self._error.configure(
                text="Account created! Click Login to continue.",
                text_color=COLORS["success"],
            )
            self._confirm.delete(0, "end")
        except DatabaseError as exc:
            self._error.configure(text=str(exc), text_color=COLORS["danger"])
