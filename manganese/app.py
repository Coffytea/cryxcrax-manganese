import sys
import os

from manganese.platform_win32 import _detect_windows_dark_mode, _set_process_dpi_awareness

_INITIAL_DARK_MODE = _detect_windows_dark_mode()

os.environ.setdefault(
    'QTWEBENGINE_CHROMIUM_FLAGS',
    '--enable-features=HardwareMediaKeyHandling '
    '--enable-gpu-rasterization '
    '--disk-cache-size=52428800'
)


def _register_mangan_scheme():
    from PyQt6.QtWebEngineCore import QWebEngineUrlScheme

    scheme = QWebEngineUrlScheme(b"mangan")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.LocalScheme
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
        | QWebEngineUrlScheme.Flag.SecureScheme
    )
    QWebEngineUrlScheme.registerScheme(scheme)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    _register_mangan_scheme()

    from manganese.window import TabbedBrowser
    from PyQt6.QtWidgets import QApplication

    _set_process_dpi_awareness()
    app = QApplication(argv)
    url_to_open = argv[1] if len(argv) > 1 else None
    window = TabbedBrowser(url_to_open=url_to_open)
    window.showMaximized()
    return app.exec()
