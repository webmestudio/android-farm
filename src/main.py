"""Scrcpy Phone Farm Dashboard - Modernized Main Application Window."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys
import math
import ctypes
from ctypes import wintypes

# Guard stdout/stderr when packaged with PyInstaller --noconsole
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w")
    except Exception:
        pass

# Ensure src parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import (
    COLORS, QUALITY_PRESETS, DEFAULT_PRESET, DEFAULT_COLUMNS,
    CELL_HEIGHT, DEFAULT_CELL_WIDTH, POLL_INTERVAL_MS, APP_ICON
)
from src.adb_manager import ADBManager, ADBDevice
from src.scrcpy_manager import ScrcpyManager
from src.sync_engine import SyncEngine
from src.ui_components import (
    DeviceCard, BulkInstallDialog, BulkShellDialog, BulkTextDialog, WiFiConnectDialog
)


class PhoneFarmApp(tk.Tk):
    """Main Application Window for Phone Farm Dashboard."""

    def __init__(self):
        super().__init__()
        self.title("⚡ Phone Farm Dashboard")
        self.geometry("1480x920")
        self.minsize(960, 640)
        self.configure(bg=COLORS["bg_root"])

        # Window Icon
        if APP_ICON and os.path.exists(APP_ICON):
            try:
                if APP_ICON.lower().endswith(".ico"):
                    self.iconbitmap(APP_ICON)
                else:
                    self._icon_img = tk.PhotoImage(file=APP_ICON)
                    self.iconphoto(True, self._icon_img)
            except Exception:
                pass

        # Core Managers
        self.adb = ADBManager()
        self.scrcpy = ScrcpyManager()
        self.sync = SyncEngine(self.adb)

        # State
        self.device_cards = {}  # serial -> DeviceCard
        self.devices = []       # List[ADBDevice]
        self.sync_target_serials = set()  # set of serials selected for sync
        self.current_columns = DEFAULT_COLUMNS
        self.master_serial = None
        self.sync_enabled = False
        self.preset_var = tk.StringVar(value=DEFAULT_PRESET)
        self._can_scroll_vertically = False

        self._is_closing = False

        self._build_header()
        self._build_body()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start periodic ADB device scanner
        self.after(500, self._start_device_scanner)

        # Start live touch & swipe sync tracker for Master screen
        threading.Thread(target=self._touch_tracker_loop, daemon=True).start()

    def _build_header(self):
        self.header_frame = tk.Frame(self, bg=COLORS["bg_header"], padx=14, pady=8)
        self.header_frame.pack(fill="x", side="top")

        # 1. Left: Live Status & Target Selection Telemetry
        f_left = tk.Frame(self.header_frame, bg=COLORS["bg_header"])
        f_left.pack(side="left")

        # Device Count Chip (Emerald Pill)
        self.f_count = tk.Frame(f_left, bg="#10231D", padx=9, pady=4)
        self.f_count.pack(side="left", padx=(0, 6))

        self.lbl_count = tk.Label(
            self.f_count,
            text="● 0 HP Online",
            font=("Segoe UI", 9, "bold"),
            bg="#10231D",
            fg="#34D399"
        )
        self.lbl_count.pack()

        # Master Chip (Amber Gold Pill)
        self.f_master = tk.Frame(f_left, bg="#1E2235", padx=9, pady=4)
        self.f_master.pack(side="left", padx=(0, 6))

        self.lbl_master_chip = tk.Label(
            self.f_master,
            text="👑 Master: -",
            font=("Segoe UI", 8, "bold"),
            bg="#1E2235",
            fg=COLORS["text_secondary"]
        )
        self.lbl_master_chip.pack()

        # Target Sync Chip (Cyan Pill)
        self.f_sync_targets = tk.Frame(f_left, bg="#0E242B", padx=9, pady=4)
        self.f_sync_targets.pack(side="left", padx=(0, 4))

        self.lbl_sync_targets = tk.Label(
            self.f_sync_targets,
            text="🎯 Target: 0/0 HP",
            font=("Segoe UI", 9, "bold"),
            bg="#0E242B",
            fg="#38BDF8"
        )
        self.lbl_sync_targets.pack()

        # Target Filter Menu Dropdown (Grouped right beside Target Chip)
        self.btn_filter = tk.Menubutton(
            f_left,
            text="🎯 Filter Sync ▾",
            bg=COLORS["bg_surface"],
            fg="#38BDF8",
            activebackground=COLORS["bg_card_hover"],
            activeforeground="#38BDF8",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.btn_filter.pack(side="left", padx=(0, 6))
        self.btn_filter.bind("<Enter>", lambda e: self.btn_filter.config(bg=COLORS["bg_card_hover"]))
        self.btn_filter.bind("<Leave>", lambda e: self.btn_filter.config(bg=COLORS["bg_surface"]))

        self.menu_filter = tk.Menu(
            self.btn_filter,
            tearoff=0,
            bg=COLORS["bg_card"],
            fg=COLORS["text_white"],
            activebackground=COLORS["border_glow"]
        )
        self.menu_filter.add_command(label="☑️ Pilih Semua HP", command=self._select_all_targets)
        self.menu_filter.add_command(label="⬜ Batal Pilih Semua (Hanya Master)", command=self._deselect_all_targets)
        self.menu_filter.add_separator()
        self.menu_filter.add_command(label="🤖 Pilih OS Sama dengan Master", command=self._filter_same_os)
        self.menu_filter.add_command(label="📐 Pilih Resolusi Sama dengan Master", command=self._filter_same_resolution)
        self.menu_filter.add_command(label="📱 Pilih Merek Sama dengan Master", command=self._filter_same_brand)
        self.menu_filter.add_separator()
        self.menu_filter.add_command(label="✨ Pilih Identik (Merek, OS & Layar Sama)", command=self._filter_exact_match)
        self.btn_filter["menu"] = self.menu_filter

        # 2. Right: Action Controls & Layout Pills
        f_right = tk.Frame(self.header_frame, bg=COLORS["bg_header"])
        f_right.pack(side="right")

        # Grid Columns Selector (Segmented buttons)
        f_cols = tk.Frame(f_right, bg="#161926", padx=3, pady=2)
        f_cols.pack(side="left", padx=(0, 8))

        lbl_col_tag = tk.Label(f_cols, text="Kolom:", font=("Segoe UI", 8), bg="#161926", fg=COLORS["text_muted"])
        lbl_col_tag.pack(side="left", padx=(4, 4))

        self.col_btns = {}
        for num in (2, 3, 4, 5, 6):
            b = tk.Button(
                f_cols,
                text=f"{num}x",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=5,
                pady=1,
                command=lambda n=num: self._set_columns(n)
            )
            b.pack(side="left", padx=1)
            self.col_btns[num] = b
        self._update_col_buttons()

        # Quality Preset Dropdown
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=COLORS["bg_input"], background=COLORS["bg_surface"], foreground=COLORS["text_white"])

        cb_preset = ttk.Combobox(
            f_right,
            textvariable=self.preset_var,
            values=list(QUALITY_PRESETS.keys()),
            width=15,
            state="readonly"
        )
        cb_preset.pack(side="left", padx=(0, 8))
        cb_preset.bind("<<ComboboxSelected>>", lambda e: self.scrcpy.set_preset(self.preset_var.get()))

        # Sync Action Toggle Button (Modern Sleek Pill)
        self.btn_sync = tk.Button(
            f_right,
            text="⚪ Sync Action: OFF",
            command=self._toggle_sync,
            bg=COLORS["bg_surface"],
            fg=COLORS["text_secondary"],
            activebackground="#282F48",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            padx=9,
            pady=3
        )
        self.btn_sync.pack(side="left", padx=(0, 8))

        # Quick Action Buttons Builder with Unified Modern Dark Styling
        def _make_action_btn(parent, text, cmd):
            b = tk.Button(
                parent,
                text=text,
                command=cmd,
                bg=COLORS["bg_surface"],
                fg=COLORS["text_white"],
                activebackground=COLORS["bg_card_hover"],
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                padx=7,
                pady=3
            )
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg=COLORS["bg_card_hover"]))
            b.bind("<Leave>", lambda e, btn=b: btn.config(bg=COLORS["bg_surface"]))
            return b

        btn_apk = _make_action_btn(f_right, "📦 APK", self._open_bulk_install)
        btn_apk.pack(side="left", padx=1)

        btn_shell = _make_action_btn(f_right, "💻 Shell", self._open_bulk_shell)
        btn_shell.pack(side="left", padx=1)

        btn_txt = _make_action_btn(f_right, "📝 Teks", self._open_bulk_text)
        btn_txt.pack(side="left", padx=1)

        btn_wake = _make_action_btn(f_right, "☀️ Layar", self._bulk_screen_on)
        btn_wake.pack(side="left", padx=1)

        btn_pwr = _make_action_btn(f_right, "⚡ Power", self._bulk_power)
        btn_pwr.pack(side="left", padx=1)

        btn_wifi = _make_action_btn(f_right, "📶 Wi-Fi", self._open_wifi_dialog)
        btn_wifi.pack(side="left", padx=1)

        # More Actions Menu
        btn_more = tk.Menubutton(
            f_right,
            text="⋮ Menu",
            bg=COLORS["bg_surface"],
            fg=COLORS["text_white"],
            activebackground=COLORS["bg_card_hover"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            padx=7,
            pady=3,
            cursor="hand2"
        )
        btn_more.pack(side="left", padx=1)
        btn_more.bind("<Enter>", lambda e: btn_more.config(bg=COLORS["bg_card_hover"]))
        btn_more.bind("<Leave>", lambda e: btn_more.config(bg=COLORS["bg_surface"]))

        menu_more = tk.Menu(btn_more, tearoff=0, bg=COLORS["bg_card"], fg=COLORS["text_white"], activebackground=COLORS["border_glow"])
        menu_more.add_command(label="📶 Hubungkan HP via Wi-Fi...", command=self._open_wifi_dialog)
        menu_more.add_separator()
        menu_more.add_command(label="🏠 Tekan HOME di Target HP", command=self._bulk_home)
        menu_more.add_command(label="◀ Tekan BACK di Target HP", command=self._bulk_back)
        menu_more.add_command(label="☀️ Hidupkan Layar Target HP", command=self._bulk_screen_on)
        menu_more.add_separator()
        menu_more.add_command(label="🔄 Reboot Target HP", command=self._bulk_reboot)
        btn_more["menu"] = menu_more

        # Scan Button
        btn_scan = _make_action_btn(f_right, "🔄", self._manual_scan)
        btn_scan.pack(side="left", padx=(3, 0))

    def _build_body(self):
        # Scrollable Canvas for Device Grid
        self.canvas = tk.Canvas(self, bg=COLORS["bg_root"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)

        # 1. Device Grid container frame inside canvas (top-centered)
        self.grid_frame = tk.Frame(self.canvas, bg=COLORS["bg_root"], padx=10, pady=10)
        self.grid_frame_id = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="n")

        # 2. Standalone Empty State frame (dead center of canvas)
        self.empty_frame = tk.Frame(self.canvas, bg=COLORS["bg_root"])
        lbl_empty_icon = tk.Label(self.empty_frame, text="⚡", font=("Segoe UI", 48), bg=COLORS["bg_root"], fg=COLORS["accent_cyan"])
        lbl_empty_icon.pack()

        lbl_empty_title = tk.Label(
            self.empty_frame,
            text="Menunggu Perangkat Android Terhubung...",
            font=("Segoe UI", 15, "bold"),
            bg=COLORS["bg_root"],
            fg=COLORS["text_white"]
        )
        lbl_empty_title.pack(pady=(12, 6))

        lbl_empty_desc = tk.Label(
            self.empty_frame,
            text="Colokkan kabel USB ke HP Anda dan pastikan USB Debugging aktif.\nLayar HP akan otomatis muncul secara live tanpa lag.",
            font=("Segoe UI", 10),
            bg=COLORS["bg_root"],
            fg=COLORS["text_secondary"],
            justify="center"
        )
        lbl_empty_desc.pack(pady=4)

        self.empty_frame_id = self.canvas.create_window((0, 0), window=self.empty_frame, anchor="center")

        # Responsive Centering & Dynamic Layout (debounced by size change only)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scroll support (only active when content overflows)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        """Only recomputes layout if canvas dimensions actually changed,
        preventing lag and stutter during window movement or menu interactions."""
        if not event:
            return
        w, h = event.width, event.height
        if getattr(self, "_last_canvas_size", None) == (w, h):
            return
        self._last_canvas_size = (w, h)
        self._update_layout()

    def _update_layout(self, event=None):
        """Dynamically centers the layout and toggles scrollbar visibility only when needed."""
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        has_devices = len(self.devices) > 0

        if not has_devices:
            # EMPTY STATE: Center prompt directly in middle, hide grid & scrollbar
            self.canvas.itemconfigure(self.grid_frame_id, state="hidden")
            self.canvas.itemconfigure(self.empty_frame_id, state="normal")
            self.canvas.coords(self.empty_frame_id, cw // 2, ch // 2)

            self._can_scroll_vertically = False
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()
            self.canvas.yview_moveto(0.0)
            self.canvas.configure(scrollregion=(0, 0, cw, ch))
        else:
            # DEVICES CONNECTED: Hide empty state, center card grid horizontally
            self.canvas.itemconfigure(self.empty_frame_id, state="hidden")
            self.canvas.itemconfigure(self.grid_frame_id, state="normal")

            gw = self.grid_frame.winfo_reqwidth()
            gh = self.grid_frame.winfo_reqheight()

            if gw < cw:
                self.canvas.coords(self.grid_frame_id, cw // 2, 20)
                self.canvas.itemconfig(self.grid_frame_id, anchor="n")
            else:
                self.canvas.coords(self.grid_frame_id, 20, 20)
                self.canvas.itemconfig(self.grid_frame_id, anchor="nw")

            content_h = gh + 40
            # Auto-show scrollbar only when content height overflows screen height
            if content_h > ch:
                self._can_scroll_vertically = True
                if not self.scrollbar.winfo_ismapped():
                    self.scrollbar.pack(side="right", fill="y")
                self.canvas.configure(scrollregion=(0, 0, max(cw, gw + 40), content_h))
            else:
                self._can_scroll_vertically = False
                if self.scrollbar.winfo_ismapped():
                    self.scrollbar.pack_forget()
                self.canvas.yview_moveto(0.0)
                self.canvas.configure(scrollregion=(0, 0, cw, ch))

    def _on_mousewheel(self, event):
        if getattr(self, "_can_scroll_vertically", False):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self, bg=COLORS["bg_header"], padx=16, pady=6)
        self.statusbar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(
            self.statusbar,
            text="Siap | Direct3D 11 Hardware Acceleration (Zero-Lag)",
            font=("Segoe UI", 8),
            bg=COLORS["bg_header"],
            fg=COLORS["text_muted"]
        )
        self.lbl_status.pack(side="left")

    def _set_columns(self, n: int):
        self.current_columns = n
        self._update_col_buttons()
        self._reposition_cards()

    def _update_col_buttons(self):
        for num, btn in self.col_btns.items():
            if num == self.current_columns:
                btn.config(bg="#0284C7", fg="#ffffff")
            else:
                btn.config(bg="#161926", fg=COLORS["text_secondary"])

    def _toggle_sync(self):
        self.sync_enabled = not self.sync_enabled
        if self.sync_enabled:
            if not self.master_serial and self.devices:
                self.master_serial = self.devices[0].serial
            self.sync.set_sync(True, self.master_serial)
            self.btn_sync.config(text="🔴 Sync Action: ON", bg="#38290D", fg="#FBBF24", activebackground="#4A3510")
            self._update_master_ui()
            self._log_status(f"🔴 Sync Action AKTIF! Master: {self.master_serial}")
        else:
            self.sync.set_sync(False, None)
            self.btn_sync.config(text="⚪ Sync Action: OFF", bg=COLORS["bg_surface"], fg=COLORS["text_secondary"], activebackground="#282F48")
            self._log_status("Sync Action Dinonaktifkan.")

    def _set_master_device(self, serial: str):
        self.master_serial = serial
        if self.sync_enabled:
            self.sync.set_sync(True, serial)
        self._update_master_ui()
        self._log_status(f"👑 Device Master diatur ke: {serial}")

    def _update_master_ui(self):
        for s, card in self.device_cards.items():
            card.set_master(s == self.master_serial)

        if self.master_serial:
            dev = next((d for d in self.devices if d.serial == self.master_serial), None)
            name = dev.model if dev else self.master_serial
            self.lbl_master_chip.config(text=f"👑 Master: {name}", fg="#FBBF24")
            self.f_master.config(bg="#261E0E")
        else:
            self.lbl_master_chip.config(text="👑 Master: -", fg=COLORS["text_secondary"])
            self.f_master.config(bg=COLORS["bg_surface"])

    def _start_device_scanner(self):
        """Background loop polling ADB devices and keeping farm screens awake without blocking GUI."""
        def _scan_loop():
            last_wake_time = 0.0
            last_battery_time = 0.0
            while not self._is_closing:
                try:
                    devs = self.adb.get_devices()
                    now = time.time()
                    should_battery = (now - last_battery_time > 10.0)
                    if should_battery:
                        last_battery_time = now

                    # Query telemetry in parallel in background thread pool (never blocks Tkinter!)
                    def _fetch_d(d):
                        if not d.has_static_info or should_battery:
                            self.adb.update_telemetry(d, update_battery=should_battery)

                    futures = [self.sync.executor.submit(_fetch_d, d) for d in devs]
                    for f in futures:
                        try:
                            f.result(timeout=3.0)
                        except Exception:
                            pass

                    # Dispatch lightweight UI update to main thread (< 0.5ms!)
                    self.after(0, lambda d=devs: self._sync_device_list(d))

                    # Keep devices awake in phone farm in background
                    if now - last_wake_time > 20.0:
                        last_wake_time = now
                        for d in devs:
                            self.sync.executor.submit(self.adb.turn_screen_on, d.serial)
                except Exception as e:
                    print(f"[Scanner Error] {e}")
                time.sleep(POLL_INTERVAL_MS / 1000.0)

        threading.Thread(target=_scan_loop, daemon=True).start()

    def _manual_scan(self):
        self._log_status("Memindai perangkat ADB...")
        def _bg_scan():
            devs = self.adb.get_devices()
            for d in devs:
                self.adb.update_telemetry(d, update_battery=True)
            self.after(0, lambda: self._sync_device_list(devs))
        threading.Thread(target=_bg_scan, daemon=True).start()

    def _touch_tracker_loop(self):
        """Passively tracks mouse clicks and swipes on the Master device screen container
        when Sync Action is ON, using pure Win32 API to eliminate Tcl interpreter lock contention."""
        user32 = ctypes.windll.user32
        VK_LBUTTON = 0x01
        my_pid = os.getpid()

        pt = wintypes.POINT()
        rect = wintypes.RECT()
        is_tracking = False
        start_x, start_y = 0, 0
        current_x, current_y = 0, 0
        start_time = 0.0
        frame_x, frame_y, frame_w, frame_h = 0, 0, 0, 0

        while not self._is_closing:
            if not self.sync_enabled or not self.master_serial:
                if is_tracking:
                    is_tracking = False
                time.sleep(0.04)
                continue

            card = self.device_cards.get(self.master_serial)
            hwnd = getattr(card, "screen_hwnd", 0) if card else 0
            if not card or not hwnd:
                time.sleep(0.04)
                continue

            # Check if left mouse button is pressed
            btn_state = user32.GetAsyncKeyState(VK_LBUTTON)
            is_down = (btn_state & 0x8000) != 0

            if is_down:
                if user32.GetCursorPos(ctypes.byref(pt)):
                    if not is_tracking:
                        # Check window under cursor belongs to dashboard or master scrcpy
                        hwnd_under = user32.WindowFromPoint(pt)
                        if hwnd_under:
                            pid = wintypes.DWORD()
                            user32.GetWindowThreadProcessId(hwnd_under, ctypes.byref(pid))
                            master_inst = self.scrcpy.instances.get(self.master_serial)
                            scrcpy_pid = master_inst.process.pid if (master_inst and master_inst.process) else 0

                            if pid.value not in (my_pid, scrcpy_pid):
                                time.sleep(0.02)
                                continue

                        # Pure Win32 screen rect: 100% thread-safe, 0ms, zero Tcl GIL contention
                        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                            fx = rect.left
                            fy = rect.top
                            fw = rect.right - rect.left
                            fh = rect.bottom - rect.top

                            if fx <= pt.x < fx + fw and fy <= pt.y < fy + fh:
                                is_tracking = True
                                start_x, start_y = pt.x, pt.y
                                current_x, current_y = pt.x, pt.y
                                start_time = time.time()
                                frame_x, frame_y, frame_w, frame_h = fx, fy, fw, fh
                    else:
                        current_x, current_y = pt.x, pt.y
            else:
                if is_tracking:
                    is_tracking = False
                    end_time = time.time()
                    if frame_w > 0 and frame_h > 0:
                        nx1 = max(0.0, min(1.0, (start_x - frame_x) / frame_w))
                        ny1 = max(0.0, min(1.0, (start_y - frame_y) / frame_h))
                        nx2 = max(0.0, min(1.0, (current_x - frame_x) / frame_w))
                        ny2 = max(0.0, min(1.0, (current_y - frame_y) / frame_h))

                        dist = math.hypot(current_x - start_x, current_y - start_y)
                        duration_ms = max(100, min(1200, int((end_time - start_time) * 1000)))

                        targets = self.get_sync_targets(exclude_master=True)
                        if targets:
                            if dist < 12:
                                # Normal tap
                                self.sync.broadcast_tap_normalized(targets, nx1, ny1, exclude_master=True)
                                self.after(0, lambda t=len(targets), x=int(nx1 * 100), y=int(ny1 * 100):
                                           self._log_status(f"👆 Tap Master ({x}%, {y}%) disinkronkan ke {t} HP target"))
                            else:
                                # Swipe gesture
                                self.sync.broadcast_swipe_normalized(targets, nx1, ny1, nx2, ny2, duration_ms, exclude_master=True)
                                self.after(0, lambda t=len(targets), ms=duration_ms:
                                           self._log_status(f"👉 Swipe Master ({ms}ms) disinkronkan ke {t} HP target"))

            time.sleep(0.02)

    def _sync_device_list(self, new_devices):
        if self._is_closing:
            return

        self.devices = new_devices
        count = len(new_devices)

        # Update header badge
        if count == 0:
            self.lbl_count.config(text="● 0 HP Online", fg=COLORS["text_muted"])
            self.f_count.config(bg=COLORS["bg_surface"])
        else:
            self.lbl_count.config(text=f"● {count} HP Online", fg="#34D399")
            self.f_count.config(bg="#10231D")

        new_serials = {d.serial for d in new_devices}
        current_serials = set(self.device_cards.keys())
        devices_changed = (new_serials != current_serials)

        # 1. Remove disconnected devices
        for s in current_serials - new_serials:
            self.scrcpy.stop_device(s)
            self.sync_target_serials.discard(s)
            card = self.device_cards.pop(s, None)
            if card:
                card.destroy()

        # 2. Add newly connected devices
        for d in new_devices:
            if d.serial not in self.device_cards:
                self.sync_target_serials.add(d.serial)
                self._add_device_card(d)

        # 3. Update telemetry on UI only (telemetry was already queried in background!)
        for d in new_devices:
            if d.serial in self.device_cards:
                card_dev = self.device_cards[d.serial].device
                card_dev.battery_level = d.battery_level
                card_dev.battery_temp = d.battery_temp
                card_dev.is_charging = d.is_charging
                card_dev.os_version = d.os_version
                card_dev.brand = d.brand
                card_dev.screen_width = d.screen_width
                card_dev.screen_height = d.screen_height
                self.device_cards[d.serial].update_telemetry()

        # Ensure master is valid
        if not self.master_serial and new_devices:
            self.master_serial = new_devices[0].serial

        self._update_master_ui()
        self._update_sync_targets_ui()

        # ONLY recalculate layout when devices were added or removed!
        if devices_changed:
            self._update_layout()

    def _add_device_card(self, device: ADBDevice):
        # Ensure screen is awake before initializing scrcpy
        self.adb.ensure_screen_awake(device.serial)

        card = DeviceCard(
            self.grid_frame,
            device=device,
            adb=self.adb,
            on_set_master=self._set_master_device,
            on_reconnect=lambda s=device.serial: self._reconnect_device(s),
            on_toggle_sync=self._toggle_card_sync,
            on_nav_broadcast=self._on_card_nav_broadcast,
            is_sync_target=(device.serial in self.sync_target_serials),
        )
        self.device_cards[device.serial] = card

        if device.serial == self.master_serial:
            card.set_master(True)

        self._reposition_cards()

        # Force complete window mapping so parent_hwnd is registered with OS
        self.update()
        parent_hwnd = card.get_container_hwnd()

        def _on_docked(serial, hwnd):
            self.after(0, card.hide_placeholder)
            self.after(0, lambda: self._log_status(f"✅ {serial} ({device.model}) terhubung & di-docking"))

        def _on_error(serial, err):
            self.after(0, lambda: card.show_error(err))
            self.after(0, lambda: self._log_status(f"❌ Error pada {serial}: {err}"))

        # Launch scrcpy with the exact card cell dimensions
        self.scrcpy.start_device(
            device.serial,
            parent_hwnd,
            card.cell_width,
            card.cell_height,
            on_docked=_on_docked,
            on_error=_on_error
        )

    def _reconnect_device(self, serial: str):
        card = self.device_cards.get(serial)
        if not card:
            return
        card.show_loading("Menyambungkan ulang...")
        self.scrcpy.stop_device(serial)
        dev = next((d for d in self.devices if d.serial == serial), None)
        if dev:
            self.adb.ensure_screen_awake(serial)
            parent_hwnd = card.get_container_hwnd()

            def _on_docked(s, h):
                self.after(0, card.hide_placeholder)
                self.after(0, lambda: self._log_status(f"✅ {s} ({dev.model}) terhubung kembali"))

            def _on_error(s, err):
                self.after(0, lambda: card.show_error(err))
                self.after(0, lambda: self._log_status(f"❌ Error pada {s}: {err}"))

            self.scrcpy.start_device(
                serial,
                parent_hwnd,
                card.cell_width,
                card.cell_height,
                on_docked=_on_docked,
                on_error=_on_error
            )

    def _reposition_cards(self):
        """Arranges cards in a neat responsive grid without horizontal stretching."""
        for idx, (serial, card) in enumerate(self.device_cards.items()):
            row = idx // self.current_columns
            col = idx % self.current_columns
            # No sticky='nsew', keep natural smartphone aspect ratio!
            card.grid(row=row, column=col, padx=12, pady=12, sticky="n")
        self._update_layout()

    def _log_status(self, text: str):
        self.lbl_status.config(text=f"[{time.strftime('%H:%M:%S')}] {text}")

    # Target Sync Management & Filters
    def get_sync_targets(self, exclude_master: bool = False):
        """Returns the list of devices selected for sync operations."""
        targets = []
        for d in self.devices:
            if d.serial in self.sync_target_serials:
                if exclude_master and d.serial == self.master_serial:
                    continue
                targets.append(d)
        return targets

    def _update_sync_targets_ui(self):
        """Updates UI chips and cards to reflect current sync targets."""
        for s, card in self.device_cards.items():
            card.set_sync_target(s in self.sync_target_serials)

        total = len(self.devices)
        sel = len([d for d in self.devices if d.serial in self.sync_target_serials])

        if total == 0:
            self.lbl_sync_targets.config(text="🎯 Target: 0/0 HP", fg=COLORS["text_muted"])
            self.f_sync_targets.config(bg=COLORS["bg_surface"])
        elif sel == total:
            self.lbl_sync_targets.config(text=f"🎯 Target: {sel}/{total} HP", fg="#38BDF8")
            self.f_sync_targets.config(bg="#0E242B")
        elif sel > 0:
            self.lbl_sync_targets.config(text=f"🎯 Target: {sel}/{total} HP", fg="#FBBF24")
            self.f_sync_targets.config(bg="#261E0E")
        else:
            self.lbl_sync_targets.config(text=f"🎯 Target: 0/{total} HP", fg="#EF4444")
            self.f_sync_targets.config(bg="#3B1219")

    def _toggle_card_sync(self, serial: str, is_target: bool):
        if is_target:
            self.sync_target_serials.add(serial)
        else:
            self.sync_target_serials.discard(serial)
        self._update_sync_targets_ui()
        action_name = "Diaktifkan" if is_target else "Dinonaktifkan"
        self._log_status(f"🎯 Target Sync {serial}: {action_name}")

    def _on_card_nav_broadcast(self, serial: str, action: str):
        """Handles navigation buttons clicked on device cards."""
        # Execute on source device first
        if action == "back":
            threading.Thread(target=self.adb.key_back, args=(serial,), daemon=True).start()
        elif action == "home":
            threading.Thread(target=self.adb.key_home, args=(serial,), daemon=True).start()
        elif action == "recents":
            threading.Thread(target=self.adb.key_recents, args=(serial,), daemon=True).start()
        elif action == "power":
            threading.Thread(target=self.adb.key_power, args=(serial,), daemon=True).start()

        # If sync enabled and triggered by master, broadcast to selected slave targets
        if self.sync_enabled and serial == self.master_serial:
            targets = self.get_sync_targets(exclude_master=True)
            if targets:
                if action == "back":
                    self.sync.broadcast_back(targets)
                elif action == "home":
                    self.sync.broadcast_home(targets)
                elif action == "recents":
                    self.sync.broadcast_recents(targets)
                elif action == "power":
                    self.sync.broadcast_power(targets)
                self._log_status(f"👑 Master navigasi '{action.upper()}' disinkronkan ke {len(targets)} HP")

    def _select_all_targets(self):
        self.sync_target_serials = {d.serial for d in self.devices}
        self._update_sync_targets_ui()
        self._log_status(f"🎯 Memilih seluruh {len(self.devices)} HP untuk sinkronisasi")

    def _deselect_all_targets(self):
        self.sync_target_serials = {self.master_serial} if self.master_serial else set()
        self._update_sync_targets_ui()
        self._log_status("🎯 Mengosongkan target sync (hanya Master)")

    def _filter_same_os(self):
        m_dev = next((d for d in self.devices if d.serial == self.master_serial), None)
        if not m_dev or not m_dev.os_version:
            messagebox.showinfo("Info", "Info OS Master belum terdeteksi. Silakan coba sesaat lagi.", parent=self)
            return
        os_ver = m_dev.os_version
        self.sync_target_serials = {d.serial for d in self.devices if d.os_version == os_ver or d.serial == self.master_serial}
        self._update_sync_targets_ui()
        self._log_status(f"🎯 Memilih HP dengan OS sama (Android {os_ver}): {len(self.sync_target_serials)} HP")

    def _filter_same_resolution(self):
        m_dev = next((d for d in self.devices if d.serial == self.master_serial), None)
        if not m_dev or m_dev.screen_width <= 0:
            messagebox.showinfo("Info", "Info Resolusi Master belum terdeteksi. Silakan coba sesaat lagi.", parent=self)
            return
        mw, mh = m_dev.screen_width, m_dev.screen_height
        self.sync_target_serials = {d.serial for d in self.devices if (d.screen_width == mw and d.screen_height == mh) or d.serial == self.master_serial}
        self._update_sync_targets_ui()
        self._log_status(f"🎯 Memilih HP dengan Resolusi sama ({mw}x{mh}): {len(self.sync_target_serials)} HP")

    def _filter_same_brand(self):
        m_dev = next((d for d in self.devices if d.serial == self.master_serial), None)
        if not m_dev or not m_dev.brand:
            messagebox.showinfo("Info", "Info Merek Master belum terdeteksi. Silakan coba sesaat lagi.", parent=self)
            return
        brand = m_dev.brand.lower()
        self.sync_target_serials = {d.serial for d in self.devices if (d.brand and d.brand.lower() == brand) or d.serial == self.master_serial}
        self._update_sync_targets_ui()
        self._log_status(f"🎯 Memilih HP dengan Merek sama ({m_dev.brand}): {len(self.sync_target_serials)} HP")

    def _filter_exact_match(self):
        m_dev = next((d for d in self.devices if d.serial == self.master_serial), None)
        if not m_dev:
            messagebox.showinfo("Info", "Belum ada HP Master yang dipilih.", parent=self)
            return
        mw, mh = m_dev.screen_width, m_dev.screen_height
        os_ver = m_dev.os_version
        brand = m_dev.brand.lower() if m_dev.brand else ""

        def _is_match(d: ADBDevice):
            if d.serial == self.master_serial:
                return True
            same_res = (d.screen_width == mw and d.screen_height == mh)
            same_os = (d.os_version == os_ver) if (os_ver and d.os_version) else True
            same_brand = (d.brand.lower() == brand) if (brand and d.brand) else True
            return same_res and same_os and same_brand

        self.sync_target_serials = {d.serial for d in self.devices if _is_match(d)}
        self._update_sync_targets_ui()
        self._log_status(f"🎯 Memilih HP identik (Merek, OS & Layar sama): {len(self.sync_target_serials)} HP")

    # Bulk Operations
    def _open_bulk_install(self):
        targets = self.get_sync_targets()
        if not targets:
            messagebox.showinfo("Info", "Tidak ada HP target sync yang dipilih! Centang minimal 1 HP.", parent=self)
            return
        BulkInstallDialog(self, targets, self.sync)

    def _open_bulk_shell(self):
        targets = self.get_sync_targets()
        if not targets:
            messagebox.showinfo("Info", "Tidak ada HP target sync yang dipilih! Centang minimal 1 HP.", parent=self)
            return
        BulkShellDialog(self, targets, self.sync)

    def _open_bulk_text(self):
        targets = self.get_sync_targets()
        if not targets:
            messagebox.showinfo("Info", "Tidak ada HP target sync yang dipilih! Centang minimal 1 HP.", parent=self)
            return
        BulkTextDialog(
            self,
            targets,
            self.sync,
            on_sent=lambda txt: self._log_status(f"Mengirim teks '{txt}' ke {len(targets)} HP target")
        )

    def _open_wifi_dialog(self):
        WiFiConnectDialog(
            self,
            self.adb,
            self.devices,
            on_connected=lambda target: (self._manual_scan(), self._log_status(f"🌐 Terhubung ke Wi-Fi ADB: {target}"))
        )

    def _bulk_home(self):
        targets = self.get_sync_targets()
        if targets:
            self.sync.broadcast_home(targets)
            self._log_status(f"Menekan HOME di {len(targets)} HP target")

    def _bulk_back(self):
        targets = self.get_sync_targets()
        if targets:
            self.sync.broadcast_back(targets)
            self._log_status(f"Menekan BACK di {len(targets)} HP target")

    def _bulk_screen_off(self):
        targets = self.get_sync_targets()
        if targets:
            self.sync.broadcast_screen_off(targets)
            self._log_status(f"Mematikan layar fisik di {len(targets)} HP target")

    def _bulk_screen_on(self):
        targets = self.get_sync_targets()
        if targets:
            self.sync.broadcast_screen_on(targets)
            self._log_status(f"Menghidupkan layar di {len(targets)} HP target")
            # Auto-reconnect any device whose display stream died
            for d in targets:
                inst = self.scrcpy.instances.get(d.serial)
                if not inst or not inst.is_running or (inst.process and inst.process.poll() is not None):
                    self.after(500, lambda s=d.serial: self._reconnect_device(s))

    def _bulk_power(self):
        targets = self.get_sync_targets()
        if targets:
            self.sync.broadcast_power(targets)
            self._log_status(f"Mengirim tombol Power ke {len(targets)} HP target")

    def _bulk_reboot(self):
        targets = self.get_sync_targets()
        if not targets:
            messagebox.showinfo("Info", "Tidak ada HP target sync yang dipilih!", parent=self)
            return
        if messagebox.askyesno("Konfirmasi", f"Apakah Anda yakin ingin me-restart {len(targets)} HP target terpilih?", parent=self):
            self.sync.broadcast_reboot(targets)
            self._log_status(f"Merestart {len(targets)} HP target")

    def _on_close(self):
        self._is_closing = True
        self.scrcpy.stop_all()
        self.sync.shutdown()
        self.destroy()


if __name__ == "__main__":
    app = PhoneFarmApp()
    app.mainloop()
