"""Reusable CustomTkinter UI components."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from optimasi.tweaks.models import Tweak
from optimasi.ui import theme


class StatCard(ctk.CTkFrame):
    """Compact system telemetry metric card for the Dashboard."""

    def __init__(self, master, title: str, value: str = "—", subtitle: str = "", accent: str = theme.ACCENT_CYAN):
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
        )
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=title.upper(),
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="ew")

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=accent,
            anchor="w",
        )
        self.value_label.grid(row=1, column=0, padx=14, pady=(0, 2), sticky="ew")

        self.sub_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            anchor="w",
            wraplength=240,
            justify="left",
        )
        self.sub_label.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")

    def update_data(self, value: str, subtitle: str = "") -> None:
        self.value_label.configure(text=value)
        if subtitle:
            self.sub_label.configure(text=subtitle)


class TweakCard(ctk.CTkFrame):
    """Interactive card representing a single Windows optimization tweak."""

    def __init__(
        self,
        master,
        tweak: Tweak,
        selected_var: ctk.BooleanVar,
        on_apply: Callable[[Tweak], None],
        on_revert: Callable[[Tweak], None],
    ):
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            corner_radius=10,
        )
        self.tweak = tweak
        self.grid_columnconfigure(1, weight=1)

        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=selected_var,
            width=24,
            checkbox_width=20,
            checkbox_height=20,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            border_color=theme.TEXT_MUTED,
        )
        self.checkbox.grid(row=0, column=0, rowspan=2, padx=(14, 8), pady=12, sticky="n")

        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.grid(row=0, column=1, padx=(0, 10), pady=(10, 2), sticky="ew")
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_row,
            text=tweak.name,
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            wraplength=540,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        badges_frame = ctk.CTkFrame(header_row, fg_color="transparent")
        badges_frame.grid(row=0, column=1, padx=(8, 0), sticky="e")

        risk_bg, risk_fg = theme.RISK_BADGE_COLORS.get(tweak.risk.value, ("#1E293B", "#94A3B8"))
        ctk.CTkLabel(
            badges_frame,
            text=tweak.risk.value,
            font=(theme.FONT_FAMILY, 10, "bold"),
            fg_color=risk_bg,
            text_color=risk_fg,
            corner_radius=6,
            padx=8,
            pady=2,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            badges_frame,
            text=tweak.source,
            font=(theme.FONT_FAMILY, 10),
            fg_color=theme.BG_CARD_ALT,
            text_color=theme.TEXT_SECONDARY,
            corner_radius=6,
            padx=8,
            pady=2,
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text=tweak.description,
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
            wraplength=680,
            justify="left",
        ).grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="ew")

        actions_col = ctk.CTkFrame(self, fg_color="transparent")
        actions_col.grid(row=0, column=2, rowspan=2, padx=(4, 14), pady=10, sticky="e")

        ctk.CTkButton(
            actions_col,
            text="Apply",
            width=72,
            height=28,
            font=(theme.FONT_FAMILY, 11, "bold"),
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color="#06121E",
            command=lambda: on_apply(tweak),
        ).pack(pady=(0, 4))

        if tweak.reversible:
            ctk.CTkButton(
                actions_col,
                text="Revert",
                width=72,
                height=26,
                font=(theme.FONT_FAMILY, 11),
                fg_color=theme.BG_CARD_ALT,
                hover_color="#334155",
                text_color=theme.TEXT_PRIMARY,
                command=lambda: on_revert(tweak),
            ).pack()
