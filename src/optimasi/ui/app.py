"""Main CustomTkinter desktop GUI for Optimasi Windows."""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from optimasi import APP_NAME, APP_VERSION
from optimasi.core.admin import is_admin, relaunch_as_admin
from optimasi.core.backup import (
    create_restore_point,
    export_registry_backup,
    list_undo_sessions,
    revert_session,
)
from optimasi.core.cleaner import (
    JunkCategoryStats,
    clean_junk,
    run_system_repair,
    scan_junk,
    trim_ram_working_sets,
)
from optimasi.core.executor import TweakExecutor
from optimasi.core.system_info import get_system_snapshot
from optimasi.tweaks import (
    ALL_TWEAKS,
    CATEGORIES,
    PRESETS,
    TWEAK_BY_ID,
    get_preset_tweaks,
    get_tweaks_by_category,
    search_tweaks,
)
from optimasi.tweaks.models import DnsSet, RiskLevel, Tweak
from optimasi.tweaks.network_dns import DNS_PRESETS, ping_endpoints
from optimasi.tweaks.privacy_debloat import SAFE_BLOAT_APPX
from optimasi.tweaks.startup import list_startup_items, set_startup_item_enabled
from optimasi.ui import theme
from optimasi.ui.widgets import StatCard, TweakCard


def resolve_asset_path(relative_path: str) -> Path:
    """Resolve asset paths both in dev source mode and Nuitka onefile/standalone builds."""
    candidates = [
        Path(__file__).resolve().parents[3] / relative_path,
        Path(__file__).resolve().parents[2] / relative_path,
        Path(sys.executable).resolve().parent / relative_path,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / relative_path)
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


