from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt


class TabTitleLabel(QLabel):
    def __init__(self, text="New Tab", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setContentsMargins(13, 0, 6, 0)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(self.fontMetrics().height() + 6)
        self._refresh()

    def setFullText(self, text):
        self._full_text = text or "New Tab"
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        fm = self.fontMetrics()
        available = max(self.contentsRect().width(), 1)
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, available)
        super().setText(elided)
        self.setToolTip(self._full_text)
