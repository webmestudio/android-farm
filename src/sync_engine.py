"""Multi-Device Synchronization and Broadcast Engine."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Optional, Dict
from .adb_manager import ADBManager, ADBDevice


class SyncEngine:
    def __init__(self, adb: ADBManager, max_workers: int = 20):
        self.adb = adb
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SyncWorker")
        self.sync_enabled: bool = False
        self.master_serial: Optional[str] = None

    def set_sync(self, enabled: bool, master_serial: Optional[str] = None):
        self.sync_enabled = enabled
        self.master_serial = master_serial

    def broadcast_key(self, devices: List[ADBDevice], keycode: int, exclude_master: bool = False):
        """Broadcasts an Android keycode to all devices in parallel."""
        targets = [d for d in devices if not (exclude_master and d.serial == self.master_serial)]
        futures = [self.executor.submit(self.adb.send_key, d.serial, keycode) for d in targets]
        return futures

    def broadcast_home(self, devices: List[ADBDevice]):
        return self.broadcast_key(devices, 3)

    def broadcast_back(self, devices: List[ADBDevice]):
        return self.broadcast_key(devices, 4)

    def broadcast_recents(self, devices: List[ADBDevice]):
        return self.broadcast_key(devices, 187)

    def broadcast_power(self, devices: List[ADBDevice]):
        return self.broadcast_key(devices, 26)

    def broadcast_screen_off(self, devices: List[ADBDevice]):
        return self.broadcast_key(devices, 223)

    def broadcast_screen_on(self, devices: List[ADBDevice]):
        return self.broadcast_key(devices, 224)

    def broadcast_text(self, devices: List[ADBDevice], text: str, exclude_master: bool = False):
        """Broadcasts typed text to all devices."""
        targets = [d for d in devices if not (exclude_master and d.serial == self.master_serial)]
        futures = [self.executor.submit(self.adb.send_text, d.serial, text) for d in targets]
        return futures

    def broadcast_tap_normalized(
        self,
        devices: List[ADBDevice],
        norm_x: float,
        norm_y: float,
        exclude_master: bool = False
    ):
        """Sends tap event scaled to each device's respective resolution."""
        targets = [d for d in devices if not (exclude_master and d.serial == self.master_serial)]

        def _tap(d: ADBDevice):
            w = d.screen_width if d.screen_width > 0 else 1080
            h = d.screen_height if d.screen_height > 0 else 2400
            px = int(norm_x * w)
            py = int(norm_y * h)
            return self.adb.send_tap(d.serial, px, py)

        futures = [self.executor.submit(_tap, d) for d in targets]
        return futures

    def broadcast_swipe_normalized(
        self,
        devices: List[ADBDevice],
        nx1: float,
        ny1: float,
        nx2: float,
        ny2: float,
        duration_ms: int = 250,
        exclude_master: bool = False
    ):
        """Sends swipe gesture scaled to each device's respective resolution."""
        targets = [d for d in devices if not (exclude_master and d.serial == self.master_serial)]

        def _swipe(d: ADBDevice):
            w = d.screen_width if d.screen_width > 0 else 1080
            h = d.screen_height if d.screen_height > 0 else 2400
            x1 = int(nx1 * w)
            y1 = int(ny1 * h)
            x2 = int(nx2 * w)
            y2 = int(ny2 * h)
            return self.adb.send_swipe(d.serial, x1, y1, x2, y2, duration_ms)

        futures = [self.executor.submit(_swipe, d) for d in targets]
        return futures

    def broadcast_apk_install(
        self,
        devices: List[ADBDevice],
        apk_path: str,
        on_device_done: Optional[Callable[[str, bool, str], None]] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """Installs APK to all devices in parallel with individual callback."""
        def _install(d: ADBDevice):
            ok, msg = self.adb.install_apk(d.serial, apk_path)
            if on_device_done:
                on_device_done(d.serial, ok, msg)
            return (d.serial, ok, msg)

        futures = [self.executor.submit(_install, d) for d in devices]
        results = {}
        for f in as_completed(futures):
            serial, ok, msg = f.result()
            results[serial] = (ok, msg)
        return results

    def broadcast_shell(
        self,
        devices: List[ADBDevice],
        cmd: str,
        on_device_done: Optional[Callable[[str, bool, str], None]] = None
    ) -> Dict[str, Tuple[bool, str]]:
        """Executes a shell command across all devices in parallel."""
        def _exec(d: ADBDevice):
            ok, out = self.adb.run_shell(d.serial, cmd)
            if on_device_done:
                on_device_done(d.serial, ok, out)
            return (d.serial, ok, out)

        futures = [self.executor.submit(_exec, d) for d in devices]
        results = {}
        for f in as_completed(futures):
            serial, ok, out = f.result()
            results[serial] = (ok, out)
        return results

    def broadcast_reboot(self, devices: List[ADBDevice]):
        """Reboots all devices simultaneously."""
        futures = [self.executor.submit(self.adb.reboot, d.serial) for d in devices]
        return futures

    def shutdown(self):
        self.executor.shutdown(wait=False)
