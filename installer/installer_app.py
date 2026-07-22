import os
import shutil
import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QProgressBar, QCheckBox, QStackedWidget,
)
from PyQt6.QtGui import QFont, QFontDatabase, QPainter, QColor, QLinearGradient, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import install_logic
import win_registration

ACCENT = "#5b8cff"
BG = "#14151a"
PANEL = "#1c1e24"
TEXT = "#f5f5f6"
TEXT_SECONDARY = "#9a9ca3"
BORDER = "#2a2c33"

def _app_base_dir():

    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SOURCE_DIR = os.path.join(_app_base_dir(), "payload")
ICON_PATH = os.path.join(_app_base_dir(), "assets", "cryx.ico")


def _load_syne_font():
    font_path = os.path.join(_app_base_dir(), "assets", "Syne-Bold.ttf")
    if os.path.isfile(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            return families[0]
    else:
        print(f"WARNING: Syne-Bold.ttf not found at {font_path!r}; "
              f"falling back to Segoe UI. Make sure assets/ ships alongside "
              f"the installer exe.", file=sys.stderr)
    return "Segoe UI"


class InstallWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, install_dir, make_desktop_shortcut, make_start_menu_shortcut, register_browser):
        super().__init__()
        self.install_dir = install_dir
        self.make_desktop_shortcut = make_desktop_shortcut
        self.make_start_menu_shortcut = make_start_menu_shortcut
        self.register_browser = register_browser

    @staticmethod
    def _install_uninstaller(uninstaller_path):

        if not getattr(sys, "frozen", False):
            return
        shutil.copy2(os.path.abspath(sys.executable), uninstaller_path)

    def run(self):
        try:
            def on_progress(i, total, name):
                self.progress.emit(i, total, name)

            install_logic.copy_application_files(SOURCE_DIR, self.install_dir, progress_cb=on_progress)

            icon_path = ICON_PATH if os.path.isfile(ICON_PATH) else os.path.join(
                self.install_dir, install_logic.EXE_NAME
            )
            install_logic.create_shortcuts(
                self.install_dir, icon_path,
                desktop=self.make_desktop_shortcut,
                start_menu=self.make_start_menu_shortcut,
            )

            uninstaller_path = os.path.join(self.install_dir, "uninstall.exe")
            self._install_uninstaller(uninstaller_path)
            install_logic.write_uninstall_registration(self.install_dir, uninstaller_path, icon_path)

            if self.register_browser:
                win_registration.register_as_browser(self.install_dir, install_logic.EXE_NAME)

            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class GradientHeader(QWidget):

    def __init__(self, syne_family, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 40, 32, 40)

        title = QLabel("Manganese")
        title.setFont(QFont(syne_family, 22, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        title.setWordWrap(True)

        subtitle = QLabel("")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.75); background: transparent;")

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addStretch()

        version = QLabel(f"v{install_logic.APP_VERSION}")
        version.setFont(QFont("Segoe UI", 9))
        version.setStyleSheet("color: rgba(255,255,255,0.55); background: transparent;")
        layout.addWidget(version)

        self.setLayout(layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#5b8cff"))
        gradient.setColorAt(1, QColor("#8b5bff"))
        painter.fillRect(self.rect(), gradient)
        super().paintEvent(event)


class WelcomePage(QWidget):
    def __init__(self, syne_family, on_next):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 48, 40, 40)
        layout.setSpacing(0)

        heading = QLabel("Welcome to Manganese Setup")
        heading.setFont(QFont(syne_family, 20, QFont.Weight.Bold))
        heading.setStyleSheet(f"color: {TEXT};")
        heading.setWordWrap(True)

        body = QLabel(
            "This will install Manganese on your computer.\n\n"

        )
        body.setFont(QFont("Segoe UI", 10))
        body.setStyleSheet(f"color: {TEXT_SECONDARY};")
        body.setWordWrap(True)

        layout.addWidget(heading)
        layout.addSpacing(18)
        layout.addWidget(body)
        layout.addStretch()

        next_btn = _primary_button("Get started")
        next_btn.clicked.connect(on_next)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(next_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)


class OptionsPage(QWidget):
    def __init__(self, syne_family, on_back, on_install):
        super().__init__()
        self.on_install = on_install
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 48, 40, 40)
        layout.setSpacing(0)

        heading = QLabel("Choose install options")
        heading.setFont(QFont(syne_family, 18, QFont.Weight.Bold))
        heading.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(heading)
        layout.addSpacing(20)

        loc_label = QLabel("Install location")
        loc_label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        loc_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(loc_label)
        layout.addSpacing(6)

        loc_row = QHBoxLayout()
        self.path_input = QLineEdit(install_logic.DEFAULT_INSTALL_DIR)
        self.path_input.setStyleSheet(_input_style())
        browse_btn = QPushButton("Browse\u2026")
        browse_btn.setStyleSheet(_secondary_button_style())
        browse_btn.clicked.connect(self._browse)
        loc_row.addWidget(self.path_input)
        loc_row.addWidget(browse_btn)
        layout.addLayout(loc_row)
        layout.addSpacing(24)

        self.desktop_checkbox = QCheckBox("Create a desktop shortcut")
        self.start_menu_checkbox = QCheckBox("Create a Start Menu shortcut")
        self.register_browser_checkbox = QCheckBox("Register Manganese as a Windows browser")
        for cb in (self.desktop_checkbox, self.start_menu_checkbox, self.register_browser_checkbox):
            cb.setChecked(True)
            cb.setFont(QFont("Segoe UI", 10))
            cb.setStyleSheet(f"color: {TEXT}; spacing: 8px;")
            layout.addWidget(cb)
            layout.addSpacing(10)

        register_note = QLabel(
            "Lets Windows list Manganese under Settings \u203a Default apps, so it can be set as your "
            "default browser for web links and .html files."
        )
        register_note.setFont(QFont("Segoe UI", 8, italic=True))
        register_note.setStyleSheet(f"color: {TEXT_SECONDARY}; margin-left: 26px;")
        register_note.setWordWrap(True)
        layout.addWidget(register_note)

        layout.addStretch()

        btn_row = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(_secondary_button_style())
        back_btn.clicked.connect(on_back)
        install_btn = _primary_button("Install")
        install_btn.clicked.connect(self._install)
        btn_row.addWidget(back_btn)
        btn_row.addStretch()
        btn_row.addWidget(install_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _browse(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose install location", self.path_input.text())
        if chosen:
            self.path_input.setText(os.path.join(chosen, "Manganese"))

    def _install(self):
        self.on_install(
            self.path_input.text().strip() or install_logic.DEFAULT_INSTALL_DIR,
            self.desktop_checkbox.isChecked(),
            self.start_menu_checkbox.isChecked(),
            self.register_browser_checkbox.isChecked(),
        )


class InstallingPage(QWidget):
    def __init__(self, syne_family):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 48, 40, 40)
        layout.setSpacing(0)

        heading = QLabel("Installing Manganese\u2026")
        heading.setFont(QFont(syne_family, 18, QFont.Weight.Bold))
        heading.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(heading)
        layout.addSpacing(24)

        self.status_label = QLabel("Preparing\u2026")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.status_label)
        layout.addSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {BORDER};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {ACCENT};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

        self.setLayout(layout)

    def set_progress(self, i, total, name):
        pct = int((i / total) * 100) if total else 0
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"Copying {name}\u2026")


