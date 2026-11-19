"""Scrcpy Phone Farm Dashboard - Modernized Main Application Window."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys

# Ensure src parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import (
    COLORS, QUALITY_PRESETS, DEFAULT_PRESET, DEFAULT_COLUMNS,
    CELL_HEIGHT, DEFAULT_CELL_WIDTH, POLL_INTERVAL_MS
)
from src.adb_manager import ADBManager, ADBDevice
from src.scrcpy_manager import ScrcpyManager
from src.sync_engine import SyncEngine
from src.ui_components import DeviceCard, BulkInstallDialog, BulkShellDialog, BulkTextDialog


class PhoneFarmApp(tk.Tk):
    """Main Application Window for Phone Farm Dashboard."""

    def __init__(self):
        super().__init__()
        self.title("⚡ Phone Farm Dashboard")
        self.geometry("1480x920")
        self.minsize(960, 640)
        self.configure(bg=COLORS["bg_root"])

        # Core Managers
        self.adb = ADBManager()
        self.scrcpy = ScrcpyManager()
        self.sync = SyncEngine(self.adb)

        # State
        self.device_cards = {}  # serial -> DeviceCard
        self.devices = []       # List[ADBDevice]
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

    def _build_header(self):
        self.header_frame = tk.Frame(self, bg=COLORS["bg_header"], padx=18, pady=10)
        self.header_frame.pack(fill="x", side="top")

        # 1. Left: Brand & Live Badges
        f_left = tk.Frame(self.header_frame, bg=COLORS["bg_header"])
        f_left.pack(side="left")

        lbl_logo = tk.Label(
            f_left,
            text="⚡ PHONE FARM",
            font=("Segoe UI", 13, "bold"),
            bg=COLORS["bg_header"],
            fg=COLORS["accent_cyan"]
        )
        lbl_logo.pack(side="left")

        # Version Pill
        lbl_ver = tk.Label(
            f_left,
            text="v5.0.1",
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_surface"],
            fg=COLORS["text_secondary"],
            padx=6,
            pady=1
        )
        lbl_ver.pack(side="left", padx=(6, 12))

        # Device Count Chip
        self.f_count = tk.Frame(f_left, bg="#132E27", padx=8, pady=3)
        self.f_count.pack(side="left", padx=(0, 8))

        self.lbl_count = tk.Label(
            self.f_count,
            text="● 0 HP Online",
            font=("Segoe UI", 9, "bold"),
            bg="#132E27",
            fg=COLORS["accent_green"]
        )
        self.lbl_count.pack()

        # Master Chip
        self.f_master = tk.Frame(f_left, bg=COLORS["bg_surface"], padx=8, pady=3)
        self.f_master.pack(side="left")

        self.lbl_master_chip = tk.Label(
            self.f_master,
            text="👑 Master: -",
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_surface"],
            fg=COLORS["text_secondary"]
        )
        self.lbl_master_chip.pack()

        # 2. Right: Action Controls & Layout Pills
        f_right = tk.Frame(self.header_frame, bg=COLORS["bg_header"])
        f_right.pack(side="right")

        # Grid Columns Selector (Segmented buttons)
        f_cols = tk.Frame(f_right, bg=COLORS["bg_surface"], padx=3, pady=3)
        f_cols.pack(side="left", padx=(0, 12))

        lbl_col_tag = tk.Label(f_cols, text="Kolom:", font=("Segoe UI", 8), bg=COLORS["bg_surface"], fg=COLORS["text_muted"])
        lbl_col_tag.pack(side="left", padx=(4, 6))

        self.col_btns = {}
        for num in (2, 3, 4, 5, 6):
            b = tk.Button(
                f_cols,
                text=f"{num}x",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=6,
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
            width=16,
            state="readonly"
        )
        cb_preset.pack(side="left", padx=(0, 12))
        cb_preset.bind("<<ComboboxSelected>>", lambda e: self.scrcpy.set_preset(self.preset_var.get()))

        # Sync Action Toggle Button (Modern Pill)
        self.btn_sync = tk.Button(
            f_right,
            text="⚪ Sync Action: OFF",
            command=self._toggle_sync,
            bg=COLORS["bg_surface"],
            fg=COLORS["text_secondary"],
            activebackground=COLORS["accent_yellow"],
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=4
        )
        self.btn_sync.pack(side="left", padx=(0, 10))

        # Quick Action Buttons
        def _make_act_btn(parent, text, bg_color, fg_color, cmd):
            b = tk.Button(
                parent,
                text=text,
                command=cmd,
                bg=bg_color,
                fg=fg_color,
                relief="flat",
                bd=0,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                padx=9,
                pady=4
            )
            return b

        btn_apk = _make_act_btn(f_right, "📦 APK", COLORS["accent_blue"], "#ffffff", self._open_bulk_install)
        btn_apk.pack(side="left", padx=2)

        btn_shell = _make_act_btn(f_right, "💻 Shell", COLORS["accent_purple"], "#ffffff", self._open_bulk_shell)
        btn_shell.pack(side="left", padx=2)

        btn_txt = _make_act_btn(f_right, "📝 Teks", COLORS["accent_cyan"], "#000000", self._open_bulk_text)
        btn_txt.pack(side="left", padx=2)

        btn_wake = _make_act_btn(f_right, "☀️ Bangunkan", COLORS["accent_orange"], "#000000", self._bulk_screen_on)
        btn_wake.pack(side="left", padx=2)

        btn_pwr = _make_act_btn(f_right, "⚡ Power", COLORS["bg_surface"], COLORS["text_white"], self._bulk_power)
        btn_pwr.pack(side="left", padx=2)

        # More Actions Menu
        btn_more = tk.Menubutton(
            f_right,
            text="⋮ Menu",
            bg=COLORS["bg_surface"],
            fg=COLORS["text_primary"],
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            cursor="hand2"
        )
        btn_more.pack(side="left", padx=2)

        menu_more = tk.Menu(btn_more, tearoff=0, bg=COLORS["bg_card"], fg=COLORS["text_white"], activebackground=COLORS["border_glow"])
        menu_more.add_command(label="🏠 Tekan HOME di Semua HP", command=self._bulk_home)
        menu_more.add_command(label="◀ Tekan BACK di Semua HP", command=self._bulk_back)
        menu_more.add_command(label="☀️ Hidupkan Layar Semua HP", command=self._bulk_screen_on)
        menu_more.add_separator()
        menu_more.add_command(label="🔄 Reboot Seluruh HP", command=self._bulk_reboot)
        btn_more["menu"] = menu_more

        # Scan Button
        btn_scan = _make_act_btn(f_right, "🔄", COLORS["bg_surface"], COLORS["text_primary"], self._manual_scan)
        btn_scan.pack(side="left", padx=(4, 0))

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

        # Responsive Centering & Dynamic Layout
        self.canvas.bind("<Configure>", self._update_layout)

        # Mousewheel scroll support (only active when content overflows)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _update_layout(self, event=None):
        """Dynamically centers the layout and toggles scrollbar visibility only when needed."""
        self.canvas.update_idletasks()
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

            self.grid_frame.update_idletasks()
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
                btn.config(bg=COLORS["accent_cyan"], fg="#000000")
            else:
                btn.config(bg=COLORS["bg_surface"], fg=COLORS["text_secondary"])

    def _toggle_sync(self):
        self.sync_enabled = not self.sync_enabled
        if self.sync_enabled:
            if not self.master_serial and self.devices:
                self.master_serial = self.devices[0].serial
            self.sync.set_sync(True, self.master_serial)
            self.btn_sync.config(text="🔴 Sync Action: ON", bg=COLORS["accent_yellow"], fg="#000000")
            self._update_master_ui()
            self._log_status(f"🔴 Sync Action AKTIF! Master: {self.master_serial}")
        else:
            self.sync.set_sync(False, None)
            self.btn_sync.config(text="⚪ Sync Action: OFF", bg=COLORS["bg_surface"], fg=COLORS["text_secondary"])
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
            self.lbl_master_chip.config(text=f"👑 Master: {name}", fg=COLORS["accent_yellow"])
            self.f_master.config(bg="#332B12")
        else:
            self.lbl_master_chip.config(text="👑 Master: -", fg=COLORS["text_secondary"])
            self.f_master.config(bg=COLORS["bg_surface"])

    def _start_device_scanner(self):
        """Background loop polling ADB devices and keeping farm screens awake."""
        def _scan_loop():
            last_wake_time = 0.0
            while not self._is_closing:
                try:
                    devs = self.adb.get_devices()
                    self.after(0, lambda d=devs: self._sync_device_list(d))

                    # Keep devices awake in phone farm (prevent black screen timeout)
                    now = time.time()
                    if now - last_wake_time > 18.0:
                        last_wake_time = now
                        for d in devs:
                            self.adb.turn_screen_on(d.serial)
                except Exception as e:
                    print(f"[Scanner Error] {e}")
                time.sleep(POLL_INTERVAL_MS / 1000.0)

        threading.Thread(target=_scan_loop, daemon=True).start()

    def _manual_scan(self):
        self._log_status("Memindai perangkat ADB...")
        threading.Thread(target=lambda: self._sync_device_list(self.adb.get_devices()), daemon=True).start()

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
            self.lbl_count.config(text=f"● {count} HP Online", fg=COLORS["accent_green"])
            self.f_count.config(bg="#132E27")

        new_serials = {d.serial for d in new_devices}
        current_serials = set(self.device_cards.keys())

        # 1. Remove disconnected devices
        for s in current_serials - new_serials:
            self.scrcpy.stop_device(s)
            card = self.device_cards.pop(s, None)
            if card:
                card.destroy()

        # 2. Add newly connected devices
        for d in new_devices:
            if d.serial not in self.device_cards:
                self.adb.update_telemetry(d)
                self._add_device_card(d)

        # 3. Update telemetry for existing devices
        for d in new_devices:
            if d.serial in self.device_cards:
                self.adb.update_telemetry(d)
                self.device_cards[d.serial].update_telemetry()

        # Ensure master is valid
        if not self.master_serial and new_devices:
            self.master_serial = new_devices[0].serial
        self._update_master_ui()
        self._update_layout()

    def _add_device_card(self, device: ADBDevice):
        # Auto-wake sleeping device so display immediately outputs video
        threading.Thread(target=self.adb.turn_screen_on, args=(device.serial,), daemon=True).start()

        card = DeviceCard(
            self.grid_frame,
            device=device,
            adb=self.adb,
            on_set_master=self._set_master_device,
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

    # Bulk Operations
    def _open_bulk_install(self):
        if not self.devices:
            messagebox.showinfo("Info", "Tidak ada HP yang terhubung!", parent=self)
            return
        BulkInstallDialog(self, self.devices, self.sync)

    def _open_bulk_shell(self):
        if not self.devices:
            messagebox.showinfo("Info", "Tidak ada HP yang terhubung!", parent=self)
            return
        BulkShellDialog(self, self.devices, self.sync)

    def _open_bulk_text(self):
        if not self.devices:
            messagebox.showinfo("Info", "Tidak ada HP yang terhubung!", parent=self)
            return
        BulkTextDialog(
            self,
            self.devices,
            self.sync,
            on_sent=lambda txt: self._log_status(f"Mengirim teks '{txt}' ke {len(self.devices)} HP")
        )

    def _bulk_home(self):
        if self.devices:
            self.sync.broadcast_home(self.devices)
            self._log_status("Menekan HOME di seluruh HP")

    def _bulk_back(self):
        if self.devices:
            self.sync.broadcast_back(self.devices)
            self._log_status("Menekan BACK di seluruh HP")

    def _bulk_screen_off(self):
        if self.devices:
            self.sync.broadcast_screen_off(self.devices)
            self._log_status("Mematikan layar fisik seluruh HP (Mirror tetap aktif)")

    def _bulk_screen_on(self):
        if self.devices:
            self.sync.broadcast_screen_on(self.devices)
            self._log_status("Menghidupkan layar seluruh HP")

    def _bulk_power(self):
        if self.devices:
            self.sync.broadcast_power(self.devices)
            self._log_status("Mengirim tombol Power ke seluruh HP")

    def _bulk_reboot(self):
        if not self.devices:
            return
        if messagebox.askyesno("Konfirmasi", f"Apakah Anda yakin ingin me-restart seluruh {len(self.devices)} HP?", parent=self):
            self.sync.broadcast_reboot(self.devices)
            self._log_status(f"Merestart {len(self.devices)} HP")

    def _on_close(self):
        self._is_closing = True
        self.scrcpy.stop_all()
        self.sync.shutdown()
        self.destroy()


if __name__ == "__main__":
    app = PhoneFarmApp()
    app.mainloop()
