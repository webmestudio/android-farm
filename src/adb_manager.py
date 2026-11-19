"""ADB Interface Manager for Device Discovery, Control, and Telemetry."""

import subprocess
import re
import time
from typing import List, Dict, Optional, Tuple
from .config import ADB_EXE

# Windows flag to suppress console window popup
NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


class ADBDevice:
    def __init__(self, serial: str, state: str, model: str = "", product: str = ""):
        self.serial = serial
        self.state = state  # 'device', 'offline', 'unauthorized'
        self.model = model or serial
        self.product = product
        self.battery_level: int = -1
        self.battery_temp: float = 0.0
        self.is_charging: bool = False
        self.screen_width: int = 1080
        self.screen_height: int = 2400
        self.os_version: str = ""
        self.brand: str = ""
        self.is_sync_target: bool = True
        self.has_static_info: bool = False

    def __repr__(self):
        return f"<ADBDevice {self.serial} ({self.model}) - Android {self.os_version or '?'} - {self.state}>"


class ADBManager:
    def __init__(self, adb_path: str = ADB_EXE):
        self.adb_path = adb_path

    def _exec(self, args: List[str], timeout: float = 10.0) -> Tuple[bool, str]:
        """Executes an adb command silently and returns (success, stdout/stderr)."""
        cmd = [self.adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=NO_WINDOW
            )
            return (res.returncode == 0, res.stdout.strip())
        except subprocess.TimeoutExpired:
            return (False, "Timeout expired")
        except Exception as e:
            return (False, str(e))

    def get_devices(self) -> List[ADBDevice]:
        """Returns a list of connected devices with model and state info."""
        ok, out = self._exec(["devices", "-l"])
        if not ok or not out:
            return []

        devices = []
        lines = out.splitlines()[1:]  # Skip 'List of devices attached'
        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]

                # Parse model:XXXX
                model = serial
                model_match = re.search(r"model:([^\s]+)", line)
                if model_match:
                    model = model_match.group(1).replace("_", " ")

                product_match = re.search(r"product:([^\s]+)", line)
                product = product_match.group(1) if product_match else ""

                devices.append(ADBDevice(serial, state, model, product))

        return devices

    def update_telemetry(self, device: ADBDevice, update_battery: bool = True) -> None:
        """Fetches battery level, temperature, and screen resolution without blocking."""
        if device.state != "device":
            return

        # 1. Fetch static specs (Screen size, OS version, Brand) ONCE per connection
        if not device.has_static_info:
            ok, out = self._exec(["-s", device.serial, "shell", "wm size; getprop ro.build.version.release; getprop ro.product.brand"], timeout=4.0)
            if ok and out:
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                for line in lines:
                    size_match = re.search(r"(\d+)\s*x\s*(\d+)", line)
                    if size_match:
                        device.screen_width = int(size_match.group(1))
                        device.screen_height = int(size_match.group(2))
                        break
                text_lines = [l for l in lines if "x" not in l and not l.startswith("Physical")]
                if len(text_lines) >= 1:
                    device.os_version = text_lines[0]
                if len(text_lines) >= 2:
                    device.brand = text_lines[1].capitalize()
                device.has_static_info = True

        # 2. Battery Info (only if requested)
        if update_battery:
            ok, out = self._exec(["-s", device.serial, "shell", "dumpsys", "battery"], timeout=4.0)
            if ok and out:
                level_match = re.search(r"level:\s*(\d+)", out)
                if level_match:
                    device.battery_level = int(level_match.group(1))

                temp_match = re.search(r"temperature:\s*(\d+)", out)
                if temp_match:
                    device.battery_temp = round(int(temp_match.group(1)) / 10.0, 1)

                usb_match = re.search(r"(AC|USB|Wireless)\s*powered:\s*true", out, re.IGNORECASE)
                status_match = re.search(r"status:\s*(\d+)", out)
                device.is_charging = bool(usb_match or (status_match and status_match.group(1) in ("2", "5")))

    def send_key(self, serial: str, keycode: int) -> bool:
        """Sends an Android keycode (e.g. 3 for Home, 4 for Back)."""
        ok, _ = self._exec(["-s", serial, "shell", "input", "keyevent", str(keycode)])
        return ok

    def key_home(self, serial: str) -> bool:
        return self.send_key(serial, 3)

    def key_back(self, serial: str) -> bool:
        return self.send_key(serial, 4)

    def key_recents(self, serial: str) -> bool:
        return self.send_key(serial, 187)

    def key_power(self, serial: str) -> bool:
        return self.send_key(serial, 26)

    def key_volume_up(self, serial: str) -> bool:
        return self.send_key(serial, 24)

    def key_volume_down(self, serial: str) -> bool:
        return self.send_key(serial, 25)

    def turn_screen_off(self, serial: str) -> bool:
        """Puts screen to sleep (KEYCODE_SLEEP = 223)."""
        return self.send_key(serial, 223)

    def turn_screen_on(self, serial: str) -> bool:
        """Wakes screen up (KEYCODE_WAKEUP = 224)."""
        return self.send_key(serial, 224)

    def ensure_screen_awake(self, serial: str) -> bool:
        """Ensures the device screen is powered on, unlocked, and stays awake."""
        # Configure device to stay awake while charging / USB connected (Phone Farm mode)
        self._exec(["-s", serial, "shell", "svc", "power", "stayon", "true"])
        self._exec(["-s", serial, "shell", "settings", "put", "system", "screen_off_timeout", "1800000"])
        ok, out = self._exec(["-s", serial, "shell", "dumpsys", "power"])
        if ok and ("mWakefulness=Asleep" in out or "mWakefulness=Dozing" in out):
            self.turn_screen_on(serial)
            self._exec(["-s", serial, "shell", "wm", "dismiss-keyguard"])
            self.send_key(serial, 82)
            time.sleep(0.3)
            return True
        elif not ok:
            self.turn_screen_on(serial)
        return False

    def send_tap(self, serial: str, x: int, y: int) -> bool:
        """Sends touch tap event to specific coordinates."""
        ok, _ = self._exec(["-s", serial, "shell", "input", "tap", str(x), str(y)])
        return ok

    def send_swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> bool:
        """Sends swipe gesture."""
        ok, _ = self._exec(["-s", serial, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        return ok

    def send_text(self, serial: str, text: str) -> bool:
        """Sends typed text to device input focus."""
        # Spaces need to be replaced with %s for adb input text
        escaped = text.replace(" ", "%s").replace("&", "\\&").replace('"', '\\"')
        ok, _ = self._exec(["-s", serial, "shell", "input", "text", escaped])
        return ok

    def install_apk(self, serial: str, apk_path: str) -> Tuple[bool, str]:
        """Installs an APK file to the device."""
        return self._exec(["-s", serial, "install", "-r", apk_path], timeout=60.0)

    def reboot(self, serial: str) -> bool:
        """Reboots device."""
        ok, _ = self._exec(["-s", serial, "reboot"])
        return ok

    def run_shell(self, serial: str, cmd: str) -> Tuple[bool, str]:
        """Executes a custom shell command."""
        return self._exec(["-s", serial, "shell", cmd])

    def open_url(self, serial: str, url: str) -> bool:
        """Opens URL in device browser."""
        ok, _ = self._exec(["-s", serial, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
        return ok

    def get_device_ip(self, serial: str) -> Optional[str]:
        """Fetches device local Wi-Fi IPv4 address."""
        ok, out = self._exec(["-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"])
        if ok and out:
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                return m.group(1)

        # Fallback to ip route or getprop
        ok, out = self._exec(["-s", serial, "shell", "ip", "route"])
        if ok and out:
            m = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                return m.group(1)
        return None

    def enable_tcpip(self, serial: str, port: int = 5555) -> Tuple[bool, str]:
        """Switches device ADB daemon to TCP/IP listening on specified port."""
        return self._exec(["-s", serial, "tcpip", str(port)])

    def connect_wireless(self, ip: str, port: int = 5555) -> Tuple[bool, str]:
        """Connects to a device over Wi-Fi TCP/IP."""
        target = f"{ip.strip()}:{port}"
        return self._exec(["connect", target], timeout=15.0)

    def pair_wireless(self, ip: str, port: int, pairing_code: str) -> Tuple[bool, str]:
        """Pairs with a device over Android 11+ wireless debugging."""
        target = f"{ip.strip()}:{port}"
        return self._exec(["pair", target, str(pairing_code).strip()], timeout=15.0)

    def disconnect_wireless(self, target: str) -> Tuple[bool, str]:
        """Disconnects wireless ADB device."""
        return self._exec(["disconnect", target.strip()])