class FinishPage(QWidget):
    def __init__(self, syne_family, on_finish):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 48, 40, 40)
        layout.setSpacing(0)

        heading = QLabel("Manganese is ready")
        heading.setFont(QFont(syne_family, 20, QFont.Weight.Bold))
        heading.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(heading)
        layout.addSpacing(14)

        body = QLabel("Setup has finished installing Manganese on your computer.")
        body.setFont(QFont("Segoe UI", 10))
        body.setStyleSheet(f"color: {TEXT_SECONDARY};")
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        self.launch_checkbox = QCheckBox("Launch Manganese now")
        self.launch_checkbox.setChecked(True)
        self.launch_checkbox.setFont(QFont("Segoe UI", 10))
        self.launch_checkbox.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(self.launch_checkbox)
        layout.addSpacing(20)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        finish_btn = _primary_button("Finish")
        finish_btn.clicked.connect(lambda: on_finish(self.launch_checkbox.isChecked()))
        btn_row.addWidget(finish_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)


class ErrorPage(QWidget):
    def __init__(self, syne_family, message):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 48, 40, 40)

        heading = QLabel("Installation failed")
        heading.setFont(QFont(syne_family, 18, QFont.Weight.Bold))
        heading.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(heading)
        layout.addSpacing(14)

        body = QLabel(message)
        body.setFont(QFont("Segoe UI", 10))
        body.setStyleSheet(f"color: {TEXT_SECONDARY};")
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        close_btn = _primary_button("Close")
        close_btn.clicked.connect(QApplication.instance().quit)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)


