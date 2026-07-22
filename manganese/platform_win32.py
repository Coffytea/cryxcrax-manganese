import sys
import ctypes
from ctypes import c_int, c_long, c_uint, c_void_p, windll, wintypes


def _detect_windows_dark_mode():
    if sys.platform != "win32":
        return True
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return True


IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    WM_NCCALCSIZE = 0x0083
    WM_NCHITTEST = 0x0084
    WM_GETMINMAXINFO = 0x0024
    WM_SIZE = 0x0005
    SIZE_MAXIMIZED = 2
    WM_DWMCOMPOSITIONCHANGED = 0x031E
    WM_DPICHANGED = 0x02E0
    WM_NCLBUTTONDOWN = 0x00A1
    WM_NCLBUTTONUP = 0x00A2
    WM_NCLBUTTONDBLCLK = 0x00A3
    WM_SETTINGCHANGE = 0x001A

    HTCLIENT = 1
    HTCAPTION = 2
    HTMINBUTTON = 8
    HTMAXBUTTON = 9
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17
    HTCLOSE = 20

    SW_RESTORE = 9
    SW_MAXIMIZE = 3

    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_CAPTION = 0x00C00000
    WS_SYSMENU = 0x00080000
    WS_THICKFRAME = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000

    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    SWP_NOACTIVATE = 0x0010

    MONITOR_DEFAULTTONEAREST = 0x00000002
    SM_CXFRAME = 32
    SM_CYFRAME = 33
    SM_CXPADDEDBORDER = 92

    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWA_BORDER_COLOR = 34
    DWMWA_TEXT_COLOR = 36
    DWMWCP_ROUND = 2
    DWMWCP_DONOTROUND = 1
    DWMWA_COLOR_NONE = 0xFFFFFFFE
    DWMWA_NCRENDERING_POLICY = 2
    DWMNCRP_ENABLED = 2

    class POINT(ctypes.Structure):
        _fields_ = [("x", c_long), ("y", c_long)]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", c_long),
            ("top", c_long),
            ("right", c_long),
            ("bottom", c_long),
        ]

    class MINMAXINFO(ctypes.Structure):
        _fields_ = [
            ("ptReserved", POINT),
            ("ptMaxSize", POINT),
            ("ptMaxPosition", POINT),
            ("ptMinTrackSize", POINT),
            ("ptMaxTrackSize", POINT),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    class NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [
            ("rgrc", RECT * 3),
            ("lppos", c_void_p),
        ]

    class MARGINS(ctypes.Structure):
        _fields_ = [
            ("cxLeftWidth", c_int),
            ("cxRightWidth", c_int),
            ("cyTopHeight", c_int),
            ("cyBottomHeight", c_int),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

    if sys.maxsize > 2 ** 32:
        GetWindowLongPtr = user32.GetWindowLongPtrW
        SetWindowLongPtr = user32.SetWindowLongPtrW
    else:
        GetWindowLongPtr = user32.GetWindowLongW
        SetWindowLongPtr = user32.SetWindowLongW
    GetWindowLongPtr.argtypes = [wintypes.HWND, c_int]
    GetWindowLongPtr.restype = ctypes.c_ssize_t
    SetWindowLongPtr.argtypes = [wintypes.HWND, c_int, ctypes.c_ssize_t]
    SetWindowLongPtr.restype = ctypes.c_ssize_t
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        c_int,
        c_int,
        c_int,
        c_int,
        c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.IsZoomed.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.ReleaseCapture.argtypes = []
    user32.ReleaseCapture.restype = wintypes.BOOL
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = wintypes.LPARAM

    try:
        user32.GetDpiForWindow.argtypes = [wintypes.HWND]
        user32.GetDpiForWindow.restype = c_uint
        user32.GetSystemMetricsForDpi.argtypes = [c_int, c_uint]
        user32.GetSystemMetricsForDpi.restype = c_int
    except AttributeError:
        pass

    try:
        user32.AdjustWindowRectExForDpi.argtypes = [
            ctypes.POINTER(RECT), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD, c_uint,
        ]
        user32.AdjustWindowRectExForDpi.restype = wintypes.BOOL
    except AttributeError:
        pass
    user32.AdjustWindowRectEx.argtypes = [
        ctypes.POINTER(RECT), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
    ]
    user32.AdjustWindowRectEx.restype = wintypes.BOOL

    dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, c_void_p, wintypes.DWORD]
    dwmapi.DwmSetWindowAttribute.restype = c_long
    dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(MARGINS)]
    dwmapi.DwmExtendFrameIntoClientArea.restype = c_long

    def _signed_word(value):
        value &= 0xFFFF
        return value - 0x10000 if value & 0x8000 else value

    def _get_x_lparam(lparam):
        return _signed_word(int(lparam))

    def _get_y_lparam(lparam):
        return _signed_word(int(lparam) >> 16)

    def _set_process_dpi_awareness():
        try:
            user32.SetProcessDpiAwarenessContext(c_void_p(-4))
            return
        except Exception:
            pass
        try:
            windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
else:
    def _set_process_dpi_awareness():
        pass
