from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import pyqtSignal, Qt


class FindLineEdit(QLineEdit):
    find_next = pyqtSignal()
    find_previous = pyqtSignal()
    closed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_previous.emit()
            else:
                self.find_next.emit()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
            return
        super().keyPressEvent(event)
