from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QGuiApplication
from PyQt6.QtCore import Qt, QSize


def _colorref(r, g, b):
    return (b << 16) | (g << 8) | r


THEMES = {
    "dark": {
        "window_bg": "#1a1b1e",
        "toolbar_bg": "#202225",
        "toolbar_border": "#17181a",
        "button_hover": "#34363b",
        "button_pressed": "#3f4147",
        "icon_color": "#c7c8cc",
        "icon_color_bright": "#ffffff",
        "tabbar_bg": "#202225",
        "tab_bg": "#2a2c30",
        "tab_text": "#9a9ca3",
        "tab_selected_bg": "#1a1b1e",
        "tab_selected_text": "#f5f5f6",
        "tab_selected_border": "#313338",
        "tab_hover_bg": "#34363b",
        "tab_hover_text": "#dfe0e3",
        "accent": "#5b8cff",
        "close_btn_icon": "#aeb0b6",
        "close_btn_hover": "#4a4d55",
        "close_btn_pressed": "#5a5d66",
        "urlbar_bg": "#2a2c30",
        "urlbar_text": "#f0f0f0",
        "urlbar_border": "#3a3c42",
        "urlbar_focus_border": "#5b8cff",
        "urlbar_focus_bg": "#2f3136",
        "urlbar_placeholder": "#7a7c82",
        "menu_bg": "#26282c",
        "menu_text": "#e6e6e6",
        "menu_border": "#3a3c42",
        "menu_item_hover_bg": "#3a3d44",
        "menu_item_hover_text": "#ffffff",
        "menu_separator": "#3a3c42",
        "tooltip_bg": "#26282c",
        "tooltip_text": "#e6e6e6",
        "tooltip_border": "#3a3c42",
        "window_controls_hover": "#3a3a3a",
        "window_controls_pressed": "#4a4a4a",
        "dwm_dark_mode": True,
        "dwm_border_color": _colorref(0x20, 0x22, 0x25),
        "dwm_text_color": _colorref(0xFF, 0xFF, 0xFF),
    },
    "light": {
        "window_bg": "#f5f5f7",
        "toolbar_bg": "#ffffff",
        "toolbar_border": "#e2e2e4",
        "button_hover": "#e9e9ec",
        "button_pressed": "#dcdce0",
        "icon_color": "#3c3c43",
        "icon_color_bright": "#111113",
        "tabbar_bg": "#eceef1",
        "tab_bg": "#e3e5e9",
        "tab_text": "#5f6368",
        "tab_selected_bg": "#ffffff",
        "tab_selected_text": "#1c1c1e",
        "tab_selected_border": "#d7d8dc",
        "tab_hover_bg": "#dadce0",
        "tab_hover_text": "#242527",
        "accent": "#3366ee",
        "close_btn_icon": "#6a6c72",
        "close_btn_hover": "#d3d4d8",
        "close_btn_pressed": "#c2c3c8",
        "urlbar_bg": "#ffffff",
        "urlbar_text": "#1c1c1e",
        "urlbar_border": "#c9cad0",
        "urlbar_focus_border": "#3366ee",
        "urlbar_focus_bg": "#ffffff",
        "urlbar_placeholder": "#9a9ba1",
        "menu_bg": "#ffffff",
        "menu_text": "#1c1c1e",
        "menu_border": "#d7d8dc",
        "menu_item_hover_bg": "#e7eaf5",
        "menu_item_hover_text": "#111113",
        "menu_separator": "#e2e2e4",
        "tooltip_bg": "#ffffff",
        "tooltip_text": "#1c1c1e",
        "tooltip_border": "#d7d8dc",
        "window_controls_hover": "#e0e0e0",
        "window_controls_pressed": "#cfcfcf",
        "dwm_dark_mode": False,
        "dwm_border_color": _colorref(0xD7, 0xD8, 0xDC),
        "dwm_text_color": _colorref(0x1C, 0x1C, 0x1E),
    },
}


