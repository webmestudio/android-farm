"""Scrcpy Instance Manager for Spawning, Monitoring, and Docking."""

import subprocess
import threading
import time
from typing import Dict, Optional, Callable
from .config import SCRCPY_EXE, BIN_DIR, QUALITY_PRESETS, DEFAULT_PRESET
from .win32_dock import find_window_by_title, dock_window, resize_docked_window

NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


class ScrcpyInstance:
    def __init__(self, serial: str, parent_hwnd: int, title: str):
        self.serial = serial
        self.parent_hwnd = parent_hwnd
        self.title = title
        self.process: Optional[subprocess.Popen] = None
        self.hwnd: int = 0
        self.is_docked: bool = False
        self.is_running: bool = False


class ScrcpyManager:
    def __init__(self, scrcpy_path: str = SCRCPY_EXE):
        self.scrcpy_path = scrcpy_path
        self.instances: Dict[str, ScrcpyInstance] = {}
        self.preset_name: str = DEFAULT_PRESET
        self._lock = threading.Lock()
        self.kill_all_lingering()

    def kill_all_lingering(self):
        """Kills any orphaned scrcpy processes from previous ungraceful exits."""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "scrcpy.exe"], capture_output=True, creationflags=NO_WINDOW)
        except Exception:
            pass

    def set_preset(self, preset_name: str):
        if preset_name in QUALITY_PRESETS:
            self.preset_name = preset_name

    def start_device(
        self,
        serial: str,
        parent_hwnd: int,
        width: int,
        height: int,
        on_docked: Optional[Callable[[str, int], None]] = None,
        on_error: Optional[Callable[[str, str], None]] = None
    ) -> bool:
        """Starts a scrcpy process for a device and docks it into parent_hwnd asynchronously."""
        with self._lock:
            if serial in self.instances and self.instances[serial].is_running:
                # Already running
                return True

            title = f"farm_scrcpy_{serial}"
            instance = ScrcpyInstance(serial, parent_hwnd, title)
            self.instances[serial] = instance

        preset = QUALITY_PRESETS[self.preset_name]

        cmd = [
            self.scrcpy_path,
            f"--serial={serial}",
            f"--window-title={title}",
            "--window-borderless",
            "--no-audio",
            f"--max-size={preset['max_size']}",
            f"--max-fps={preset['max_fps']}",
            f"--video-bit-rate={preset['bitrate']}",
        ]

        try:
            # Set working directory to scrcpy's bin directory so it finds all DLLs and scrcpy-server
            bin_dir = str(BIN_DIR)
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=bin_dir,
                creationflags=NO_WINDOW
            )
            instance.process = p
            instance.is_running = True
        except Exception as e:
            instance.is_running = False
            if on_error:
                on_error(serial, f"Failed to spawn scrcpy: {e}")
            return False

        # Start background thread to await window creation and dock
        def _dock_worker():
            start_time = time.time()
            hwnd = 0
            while time.time() - start_time < 15.0:
                # Check if process died
                poll = instance.process.poll()
                if poll is not None:
                    err_bytes = instance.process.stderr.read() if instance.process.stderr else b""
                    err_msg = err_bytes.decode("utf-8", errors="ignore").strip()
                    instance.is_running = False
                    if on_error:
                        on_error(serial, f"Display crash ({poll}): {err_msg[:60] if err_msg else 'Unknown error'}")
                    return

                hwnd = find_window_by_title(title, timeout=0.4)
                if hwnd:
                    break
                time.sleep(0.1)

            if not hwnd:
                if on_error:
                    on_error(serial, "Window timeout - display window did not appear")
                return

            instance.hwnd = hwnd

            # Perform the Win32 reparenting/docking
            success = dock_window(hwnd, parent_hwnd, width, height)
            if success:
                instance.is_docked = True
                if on_docked:
                    on_docked(serial, hwnd)
            else:
                if on_error:
                    on_error(serial, "Failed to dock display window")

        threading.Thread(target=_dock_worker, daemon=True).start()
        return True

    def resize_device(self, serial: str, width: int, height: int) -> bool:
        """Resizes the docked window for a specific device."""
        with self._lock:
            inst = self.instances.get(serial)
            if inst and inst.hwnd and inst.is_docked:
                return resize_docked_window(inst.hwnd, width, height)
        return False

    def resize_all(self, width: int, height: int):
        """Resizes all currently docked windows to new dimensions."""
        with self._lock:
            for inst in self.instances.values():
                if inst.hwnd and inst.is_docked:
                    resize_docked_window(inst.hwnd, width, height)

    def stop_device(self, serial: str):
        """Terminates scrcpy process for a device."""
        with self._lock:
            inst = self.instances.pop(serial, None)

        if inst and inst.process:
            try:
                inst.process.terminate()
                inst.process.wait(timeout=1.0)
            except Exception:
                try:
                    inst.process.kill()
                except Exception:
                    pass
            inst.is_running = False

    def stop_all(self):
        """Stops all running scrcpy processes."""
        with self._lock:
            serials = list(self.instances.keys())

        for s in serials:
            self.stop_device(s)