class OptimasiApp(ctk.CTk):
    """Modern Windows Optimization Desktop Application."""

    NAV_ITEMS = [
        ("dashboard", "Dashboard"),
        ("CPU & Power", "CPU & Power"),
        ("GPU & Gaming", "GPU & Gaming"),
        ("Network & DNS", "Network & DNS"),
        ("Privacy & Debloat", "Privacy & Debloat"),
        ("RAM & Storage", "RAM & Storage"),
        ("Services & System", "Services & System"),
        ("cleaner", "Cleaner & Repair"),
        ("startup", "Startup Apps"),
    ]

    def __init__(self, start_dry_run: bool = False):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1220x780")
        self.minsize(1020, 660)
        self.configure(fg_color=theme.BG_APP)

        icon_path = resolve_asset_path("assets/app.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.dry_run_var = ctk.BooleanVar(value=start_dry_run)
        self.search_var = ctk.StringVar(value="")
        self.current_page = "dashboard"
        self.is_busy = False

        # Per-tweak selection state across all pages
        self.tweak_vars: dict[str, ctk.BooleanVar] = {
            t.id: ctk.BooleanVar(value=t.default_selected) for t in ALL_TWEAKS
        }
        self.junk_vars: dict[str, ctk.BooleanVar] = {}
        self.junk_stats: list[JunkCategoryStats] = []
        self.recycle_bin_var = ctk.BooleanVar(value=False)
        self.appx_vars: dict[str, ctk.BooleanVar] = {
            pkg: ctk.BooleanVar(value=True) for pkg, _ in SAFE_BLOAT_APPX
        }
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.stat_cards: dict[str, StatCard] = {}

        self._build_layout()
        self._select_page("dashboard")
        self.after(150, self._refresh_dashboard_stats)

    # ------------------------------------------------------------------
    # Layout Construction
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Left Sidebar
        self.sidebar = ctk.CTkFrame(self, width=228, fg_color=theme.BG_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsw")
        self.sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(18, 12))
        ctk.CTkLabel(
            brand,
            text="OPTIMASI",
            font=(theme.FONT_FAMILY, 20, "bold"),
            text_color=theme.ACCENT_CYAN,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text=f"Windows Optimizer v{APP_VERSION}",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=theme.BORDER_SUBTLE).pack(fill="x", padx=14, pady=(0, 10))

        for page_id, label in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {label}",
                anchor="w",
                height=38,
                corner_radius=8,
                font=(theme.FONT_FAMILY, 13, "bold"),
                fg_color="transparent",
                hover_color=theme.BG_CARD,
                text_color=theme.TEXT_SECONDARY,
                command=lambda pid=page_id: self._select_page(pid),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[page_id] = btn

        # Footer info inside sidebar
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=14, pady=14)
        ctk.CTkLabel(
            footer,
            text=f"Runtime: Python {sys.version.split()[0]}\nTweaks Loaded: {len(ALL_TWEAKS)}",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED,
            justify="left",
        ).pack(anchor="w")

        # Top Header Bar
        self.header = ctk.CTkFrame(self, height=60, fg_color=theme.BG_SIDEBAR, corner_radius=0)
        self.header.grid(row=0, column=1, sticky="ew")
        self.header.grid_columnconfigure(1, weight=1)

        self.page_title_label = ctk.CTkLabel(
            self.header,
            text="Dashboard",
            font=(theme.FONT_FAMILY, 18, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self.page_title_label.grid(row=0, column=0, padx=20, pady=14, sticky="w")

        self.search_entry = ctk.CTkEntry(
            self.header,
            textvariable=self.search_var,
            placeholder_text="Search tweaks (e.g. Nagle, HAGS, Copilot, DNS, SSD)...",
            width=320,
            height=34,
            fg_color=theme.BG_INPUT,
            border_color=theme.BORDER_SUBTLE,
            text_color=theme.TEXT_PRIMARY,
        )
        self.search_entry.grid(row=0, column=1, padx=12, pady=12, sticky="e")
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        controls = ctk.CTkFrame(self.header, fg_color="transparent")
        controls.grid(row=0, column=2, padx=(6, 18), pady=12, sticky="e")

        self.dry_run_switch = ctk.CTkSwitch(
            controls,
            text="Dry-Run",
            variable=self.dry_run_var,
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_SECONDARY,
            progress_color=theme.ACCENT_AMBER,
        )
        self.dry_run_switch.pack(side="left", padx=(0, 12))

        admin_ok = is_admin()
        self.admin_btn = ctk.CTkButton(
            controls,
            text="ADMIN ACTIVE" if admin_ok else "ELEVATE (ADMIN)",
            width=128,
            height=30,
            corner_radius=8,
            font=(theme.FONT_FAMILY, 11, "bold"),
            fg_color="#064E3B" if admin_ok else "#78350F",
            hover_color="#065F46" if admin_ok else "#92400E",
            text_color="#34D399" if admin_ok else "#FDE68A",
            command=self._handle_elevate if not admin_ok else (lambda: self.log("Already running with Administrator privileges.")),
        )
        self.admin_btn.pack(side="left")

        # Main Scrollable Content Area
        self.content = ctk.CTkScrollableFrame(self, fg_color=theme.BG_APP, corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.content.grid_columnconfigure(0, weight=1)

        # Bottom Live Log Console
        self.console_frame = ctk.CTkFrame(self, height=150, fg_color=theme.BG_SIDEBAR, corner_radius=0)
        self.console_frame.grid(row=2, column=1, sticky="ew")
        self.console_frame.grid_columnconfigure(0, weight=1)

        console_bar = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        console_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(6, 2))
        ctk.CTkLabel(
            console_bar,
            text="EXECUTION LOG",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_SECONDARY,
        ).pack(side="left")
        self.status_badge = ctk.CTkLabel(
            console_bar,
            text="Ready",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.ACCENT_CYAN,
        )
        self.status_badge.pack(side="left", padx=14)
        ctk.CTkButton(
            console_bar,
            text="Clear Log",
            width=76,
            height=22,
            font=(theme.FONT_FAMILY, 11),
            fg_color=theme.BG_CARD,
            hover_color=theme.BG_CARD_ALT,
            command=self._clear_log,
        ).pack(side="right")

        self.console_box = ctk.CTkTextbox(
            self.console_frame,
            height=105,
            fg_color=theme.BG_CONSOLE,
            text_color="#CBD5E1",
            font=(theme.FONT_MONO, 11),
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
        )
        self.console_box.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")
        self.log(f"{APP_NAME} v{APP_VERSION} initialized. Dry-Run mode is {'ON' if self.dry_run_var.get() else 'OFF'}.")

    # ------------------------------------------------------------------
    # Logging & Background Runner
    # ------------------------------------------------------------------
    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {message}\n"

        def _append() -> None:
            self.console_box.insert("end", line)
            self.console_box.see("end")

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.after(0, _append)

    def _clear_log(self) -> None:
        self.console_box.delete("1.0", "end")

    def _set_status(self, text: str) -> None:
        if threading.current_thread() is threading.main_thread():
            self.status_badge.configure(text=text)
        else:
            self.after(0, lambda: self.status_badge.configure(text=text))

    def _run_async(self, label: str, fn: Callable[[], None], on_done: Callable[[], None] | None = None) -> None:
        if self.is_busy:
            self.log("Another task is currently running. Please wait...")
            return
        self.is_busy = True
        self._set_status(f"Running: {label}...")

        def _worker() -> None:
            try:
                fn()
            except Exception as exc:
                self.log(f"ERROR in {label}: {exc}")
            finally:
                def _finish() -> None:
                    self.is_busy = False
                    self._set_status("Ready")
                    if on_done:
                        on_done()
                self.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_elevate(self) -> None:
        self.log("Requesting Windows UAC Administrator elevation...")
        if relaunch_as_admin():
            self.destroy()
        else:
            self.log("UAC elevation was cancelled or failed.")

    # ------------------------------------------------------------------
    # Navigation & Page Rendering
    # ------------------------------------------------------------------
    def _clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    def _select_page(self, page_id: str) -> None:
        self.current_page = page_id
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(fg_color=theme.BG_CARD_ALT, text_color=theme.ACCENT_CYAN)
            else:
                btn.configure(fg_color="transparent", text_color=theme.TEXT_SECONDARY)

        label_map = dict(self.NAV_ITEMS)
        self.page_title_label.configure(text=label_map.get(page_id, page_id))
        self._clear_content()

        if page_id == "dashboard":
            self._render_dashboard()
        elif page_id == "cleaner":
            self._render_cleaner_page()
        elif page_id == "startup":
            self._render_startup_page()
        elif page_id in CATEGORIES:
            self._render_tweak_category(page_id)

    def _on_search_change(self, _event=None) -> None:
        query = self.search_var.get().strip()
        if not query:
            self._select_page(self.current_page)
            return
        self.page_title_label.configure(text=f"Search: '{query}'")
        self._clear_content()
        matches = search_tweaks(query)
        self._render_tweak_list_section(
            title=f"Matching Tweaks ({len(matches)})",
            tweaks=matches,
            subtitle="Showing matching optimization tweaks across all categories.",
        )

    # ------------------------------------------------------------------
    # Page: Dashboard
    # ------------------------------------------------------------------
    def _render_dashboard(self) -> None:
        container = ctk.CTkFrame(self.content, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=16, sticky="ew")
        container.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Hardware Telemetry Cards
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            hdr,
            text="System Overview",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")
        ctk.CTkButton(
            hdr,
            text="Refresh Stats",
            width=110,
            height=28,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=self._refresh_dashboard_stats,
        ).pack(side="right")

        self.stat_cards = {
            "cpu": StatCard(container, "CPU", "Detecting...", "Cores & load", theme.ACCENT_CYAN),
            "ram": StatCard(container, "Memory (RAM)", "Detecting...", "Available / Total", theme.ACCENT_BLUE),
            "gpu": StatCard(container, "Graphics (GPU)", "Detecting...", "Vendor auto-detect", theme.ACCENT_GREEN),
            "os": StatCard(container, "OS & Power Plan", "Detecting...", "Build & active plan", theme.ACCENT_AMBER),
        }
        for col, key in enumerate(["cpu", "ram", "gpu", "os"]):
            self.stat_cards[key].grid(row=1, column=col, padx=6, pady=(0, 16), sticky="nsew")

        # Safety & Backup Bar
        safety_card = ctk.CTkFrame(
            container,
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
        )
        safety_card.grid(row=2, column=0, columnspan=4, padx=6, pady=(0, 18), sticky="ew")
        safety_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            safety_card,
            text="Safety, Backup & Undo",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=16, pady=(12, 2), sticky="w")
        ctk.CTkLabel(
            safety_card,
            text="Recommended before applying aggressive tweaks: create a Restore Point or export a Registry snapshot. Every tweak session also records an Undo log.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_SECONDARY,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        btn_row = ctk.CTkFrame(safety_card, fg_color="transparent")
        btn_row.grid(row=0, column=1, rowspan=2, padx=16, pady=12, sticky="e")

        ctk.CTkButton(
            btn_row,
            text="Restore Point",
            width=120,
            height=34,
            fg_color=theme.ACCENT_BLUE,
            command=self._action_restore_point,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row,
            text="Backup Registry",
            width=130,
            height=34,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=self._action_backup_registry,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row,
            text="Undo Last Session",
            width=138,
            height=34,
            fg_color="#78350F",
            hover_color="#92400E",
            text_color="#FDE68A",
            command=self._action_undo_last,
        ).pack(side="left", padx=4)

        # One-Click Presets
        ctk.CTkLabel(
            container,
            text="One-Click Optimization Profiles",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=3, column=0, columnspan=4, padx=6, pady=(4, 10), sticky="w")

        presets_frame = ctk.CTkFrame(container, fg_color="transparent")
        presets_frame.grid(row=4, column=0, columnspan=4, sticky="ew")
        presets_frame.grid_columnconfigure((0, 1, 2), weight=1)

        badge_colors = {
            "safe_daily": (theme.ACCENT_GREEN, theme.ACCENT_GREEN_HOVER),
            "gaming_pro": (theme.ACCENT_CYAN, theme.ACCENT_CYAN_HOVER),
            "extreme": (theme.ACCENT_RED, theme.ACCENT_RED_HOVER),
        }

        for idx, preset in enumerate(PRESETS):
            pcard = ctk.CTkFrame(
                presets_frame,
                fg_color=theme.BG_CARD,
                border_color=theme.BORDER_SUBTLE,
                border_width=1,
                corner_radius=12,
            )
            pcard.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")
            pcard.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                pcard,
                text=preset.badge,
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.ACCENT_CYAN,
                anchor="w",
            ).grid(row=0, column=0, padx=16, pady=(14, 2), sticky="w")

            ctk.CTkLabel(
                pcard,
                text=preset.name,
                font=(theme.FONT_FAMILY, 15, "bold"),
                text_color=theme.TEXT_PRIMARY,
                anchor="w",
            ).grid(row=1, column=0, padx=16, pady=(0, 6), sticky="w")

            ctk.CTkLabel(
                pcard,
                text=f"{preset.description}\n\nIncludes {len(preset.tweak_ids)} curated tweaks.",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_SECONDARY,
                wraplength=260,
                justify="left",
                anchor="w",
            ).grid(row=2, column=0, padx=16, pady=(0, 14), sticky="nw")

            fg, hov = badge_colors.get(preset.id, (theme.ACCENT_CYAN, theme.ACCENT_CYAN_HOVER))
            ctk.CTkButton(
                pcard,
                text=f"Run {preset.name}",
                height=36,
                font=(theme.FONT_FAMILY, 12, "bold"),
                fg_color=fg,
                hover_color=hov,
                text_color="#06121E" if preset.id != "extreme" else "#FFFFFF",
                command=lambda pid=preset.id, pname=preset.name: self._run_preset(pid, pname),
            ).grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")

    def _refresh_dashboard_stats(self) -> None:
        def _collect() -> None:
            snap = get_system_snapshot()

            def _apply() -> None:
                if "cpu" not in self.stat_cards:
                    return
                cpu = snap["cpu"]
                ram = snap["ram"]
                disk = snap["disk_c"]
                os_i = snap["os"]
                gpus = snap["gpus"]
                gpu_name = gpus[0]["name"] if gpus else "No Dedicated GPU"
                self.stat_cards["cpu"].update_data(
                    f"{cpu['usage_percent']}% Load",
                    f"{cpu['name'][:36]}\n{cpu['physical_cores']}C/{cpu['logical_cores']}T ({cpu['vendor']})",
                )
                self.stat_cards["ram"].update_data(
                    f"{ram['used_gb']} / {ram['total_gb']} GB",
                    f"{ram['percent']}% Used • {ram['available_gb']} GB Free\nDisk C: {disk['free_gb']} GB free",
                )
                self.stat_cards["gpu"].update_data(
                    snap["gpu_primary_vendor"],
                    f"{gpu_name[:42]}\nDetected {len(gpus)} adapter(s)",
                )
                self.stat_cards["os"].update_data(
                    os_i["name"],
                    f"Build {os_i['build']} ({os_i['display_version']})\nPower: {snap['power_plan'][:28]}",
                )

            self.after(0, _apply)

        threading.Thread(target=_collect, daemon=True).start()

    def _action_restore_point(self) -> None:
        dry = self.dry_run_var.get()
        self._run_async("System Restore Point", lambda: create_restore_point(dry_run=dry, log_cb=self.log))

    def _action_backup_registry(self) -> None:
        dry = self.dry_run_var.get()
        self._run_async("Registry Backup", lambda: export_registry_backup(full=False, dry_run=dry, log_cb=self.log))

    def _action_undo_last(self) -> None:
        sessions = list_undo_sessions()
        if not sessions:
            self.log("No undo sessions found yet. Apply a tweak first to record an undo snapshot.")
            return
        latest = sessions[0]
        dry = self.dry_run_var.get()
        self.log(f"Reverting latest session: {latest['label']} ({latest['entry_count']} changes)...")
        self._run_async(
            "Undo Last Session",
            lambda: revert_session(latest["path"], dry_run=dry, log_cb=self.log),
        )

    def _run_preset(self, preset_id: str, preset_name: str) -> None:
        tweaks = get_preset_tweaks(preset_id)
        dry = self.dry_run_var.get()

        def _work() -> None:
            executor = TweakExecutor(dry_run=dry, log_cb=self.log)
            res = executor.run_tweaks(tweaks, revert=False, session_label=preset_name)
            self.log(
                f"Preset '{preset_name}' finished: {res.succeeded} actions ok, {res.failed} failed, {res.skipped} skipped."
            )

        self._run_async(preset_name, _work, on_done=self._refresh_dashboard_stats)

    # ------------------------------------------------------------------
    # Page: Tweak Categories & Search
    # ------------------------------------------------------------------
    def _render_tweak_category(self, category: str) -> None:
        tweaks = get_tweaks_by_category(category)
        extra_row = 0

        if category == "Network & DNS":
            self._render_network_tools_panel(row=0)
            extra_row = 1
        elif category == "Privacy & Debloat":
            self._render_appx_panel(row=0)
            extra_row = 1

        self._render_tweak_list_section(
            title=f"{category} Tweaks ({len(tweaks)})",
            tweaks=tweaks,
            subtitle="Select tweaks to batch apply, or click Apply / Revert on individual cards.",
            start_row=extra_row,
        )

    def _render_network_tools_panel(self, row: int = 0) -> None:
        panel = ctk.CTkFrame(
            self.content,
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
        )
        panel.grid(row=row, column=0, padx=20, pady=(14, 4), sticky="ew")
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Quick DNS Switcher & Latency Ping Benchmark",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        dns_bar = ctk.CTkFrame(panel, fg_color="transparent")
        dns_bar.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")

        for key, label, primary, secondary in DNS_PRESETS:
            short = label.split("(")[0].strip().replace(" Public", "").replace(" Security", "").replace(" Ad-Blocking", "").replace(" Default ISP / ", "")
            ctk.CTkButton(
                dns_bar,
                text=f"{short}" + (f" ({primary})" if primary else ""),
                height=30,
                fg_color=theme.BG_CARD_ALT,
                hover_color="#334155",
                font=(theme.FONT_FAMILY, 11, "bold"),
                command=lambda p=primary, s=secondary, lbl=label: self._apply_quick_dns(p, s, lbl),
            ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            dns_bar,
            text="Ping Test",
            width=96,
            height=30,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color="#06121E",
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=self._run_ping_test,
        ).pack(side="right")

    def _apply_quick_dns(self, primary: str | None, secondary: str | None, label: str) -> None:
        dry = self.dry_run_var.get()
        t = Tweak(
            id="quick_dns",
            name=f"Set DNS: {label}",
            category="Network & DNS",
            risk=RiskLevel.SAFE,
            source="Quick DNS",
            description="",
            apply_actions=[DnsSet(primary, secondary, label)],
        )
        self._run_async(
            f"DNS -> {label}",
            lambda: TweakExecutor(dry_run=dry, log_cb=self.log).run_tweaks([t], session_label=f"DNS {label}"),
        )

    def _run_ping_test(self) -> None:
        def _work() -> None:
            self.log("Running latency ping test (Cloudflare, Google, Quad9, AdGuard)...")
            for row in ping_endpoints():
                self.log(f"  {row['label']} ({row['ip']}): {row['latency']}")

        self._run_async("Ping Test", _work)

    def _render_appx_panel(self, row: int = 0) -> None:
        panel = ctk.CTkFrame(
            self.content,
            fg_color=theme.BG_CARD,
            border_color=theme.BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
        )
        panel.grid(row=row, column=0, padx=20, pady=(14, 4), sticky="ew")
        panel.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=16, pady=(12, 6), sticky="ew")
        ctk.CTkLabel(
            hdr,
            text="Selective UWP Bloatware Remover (Keeps Store, Terminal & Calculator)",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")
        ctk.CTkButton(
            hdr,
            text="Remove Checked Apps",
            width=165,
            height=30,
            fg_color=theme.ACCENT_RED,
            hover_color=theme.ACCENT_RED_HOVER,
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=self._remove_checked_appx,
        ).pack(side="right")

        grid = ctk.CTkFrame(panel, fg_color="transparent")
        grid.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, (pkg, friendly) in enumerate(SAFE_BLOAT_APPX):
            ctk.CTkCheckBox(
                grid,
                text=friendly,
                variable=self.appx_vars[pkg],
                font=(theme.FONT_FAMILY, 11),
                checkbox_width=18,
                checkbox_height=18,
                fg_color=theme.ACCENT_CYAN,
            ).grid(row=idx // 4, column=idx % 4, padx=6, pady=3, sticky="w")

    def _remove_checked_appx(self) -> None:
        from optimasi.tweaks.models import AppxRemove

        selected = [pkg for pkg, var in self.appx_vars.items() if var.get()]
        if not selected:
            self.log("No UWP apps selected for removal.")
            return
        dry = self.dry_run_var.get()
        t = Tweak(
            id="custom_appx",
            name=f"Remove {len(selected)} Selected UWP Apps",
            category="Privacy & Debloat",
            risk=RiskLevel.MODERATE,
            source="User Selection",
            description="",
            apply_actions=[AppxRemove(selected)],
        )
        self._run_async(
            "AppX Removal",
            lambda: TweakExecutor(dry_run=dry, log_cb=self.log).run_tweaks([t], session_label="AppX Debloat"),
        )

    def _render_tweak_list_section(self, title: str, tweaks: list[Tweak], subtitle: str, start_row: int = 0) -> None:
        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.grid(row=start_row, column=0, padx=20, pady=(14, 8), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        title_col = ctk.CTkFrame(toolbar, fg_color="transparent")
        title_col.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title_col, text=title, font=(theme.FONT_FAMILY, 16, "bold"), text_color=theme.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_col, text=subtitle, font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_SECONDARY).pack(anchor="w")

        btn_col = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_col.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_col,
            text="Select Safe",
            width=92,
            height=30,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=lambda: self._select_tweaks(tweaks, safe_only=True),
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_col,
            text="Select All",
            width=86,
            height=30,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=lambda: self._select_tweaks(tweaks, value=True),
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_col,
            text="Clear",
            width=66,
            height=30,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=lambda: self._select_tweaks(tweaks, value=False),
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_col,
            text="Apply Selected",
            width=124,
            height=30,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color="#06121E",
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=lambda: self._run_tweaks_batch(tweaks, revert=False),
        ).pack(side="left", padx=(8, 3))
        ctk.CTkButton(
            btn_col,
            text="Revert Selected",
            width=120,
            height=30,
            fg_color="#78350F",
            hover_color="#92400E",
            text_color="#FDE68A",
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=lambda: self._run_tweaks_batch(tweaks, revert=True),
        ).pack(side="left", padx=3)

        for i, tweak in enumerate(tweaks):
            card = TweakCard(
                self.content,
                tweak=tweak,
                selected_var=self.tweak_vars[tweak.id],
                on_apply=lambda tw: self._run_single_tweak(tw, revert=False),
                on_revert=lambda tw: self._run_single_tweak(tw, revert=True),
            )
            card.grid(row=start_row + 1 + i, column=0, padx=20, pady=5, sticky="ew")

    def _select_tweaks(self, tweaks: list[Tweak], value: bool = True, safe_only: bool = False) -> None:
        for t in tweaks:
            if safe_only:
                self.tweak_vars[t.id].set(t.risk == RiskLevel.SAFE)
            else:
                self.tweak_vars[t.id].set(value)

    def _run_single_tweak(self, tweak: Tweak, revert: bool = False) -> None:
        dry = self.dry_run_var.get()
        mode = "Revert" if revert else "Apply"
        self._run_async(
            f"{mode} {tweak.name}",
            lambda: TweakExecutor(dry_run=dry, log_cb=self.log).run_tweaks([tweak], revert=revert, session_label=tweak.name),
        )

    def _run_tweaks_batch(self, tweaks: list[Tweak], revert: bool = False) -> None:
        chosen = [t for t in tweaks if self.tweak_vars[t.id].get()]
        if not chosen:
            self.log("No tweaks checked in this view.")
            return
        dry = self.dry_run_var.get()
        mode = "Revert" if revert else "Apply"

        def _work() -> None:
            res = TweakExecutor(dry_run=dry, log_cb=self.log).run_tweaks(
                chosen,
                revert=revert,
                session_label=f"{mode} {len(chosen)} tweaks",
            )
            self.log(f"Batch {mode} complete: {res.succeeded} actions ok, {res.failed} failed.")

        self._run_async(f"{mode} {len(chosen)} tweaks", _work)

    # ------------------------------------------------------------------
    # Page: Cleaner & System Repair
    # ------------------------------------------------------------------
    def _render_cleaner_page(self) -> None:
        wrapper = ctk.CTkFrame(self.content, fg_color="transparent")
        wrapper.grid(row=0, column=0, padx=20, pady=16, sticky="ew")
        wrapper.grid_columnconfigure(0, weight=1)

        # Junk Cleaner Header
        hdr = ctk.CTkFrame(wrapper, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            hdr,
            text="Junk, Cache & Shader Cleaner",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")

        btns = ctk.CTkFrame(hdr, fg_color="transparent")
        btns.pack(side="right")
        ctk.CTkButton(
            btns,
            text="Scan Junk",
            width=110,
            height=32,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=self._scan_junk_async,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns,
            text="Clean Selected",
            width=130,
            height=32,
            fg_color=theme.ACCENT_CYAN,
            hover_color=theme.ACCENT_CYAN_HOVER,
            text_color="#06121E",
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=self._clean_junk_async,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns,
            text="Trim RAM Now",
            width=120,
            height=32,
            fg_color=theme.ACCENT_GREEN,
            hover_color=theme.ACCENT_GREEN_HOVER,
            text_color="#06121E",
            font=(theme.FONT_FAMILY, 12, "bold"),
            command=self._trim_ram_async,
        ).pack(side="left", padx=4)

        self.cleaner_list_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        self.cleaner_list_frame.grid(row=1, column=0, sticky="ew")
        self.cleaner_list_frame.grid_columnconfigure(0, weight=1)

        if not self.junk_stats:
            self.junk_stats = scan_junk()
        self._populate_junk_rows()

        ctk.CTkCheckBox(
            wrapper,
            text="Also Empty Windows Recycle Bin",
            variable=self.recycle_bin_var,
            font=(theme.FONT_FAMILY, 12),
            fg_color=theme.ACCENT_CYAN,
        ).grid(row=2, column=0, pady=(8, 16), sticky="w")

        # System Repair & Maintenance
        ctk.CTkLabel(
            wrapper,
            text="Windows System Repair & SSD Maintenance",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=3, column=0, pady=(4, 10), sticky="w")

        repair_grid = ctk.CTkFrame(wrapper, fg_color="transparent")
        repair_grid.grid(row=4, column=0, sticky="ew")
        repair_grid.grid_columnconfigure((0, 1, 2), weight=1)

        repairs = [
            ("dism_restore", "DISM RestoreHealth", "Repairs Windows component store corruption."),
            ("sfc", "SFC /scannow", "Scans and repairs protected Windows system files."),
            ("dism_cleanup", "DISM Component Cleanup", "Cleans superseded WinSxS update backups."),
            ("ssd_trim", "SSD Optimize / ReTrim (C:)", "Sends TRIM command to keep NVMe/SATA SSD fast."),
            ("flush_dns", "Flush DNS Cache", "Clears stale DNS resolver entries."),
            ("network_reset", "Winsock & TCP/IP Reset", "Repairs broken network sockets and routing."),
        ]
        for idx, (mode, title, desc) in enumerate(repairs):
            card = ctk.CTkFrame(
                repair_grid,
                fg_color=theme.BG_CARD,
                border_color=theme.BORDER_SUBTLE,
                border_width=1,
                corner_radius=10,
            )
            card.grid(row=idx // 3, column=idx % 3, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=(theme.FONT_FAMILY, 13, "bold"), text_color=theme.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=desc, font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_SECONDARY, wraplength=240, justify="left").pack(anchor="w", padx=14, pady=(0, 10))
            ctk.CTkButton(
                card,
                text="Run Tool",
                height=30,
                fg_color=theme.BG_CARD_ALT,
                hover_color="#334155",
                command=lambda m=mode, t=title: self._run_repair_async(m, t),
            ).pack(fill="x", padx=14, pady=(0, 12))

    def _populate_junk_rows(self) -> None:
        for child in self.cleaner_list_frame.winfo_children():
            child.destroy()

        total_mb = round(sum(s.size_mb for s in self.junk_stats), 2)
        for idx, stat in enumerate(self.junk_stats):
            if stat.key not in self.junk_vars:
                self.junk_vars[stat.key] = ctk.BooleanVar(value=stat.key in ("user_temp", "windows_temp", "shader_cache", "crash_wer"))
            row = ctk.CTkFrame(
                self.cleaner_list_frame,
                fg_color=theme.BG_CARD,
                border_color=theme.BORDER_SUBTLE,
                border_width=1,
                corner_radius=8,
            )
            row.grid(row=idx, column=0, pady=3, sticky="ew")
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkCheckBox(
                row,
                text="",
                variable=self.junk_vars[stat.key],
                width=24,
                fg_color=theme.ACCENT_CYAN,
            ).grid(row=0, column=0, padx=(12, 6), pady=8)
            ctk.CTkLabel(
                row,
                text=f"{stat.label}  —  {stat.description}",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_PRIMARY,
                anchor="w",
            ).grid(row=0, column=1, padx=4, pady=8, sticky="ew")
            ctk.CTkLabel(
                row,
                text=f"{stat.file_count} files • {stat.size_mb} MB",
                font=(theme.FONT_MONO, 11, "bold"),
                text_color=theme.ACCENT_CYAN if stat.size_mb > 0 else theme.TEXT_MUTED,
            ).grid(row=0, column=2, padx=14, pady=8, sticky="e")

        self.log(f"Junk scan ready: ~{total_mb} MB detected across {len(self.junk_stats)} categories.")

    def _scan_junk_async(self) -> None:
        def _work() -> None:
            self.junk_stats = scan_junk()
            self.after(0, self._populate_junk_rows)

        self._run_async("Junk Scan", _work)

    def _clean_junk_async(self) -> None:
        selected = [k for k, v in self.junk_vars.items() if v.get()]
        if not selected:
            self.log("No junk categories selected.")
            return
        dry = self.dry_run_var.get()
        inc_bin = self.recycle_bin_var.get()

        def _work() -> None:
            clean_junk(selected, include_recycle_bin=inc_bin, dry_run=dry, log_cb=self.log)
            self.junk_stats = scan_junk()
            self.after(0, self._populate_junk_rows)

        self._run_async("Junk Cleanup", _work)

    def _trim_ram_async(self) -> None:
        dry = self.dry_run_var.get()
        self._run_async("Trim RAM Working Sets", lambda: trim_ram_working_sets(dry_run=dry, log_cb=self.log))

    def _run_repair_async(self, mode: str, title: str) -> None:
        dry = self.dry_run_var.get()
        self._run_async(title, lambda: run_system_repair(mode, dry_run=dry, log_cb=self.log))

    # ------------------------------------------------------------------
    # Page: Startup Programs Manager
    # ------------------------------------------------------------------
    def _render_startup_page(self) -> None:
        wrapper = ctk.CTkFrame(self.content, fg_color="transparent")
        wrapper.grid(row=0, column=0, padx=20, pady=16, sticky="ew")
        wrapper.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(wrapper, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            hdr,
            text="Windows Startup Programs (HKCU & HKLM Run)",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(side="left")
        ctk.CTkButton(
            hdr,
            text="Refresh List",
            width=100,
            height=30,
            fg_color=theme.BG_CARD_ALT,
            hover_color="#334155",
            command=lambda: self._select_page("startup"),
        ).pack(side="right")

        items = list_startup_items()
        if not items:
            ctk.CTkLabel(wrapper, text="No Run startup entries found.", text_color=theme.TEXT_MUTED).grid(row=1, column=0, pady=20)
            return

        for idx, item in enumerate(items):
            card = ctk.CTkFrame(
                wrapper,
                fg_color=theme.BG_CARD,
                border_color=theme.BORDER_SUBTLE,
                border_width=1,
                corner_radius=10,
            )
            card.grid(row=idx + 1, column=0, pady=4, sticky="ew")
            card.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                card,
                text=item.hive,
                font=(theme.FONT_MONO, 10, "bold"),
                fg_color=theme.BG_CARD_ALT,
                text_color=theme.ACCENT_CYAN,
                corner_radius=6,
                padx=8,
                pady=3,
            ).grid(row=0, column=0, padx=12, pady=10)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.grid(row=0, column=1, padx=6, pady=8, sticky="ew")
            ctk.CTkLabel(info, text=item.name, font=(theme.FONT_FAMILY, 13, "bold"), text_color=theme.TEXT_PRIMARY, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=item.command[:95], font=(theme.FONT_MONO, 11), text_color=theme.TEXT_MUTED, anchor="w").pack(anchor="w")

            var = ctk.BooleanVar(value=item.enabled)
            sw = ctk.CTkSwitch(
                card,
                text="Enabled" if item.enabled else "Disabled",
                variable=var,
                progress_color=theme.ACCENT_CYAN,
                command=lambda it=item, v=var: self._toggle_startup(it.hive, it.name, v.get()),
            )
            sw.grid(row=0, column=2, padx=14, pady=10, sticky="e")

    def _toggle_startup(self, hive: str, name: str, enabled: bool) -> None:
        dry = self.dry_run_var.get()
        ok, msg = set_startup_item_enabled(hive, name, enabled, dry_run=dry)
        self.log(msg)
        if not ok:
            self._select_page("startup")


def run_gui(start_dry_run: bool = False) -> int:
    app = OptimasiApp(start_dry_run=start_dry_run)
    app.mainloop()
    return 0
