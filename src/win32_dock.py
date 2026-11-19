"""Win32 API utilities for docking and managing embedded scrcpy windows on Windows."""

import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# Win32 Constants
GWL_STYLE = -16
GWL_EXSTYLE = -20

WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_CLIPSIBLINGS = 0x04000000
WS_CLIPCHILDREN = 0x02000000
WS_CAPTION = 0x00C00000
WS_BORDER = 0x00800000
WS_DLGFRAME = 0x00400000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000

WS_EX_DLGMODALFRAME = 0x00000001
WS_EX_WINDOWEDGE = 0x00000100
WS_EX_CLIENTEDGE = 0x00000200
WS_EX_STATICEDGE = 0x00020000

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOREDRAW = 0x0008
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

SW_HIDE = 0
SW_SHOW = 5

# 64-bit safe function prototypes
LONG_PTR = ctypes.c_ssize_t

user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.MoveWindow.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL

GetWindowLong = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
SetWindowLong = getattr(user32, 'SetWindowLongPtrW', user32.SetWindowLongW)

GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLong.restype = LONG_PTR

SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
SetWindowLong.restype = LONG_PTR

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def find_window_by_title(exact_or_prefix: str, timeout: float = 6.0) -> int:
    """Find a window HWND by exact title or matching prefix with a timeout."""
    start = time.time()
    while time.time() - start < timeout:
        # First try exact match
        hwnd = user32.FindWindowW(None, exact_or_prefix)
        if hwnd:
            return hwnd

        # Otherwise enumerate windows and search prefix
        matched_hwnd = 0

        def enum_cb(h, _):
            nonlocal matched_hwnd
            length = user32.GetWindowTextLengthW(h)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h, buff, length + 1)
                title = buff.value
                if title.startswith(exact_or_prefix) or exact_or_prefix in title:
                    matched_hwnd = h
                    return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if matched_hwnd:
            return matched_hwnd

        time.sleep(0.1)

    return 0


def dock_window(child_hwnd: int, parent_hwnd: int, width: int, height: int) -> bool:
    """Embeds child_hwnd into parent_hwnd with proper clipping and sizing."""
    if not child_hwnd or not parent_hwnd:
        return False

    try:
        # 1. Ensure parent container has WS_CLIPCHILDREN | WS_CLIPSIBLINGS
        # so Tkinter canvas never paints over the video stream
        p_style = GetWindowLong(parent_hwnd, GWL_STYLE) & 0xFFFFFFFF
        p_style |= (WS_CLIPCHILDREN | WS_CLIPSIBLINGS)
        p_signed = p_style if p_style < 0x80000000 else p_style - 0x100000000
        SetWindowLong(parent_hwnd, GWL_STYLE, p_signed)

        # 2. Reparent scrcpy borderless window directly into container.
        # DO NOT modify child GWL_STYLE (stripping WS_POPUP breaks Direct3D 11 DXGI SwapChain presentation!)
        user32.SetParent(child_hwnd, parent_hwnd)

        # 3. Position and size to fit container exactly
        user32.MoveWindow(child_hwnd, 0, 0, width, height, True)
        user32.ShowWindow(child_hwnd, SW_SHOW)
        return True
    except Exception as e:
        print(f"[Dock Error] Failed to dock {child_hwnd} into {parent_hwnd}: {e}")
        return False


def resize_docked_window(child_hwnd: int, width: int, height: int) -> bool:
    """Resizes an already docked window to new dimensions."""
    if not child_hwnd:
        return False
    return bool(user32.MoveWindow(child_hwnd, 0, 0, width, height, True))


def undock_or_close(child_hwnd: int) -> None:
    """Safely closes or detaches a docked window."""
    if not child_hwnd:
        return
    WM_CLOSE = 0x0010
    user32.PostMessageW(child_hwnd, WM_CLOSE, 0, 0)