def create_vector_icon(icon_type, size=QSize(20, 20), color=QColor("#ddd")):
    dpr = 1.0
    try:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            dpr = max(1.0, float(screen.devicePixelRatio()))
    except Exception:
        dpr = 1.0

    device_w = max(1, round(size.width() * dpr))
    device_h = max(1, round(size.height() * dpr))
    pixmap = QPixmap(device_w, device_h)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(dpr, dpr)
    
    pen = QPen(color, 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    
    w, h = size.width(), size.height()
    
    if icon_type == "back":
        painter.drawLine(int(w * 0.6), int(h * 0.25), int(w * 0.35), int(h * 0.5))
        painter.drawLine(int(w * 0.35), int(h * 0.5), int(w * 0.6), int(h * 0.75))
    elif icon_type == "forward":
        painter.drawLine(int(w * 0.4), int(h * 0.25), int(w * 0.65), int(h * 0.5))
        painter.drawLine(int(w * 0.65), int(h * 0.5), int(w * 0.4), int(h * 0.75))
    elif icon_type == "refresh":
        pen.setWidthF(1.8)
        painter.setPen(pen)
        rect = pixmap.rect().adjusted(5, 5, -5, -5)
        painter.drawArc(rect, 45 * 16, 270 * 16)
        tip_x = rect.right() - 1
        tip_y = rect.top() + int(rect.height() * 0.15)
        painter.drawLine(tip_x, tip_y, tip_x, tip_y - int(h * 0.15))
        painter.drawLine(tip_x, tip_y, tip_x - int(w * 0.15), tip_y)
    elif icon_type == "new_tab":
        cx, cy = w / 2.0, h / 2.0
        arm = w * 0.26
        painter.drawLine(int(round(cx)), int(round(cy - arm)), int(round(cx)), int(round(cy + arm)))
        painter.drawLine(int(round(cx - arm)), int(round(cy)), int(round(cx + arm)), int(round(cy)))
    elif icon_type == "minimize":
        painter.drawLine(int(w * 0.25), int(h * 0.6), int(w * 0.75), int(h * 0.6))
    elif icon_type == "maximize":
        painter.drawRect(int(w * 0.35), int(h * 0.35), int(w * 0.3), int(h * 0.3))
    elif icon_type == "restore":
        painter.drawRect(int(w * 0.45), int(h * 0.3), int(w * 0.25), int(h * 0.25))
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        painter.drawRect(int(w * 0.3), int(h * 0.45), int(w * 0.25), int(h * 0.25))
    elif icon_type == "close":
        painter.drawLine(int(w * 0.35), int(h * 0.35), int(w * 0.65), int(h * 0.65))
        painter.drawLine(int(w * 0.65), int(h * 0.35), int(w * 0.35), int(h * 0.65))
    elif icon_type == "downloads":
        painter.drawLine(int(w * 0.5), int(h * 0.2), int(w * 0.5), int(h * 0.65))
        painter.drawLine(int(w * 0.3), int(h * 0.45), int(w * 0.5), int(h * 0.65))
        painter.drawLine(int(w * 0.7), int(h * 0.45), int(w * 0.5), int(h * 0.65))
        painter.drawLine(int(w * 0.25), int(h * 0.8), int(w * 0.75), int(h * 0.8))
    elif icon_type == "settings":
        painter.drawLine(int(w * 0.25), int(h * 0.3), int(w * 0.75), int(h * 0.3))
        painter.drawLine(int(w * 0.25), int(h * 0.5), int(w * 0.75), int(h * 0.5))
        painter.drawLine(int(w * 0.25), int(h * 0.7), int(w * 0.75), int(h * 0.7))
    elif icon_type == "fullscreen":
        pen.setWidthF(1.8)
        painter.setPen(pen)
        m = w * 0.22
        a = w * 0.16
        painter.drawLine(int(m), int(m), int(m + a), int(m))
        painter.drawLine(int(m), int(m), int(m), int(m + a))
        painter.drawLine(int(w - m), int(m), int(w - m - a), int(m))
        painter.drawLine(int(w - m), int(m), int(w - m), int(m + a))
        painter.drawLine(int(m), int(h - m), int(m + a), int(h - m))
        painter.drawLine(int(m), int(h - m), int(m), int(h - m - a))
        painter.drawLine(int(w - m), int(h - m), int(w - m - a), int(h - m))
        painter.drawLine(int(w - m), int(h - m), int(w - m), int(h - m - a))
        
    painter.end()
    return QIcon(pixmap)
