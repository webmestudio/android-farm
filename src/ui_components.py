"""Modern UI Components for Device Cards, Quick Navigation, and Modal Dialogs."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Callable, Optional, Dict
from .config import COLORS, CELL_HEIGHT, DEFAULT_CELL_WIDTH
from .adb_manager import ADBDevice, ADBManager


class DeviceCard(tk.Frame):
    """Modern smartphone frame card embedding the native scrcpy screen without black bars."""

    def __init__(
        self,
        parent,
        device: ADBDevice,
        adb: ADBManager,
        on_set_master: Optional[Callable[[str], None]] = None,
        on_reconnect: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(
            parent,
            bg=COLORS["bg_card"],
            highlightbackground=COLORS["border_card"],
            highlightcolor=COLORS["border_glow"],
            highlightthickness=1,
            **kwargs
        )
        self.device = device
        self.adb = adb
        self.on_set_master = on_set_master
        self.on_reconnect = on_reconnect
        self.is_master = False

        # Calculate exact phone aspect ratio
        sw = device.screen_width if device.screen_width > 0 else 1080
        sh = device.screen_height if device.screen_height > 0 else 2400
        ratio = sw / sh if sh > 0 else 0.46
        # Clamp ratio between 0.42 (ultra tall 20:9) and 0.60 (standard 16:9)
        ratio = max(0.42, min(0.60, ratio))
        self.cell_height = CELL_HEIGHT
        self.cell_width = int(self.cell_height * ratio)

        self._build_ui()

    def _build_ui(self):
        # 1. Top Phone Chassis Header Bar
        self.header = tk.Frame(self, bg=COLORS["bg_header"], padx=8, pady=6)
        self.header.pack(fill="x", side="top")

        # Status Dot (Green) + Model Name
        f_left = tk.Frame(self.header, bg=COLORS["bg_header"])
        f_left.pack(side="left")

        self.dot_indicator = tk.Label(
            f_left,
            text="●",
            font=("Segoe UI", 8),
            bg=COLORS["bg_header"],
            fg=COLORS["accent_green"]
        )
        self.dot_indicator.pack(side="left", padx=(0, 4))

        # Truncate model name if too long
        display_name = self.device.model
        if len(display_name) > 13:
            display_name = display_name[:11] + ".."

        self.lbl_model = tk.Label(
            f_left,
            text=display_name,
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_header"],
            fg=COLORS["text_white"]
        )
        self.lbl_model.pack(side="left")

        # Right side: Battery Pill + Temp Chip
        f_right = tk.Frame(self.header, bg=COLORS["bg_header"])
        f_right.pack(side="right")

        # Battery Pill
        self.f_battery = tk.Frame(f_right, bg="#132E27", padx=5, pady=1)
        self.f_battery.pack(side="right", padx=(4, 0))

        self.lbl_battery = tk.Label(
            self.f_battery,
            text="--%",
            font=("Segoe UI", 8, "bold"),
            bg="#132E27",
            fg=COLORS["accent_green"]
        )
        self.lbl_battery.pack()

        # Temp Chip
        self.lbl_temp = tk.Label(
            f_right,
            text="",
            font=("Segoe UI", 8),
            bg=COLORS["bg_header"],
            fg=COLORS["text_secondary"]
        )
        self.lbl_temp.pack(side="right")

        # 2. Smartphone Screen Container (Pixel-perfect matching phone ratio)
        self.screen_frame = tk.Frame(
            self,
            bg="#000000",
            width=self.cell_width,
            height=self.cell_height
        )
        self.screen_frame.pack(side="top")
        self.screen_frame.pack_propagate(False)

        # Loading Indicator directly on screen_frame
        self.placeholder_lbl = tk.Label(
            self.screen_frame,
            text="📱 Menghubungkan...",
            font=("Segoe UI", 10),
            bg="#000000",
            fg=COLORS["text_secondary"]
        )
        self.placeholder_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self.placeholder_lbl.bind("<Button-1>", lambda e: self._on_reconnect_click())

        # 3. Bottom Modern Navigation Dock
        self.toolbar = tk.Frame(self, bg=COLORS["bg_header"], padx=6, pady=5)
        self.toolbar.pack(fill="x", side="bottom")

        def _make_nav_btn(parent, text, cmd, width=3):
            b = tk.Button(
                parent,
                text=text,
                command=cmd,
                bg=COLORS["bg_surface"],
                fg=COLORS["text_primary"],
                activebackground=COLORS["accent_blue"],
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                width=width,
                pady=2
            )
            b.bind("<Enter>", lambda e: b.config(bg=COLORS["bg_card_hover"]))
            b.bind("<Leave>", lambda e: b.config(bg=COLORS["bg_surface"]))
            return b

        self.btn_back = _make_nav_btn(self.toolbar, "◀", self._action_back)
        self.btn_back.pack(side="left", padx=1)

        self.btn_home = _make_nav_btn(self.toolbar, "⭕", self._action_home)
        self.btn_home.pack(side="left", padx=1)

        self.btn_recents = _make_nav_btn(self.toolbar, "▢", self._action_recents)
        self.btn_recents.pack(side="left", padx=1)

        self.btn_power = _make_nav_btn(self.toolbar, "⚡ Power", self._action_power, width=5)
        self.btn_power.pack(side="left", padx=1)

        # Master Button (Right)
        self.btn_master = tk.Button(
            self.toolbar,
            text="👑 Master",
            command=self._action_master,
            bg=COLORS["bg_surface"],
            fg=COLORS["text_secondary"],
            activebackground=COLORS["accent_yellow"],
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            padx=6,
            pady=2
        )
        self.btn_master.pack(side="right", padx=1)

    def get_container_hwnd(self) -> int:
        """Returns the Win32 HWND of the screen frame for scrcpy docking."""
        self.screen_frame.update_idletasks()
        return self.screen_frame.winfo_id()

    def hide_placeholder(self):
        """Hides the loading placeholder once docked."""
        if hasattr(self, 'placeholder_lbl') and self.placeholder_lbl and self.placeholder_lbl.winfo_exists():
            self.placeholder_lbl.place_forget()

    def show_loading(self, text: str = "Menghubungkan..."):
        """Displays loading placeholder."""
        if hasattr(self, 'placeholder_lbl') and self.placeholder_lbl and self.placeholder_lbl.winfo_exists():
            self.placeholder_lbl.config(text=f"📱 {text}", fg=COLORS["text_secondary"])
            self.placeholder_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def show_error(self, err_text: str):
        """Displays error on placeholder."""
        if hasattr(self, 'placeholder_lbl') and self.placeholder_lbl and self.placeholder_lbl.winfo_exists():
            self.placeholder_lbl.config(
                text=f"⚠️ {err_text[:30]}\n\n[Klik untuk Coba Lagi]",
                fg=COLORS["accent_red"],
                cursor="hand2"
            )
            self.placeholder_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def _on_reconnect_click(self):
        if self.on_reconnect:
            self.on_reconnect(self.device.serial)

    def set_master(self, is_master: bool):
        self.is_master = is_master
        if is_master:
            self.config(highlightbackground=COLORS["border_master"], highlightthickness=2)
            self.btn_master.config(bg=COLORS["accent_yellow"], fg="#000000")
            self.dot_indicator.config(fg=COLORS["accent_yellow"])
        else:
            self.config(highlightbackground=COLORS["border_card"], highlightthickness=1)
            self.btn_master.config(bg=COLORS["bg_surface"], fg=COLORS["text_secondary"])
            self.dot_indicator.config(fg=COLORS["accent_green"])

    def update_telemetry(self):
        """Updates battery level and temperature on UI."""
        if self.device.battery_level >= 0:
            bolt = "⚡" if self.device.is_charging else ""
            self.lbl_battery.config(text=f"{bolt}{self.device.battery_level}%")
            if self.device.battery_level > 50:
                self.f_battery.config(bg="#132E27")
                self.lbl_battery.config(bg="#132E27", fg=COLORS["accent_green"])
            elif self.device.battery_level > 20:
                self.f_battery.config(bg="#332B12")
                self.lbl_battery.config(bg="#332B12", fg=COLORS["accent_yellow"])
            else:
                self.f_battery.config(bg="#3B1219")
                self.lbl_battery.config(bg="#3B1219", fg=COLORS["accent_red"])

        if self.device.battery_temp > 0:
            self.lbl_temp.config(text=f"🌡 {self.device.battery_temp}°C")

    # Actions
    def _action_back(self):
        threading.Thread(target=self.adb.key_back, args=(self.device.serial,), daemon=True).start()

    def _action_home(self):
        threading.Thread(target=self.adb.key_home, args=(self.device.serial,), daemon=True).start()

    def _action_recents(self):
        threading.Thread(target=self.adb.key_recents, args=(self.device.serial,), daemon=True).start()

    def _action_power(self):
        """Sends KEYCODE_POWER (26) to toggle screen on/off like physical phone power button."""
        threading.Thread(target=self.adb.key_power, args=(self.device.serial,), daemon=True).start()

    def _action_wake(self):
        """Sends KEYCODE_WAKEUP (224) to turn on screen if asleep."""
        threading.Thread(target=self.adb.turn_screen_on, args=(self.device.serial,), daemon=True).start()

    def _action_master(self):
        if self.on_set_master:
            self.on_set_master(self.device.serial)


def center_toplevel(window: tk.Toplevel, parent: Optional[tk.Misc] = None, width: int = 500, height: int = 400):
    """Centers a Toplevel modal dialog directly in the middle of its parent window or screen."""
    window.update_idletasks()

    x = None
    y = None
    if parent and parent.winfo_exists() and parent.winfo_ismapped():
        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            if pw > 100 and ph > 100:
                px = parent.winfo_rootx()
                py = parent.winfo_rooty()
                x = px + max(0, (pw - width) // 2)
                y = py + max(0, (ph - height) // 2)
        except Exception:
            pass

    if x is None or y is None:
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")


class BulkInstallDialog(tk.Toplevel):
    """Modern modal dialog for bulk APK installation across all phones."""

    def __init__(self, parent, devices, sync_engine, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("📦 Bulk APK Installer")
        self.configure(bg=COLORS["bg_root"])
        self.devices = devices
        self.sync_engine = sync_engine
        self.transient(parent)

        self._build_ui()
        center_toplevel(self, parent, 560, 440)
        self.grab_set()

    def _build_ui(self):
        pad = 14
        header_f = tk.Frame(self, bg=COLORS["bg_header"], padx=pad, pady=10)
        header_f.pack(fill="x")

        lbl = tk.Label(
            header_f,
            text="📦 Install APK ke Seluruh Device Serentak",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_header"],
            fg=COLORS["text_white"]
        )
        lbl.pack(anchor="w")

        body_f = tk.Frame(self, bg=COLORS["bg_root"], padx=pad, pady=pad)
        body_f.pack(fill="both", expand=True)

        # Path input row
        f_path = tk.Frame(body_f, bg=COLORS["bg_root"])
        f_path.pack(fill="x", pady=(0, 10))

        self.entry_path = tk.Entry(
            f_path,
            bg=COLORS["bg_input"],
            fg=COLORS["text_white"],
            insertbackground="#ffffff",
            relief="flat",
            font=("Segoe UI", 9)
        )
        self.entry_path.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        btn_browse = tk.Button(
            f_path,
            text="Pilih APK...",
            bg=COLORS["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            command=self._browse
        )
        btn_browse.pack(side="right")

        # Results treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=COLORS["bg_header"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_header"],
            borderwidth=0
        )
        style.configure("Treeview.Heading", background=COLORS["bg_surface"], foreground=COLORS["text_white"], relief="flat")

        self.tree = ttk.Treeview(body_f, columns=("serial", "model", "status"), show="headings", height=8)
        self.tree.heading("serial", text="Serial")
        self.tree.heading("model", text="Device")
        self.tree.heading("status", text="Status")
        self.tree.column("serial", width=120)
        self.tree.column("model", width=140)
        self.tree.column("status", width=200)
        self.tree.pack(fill="both", expand=True, pady=(0, 10))

        for d in self.devices:
            self.tree.insert("", "end", iid=d.serial, values=(d.serial, d.model, "Siap"))

        # Install Action button
        self.btn_install = tk.Button(
            body_f,
            text="🚀 Mulai Install ke Seluruh Device",
            bg=COLORS["accent_green"],
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self._start_install
        )
        self.btn_install.pack(fill="x")

    def _browse(self):
        file = filedialog.askopenfilename(filetypes=[("Android APK", "*.apk")], parent=self)
        if file:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, file)

    def _start_install(self):
        apk = self.entry_path.get().strip()
        if not apk:
            messagebox.showwarning("Peringatan", "Pilih file APK terlebih dahulu!", parent=self)
            return

        self.btn_install.config(state="disabled", text="⏳ Sedang Menginstall...")

        def _worker():
            for d in self.devices:
                self.tree.set(d.serial, "status", "⏳ Menginstall...")

            def _on_done(serial, ok, msg):
                status_text = "✅ Berhasil" if ok else f"❌ Gagal: {msg[:30]}"
                self.after(0, lambda: self.tree.set(serial, "status", status_text))

            self.sync_engine.broadcast_apk_install(self.devices, apk, on_device_done=_on_done)
            self.after(0, lambda: self.btn_install.config(state="normal", text="✅ Selesai!"))

        threading.Thread(target=_worker, daemon=True).start()


class BulkShellDialog(tk.Toplevel):
    """Modern modal dialog to run ADB shell command across all devices simultaneously."""

    def __init__(self, parent, devices, sync_engine, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("💻 Bulk Shell Command")
        self.configure(bg=COLORS["bg_root"])
        self.devices = devices
        self.sync_engine = sync_engine
        self.transient(parent)

        self._build_ui()
        center_toplevel(self, parent, 660, 500)
        self.grab_set()

    def _build_ui(self):
        pad = 14
        header_f = tk.Frame(self, bg=COLORS["bg_header"], padx=pad, pady=10)
        header_f.pack(fill="x")

        lbl = tk.Label(
            header_f,
            text="💻 Jalankan Perintah Shell ke Seluruh HP",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_header"],
            fg=COLORS["text_white"]
        )
        lbl.pack(anchor="w")

        body_f = tk.Frame(self, bg=COLORS["bg_root"], padx=pad, pady=pad)
        body_f.pack(fill="both", expand=True)

        # Command input row
        f_cmd = tk.Frame(body_f, bg=COLORS["bg_root"])
        f_cmd.pack(fill="x", pady=(0, 8))

        self.entry_cmd = tk.Entry(
            f_cmd,
            bg=COLORS["bg_input"],
            fg=COLORS["text_white"],
            insertbackground="#ffffff",
            relief="flat",
            font=("Consolas", 10)
        )
        self.entry_cmd.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))
        self.entry_cmd.insert(0, "getprop ro.build.version.release")
        self.entry_cmd.bind("<Return>", lambda e: self._run_command())

        btn_run = tk.Button(
            f_cmd,
            text="Jalankan ▶",
            bg=COLORS["accent_cyan"],
            fg="#000000",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            command=self._run_command
        )
        btn_run.pack(side="right")

        # Output text area
        self.txt_output = tk.Text(
            body_f,
            bg=COLORS["bg_header"],
            fg=COLORS["accent_green"],
            font=("Consolas", 9),
            relief="flat",
            wrap="none",
            padx=8,
            pady=8
        )
        self.txt_output.pack(fill="both", expand=True)

    def _run_command(self):
        cmd = self.entry_cmd.get().strip()
        if not cmd:
            return

        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert(tk.END, f">> adb shell {cmd}\n\n")

        def _worker():
            def _on_done(serial, ok, out):
                tag = "OK" if ok else "ERR"
                res_line = f"[{serial}] ({tag}): {out}\n"
                self.after(0, lambda: self.txt_output.insert(tk.END, res_line))

            self.sync_engine.broadcast_shell(self.devices, cmd, on_device_done=_on_done)

        threading.Thread(target=_worker, daemon=True).start()


class BulkTextDialog(tk.Toplevel):
    """Modern modal dialog to broadcast typed text to all devices simultaneously, centered over parent."""

    def __init__(self, parent, devices, sync_engine, on_sent: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("📝 Broadcast Teks")
        self.configure(bg=COLORS["bg_root"])
        self.devices = devices
        self.sync_engine = sync_engine
        self.on_sent = on_sent
        self.transient(parent)

        self._build_ui()
        center_toplevel(self, parent, 460, 200)
        self.grab_set()

    def _build_ui(self):
        header_f = tk.Frame(self, bg=COLORS["bg_header"], padx=16, pady=10)
        header_f.pack(fill="x")

        lbl = tk.Label(
            header_f,
            text=f"📝 Ketik Teks ke {len(self.devices)} HP Serentak",
            bg=COLORS["bg_header"],
            fg=COLORS["text_white"],
            font=("Segoe UI", 10, "bold")
        )
        lbl.pack(anchor="w")

        body_f = tk.Frame(self, bg=COLORS["bg_root"], padx=16, pady=16)
        body_f.pack(fill="both", expand=True)

        self.entry = tk.Entry(
            body_f,
            bg=COLORS["bg_input"],
            fg=COLORS["text_white"],
            insertbackground="#ffffff",
            font=("Segoe UI", 10),
            relief="flat"
        )
        self.entry.pack(fill="x", pady=(0, 12), ipady=6)
        self.entry.focus_set()

        def _send():
            txt = self.entry.get()
            if txt:
                self.sync_engine.broadcast_text(self.devices, txt)
                if self.on_sent:
                    self.on_sent(txt)
                self.destroy()

        self.entry.bind("<Return>", lambda e: _send())

        btn = tk.Button(
            body_f,
            text="🚀 Kirim ke Semua HP (Enter)",
            bg=COLORS["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            command=_send,
            pady=6
        )
        btn.pack(fill="x")


class WiFiConnectDialog(tk.Toplevel):
    """Modern modal dialog to connect Android devices over Wi-Fi (Wireless ADB)."""

    def __init__(self, parent, adb: ADBManager, devices, on_connected: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("📶 Hubungkan HP via Wi-Fi (Nirkabel)")
        self.configure(bg=COLORS["bg_root"])
        self.adb = adb
        self.devices = devices
        self.on_connected = on_connected
        self.transient(parent)

        self._build_ui()
        center_toplevel(self, parent, 560, 650)
        self.grab_set()

    def _build_ui(self):
        header_f = tk.Frame(self, bg=COLORS["bg_header"], padx=18, pady=12)
        header_f.pack(fill="x")

        lbl_title = tk.Label(
            header_f,
            text="📶 Hubungkan HP via Wi-Fi (Nirkabel)",
            font=("Segoe UI", 12, "bold"),
            bg=COLORS["bg_header"],
            fg=COLORS["accent_green"]
        )
        lbl_title.pack(anchor="w")

        lbl_desc = tk.Label(
            header_f,
            text="Pastikan HP dan Komputer Anda terhubung ke jaringan Wi-Fi / Router yang sama.",
            font=("Segoe UI", 8),
            bg=COLORS["bg_header"],
            fg=COLORS["text_secondary"]
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        body_f = tk.Frame(self, bg=COLORS["bg_root"], padx=18, pady=14)
        body_f.pack(fill="both", expand=True)

        # ==========================================
        # SECTION 1: 1-Klik Switch dari USB ke Wi-Fi
        # ==========================================
        f_sec1 = tk.LabelFrame(
            body_f,
            text=" ⚡ Cara Praktis: Switch dari USB ke Wi-Fi (1-Klik) ",
            bg=COLORS["bg_card"],
            fg=COLORS["accent_cyan"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=10
        )
        f_sec1.pack(fill="x", pady=(0, 14))

        # Check for USB devices
        usb_devices = [d for d in self.devices if ":" not in d.serial]

        if usb_devices:
            dev_labels = [f"{d.serial} ({d.model})" for d in usb_devices]
            self.sel_usb_var = tk.StringVar(value=dev_labels[0])

            lbl_hint1 = tk.Label(
                f_sec1,
                text="Pilih HP yang dicolok kabel USB:",
                font=("Segoe UI", 8),
                bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"]
            )
            lbl_hint1.pack(anchor="w", pady=(0, 4))

            cb_dev = ttk.Combobox(f_sec1, textvariable=self.sel_usb_var, values=dev_labels, state="readonly")
            cb_dev.pack(fill="x", pady=(0, 8))

            self.lbl_ip_info = tk.Label(
                f_sec1,
                text="🔍 Memeriksa IP Wi-Fi perangkat...",
                font=("Segoe UI", 8),
                bg=COLORS["bg_card"],
                fg=COLORS["text_muted"]
            )
            self.lbl_ip_info.pack(anchor="w", pady=(0, 8))

            def _update_detected_ip(*args):
                sel_text = self.sel_usb_var.get()
                serial = sel_text.split()[0] if sel_text else None
                if serial:
                    def _fetch():
                        ip = self.adb.get_device_ip(serial)
                        if ip:
                            self.after(0, lambda: self.lbl_ip_info.config(
                                text=f"🌐 IP Wi-Fi Terdeteksi: {ip}",
                                fg=COLORS["accent_green"]
                            ))
                            self.after(0, lambda: self.entry_ip.delete(0, tk.END) or self.entry_ip.insert(0, ip))
                        else:
                            self.after(0, lambda: self.lbl_ip_info.config(
                                text="⚠️ HP belum terhubung ke Wi-Fi!",
                                fg=COLORS["accent_red"]
                            ))
                    threading.Thread(target=_fetch, daemon=True).start()

            cb_dev.bind("<<ComboboxSelected>>", _update_detected_ip)
            self.after(200, _update_detected_ip)

            self.btn_switch = tk.Button(
                f_sec1,
                text="⚡ Aktifkan Mode Wi-Fi & Sambungkan",
                bg=COLORS["accent_cyan"],
                fg="#000000",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                cursor="hand2",
                pady=5,
                command=self._switch_usb_to_wifi
            )
            self.btn_switch.pack(fill="x")
        else:
            lbl_no_usb = tk.Label(
                f_sec1,
                text="Tidak ada HP yang terhubung via kabel USB.\nColokkan HP via USB sekali saja untuk mengaktifkan Wi-Fi secara otomatis.",
                font=("Segoe UI", 8),
                bg=COLORS["bg_card"],
                fg=COLORS["text_muted"],
                justify="left"
            )
            lbl_no_usb.pack(anchor="w")

        # ==========================================
        # SECTION 2: Sambung Manual (IP & Port)
        # ==========================================
        f_sec2 = tk.LabelFrame(
            body_f,
            text=" 🔗 Sambung Manual ke IP & Port ",
            bg=COLORS["bg_card"],
            fg=COLORS["text_white"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=10
        )
        f_sec2.pack(fill="x")

        f_inputs = tk.Frame(f_sec2, bg=COLORS["bg_card"])
        f_inputs.pack(fill="x", pady=(0, 8))

        lbl_ip = tk.Label(f_inputs, text="IP Address:", font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        lbl_ip.grid(row=0, column=0, sticky="w", padx=(0, 8))

        lbl_port = tk.Label(f_inputs, text="Port:", font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        lbl_port.grid(row=0, column=1, sticky="w")

        self.entry_ip = tk.Entry(f_inputs, bg=COLORS["bg_input"], fg=COLORS["text_white"], font=("Segoe UI", 9), relief="flat")
        self.entry_ip.grid(row=1, column=0, sticky="ew", padx=(0, 8), ipady=3)
        self.entry_ip.insert(0, "192.168.1.")

        self.entry_port = tk.Entry(f_inputs, bg=COLORS["bg_input"], fg=COLORS["text_white"], font=("Segoe UI", 9), relief="flat", width=8)
        self.entry_port.grid(row=1, column=1, sticky="w", ipady=3)
        self.entry_port.insert(0, "5555")

        f_inputs.columnconfigure(0, weight=1)

        self.btn_manual = tk.Button(
            f_sec2,
            text="🔌 Hubungkan Nirkabel",
            bg=COLORS["accent_blue"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            pady=5,
            command=self._manual_connect
        )
        self.btn_manual.pack(fill="x")

        # ==========================================
        # SECTION 3: Pairing Nirkabel (Android 11+ Murni Tanpa USB)
        # ==========================================
        f_sec3 = tk.LabelFrame(
            body_f,
            text=" 🔒 Android 11+ Wireless Pairing (Murni Tanpa USB) ",
            bg=COLORS["bg_card"],
            fg=COLORS["accent_yellow"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=10
        )
        f_sec3.pack(fill="x", pady=(12, 0))

        lbl_pair_desc = tk.Label(
            f_sec3,
            text="Di HP: Buka Opsi Pengembang > Debugging Nirkabel > 'Pasangkan dengan kode'",
            font=("Segoe UI", 8),
            bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"]
        )
        lbl_pair_desc.pack(anchor="w", pady=(0, 6))

        f_pair_inputs = tk.Frame(f_sec3, bg=COLORS["bg_card"])
        f_pair_inputs.pack(fill="x", pady=(0, 8))

        lbl_p_ip = tk.Label(f_pair_inputs, text="IP & Port Pairing:", font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        lbl_p_ip.grid(row=0, column=0, sticky="w", padx=(0, 8))

        lbl_p_code = tk.Label(f_pair_inputs, text="Kode 6-Digit:", font=("Segoe UI", 8), bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        lbl_p_code.grid(row=0, column=1, sticky="w")

        self.entry_pair_addr = tk.Entry(f_pair_inputs, bg=COLORS["bg_input"], fg=COLORS["text_white"], font=("Segoe UI", 9), relief="flat")
        self.entry_pair_addr.grid(row=1, column=0, sticky="ew", padx=(0, 8), ipady=3)
        self.entry_pair_addr.insert(0, "192.168.1.9:")

        self.entry_pair_code = tk.Entry(f_pair_inputs, bg=COLORS["bg_input"], fg=COLORS["text_white"], font=("Segoe UI", 9), relief="flat", width=12)
        self.entry_pair_code.grid(row=1, column=1, sticky="w", ipady=3)

        f_pair_inputs.columnconfigure(0, weight=1)

        self.btn_pair = tk.Button(
            f_sec3,
            text="🤝 Pasangkan (Pair Device)",
            bg=COLORS["accent_yellow"],
            fg="#000000",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            pady=5,
            command=self._pair_wireless
        )
        self.btn_pair.pack(fill="x")

        # Status / Feedback label
        self.lbl_feedback = tk.Label(
            body_f,
            text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg_root"],
            fg=COLORS["accent_green"],
            wraplength=520,
            justify="center"
        )
        self.lbl_feedback.pack(pady=(12, 0))

    def _switch_usb_to_wifi(self):
        sel_text = getattr(self, "sel_usb_var", None)
        if not sel_text:
            return
        serial = sel_text.get().split()[0]
        if not serial:
            return

        self.btn_switch.config(state="disabled", text="⏳ Mengaktifkan Mode TCP/IP...")
        self.lbl_feedback.config(text="Memulai mode TCP/IP pada HP...", fg=COLORS["text_secondary"])

        def _worker():
            # 1. Get device IP
            ip = self.adb.get_device_ip(serial)
            if not ip:
                self.after(0, lambda: self.lbl_feedback.config(
                    text="❌ Gagal: HP belum terhubung ke Wi-Fi atau IP tidak ditemukan!",
                    fg=COLORS["accent_red"]
                ))
                self.after(0, lambda: self.btn_switch.config(state="normal", text="⚡ Aktifkan Mode Wi-Fi & Sambungkan"))
                return

            # 2. adb tcpip 5555
            ok, out = self.adb.enable_tcpip(serial, 5555)
            if not ok:
                self.after(0, lambda: self.lbl_feedback.config(
                    text=f"❌ Gagal mengaktifkan port TCP/IP: {out}",
                    fg=COLORS["accent_red"]
                ))
                self.after(0, lambda: self.btn_switch.config(state="normal", text="⚡ Aktifkan Mode Wi-Fi & Sambungkan"))
                return

            time.sleep(1.0)

            # 3. adb connect IP:5555
            self.after(0, lambda: self.lbl_feedback.config(
                text=f"Menyambungkan ke {ip}:5555...",
                fg=COLORS["text_secondary"]
            ))
            ok_c, out_c = self.adb.connect_wireless(ip, 5555)

            if ok_c and ("connected" in out_c.lower() or "already" in out_c.lower()):
                msg = f"🎉 Berhasil terhubung ke {ip}:5555!\nKabel USB sekarang aman dicabut. Layar Wi-Fi akan otomatis muncul."
                self.after(0, lambda: self.lbl_feedback.config(text=msg, fg=COLORS["accent_green"]))
                if self.on_connected:
                    self.on_connected(f"{ip}:5555")
            else:
                msg = f"⚠️ Respon ADB: {out_c}\nPastikan PC dan HP dalam satu jaringan Wi-Fi."
                self.after(0, lambda: self.lbl_feedback.config(text=msg, fg=COLORS["accent_yellow"]))

            self.after(0, lambda: self.btn_switch.config(state="normal", text="⚡ Aktifkan Mode Wi-Fi & Sambungkan"))

        threading.Thread(target=_worker, daemon=True).start()

    def _manual_connect(self):
        ip = self.entry_ip.get().strip()
        port_str = self.entry_port.get().strip() or "5555"

        if not ip or ip == "192.168.1.":
            self.lbl_feedback.config(text="Masukkan alamat IP HP yang valid!", fg=COLORS["accent_red"])
            return

        try:
            port = int(port_str)
        except ValueError:
            self.lbl_feedback.config(text="Port harus berupa angka!", fg=COLORS["accent_red"])
            return

        self.btn_manual.config(state="disabled", text="⏳ Menyambungkan...")
        self.lbl_feedback.config(text=f"Menghubungkan ke {ip}:{port}...", fg=COLORS["text_secondary"])

        def _worker():
            ok, out = self.adb.connect_wireless(ip, port)
            if ok and ("connected" in out.lower() or "already" in out.lower()):
                msg = f"🎉 Berhasil terhubung ke {ip}:{port}!"
                self.after(0, lambda: self.lbl_feedback.config(text=msg, fg=COLORS["accent_green"]))
                if self.on_connected:
                    self.on_connected(f"{ip}:{port}")
            else:
                msg = f"❌ Gagal: {out}\nPeriksa IP, Port, dan pastikan Wi-Fi aktif."
                self.after(0, lambda: self.lbl_feedback.config(text=msg, fg=COLORS["accent_red"]))

            self.after(0, lambda: self.btn_manual.config(state="normal", text="🔌 Hubungkan Nirkabel"))

        threading.Thread(target=_worker, daemon=True).start()

    def _pair_wireless(self):
        addr = self.entry_pair_addr.get().strip()
        code = self.entry_pair_code.get().strip()
        if not addr or ":" not in addr or not code:
            self.lbl_feedback.config(text="Masukkan IP:Port Pairing dan Kode 6-digit!", fg=COLORS["accent_red"])
            return

        ip, port_str = addr.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            self.lbl_feedback.config(text="Port pairing harus angka!", fg=COLORS["accent_red"])
            return

        self.btn_pair.config(state="disabled", text="⏳ Memasangkan...")
        self.lbl_feedback.config(text=f"Memasangkan ke {addr}...", fg=COLORS["text_secondary"])

        def _worker():
            ok, out = self.adb.pair_wireless(ip, port, code)
            if ok and "success" in out.lower():
                msg = f"🎉 Berhasil dipasangkan ke {ip}!\nSekarang lihat 'Alamat IP & Port' di halaman utama Debugging Nirkabel HP,\nmasukkan ke kolom 'Sambung Manual' di atas lalu klik 'Hubungkan Nirkabel'."
                self.after(0, lambda: self.lbl_feedback.config(text=msg, fg=COLORS["accent_green"]))
                self.after(0, lambda: self.entry_ip.delete(0, tk.END) or self.entry_ip.insert(0, ip))
            else:
                msg = f"❌ Gagal Pairing: {out}\nPastikan kode dan port pairing masih aktif di HP."
                self.after(0, lambda: self.lbl_feedback.config(text=msg, fg=COLORS["accent_red"]))

            self.after(0, lambda: self.btn_pair.config(state="normal", text="🤝 Pasangkan (Pair Device)"))

        threading.Thread(target=_worker, daemon=True).start()