def _primary_button(text):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(38)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {ACCENT};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0 22px;
            font-size: 10.5pt;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: #6f9aff; }}
        QPushButton:pressed {{ background: #4a78e0; }}
    """)
    return btn


def _secondary_button_style():
    return f"""
        QPushButton {{
            background: transparent;
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 0 18px;
            font-size: 10.5pt;
        }}
        QPushButton:hover {{ background: {BORDER}; }}
    """


def _input_style():
    return f"""
        QLineEdit {{
            background: {PANEL};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 10pt;
        }}
        QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
    """


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.syne_family = _load_syne_font()
        self.setWindowTitle("Manganese Setup")
        self.setFixedSize(760, 460)
        if os.path.isfile(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        central = QWidget()
        central.setStyleSheet(f"background: {BG};")
        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.header = GradientHeader(self.syne_family)
        outer.addWidget(self.header)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        central.setLayout(outer)
        self.setCentralWidget(central)

        self.welcome_page = WelcomePage(self.syne_family, self._go_to_options)
        self.options_page = OptionsPage(self.syne_family, self._go_to_welcome, self._start_install)
        self.installing_page = InstallingPage(self.syne_family)

        self.stack.addWidget(self.welcome_page)
        self.stack.addWidget(self.options_page)
        self.stack.addWidget(self.installing_page)

        self._worker = None

    def _go_to_welcome(self):
        self.stack.setCurrentWidget(self.welcome_page)

    def _go_to_options(self):
        self.stack.setCurrentWidget(self.options_page)

    def _start_install(self, install_dir, desktop_shortcut, start_menu_shortcut, register_browser):
        self.stack.setCurrentWidget(self.installing_page)
        self._worker = InstallWorker(install_dir, desktop_shortcut, start_menu_shortcut, register_browser)
        self._worker.progress.connect(self.installing_page.set_progress)
        self._worker.finished_ok.connect(lambda: self._go_to_finish(install_dir))
        self._worker.failed.connect(self._go_to_error)
        self._worker.start()

    def _go_to_finish(self, install_dir):
        finish_page = FinishPage(self.syne_family, lambda launch: self._finish(launch, install_dir))
        self.stack.addWidget(finish_page)
        self.stack.setCurrentWidget(finish_page)

    def _go_to_error(self, message):
        error_page = ErrorPage(self.syne_family, message)
        self.stack.addWidget(error_page)
        self.stack.setCurrentWidget(error_page)

    def _finish(self, launch, install_dir):
        if launch:
            exe_path = os.path.join(install_dir, install_logic.EXE_NAME)
            try:
                os.startfile(exe_path)
            except Exception:
                pass
        self.close()


def main():

    running_as_uninstaller = (
        "--uninstall" in sys.argv
        or os.path.basename(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).lower()
        == "uninstall.exe"
    )
    if running_as_uninstaller:
        from uninstaller import run_uninstall
        return run_uninstall("--quiet" in sys.argv, "--purge-data" in sys.argv)

    if not install_logic.is_running_as_admin():
        install_logic.relaunch_as_admin()
        return

    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
