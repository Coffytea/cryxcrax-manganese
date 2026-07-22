import os
import json
import ctypes
import urllib.parse
import urllib.request
from ctypes import byref, c_int, c_uint, sizeof, wintypes

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QTabWidget, QWidget,
    QVBoxLayout, QMenu, QToolButton, QMessageBox, QSplitter, QWidgetAction,
    QLabel, QHBoxLayout, QSlider, QFileDialog, QSizePolicy, QTabBar,
)
from PyQt6.QtGui import QAction, QKeySequence, QColor, QGuiApplication
from PyQt6.QtCore import (
    QTimer, QUrl, Qt, QPoint, QEvent, QSize,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

try:
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
    PRINT_SUPPORT_AVAILABLE = True
except ImportError:
    PRINT_SUPPORT_AVAILABLE = False
try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from manganese.platform_win32 import *
from manganese.platform_win32 import _detect_windows_dark_mode, _get_x_lparam, _get_y_lparam

from manganese.theming import THEMES, create_vector_icon
from manganese.pages import (
    NEW_TAB_URL, MANGAN_SETTINGS_URL, MANGAN_DOWNLOADS_URL, MANGAN_HISTORY_URL,
)
from manganese.pages.new_tab import new_tab_html, background_to_data_uri
from manganese.pages.internal_pages import (
    internal_page_shell, build_settings_page, build_downloads_page, build_history_page,
    build_site_data_page,
)
from manganese.widgets.tab_title import TabTitleLabel
from manganese.widgets.find_bar import FindLineEdit
from manganese.widgets.draggable import DraggableToolBar, DraggableTabBar
from manganese.widgets.browser_view import BrowserView
from manganese.downloads import DownloadItem
from manganese.url_scheme import ManganUrlSchemeHandler
from manganese.shortcuts import GlobalShortcutFilter
from manganese.tab_suspension import TabSuspender
from manganese import window_registry
from manganese.shared_profile import (
    get_shared_profile, get_shared_cookie_tracker,
    get_shared_history_store, get_shared_prefs,
    get_mangan_scheme_handler, set_mangan_scheme_handler,
    get_shared_downloads_list, is_download_signal_connected, mark_download_signal_connected,
)


class TabbedBrowser(QMainWindow):
    def __init__(self, url_to_open=None):
        super().__init__()
        window_registry.register(self)
        self._native_frame_ready = False
        self._toggle_maximize_pending = False
        self._last_dpi = 96
        self.dark_mode = self._detect_dark_mode()
        self._themed_icon_widgets = []
        self._tab_close_buttons = []
        self._tab_splitters = []
        self._tab_devtools = []
        self.history_store = get_shared_history_store()
        self.prefs = get_shared_prefs()
        self.tab_suspender = TabSuspender(
            is_internal_url=self._is_internal_page_url,
            enabled=self.prefs.get_tab_suspension_enabled(),
        )
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_theme_changed)
        except Exception:
            pass
        self.setWindowTitle("Manganese")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(1024, 768)
        self.url_to_open = url_to_open
        
        self.gpu_profile = get_shared_profile(self)
        self.cookie_tracker = get_shared_cookie_tracker()
        if get_mangan_scheme_handler() is None:
            handler = ManganUrlSchemeHandler(self, self)
            set_mangan_scheme_handler(handler)
            self.gpu_profile.installUrlSchemeHandler(b"mangan", handler)
        
        self.home_page = self.url_to_open if self.url_to_open else "https://www.google.com"
        
        self.downloads_list = get_shared_downloads_list()

        self._shortcut_map = {}


        self.tabs = QTabWidget()
        self.tabs.setTabBar(DraggableTabBar(self))
        self.tabs.setStyleSheet(self._tabbar_stylesheet())
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.tabBar().setExpanding(False)

        central_container = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.find_bar = self._create_find_bar()
        central_layout.addWidget(self.find_bar)
        central_layout.addWidget(self.tabs)
        central_container.setLayout(central_layout)
        self.setCentralWidget(central_container)

        nav = DraggableToolBar()
        self.nav = nav
        nav.parent_window = self
        nav.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        nav.setContentsMargins(8, 0, 0, 0)
        nav.setMovable(False)
        nav.setFloatable(False)
        nav.setFixedHeight(40)
        nav.setIconSize(QSize(19, 19))
        nav.setStyleSheet(self._toolbar_stylesheet())
        self.addToolBar(nav)
        nav.layout().setContentsMargins(0, 0, 0, 0)
        nav.layout().setSpacing(3)

        back_btn = QAction(self._icon("back"), "Back", self)
        forward_btn = QAction(self._icon("forward"), "Forward", self)
        refresh_btn = QAction(self._icon("refresh"), "Reload", self)
        refresh_btn.setShortcut(QKeySequence("F5"))
        new_tab_btn = QAction(self._icon("new_tab"), "New Tab", self)
        new_tab_btn.setShortcut(QKeySequence("Ctrl+T"))
        self._themed_icon_widgets.extend([
            (back_btn, "back", QSize(20, 20), False),
            (forward_btn, "forward", QSize(20, 20), False),
            (refresh_btn, "refresh", QSize(20, 20), False),
            (new_tab_btn, "new_tab", QSize(20, 20), False),
        ])

        self.downloads_btn = QToolButton()
        self.downloads_btn.setIcon(self._icon("downloads"))
        self._themed_icon_widgets.append((self.downloads_btn, "downloads", QSize(20, 20), False))
        self.downloads_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.downloads_btn.setMinimumWidth(40)
        downloads_menu = QMenu()
        downloads_menu.setStyleSheet(self._chrome_menu_stylesheet())
        self.downloads_btn.setMenu(downloads_menu)
        self.downloads_menu = downloads_menu
        nav.addWidget(self.downloads_btn)

        settings_btn = QToolButton()
        settings_btn.setIcon(self._icon("settings"))
        self._themed_icon_widgets.append((settings_btn, "settings", QSize(20, 20), False))
        settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        settings_btn.setMinimumWidth(40)
        nav.addWidget(settings_btn)

        nav.addAction(back_btn)
        nav.addAction(forward_btn)
        nav.addAction(refresh_btn)
        nav.addAction(new_tab_btn)
        
        back_btn.triggered.connect(self.back)
        forward_btn.triggered.connect(self.forward)
        refresh_btn.triggered.connect(self.reload)
        new_tab_btn.triggered.connect(self.add_tab)

        settings_menu = QMenu()
        settings_btn.setMenu(settings_menu)
        self.settings_menu = settings_menu
        settings_menu.setStyleSheet(self._chrome_menu_stylesheet())

        action_new_tab_menu = settings_menu.addAction(self._icon("new_tab"), "New tab")
        action_new_tab_menu.setShortcut(QKeySequence("Ctrl+T"))
        action_new_tab_menu.triggered.connect(lambda: self.add_tab())
        self._themed_icon_widgets.append((action_new_tab_menu, "new_tab", QSize(18, 18), False))

        settings_menu.addSeparator()

        self.zoom_row_widget = self._create_zoom_row()
        zoom_row_action = QWidgetAction(self)
        zoom_row_action.setDefaultWidget(self.zoom_row_widget)
        settings_menu.addAction(zoom_row_action)

        settings_menu.addSeparator()

        self.volume_boost = 100
        self.volume_row_widget = self._create_volume_row()
        volume_row_action = QWidgetAction(self)
        volume_row_action.setDefaultWidget(self.volume_row_widget)
        settings_menu.addAction(volume_row_action)

        settings_menu.addSeparator()

        action_print = settings_menu.addAction("Print\u2026")
        action_print.setShortcut(QKeySequence("Ctrl+P"))
        action_print.triggered.connect(self.print_page)

        action_find_menu = settings_menu.addAction("Find in page")
        action_find_menu.setShortcut(QKeySequence("Ctrl+F"))
        action_find_menu.triggered.connect(self.open_find_bar)

        settings_menu.addSeparator()

        action_open_file = settings_menu.addAction("Open File\u2026")
        action_open_file.triggered.connect(self.open_file_dialog)

        action_history_menu = settings_menu.addAction("History")
        action_history_menu.setShortcut(QKeySequence("Ctrl+H"))
        action_history_menu.triggered.connect(lambda: self.add_tab(QUrl(MANGAN_HISTORY_URL), "History"))

        action_downloads_menu = settings_menu.addAction("Downloads")
        action_downloads_menu.setShortcut(QKeySequence("Ctrl+J"))
        action_downloads_menu.triggered.connect(lambda: self.add_tab(QUrl(MANGAN_DOWNLOADS_URL), "Downloads"))

        settings_menu.addSeparator()

        action_settings = settings_menu.addAction("Settings")
        action_settings.triggered.connect(lambda: self.add_tab(QUrl(MANGAN_SETTINGS_URL), "Settings"))

        self.url_bar = QLineEdit()
        self.url_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.url_bar.setPlaceholderText("Search or enter address")
        nav.addWidget(self.url_bar)


        self.window_controls = QWidget()
        self.window_controls.setObjectName("windowControlsContainer")
        self.window_controls.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)

        self.minimize_btn = QToolButton()
        self.maximize_btn = QToolButton()
        self.close_btn = QToolButton()

        self.minimize_btn.setObjectName("minimizeButton")
        self.maximize_btn.setObjectName("maximizeButton")
        self.close_btn.setObjectName("closeButton")

        self.minimize_btn.setIcon(self._icon("minimize"))
        self.maximize_btn.setIcon(self._icon("maximize"))
        self.close_btn.setIcon(self._icon("close"))
        self._themed_icon_widgets.append((self.minimize_btn, "minimize", QSize(20, 20), False))
        self._themed_icon_widgets.append((self.close_btn, "close", QSize(20, 20), False))

        for btn in [self.minimize_btn, self.maximize_btn, self.close_btn]:
            btn.setFixedWidth(46)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
            btn.setIconSize(QSize(20, 20))

        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.close)

        controls_layout.addWidget(self.minimize_btn)
        controls_layout.addWidget(self.maximize_btn)
        controls_layout.addWidget(self.close_btn)
        self.window_controls.setLayout(controls_layout)
        self.window_controls.setFixedHeight(40)

        nav.addWidget(self.window_controls)

        if self.url_to_open:
            self.add_tab(QUrl(self.url_to_open), "New Tab")
        else:
            self.add_tab()
        self.tabs.currentChanged.connect(self._on_current_tab_changed_suspension)
        self.tabs.currentChanged.connect(self.update_url_bar)
        self.tabs.currentChanged.connect(self._update_tab_colors)
        self.tabs.currentChanged.connect(self._update_zoom_label)

        self._shortcut_map.update({
            "Ctrl+T": lambda: self.add_tab(),
            "Ctrl+W": self.close_current_tab,
            "F5": self.reload,
            "Ctrl+R": self.reload,
            "F12": self.toggle_devtools,
            "Ctrl+Tab": self.next_tab,
            "Ctrl+Shift+Tab": self.previous_tab,
            "Ctrl+L": self.focus_url_bar,
            "Alt+D": self.focus_url_bar,
            "Ctrl+F": self.open_find_bar,
            "Ctrl+P": self.print_page,
            "F11": self.toggle_fullscreen,
            "Ctrl+H": lambda: self.add_tab(QUrl(MANGAN_HISTORY_URL), "History"),
            "Ctrl+J": lambda: self.add_tab(QUrl(MANGAN_DOWNLOADS_URL), "Downloads"),
            "Ctrl+=": self.zoom_in,
            "Ctrl++": self.zoom_in,
            "Ctrl+-": self.zoom_out,
            "Ctrl+0": self.zoom_reset,
        })
        self._shortcut_filter = GlobalShortcutFilter(self)
        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.installEventFilter(self._shortcut_filter)

        action_devtools = QAction("Toggle DevTools", self)
        action_devtools.setShortcut(QKeySequence("F12"))
        action_devtools.triggered.connect(self.toggle_devtools)
        self.addAction(action_devtools)

        action_next_tab = QAction("Next Tab", self)
        action_next_tab.setShortcut(QKeySequence("Ctrl+Tab"))
        action_next_tab.triggered.connect(self.next_tab)
        self.addAction(action_next_tab)

        action_prev_tab = QAction("Previous Tab", self)
        action_prev_tab.setShortcut(QKeySequence("Ctrl+Shift+Tab"))
        action_prev_tab.triggered.connect(self.previous_tab)
        self.addAction(action_prev_tab)

        action_focus_url = QAction("Focus Address Bar", self)
        action_focus_url.setShortcut(QKeySequence("Ctrl+L"))
        action_focus_url.triggered.connect(self.focus_url_bar)
        self.addAction(action_focus_url)

        action_focus_url_alt = QAction("Focus Address Bar (Alt+D)", self)
        action_focus_url_alt.setShortcut(QKeySequence("Alt+D"))
        action_focus_url_alt.triggered.connect(self.focus_url_bar)
        self.addAction(action_focus_url_alt)


        action_fullscreen = QAction("Toggle Fullscreen", self)
        action_fullscreen.setShortcut(QKeySequence("F11"))
        action_fullscreen.triggered.connect(self.toggle_fullscreen)
        self.addAction(action_fullscreen)
        
        QTimer.singleShot(500, self.update_url_bar)
        QTimer.singleShot(0, self._ensure_native_frame)
        QTimer.singleShot(0, lambda: self.refresh_theme(self.dark_mode))

    def showEvent(self, event):
        super().showEvent(event)
        self._ensure_native_frame()
        self._update_maximize_button()

    def closeEvent(self, event):
        window_registry.unregister(self)
        super().closeEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_maximize_button()
            if IS_WINDOWS and self.winId():
                QTimer.singleShot(0, lambda: self._apply_dwm_attributes(int(self.winId())))


    def _detect_dark_mode(self):
        try:
            hints = QGuiApplication.styleHints()
            scheme = hints.colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                return True
            if scheme == Qt.ColorScheme.Light:
                return False
        except Exception:
            pass
        return _detect_windows_dark_mode()

    def _on_system_theme_changed(self, *args):
        QTimer.singleShot(0, self.refresh_theme)

    def _theme(self):
        base = THEMES["dark"] if self.dark_mode else THEMES["light"]
        accent = self.prefs.get_accent_color(self.dark_mode)
        if accent and accent != base["accent"]:
            themed = dict(base)
            themed["accent"] = accent
            themed["urlbar_focus_border"] = accent
            return themed
        return base

    def _icon(self, name, size=QSize(20, 20), bright=False):
        t = self._theme()
        color = t["icon_color_bright"] if bright else t["icon_color"]
        return create_vector_icon(name, size=size, color=QColor(color))

    def _new_tab_html(self):
        return new_tab_html(
            self.dark_mode, self.browserengine, self.prefs.get_new_tab_background(),
            self.prefs.get_accent_color(self.dark_mode),
        )

    def _push_new_tab_search_engine(self):
        prefix_json = json.dumps(self.browserengine)
        for browser in self._iter_browsers():
            try:
                if browser.url().toString() == NEW_TAB_URL:
                    browser.page().runJavaScript("window.__mgSearchPrefix = %s;" % prefix_json)
            except RuntimeError:
                pass

    def _toolbar_stylesheet(self):
        t = self._theme()
        return f"""
            QToolBar {{
                background: {t['toolbar_bg']};
                border: none;
                border-bottom: 1px solid {t['toolbar_border']};
                spacing: 3px;
                margin: 0px;
                padding: 0px;
            }}
            QToolBar QToolButton {{
                margin-top: 2px;
                margin-bottom: 2px;
                background: transparent;
                border: none;
                border-radius: 7px;
                padding: 6px;
                color: {t['icon_color']};
            }}
            QToolBar QToolButton:hover {{
                background: {t['button_hover']};
                color: {t['icon_color_bright']};
            }}
            QToolBar QToolButton:pressed {{
                background: {t['button_pressed']};
            }}
            /* Hide the little dropdown-arrow indicator Qt draws on any
               QToolButton with a menu attached (downloads/settings) --
               requested removal of the "little down arrows". */
            QToolBar QToolButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QToolBar QLineEdit {{
                margin-top: 4px;
                margin-bottom: 4px;
            }}
            QWidget#windowControlsContainer {{
                background: transparent;
                margin: 0px;
                padding: 0px;
            }}
            QToolBar QToolButton#minimizeButton,
            QToolBar QToolButton#maximizeButton,
            QToolBar QToolButton#closeButton {{
                margin: 0px;
                padding: 0px;
                border-radius: 0px;
                background: transparent;
            }}
            QToolBar QToolButton#minimizeButton:hover,
            QToolBar QToolButton#maximizeButton:hover,
            QToolBar QToolButton#closeButton:hover {{
                background: {t['window_controls_hover']};
            }}
            QToolBar QToolButton#minimizeButton:pressed,
            QToolBar QToolButton#maximizeButton:pressed,
            QToolBar QToolButton#closeButton:pressed {{
                background: {t['window_controls_pressed']};
            }}
        """

    def _tabbar_stylesheet(self):
        t = self._theme()
        return f"""
            QTabBar {{
                background: {t['tabbar_bg']};
            }}
            QTabBar::tab {{
                background: {t['tab_bg']};
                color: {t['tab_text']};
                padding: 8px 18px;
                margin-right: -2px;
                margin-left: 4px;
                margin-top: 4px;
                border: 1px solid transparent;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 12.5px;
                font-family: 'Segoe UI';
                min-width: 90px;
                max-width: 220px;
            }}
            QTabBar::tab:selected {{
                background: {t['tab_selected_bg']};
                color: {t['tab_selected_text']};
                border: 1px solid {t['tab_selected_border']};
                border-bottom: 2px solid {t['accent']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {t['tab_hover_bg']};
                color: {t['tab_hover_text']};
            }}
            QTabBar::tab:!selected {{
                margin-top: 6px;
            }}
        """

    def _app_stylesheet(self):
        t = self._theme()
        return f"""
            QMainWindow {{ background-color: {t['window_bg']}; }}
            QToolBar {{ background-color: {t['toolbar_bg']}; spacing: 3px; padding: 4px; border: none; }}
            QLineEdit {{
                background: {t['urlbar_bg']};
                color: {t['urlbar_text']};
                border: 1px solid {t['urlbar_border']};
                padding: 7px 12px;
                border-radius: 8px;
                font-size: 13px;
                selection-background-color: {t['accent']};
            }}
            QLineEdit:focus {{ border: 1px solid {t['urlbar_focus_border']}; background: {t['urlbar_focus_bg']}; }}
            QLineEdit::placeholder {{ color: {t['urlbar_placeholder']}; }}
            QTabWidget::pane {{ border: none; background: {t['window_bg']}; }}
            QMenu {{
                background-color: {t['menu_bg']};
                color: {t['menu_text']};
                border: 1px solid {t['menu_border']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {t['menu_item_hover_bg']};
                color: {t['menu_item_hover_text']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t['menu_separator']};
                margin: 6px 4px;
            }}
            QToolTip {{
                background-color: {t['tooltip_bg']};
                color: {t['tooltip_text']};
                border: 1px solid {t['tooltip_border']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """

    def _chrome_menu_stylesheet(self):
        t = self._theme()
        return f"""
            QMenu {{
                background-color: {t['menu_bg']};
                color: {t['menu_text']};
                border: 1px solid {t['menu_border']};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 220px;
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background-color: {t['menu_item_hover_bg']};
                color: {t['menu_item_hover_text']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t['menu_separator']};
                margin: 6px 4px;
            }}
            QMenu::right-arrow {{
                width: 10px;
                height: 10px;
            }}
            QMenu::indicator {{
                width: 0px;
            }}
        """

    def _tab_close_button_stylesheet(self):
        t = self._theme()
        return f"""
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding-top: 1px;
            }}
            QToolButton:hover {{
                background: {t['close_btn_hover']};
            }}
            QToolButton:pressed {{
                background: {t['close_btn_pressed']};
            }}
        """

    def _splitter_stylesheet(self):
        t = self._theme()
        return f"""
            QSplitter::handle {{
                background: {t['toolbar_border']};
            }}
            QSplitter::handle:hover {{
                background: {t['accent']};
            }}
        """

    def _devtools_theme_js(self):
        theme = "dark" if self.dark_mode else "light"
        dark_bool = "true" if self.dark_mode else "false"
        return ("""(function(){
            try{
                var val = '"%s"';
                if (window.localStorage && localStorage.getItem("uiTheme") !== val) {
                    localStorage.setItem("uiTheme", val);
                }
            }catch(e){}
            try{
                var dark = %s;
                if (document.documentElement) {
                    document.documentElement.classList.toggle('-theme-with-dark-background', dark);
                }
                if (document.body) {
                    document.body.classList.toggle('-theme-with-dark-background', dark);
                }
            }catch(e){}
        })();""") % (theme, dark_bool)

    def set_accent_color(self, hex_color):
        if not hex_color or not QColor(hex_color).isValid():
            return
        self.prefs.set_accent_color(self.dark_mode, hex_color)
        self.refresh_theme(self.dark_mode)

    def reset_accent_colors(self):
        self.prefs.reset_accent_colors()
        self.refresh_theme(self.dark_mode)

    def set_new_tab_background(self, spec):
        if spec is None:
            self.prefs.clear_new_tab_background()
        elif isinstance(spec, str) and spec.startswith("#"):
            self.prefs.set_new_tab_background("color", spec)
        else:
            self.prefs.set_new_tab_background("image", spec)
        self._push_new_tab_background()

    def _push_new_tab_background(self):
        bg = background_to_data_uri(self.prefs.get_new_tab_background())
        js = "if(window.__mgSetBackground){window.__mgSetBackground(%s);}" % json.dumps(bg)
        for browser in self._iter_browsers():
            try:
                if browser.url().toString() == NEW_TAB_URL:
                    browser.page().runJavaScript(js)
            except RuntimeError:
                pass

    def refresh_theme(self, dark_mode=None):
        if dark_mode is None:
            dark_mode = self._detect_dark_mode()
        self.dark_mode = dark_mode
        t = self._theme()

        self.nav.setStyleSheet(self._toolbar_stylesheet())
        self.tabs.setStyleSheet(self._tabbar_stylesheet())

        for widget, name, size, bright in self._themed_icon_widgets:
            try:
                widget.setIcon(self._icon(name, size, bright=bright))
            except RuntimeError:
                pass
        self._update_maximize_button()

        for btn in self._tab_close_buttons:
            try:
                btn.setIcon(create_vector_icon("close", size=QSize(13, 13), color=QColor(t["close_btn_icon"])))
                btn.setStyleSheet(self._tab_close_button_stylesheet())
            except RuntimeError:
                pass

        for splitter in self._tab_splitters:
            try:
                splitter.setStyleSheet(self._splitter_stylesheet())
            except RuntimeError:
                pass

        for dev in self._tab_devtools:
            try:
                dev.page().runJavaScript(self._devtools_theme_js())
            except RuntimeError:
                pass

        new_theme_attr = "dark" if self.dark_mode else "light"
        new_accent = self.prefs.get_accent_color(self.dark_mode)
        for browser in self._iter_browsers():
            try:
                u = browser.url().toString()
                if u == NEW_TAB_URL or u.startswith("mangan://"):
                    browser.page().runJavaScript(
                        "if(document.documentElement){"
                        "document.documentElement.setAttribute('data-theme', %s);"
                        "document.documentElement.style.setProperty('--accent', %s, 'important');"
                        "document.documentElement.style.setProperty('--search-border-focus', %s, 'important');"
                        "}" % (json.dumps(new_theme_attr), json.dumps(new_accent), json.dumps(new_accent))
                    )
            except RuntimeError:
                pass

        lbl = getattr(self, "volume_boost_label", None)
        if lbl is not None:
            try:
                lbl.setStyleSheet(f'color: {t["menu_text"]}')
            except RuntimeError:
                pass

        find_bar = getattr(self, "find_bar", None)
        if find_bar is not None:
            try:
                find_bar.setStyleSheet(self._find_bar_stylesheet())
            except RuntimeError:
                pass

        settings_menu = getattr(self, "settings_menu", None)
        if settings_menu is not None:
            try:
                settings_menu.setStyleSheet(self._chrome_menu_stylesheet())
            except RuntimeError:
                pass
        downloads_menu = getattr(self, "downloads_menu", None)
        if downloads_menu is not None:
            try:
                downloads_menu.setStyleSheet(self._chrome_menu_stylesheet())
            except RuntimeError:
                pass

        self._update_zoom_row_style()
        self._update_volume_row_style()

        self._update_tab_colors(self.tabs.currentIndex())
        self.update_downloads_display()

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(self._app_stylesheet())

        if IS_WINDOWS and self.winId():
            self._apply_dwm_attributes(int(self.winId()))

    def nativeEvent(self, eventType, message):
        if IS_WINDOWS:
            try:
                if bytes(eventType) not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                    return False, 0
                msg = wintypes.MSG.from_address(int(message))
                hwnd = int(msg.hWnd)

                if msg.message == WM_NCCALCSIZE:
                    self._handle_nc_calc_size(hwnd, int(msg.wParam), int(msg.lParam))
                    return True, 0

                if msg.message == WM_GETMINMAXINFO:
                    self._handle_get_min_max_info(hwnd, int(msg.lParam))
                    return True, 0

                if getattr(self, "_native_titlebar_dragging", False):
                    if msg.message == WM_NCHITTEST:
                        return True, HTCAPTION
                    return False, 0

                if msg.message == WM_NCHITTEST:
                    return True, self._hit_test(hwnd, int(msg.lParam))

                if msg.message == WM_NCLBUTTONDBLCLK and int(msg.wParam) == HTCAPTION:
                    self.toggle_maximize()
                    return True, 0

                if msg.message == WM_SIZE and int(msg.wParam) == SIZE_MAXIMIZED:
                    QTimer.singleShot(0, self._enforce_maximized_geometry)

                if msg.message in (WM_DWMCOMPOSITIONCHANGED, WM_DPICHANGED):
                    QTimer.singleShot(0, self._ensure_native_frame)

                if msg.message == WM_SETTINGCHANGE and msg.lParam:
                    try:
                        setting_name = ctypes.wstring_at(msg.lParam)
                    except Exception:
                        setting_name = ""
                    if setting_name in ("ImmersiveColorSet", "WindowsThemeElement"):
                        QTimer.singleShot(0, self.refresh_theme)
            except Exception:
                pass

        return False, 0

    def _handle_nc_calc_size(self, hwnd, wparam, lparam):
        if wparam:
            try:
                if user32.IsZoomed(hwnd):
                    params = NCCALCSIZE_PARAMS.from_address(lparam)
                    frame_x, frame_y = self._maximized_frame_px(hwnd)
                    params.rgrc[0].top += frame_y
                    params.rgrc[0].left += frame_x
                    params.rgrc[0].right -= frame_x
                    params.rgrc[0].bottom -= frame_y
            except Exception:
                pass
        return

    def _ensure_native_frame(self):
        if not IS_WINDOWS or not self.winId():
            return

        hwnd = int(self.winId())
        self._last_dpi = self._dpi_for_window(hwnd)
        self._resize_border_cached = self._resize_border_px(hwnd)
        self._maximized_frame_cached = self._maximized_frame_px(hwnd)

        style = GetWindowLongPtr(hwnd, GWL_STYLE)
        native_style = WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
        if (style & native_style) != native_style:
            SetWindowLongPtr(hwnd, GWL_STYLE, style | native_style)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)

        self._apply_dwm_attributes(hwnd)
        self._native_frame_ready = True

    def _is_native_maximized(self):
        if IS_WINDOWS and self.winId():
            try:
                return bool(user32.IsZoomed(int(self.winId())))
            except Exception:
                pass
        return self.isMaximized()

    def _update_maximize_button(self):
        btn = getattr(self, "maximize_btn", None)
        if btn is None:
            return

        if self._is_native_maximized():
            btn.setIcon(self._icon("restore"))
            btn.setToolTip("Restore")
        else:
            btn.setIcon(self._icon("maximize"))
            btn.setToolTip("Maximize")

    def _apply_dwm_attributes(self, hwnd):
        try:
            maximized = self._is_native_maximized()
            t = self._theme()
            dark = c_int(1 if t["dwm_dark_mode"] else 0)
            nc_rendering = c_int(DWMNCRP_ENABLED)
            text_color = c_uint(t["dwm_text_color"])
            rounded = c_int(DWMWCP_DONOTROUND if maximized else DWMWCP_ROUND)
            border_color = c_uint(t["dwm_border_color"])
            margins = MARGINS(1, 1, 1, 1)

            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_NCRENDERING_POLICY, byref(nc_rendering), sizeof(nc_rendering))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(dark), sizeof(dark))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, byref(rounded), sizeof(rounded))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, byref(border_color), sizeof(border_color))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, byref(text_color), sizeof(text_color))
            dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))
        except Exception:
            pass

    def _dpi_for_window(self, hwnd):
        try:
            return int(user32.GetDpiForWindow(hwnd))
        except Exception:
            return 96

    def _resize_border_px(self, hwnd):
        dpi = self._dpi_for_window(hwnd)
        try:
            frame = int(user32.GetSystemMetricsForDpi(SM_CXFRAME, dpi))
            padded = int(user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi))
        except Exception:
            frame = int(user32.GetSystemMetrics(SM_CXFRAME))
            padded = int(user32.GetSystemMetrics(SM_CXPADDEDBORDER))
        return max(8, frame + padded)

    def _frame_margins(self, hwnd):
        try:
            style = int(GetWindowLongPtr(hwnd, GWL_STYLE))
            ex_style = int(GetWindowLongPtr(hwnd, GWL_EXSTYLE))
            dpi = self._dpi_for_window(hwnd)
            rect = RECT(0, 0, 0, 0)
            ok = False
            if hasattr(user32, "AdjustWindowRectExForDpi"):
                try:
                    ok = bool(user32.AdjustWindowRectExForDpi(byref(rect), style, False, ex_style, dpi))
                except Exception:
                    ok = False
            if not ok:
                ok = bool(user32.AdjustWindowRectEx(byref(rect), style, False, ex_style))
            if ok:
                return -rect.left, -rect.top, rect.right, rect.bottom
        except Exception:
            pass
        frame_x, frame_y = self._maximized_frame_px(hwnd)
        return frame_x, frame_y, frame_x, frame_y

    def _maximized_frame_px(self, hwnd):
        dpi = self._dpi_for_window(hwnd)
        try:
            frame_x = int(user32.GetSystemMetricsForDpi(SM_CXFRAME, dpi))
            frame_y = int(user32.GetSystemMetricsForDpi(SM_CYFRAME, dpi))
            padded = int(user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi))
        except Exception:
            frame_x = int(user32.GetSystemMetrics(SM_CXFRAME))
            frame_y = int(user32.GetSystemMetrics(SM_CYFRAME))
            padded = int(user32.GetSystemMetrics(SM_CXPADDEDBORDER))
        return max(1, frame_x + padded), max(1, frame_y + padded)

    def _hit_test(self, hwnd, lparam):
        if getattr(self, "_native_titlebar_dragging", False):
            return HTCAPTION

        x = _get_x_lparam(lparam)
        y = _get_y_lparam(lparam)
        rect = RECT()
        user32.GetWindowRect(hwnd, byref(rect))

        border = getattr(self, "_resize_border_cached", None)
        if border is None:
            border = self._resize_border_px(hwnd)
        on_left = rect.left <= x < rect.left + border
        on_right = rect.right - border <= x < rect.right
        on_top = rect.top <= y < rect.top + border
        on_bottom = rect.bottom - border <= y < rect.bottom

        if not self._is_native_maximized():
            if on_top and on_left:
                return HTTOPLEFT
            if on_top and on_right:
                return HTTOPRIGHT
            if on_bottom and on_left:
                return HTBOTTOMLEFT
            if on_bottom and on_right:
                return HTBOTTOMRIGHT
            if on_left:
                return HTLEFT
            if on_right:
                return HTRIGHT
            if on_top:
                return HTTOP
            if on_bottom:
                return HTBOTTOM

        qt_global = self._physical_to_qt_global(hwnd, x, y, rect)

        if self.is_native_caption_point(qt_global):
            return HTCAPTION
        return HTCLIENT

    def _physical_to_qt_global(self, hwnd, x, y, rect=None):
        if rect is None:
            rect = RECT()
            if not user32.GetWindowRect(hwnd, byref(rect)):
                return QPoint(x, y)
        scale = max(self._last_dpi / 96.0, 0.01)
        logical_top_left = self.frameGeometry().topLeft()
        return QPoint(
            logical_top_left.x() + int(round((x - rect.left) / scale)),
            logical_top_left.y() + int(round((y - rect.top) / scale)),
        )

    def is_native_caption_point(self, global_pos, allow_child_widgets=False):
        nav = getattr(self, "nav", None)

        if nav is not None and nav.isVisible():
            local = nav.mapFromGlobal(global_pos)
            if nav.rect().contains(local):
                if allow_child_widgets or nav.childAt(local) is None:
                    return True

        tab_bar = self.tabs.tabBar() if hasattr(self, "tabs") else None
        if tab_bar is not None and tab_bar.isVisible():
            local = tab_bar.mapFromGlobal(global_pos)
            if tab_bar.rect().contains(local):
                if allow_child_widgets or tab_bar.tabAt(local) == -1:
                    return True

        return False

    def start_native_titlebar_drag(self, global_pos, allow_child_widgets=False):
        if not IS_WINDOWS or not self.is_native_caption_point(global_pos, allow_child_widgets):
            return False

        hwnd = int(self.winId())
        self._native_titlebar_dragging = True
        try:
            user32.ReleaseCapture()
            user32.SendMessageW(hwnd, 0x00A1, HTCAPTION, 0)
        finally:
            self._native_titlebar_dragging = False
        return True

    def _enforce_maximized_geometry(self):
        if not IS_WINDOWS or not self.winId():
            return
        hwnd = int(self.winId())
        try:
            if not bool(user32.IsZoomed(hwnd)):
                return

            monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
            if not monitor:
                return
            monitor_info = MONITORINFO()
            monitor_info.cbSize = sizeof(MONITORINFO)
            if not user32.GetMonitorInfoW(monitor, byref(monitor_info)):
                return

            work = monitor_info.rcWork
            frame_x, frame_y = self._maximized_frame_px(hwnd)
            x = work.left - frame_x
            y = work.top - frame_y
            w = (work.right - work.left) + (frame_x * 2)
            h = (work.bottom - work.top) + (frame_y * 2)

            user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE)
        except Exception:
            pass

    def _handle_get_min_max_info(self, hwnd, lparam):
        mmi = MINMAXINFO.from_address(lparam)
        monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if monitor:
            monitor_info = MONITORINFO()
            monitor_info.cbSize = sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(monitor, byref(monitor_info)):
                work = monitor_info.rcWork
                mon = monitor_info.rcMonitor
                frame_x, frame_y = self._maximized_frame_px(hwnd)
                mmi.ptMaxPosition.x = work.left - mon.left - frame_x
                mmi.ptMaxPosition.y = work.top - mon.top - frame_y
                mmi.ptMaxSize.x = work.right - work.left + (frame_x * 2)
                mmi.ptMaxSize.y = work.bottom - work.top + (frame_y * 2)

        dpi_scale = self._dpi_for_window(hwnd) / 96.0
        mmi.ptMinTrackSize.x = int(640 * dpi_scale)
        mmi.ptMinTrackSize.y = int(420 * dpi_scale)

    def get_downloads_dir(self):
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    @property
    def active_downloads(self):
        return sum(1 for dl in self.downloads_list if not dl.is_finished)

    def _broadcast_downloads_display(self):
        for w in window_registry.all_windows():
            try:
                w.update_downloads_display()
            except RuntimeError:
                pass

    def save_image_as(self, img_url):
        if not PIL_AVAILABLE:
            QMessageBox.warning(self, "Missing Dependency", "Please install Pillow: pip install Pillow")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image As",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;WebP Image (*.webp);;BMP Image (*.bmp);;GIF Image (*.gif);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            class MockDownloadItem:
                def totalBytes(self):
                    return 0
                def receivedBytes(self):
                    return 0
            
            mock_item = MockDownloadItem()
            dl = DownloadItem(mock_item, file_path)
            self.downloads_list.append(dl)
            self._broadcast_downloads_display()
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                img_data = response.read()
            
            img = Image.open(BytesIO(img_data))
            
            if file_path.lower().endswith(('.jpg', '.jpeg')) and img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            img.save(file_path, quality=95)
            
            dl.is_finished = True
            
            self._broadcast_downloads_display()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save image:\n{str(e)}")

    def handle_download(self, download_item):
        downloads_dir = self.get_downloads_dir()
        filename = os.path.basename(download_item.downloadFileName())
        target_path = os.path.join(downloads_dir, filename)
        download_item.setDownloadDirectory(downloads_dir)
        download_item.setDownloadFileName(filename)
        download_item.accept()
        
        dl = DownloadItem(download_item, target_path)
        self.downloads_list.append(dl)
        
        download_item.receivedBytesChanged.connect(lambda: self.update_download_progress(dl, download_item))
        download_item.stateChanged.connect(lambda state: self.download_state(dl, download_item, state, target_path))
        
        self._broadcast_downloads_display()

    def update_download_progress(self, dl, download_item):
        dl.received_bytes = download_item.receivedBytes()
        if dl.total_bytes > 0:
            progress = int((dl.received_bytes / dl.total_bytes) * 100)
        else:
            progress = 0
        dl.progress_changed.emit(progress)
        self._broadcast_downloads_display()

    def download_state(self, dl, item, state, path):
        if item.isFinished():
            dl.is_finished = True
        self._broadcast_downloads_display()

    def _human_size(self, num_bytes):
        try:
            num_bytes = float(num_bytes)
        except Exception:
            return "0 B"
        for unit in ("B", "KB", "MB", "GB"):
            if num_bytes < 1024.0 or unit == "GB":
                if unit == "B":
                    return f"{int(num_bytes)} {unit}"
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} GB"

    def update_downloads_display(self):
        self.downloads_menu.clear()

        if self.active_downloads > 0:
            self.downloads_btn.setText(str(self.active_downloads))
            self.downloads_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        else:
            self.downloads_btn.setText("")
            self.downloads_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        t = self._theme()

        header = QLabel("Downloads")
        header.setStyleSheet(f"color: {t['menu_text']}; font-size: 14px; font-weight: 600; padding: 4px 10px 8px 10px; background: transparent;")
        header_action = QWidgetAction(self)
        header_action.setDefaultWidget(header)
        self.downloads_menu.addAction(header_action)
        self.downloads_menu.addSeparator()

        if not self.downloads_list:
            empty = QLabel("No downloads yet")
            empty.setStyleSheet(f"color: {t['tab_text']}; padding: 10px; background: transparent;")
            empty_action = QWidgetAction(self)
            empty_action.setDefaultWidget(empty)
            self.downloads_menu.addAction(empty_action)
        else:
            for dl in reversed(self.downloads_list[-8:]):
                row = QWidget()
                row.setFixedWidth(320)
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(10, 6, 10, 6)
                row_layout.setSpacing(10)

                icon_lbl = QLabel()
                icon_lbl.setFixedSize(28, 28)
                icon_lbl.setPixmap(create_vector_icon("downloads", size=QSize(18, 18), color=QColor(t["icon_color"])).pixmap(18, 18))
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_lbl.setStyleSheet(f"background: {t['button_hover']}; border-radius: 6px;")

                text_col = QVBoxLayout()
                text_col.setSpacing(1)
                name_lbl = QLabel(dl.filename)
                name_lbl.setStyleSheet(f"color: {t['menu_text']}; font-size: 12.5px; font-weight: 500; background: transparent;")
                name_lbl.setFixedWidth(190)
                fm = name_lbl.fontMetrics()
                name_lbl.setText(fm.elidedText(dl.filename, Qt.TextElideMode.ElideMiddle, 190))
                name_lbl.setToolTip(dl.filename)

                if dl.is_finished:
                    subtitle = "Done"
                elif dl.total_bytes > 0:
                    pct = int((dl.received_bytes / dl.total_bytes) * 100)
                    subtitle = f"{self._human_size(dl.received_bytes)} / {self._human_size(dl.total_bytes)} \u2022 {pct}%"
                else:
                    subtitle = f"{self._human_size(dl.received_bytes)} downloaded"
                sub_lbl = QLabel(subtitle)
                sub_lbl.setStyleSheet(f"color: {t['tab_text']}; font-size: 11px; background: transparent;")

                text_col.addWidget(name_lbl)
                text_col.addWidget(sub_lbl)

                remove_btn = QToolButton()
                remove_btn.setIcon(create_vector_icon("close", size=QSize(11, 11), color=QColor(t["close_btn_icon"])))
                remove_btn.setIconSize(QSize(11, 11))
                remove_btn.setFixedSize(22, 22)
                remove_btn.setToolTip("Remove from list")
                remove_btn.setStyleSheet(self._tab_close_button_stylesheet())
                idx_ref = self.downloads_list.index(dl)
                remove_btn.clicked.connect(lambda checked=False, i=idx_ref: self.clear_download(i))

                row_layout.addWidget(icon_lbl)
                row_layout.addLayout(text_col)
                row_layout.addStretch()
                row_layout.addWidget(remove_btn)
                row.setLayout(row_layout)
                row.setStyleSheet("QWidget:hover { background: transparent; }")

                row_action = QWidgetAction(self)
                row_action.setDefaultWidget(row)
                self.downloads_menu.addAction(row_action)

        self.downloads_menu.addSeparator()
        open_folder = self.downloads_menu.addAction("Open Downloads Folder")
        open_folder.triggered.connect(self.open_downloads_folder)
        full_history = self.downloads_menu.addAction("Full download history")
        full_history.triggered.connect(lambda: self.add_tab(QUrl(MANGAN_DOWNLOADS_URL), "Downloads"))

    def open_download_file(self, filepath):
        try:
            os.startfile(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")

    def clear_download(self, idx):
        if 0 <= idx < len(self.downloads_list):
            self.downloads_list.pop(idx)
            self.update_downloads_display()

    def open_downloads_folder(self):
        os.startfile(self.get_downloads_dir())

    def _create_zoom_row(self):
        widget = QWidget()
        widget.setObjectName("zoomRow")
        layout = QHBoxLayout()
        layout.setContentsMargins(38, 4, 10, 4)
        layout.setSpacing(4)

        label = QLabel("Zoom")
        label.setObjectName("zoomRowLabel")
        layout.addWidget(label)
        layout.addStretch()

        minus_btn = QToolButton()
        minus_btn.setObjectName("zoomMinusBtn")
        minus_btn.setText("\u2212")
        minus_btn.setFixedSize(26, 26)
        minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        minus_btn.setToolTip("Zoom out")
        minus_btn.clicked.connect(self.zoom_out)

        self.zoom_pct_label = QLabel("100%")
        self.zoom_pct_label.setObjectName("zoomPctLabel")
        self.zoom_pct_label.setFixedWidth(40)
        self.zoom_pct_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_pct_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_pct_label.setToolTip("Reset zoom")
        self.zoom_pct_label.mousePressEvent = lambda ev: self.zoom_reset()

        plus_btn = QToolButton()
        plus_btn.setObjectName("zoomPlusBtn")
        plus_btn.setText("+")
        plus_btn.setFixedSize(26, 26)
        plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_btn.setToolTip("Zoom in")
        plus_btn.clicked.connect(self.zoom_in)

        divider = QLabel()
        divider.setFixedWidth(1)
        divider.setObjectName("zoomDivider")

        self.fullscreen_btn_menu = QToolButton()
        self.fullscreen_btn_menu.setObjectName("zoomFullscreenBtn")
        self.fullscreen_btn_menu.setFixedSize(26, 26)
        self.fullscreen_btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_btn_menu.setToolTip("Full screen (F11)")
        self.fullscreen_btn_menu.clicked.connect(self.toggle_fullscreen)

        layout.addWidget(minus_btn)
        layout.addWidget(self.zoom_pct_label)
        layout.addWidget(plus_btn)
        layout.addSpacing(6)
        layout.addWidget(divider)
        layout.addSpacing(6)
        layout.addWidget(self.fullscreen_btn_menu)

        widget.setLayout(layout)
        self._zoom_row_label = label
        self._zoom_row_minus_btn = minus_btn
        self._zoom_row_plus_btn = plus_btn
        self._zoom_row_divider = divider
        self._update_zoom_row_style()
        return widget

    def _create_volume_row(self):
        widget = QWidget()
        widget.setObjectName("volumeRow")
        layout = QHBoxLayout()
        layout.setContentsMargins(14, 4, 10, 4)
        layout.setSpacing(8)

        label = QLabel("Volume Boost")
        label.setObjectName("volumeRowLabel")
        self.volume_boost_label = label

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 400)
        slider.setValue(self.volume_boost)
        slider.setFixedWidth(120)
        slider.setToolTip("Boost page audio (percent)")

        pct_label = QLabel(f"{self.volume_boost}%")
        pct_label.setObjectName("volumePctLabel")
        pct_label.setFixedWidth(40)
        pct_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_pct_label = pct_label

        def _on_change(v):
            self.set_volume_boost(v)
            pct_label.setText(f"{v}%")

        slider.valueChanged.connect(_on_change)
        self.volume_slider = slider

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(slider)
        layout.addWidget(pct_label)
        widget.setLayout(layout)
        self._update_volume_row_style()
        return widget

    def _update_zoom_row_style(self):
        if not hasattr(self, "zoom_pct_label"):
            return
        t = self._theme()
        btn_css = f"""
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 13px;
                color: {t['icon_color']};
                font-size: 15px;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: {t['button_hover']};
                color: {t['icon_color_bright']};
            }}
            QToolButton:pressed {{
                background: {t['button_pressed']};
            }}
        """
        for btn in (getattr(self, "_zoom_row_minus_btn", None), getattr(self, "_zoom_row_plus_btn", None)):
            if btn is not None:
                btn.setStyleSheet(btn_css)

        fs_btn = getattr(self, "fullscreen_btn_menu", None)
        if fs_btn is not None:
            fs_btn.setStyleSheet(btn_css)
            fs_btn.setIcon(create_vector_icon("fullscreen", size=QSize(15, 15), color=QColor(t["icon_color"])))
            fs_btn.setIconSize(QSize(15, 15))

        label = getattr(self, "_zoom_row_label", None)
        if label is not None:
            label.setStyleSheet(f"color: {t['menu_text']}; font-size: 13px; background: transparent;")

        self.zoom_pct_label.setStyleSheet(f"color: {t['menu_text']}; font-size: 13px; background: transparent;")

        divider = getattr(self, "_zoom_row_divider", None)
        if divider is not None:
            divider.setStyleSheet(f"background: {t['menu_separator']};")

        self._update_zoom_label()

    def _update_volume_row_style(self):
        if not hasattr(self, "volume_pct_label"):
            return
        t = self._theme()
        self.volume_boost_label.setStyleSheet(f"color: {t['menu_text']}; font-size: 13px; background: transparent;")
        self.volume_pct_label.setStyleSheet(f"color: {t['menu_text']}; font-size: 13px; background: transparent;")

    def zoom_in(self):
        b = self.current_browser()
        if b is None:
            return
        b.setZoomFactor(min(5.0, round(b.zoomFactor() + 0.1, 2)))
        self._update_zoom_label()

    def zoom_out(self):
        b = self.current_browser()
        if b is None:
            return
        b.setZoomFactor(max(0.25, round(b.zoomFactor() - 0.1, 2)))
        self._update_zoom_label()

    def zoom_reset(self):
        b = self.current_browser()
        if b is None:
            return
        b.setZoomFactor(1.0)
        self._update_zoom_label()

    def _update_zoom_label(self, *args):
        lbl = getattr(self, "zoom_pct_label", None)
        if lbl is None:
            return
        b = self.current_browser()
        if b is None:
            return
        try:
            pct = int(round(b.zoomFactor() * 100))
        except RuntimeError:
            return
        lbl.setText(f"{pct}%")

    def print_page(self):
        browser = self.current_browser()
        if browser is None:
            return
        if not PRINT_SUPPORT_AVAILABLE:
            QMessageBox.warning(
                self,
                "Printing Unavailable",
                "Printing requires the PyQt6 print support module.\nInstall it with: pip install PyQt6-QtPrintSupport",
            )
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print")
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            try:
                browser.page().print(printer, lambda ok: None)
            except Exception as e:
                QMessageBox.critical(self, "Print Error", f"Could not print this page:\n{str(e)}")

    def show_about(self):
        QMessageBox.information(self, "About Manganese", "Cryxcrax Manganese V2.0\nBuilt by Mult1c")

    def add_tab(self, qurl=None, label="New Tab"):
        show_new_tab_page = not qurl or qurl.isEmpty()
        
        browser = BrowserView(profile=self.gpu_profile, parent_window=self)
        browser._is_new_tab_page = show_new_tab_page
        if show_new_tab_page:
            browser.setHtml(self._new_tab_html(), QUrl(NEW_TAB_URL))
        else:
            browser.setUrl(qurl)

        def _clear_new_tab_flag_on_navigation(new_url, b=browser):
            if new_url.toString() not in (NEW_TAB_URL, ""):
                b._is_new_tab_page = False
        browser.urlChanged.connect(_clear_new_tab_flag_on_navigation)

        browser.urlChanged.connect(self.update_url_bar)
        browser.urlChanged.connect(lambda u, b=browser: self._record_history(b, u))
        self.tab_suspender.register_tab(browser)

        if not is_download_signal_connected():
            self.gpu_profile.downloadRequested.connect(self.handle_download)
            mark_download_signal_connected()
        
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(0,0,0,0)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet(self._splitter_stylesheet())
        self._tab_splitters.append(splitter)
        splitter.addWidget(browser)

        layout.addWidget(splitter)
        tab.setLayout(layout)

        browser._devtools = None
        browser._splitter = splitter

        self.tabs.addTab(tab, label)
        self.tabs.setCurrentWidget(tab)
        self.tabs.setTabText(self.tabs.indexOf(tab), "")

        title_label = TabTitleLabel(label)
        title_label.setFixedWidth(108)
        tab._title_label = title_label
        self.tabs.tabBar().setTabButton(self.tabs.indexOf(tab), QTabBar.ButtonPosition.LeftSide, title_label)
        self._update_tab_colors(self.tabs.currentIndex())

        browser.titleChanged.connect(lambda title, t=tab: self._update_tab_title(t, title))

        close_btn = QToolButton()
        close_btn.setIcon(create_vector_icon("close", size=QSize(13, 13), color=QColor(self._theme()["close_btn_icon"])))
        close_btn.setIconSize(QSize(13, 13))
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close Tab")
        close_btn.setStyleSheet(self._tab_close_button_stylesheet())
        close_btn.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(tab)))
        self.tabs.tabBar().setTabButton(self.tabs.indexOf(tab), QTabBar.ButtonPosition.RightSide, close_btn)
        self._tab_close_buttons.append(close_btn)

    def _update_tab_title(self, tab, title):
        lbl = getattr(tab, "_title_label", None)
        if lbl:
            lbl.setFullText(title)

    def _record_history(self, browser, qurl):
        try:
            url_str = qurl.toString()
        except Exception:
            return
        if not url_str or url_str in (NEW_TAB_URL, "about:blank") or url_str.startswith("mangan://"):
            return

        def _add_entry():
            t = browser.title() or url_str
            self.history_store.add(t, url_str)
        QTimer.singleShot(400, _add_entry)

    def _update_tab_colors(self, current_index):
        t = self._theme()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            lbl = getattr(tab, "_title_label", None) if tab else None
            if not lbl:
                continue
            color = t["tab_selected_text"] if i == current_index else t["tab_text"]
            lbl.setStyleSheet(f"color: {color}; font-size: 12.5px; font-family: 'Segoe UI'; background: transparent;")

    def close_tab(self, index):
        if self.tabs.count() > 1:
            tab = self.tabs.widget(index)
            browser = self._browser_for_tab(tab)
            if browser is not None:
                self.tab_suspender.unregister_tab(browser)
            self.tabs.removeTab(index)
            self._destroy_orphaned_tab(tab)
        else:
            self.close()

    def close_current_tab(self):
        self.close_tab(self.tabs.currentIndex())

    def detach_tab_to_new_window(self, index, global_pos):
        if not (0 <= index < self.tabs.count()):
            return
        tab = self.tabs.widget(index)
        browser = self._browser_for_tab(tab)
        if browser is None:
            return
        url = browser.url()
        title = browser.title() or "New Tab"
        was_new_tab_page = getattr(browser, "_is_new_tab_page", False) or self._is_internal_page_url(url.toString())

        self.tab_suspender.unregister_tab(browser)
        self.tabs.removeTab(index)
        self._destroy_orphaned_tab(tab)

        new_window = TabbedBrowser(url_to_open=None)
        reopen_url = None if was_new_tab_page else url
        new_window.add_tab(reopen_url, title)
        if new_window.tabs.count() > 1:
            new_window.close_tab(0)

        new_window.resize(self.size())
        new_window.move(global_pos.x() - 120, max(0, global_pos.y() - 20))
        new_window.show()
        new_window.raise_()
        new_window.activateWindow()

        if self.tabs.count() == 0:
            self.close()

    def _destroy_orphaned_tab(self, tab):
        browser = self._browser_for_tab(tab)
        if browser is not None:
            try:
                browser.urlChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                browser.loadFinished.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                browser.titleChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            dev = getattr(browser, "_devtools", None)
            if dev is not None:
                try:
                    self._tab_devtools.remove(dev)
                except ValueError:
                    pass
        splitter = getattr(browser, "_splitter", None) if browser is not None else None
        if splitter is not None:
            try:
                self._tab_splitters.remove(splitter)
            except ValueError:
                pass
        try:
            tab.deleteLater()
        except RuntimeError:
            pass

    def reattach_tab_to_window(self, index, target_window, global_pos):
        if target_window is self or not (0 <= index < self.tabs.count()):
            return
        tab = self.tabs.widget(index)
        browser = self._browser_for_tab(tab)
        if browser is None:
            return
        url = browser.url()
        title = browser.title() or "New Tab"
        was_new_tab_page = getattr(browser, "_is_new_tab_page", False) or self._is_internal_page_url(url.toString())

        self.tab_suspender.unregister_tab(browser)
        self.tabs.removeTab(index)
        self._destroy_orphaned_tab(tab)

        reopen_url = None if was_new_tab_page else url
        target_window.add_tab(reopen_url, title)
        target_window.raise_()
        target_window.activateWindow()

        if self.tabs.count() == 0:
            self.close()

    def _browser_for_tab(self, tab):
        if tab is None:
            return None
        try:
            w = tab.layout().itemAt(0).widget()
        except Exception:
            return None
        try:
            if isinstance(w, QSplitter):
                return w.widget(0)
        except Exception:
            pass
        return w

    def current_browser(self):
        return self._browser_for_tab(self.tabs.currentWidget())

    def _iter_browsers(self):
        for i in range(self.tabs.count()):
            browser = self._browser_for_tab(self.tabs.widget(i))
            if browser is not None:
                yield browser

    browserengine = "https://www.google.com/search?q="
    search_engine_name = "Google"

    def google_be(self):
        self.browserengine = "https://www.google.com/search?q="
        self.home_page = "https://www.google.com"
        self.search_engine_name = "Google"
        self._push_new_tab_search_engine()

    def bing_be(self):
        self.browserengine = "https://www.bing.com/search?q="
        self.home_page = "https://www.bing.com"
        self.search_engine_name = "Microsoft Bing"
        self._push_new_tab_search_engine()

    def yahoo_be(self):
        self.browserengine = "https://search.yahoo.com/search?p="
        self.home_page = "https://search.yahoo.com"
        self.search_engine_name = "Yahoo Search"
        self._push_new_tab_search_engine()

    def duck_be(self):
        self.browserengine = "https://duckduckgo.com/?q="
        self.home_page = "https://duckduckgo.com"
        self.search_engine_name = "DuckDuckGo"
        self._push_new_tab_search_engine()
        
    def yandex_be(self):
        self.browserengine = "https://yandex.com/search/?text="
        self.home_page = "https://yandex.com"
        self.search_engine_name = "Yandex"
        self._push_new_tab_search_engine()

    def navigate_to_url(self):
        browserengine = self.browserengine
        url = self.url_bar.text()
        if url.startswith("http://") or url.startswith("https://") or url.startswith("mangan://"):
            url = url
        elif "." in url and " " not in url:
            url = "https://" + url
        else:
            url = browserengine + url
        self.current_browser().setUrl(QUrl(url))

    def set_volume_boost(self, percent:int):
        try:
            self.volume_boost = int(percent)
            gain = float(self.volume_boost) / 100.0
            js = ("(function(){"
                  "try{"
                  "var G=%s;"
                  "if(!window.__manganese_audio_booster_installed){"
                      "window.__manganese_audio_booster_installed = true;"
                      "window.__manganese_context = new (window.AudioContext || window.webkitAudioContext)();"
                      "window.__manganese_gain = window.__manganese_context.createGain();"
                      "window.__manganese_gain.gain.value = G;"
                      "window.__manganese_gain.connect(window.__manganese_context.destination);"
                      "window.__manganese_sources = new WeakMap();"
                      "function attach(el){"
                          "try{"
                              "if(window.__manganese_sources.has(el)) return;"
                              "var src = window.__manganese_context.createMediaElementSource(el);"
                              "src.connect(window.__manganese_gain);"
                              "window.__manganese_sources.set(el, src);"
                          "}catch(e){}"
                      "}"
                      "document.querySelectorAll('audio,video').forEach(attach);"
                      "var mo = new MutationObserver(function(m){"
                          "m.forEach(function(rec){"
                              "rec.addedNodes.forEach(function(node){"
                                  "if(node && node.tagName && (node.tagName.toLowerCase()==='audio' || node.tagName.toLowerCase()==='video')) attach(node);"
                              "});"
                          "});"
                      "});"
                      "mo.observe(document.documentElement || document.body, {childList:true, subtree:true});"
                      "window.__manganese_set_gain = function(v){ if(window.__manganese_gain) window.__manganese_gain.gain.value = v; };"
                  "} else {"
                      "if(window.__manganese_set_gain) window.__manganese_set_gain(G);"
                  "}"
                  "}catch(e){}"
                  "})();") % (repr(gain))
            page = self.current_browser().page()
            page.runJavaScript(js)
        except Exception:
            pass

    def _is_internal_page_url(self, url_str):
        return url_str in (NEW_TAB_URL, NEW_TAB_URL + "/") or url_str.startswith("mangan://")

    def _on_current_tab_changed_suspension(self, index):
        browsers = list(self._iter_browsers())
        active = self.current_browser()
        if active is not None:
            self.tab_suspender.on_active_tab_changed(browsers, active)

    def update_url_bar(self):
        browser = self.current_browser()
        if browser is None:
            return
        current_url = browser.url().toString()

        if current_url in (NEW_TAB_URL, NEW_TAB_URL + "/", "about:blank"):
            self.url_bar.setText("")
            return

        home_normalized = self.home_page.rstrip('/')
        current_normalized = current_url.rstrip('/')
        
        if current_normalized == home_normalized:
            self.url_bar.setText("")
        else:
            self.url_bar.setText(current_url)

    def back(self):
        self.current_browser().back()

    def forward(self):
        self.current_browser().forward()

    def reload(self):
        self.current_browser().reload() 

    def next_tab(self):
        count = self.tabs.count()
        if count > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % count)

    def previous_tab(self):
        count = self.tabs.count()
        if count > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % count)

    def focus_url_bar(self):
        self.url_bar.setFocus()
        self.url_bar.selectAll()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            if getattr(self, "_pre_fullscreen_maximized", False):
                self.showMaximized()
            else:
                self.showNormal()
        else:
            self._pre_fullscreen_maximized = self._is_native_maximized()
            self.showFullScreen()

    def _create_find_bar(self):
        bar = QWidget()
        bar.setVisible(False)
        bar.setFixedHeight(40)
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.find_input = FindLineEdit()
        self.find_input.setPlaceholderText("Find in page")
        self.find_input.textChanged.connect(lambda text: self._find_in_page(text))
        self.find_input.find_next.connect(lambda: self._find_in_page(self.find_input.text(), backward=False))
        self.find_input.find_previous.connect(lambda: self._find_in_page(self.find_input.text(), backward=True))
        self.find_input.closed.connect(self.close_find_bar)

        prev_btn = QToolButton()
        prev_btn.setIcon(self._icon("back", QSize(14, 14)))
        prev_btn.setIconSize(QSize(14, 14))
        prev_btn.setFixedSize(28, 28)
        prev_btn.setToolTip("Previous match (Shift+Enter)")
        prev_btn.clicked.connect(lambda: self._find_in_page(self.find_input.text(), backward=True))

        next_btn = QToolButton()
        next_btn.setIcon(self._icon("forward", QSize(14, 14)))
        next_btn.setIconSize(QSize(14, 14))
        next_btn.setFixedSize(28, 28)
        next_btn.setToolTip("Next match (Enter)")
        next_btn.clicked.connect(lambda: self._find_in_page(self.find_input.text(), backward=False))

        close_btn = QToolButton()
        close_btn.setIcon(self._icon("close", QSize(18, 18)))
        close_btn.setIconSize(QSize(18, 18))
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("Close (Esc)")
        close_btn.clicked.connect(self.close_find_bar)

        self._themed_icon_widgets.extend([
            (prev_btn, "back", QSize(14, 14), False),
            (next_btn, "forward", QSize(14, 14), False),
            (close_btn, "close", QSize(18, 18), False),
        ])

        layout.addWidget(self.find_input)
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)
        layout.addWidget(close_btn)
        bar.setLayout(layout)
        bar.setStyleSheet(self._find_bar_stylesheet())
        return bar

    def _find_bar_stylesheet(self):
        t = self._theme()
        return f"""
            QWidget {{
                background: {t['toolbar_bg']};
                border-bottom: 1px solid {t['toolbar_border']};
            }}
            QLineEdit {{
                background: {t['urlbar_bg']};
                color: {t['urlbar_text']};
                border: 1px solid {t['urlbar_border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t['urlbar_focus_border']};
            }}
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px;
                color: {t['icon_color']};
            }}
            QToolButton:hover {{
                background: {t['button_hover']};
                color: {t['icon_color_bright']};
            }}
        """

    def open_find_bar(self):
        self.find_bar.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def close_find_bar(self):
        self.find_bar.setVisible(False)
        browser = self.current_browser()
        if browser is not None:
            try:
                browser.findText("")
            except Exception:
                pass
            browser.setFocus()

    def _find_in_page(self, text, backward=False):
        browser = self.current_browser()
        if browser is None:
            return
        try:
            flags = QWebEnginePage.FindFlag.FindBackward if backward else QWebEnginePage.FindFlag(0)
            browser.findText(text, flags)
        except Exception:
            pass

    def _ensure_devtools(self, browser, splitter):
        dev = browser._devtools
        if dev is not None:
            return dev
        dev = QWebEngineView()
        dev.setPage(QWebEnginePage(self.gpu_profile, dev))
        dev.setVisible(False)
        browser.page().setDevToolsPage(dev.page())
        dev.loadFinished.connect(lambda ok, d=dev: d.page().runJavaScript(self._devtools_theme_js()) if ok else None)
        self._tab_devtools.append(dev)
        splitter.addWidget(dev)
        browser._devtools = dev
        return dev

    def toggle_devtools(self):
        b = self.current_browser()
        if b is None:
            return
        splitter = getattr(b, '_splitter', None)
        if splitter is None:
            return
        dev = self._ensure_devtools(b, splitter)
        if dev.isVisible():
            dev.hide()
            sizes = splitter.sizes()
            if len(sizes) >= 2:
                splitter.setSizes([sizes[0] + sizes[1], 0])
        else:
            dev.show()
            try:
                dev.page().runJavaScript(self._devtools_theme_js())
            except RuntimeError:
                pass
            total = splitter.size().width() if splitter.size().width() > 0 else self.width()
            left = int(total * 0.6)
            right = total - left
            splitter.setSizes([left, right])

    def toggle_maximize(self):
        if self._toggle_maximize_pending:
            return
        self._toggle_maximize_pending = True
        QTimer.singleShot(0, self._apply_toggle_maximize)

    def _apply_toggle_maximize(self):
        self._toggle_maximize_pending = False
        if IS_WINDOWS and self.winId():
            hwnd = int(self.winId())
            try:
                if bool(user32.IsZoomed(hwnd)):
                    user32.ShowWindow(hwnd, SW_RESTORE)
                else:
                    user32.ShowWindow(hwnd, SW_MAXIMIZE)
                return
            except Exception:
                pass
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Web Files (*.html *.htm);;PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            file_url = QUrl.fromLocalFile(os.path.abspath(file_path))
            label = os.path.basename(file_path)
            self.add_tab(file_url, label)


    def build_internal_page(self, page, url=None):
        theme_attr = "dark" if self.dark_mode else "light"
        if page == "settings":
            return self._build_settings_page(theme_attr)
        if page == "downloads":
            return self._build_downloads_page(theme_attr)
        if page == "history":
            return self._build_history_page(theme_attr)
        if page == "sitedata":
            return self._build_site_data_page(theme_attr)
        return internal_page_shell(theme_attr, "Not found", "<h1>Page not found</h1>")

    def _build_settings_page(self, theme_attr):
        return build_settings_page(
            theme_attr, self.search_engine_name, self.get_downloads_dir(),
            accent_color=self.prefs.get_accent_color(self.dark_mode),
            new_tab_background=self.prefs.get_new_tab_background(),
            tab_suspension_enabled=self.prefs.get_tab_suspension_enabled(),
        )

    def _build_downloads_page(self, theme_attr):
        return build_downloads_page(theme_attr, self.downloads_list, self._human_size)

    def _build_history_page(self, theme_attr):
        return build_history_page(theme_attr, self.history_store.entries)

    def _build_site_data_page(self, theme_attr):
        return build_site_data_page(theme_attr, self.cookie_tracker.sites())

    def handle_internal_action(self, url, page):
        query = QUrl(url).query()
        params = dict(urllib.parse.parse_qsl(query))

        refresh_page = "settings"

        if params.get("set") == "engine":
            value = params.get("value", "")
            mapping = {
                "google": self.google_be, "bing": self.bing_be, "yahoo": self.yahoo_be,
                "duck": self.duck_be, "yandex": self.yandex_be,
            }
            fn = mapping.get(value)
            if fn:
                fn()

        elif params.get("set") == "accent":
            self.set_accent_color(params.get("value", ""))

        elif params.get("set") == "newtab_bg":
            self.set_new_tab_background(params.get("value", ""))

        elif params.get("clear_newtab_bg") == "1":
            self.set_new_tab_background(None)

        elif params.get("set") == "tab_suspension":
            enabled = params.get("value") == "1"
            self.prefs.set_tab_suspension_enabled(enabled)
            self.tab_suspender.set_enabled(enabled)

        elif params.get("choose_newtab_image") == "1":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Choose New Tab background image", "",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*)",
            )
            if file_path:
                self.set_new_tab_background(file_path)

        elif params.get("clear_history") == "1":
            self.history_store.clear()
            refresh_page = "history"

        elif params.get("delete_history_entry") == "1":
            self.history_store.delete_entry(
                params.get("url", ""), params.get("visited_at", "")
            )
            refresh_page = "history"

        elif params.get("delete_site_cookies") == "1":
            self.cookie_tracker.delete_site(params.get("domain", ""))
            refresh_page = "sitedata"

        elif params.get("clear_all_cookies") == "1":
            self.cookie_tracker.delete_all()
            refresh_page = "sitedata"

        theme_attr = "dark" if self.dark_mode else "light"
        builders = {
            "settings": self._build_settings_page,
            "history": self._build_history_page,
            "sitedata": self._build_site_data_page,
        }
        builder = builders.get(refresh_page, self._build_settings_page)
        try:
            page.runJavaScript(
                "document.open(); document.write(%s); document.close();" % json.dumps(builder(theme_attr))
            )
        except Exception:
            pass
