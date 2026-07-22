from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QKeySequence
from PyQt6.QtCore import QObject, QEvent


class GlobalShortcutFilter(QObject):

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            window = self.window
            try:
                if QApplication.activeWindow() is not window:
                    return False
            except Exception:
                pass
            try:
                seq = QKeySequence(event.keyCombination()).toString()
            except Exception:
                return False
            if not seq:
                return False
            handler = window._shortcut_map.get(seq)
            if handler is not None:
                handler()
                return True
        return False
