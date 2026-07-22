from PyQt6.QtWidgets import QToolBar, QTabBar, QWidget, QApplication
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import Qt

from manganese import window_registry

DETACH_THRESHOLD_PX = 40


class DraggableToolBar(QToolBar):
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                if self.parent_window.start_native_titlebar_drag(event.globalPosition().toPoint()):
                    return
            except Exception:
                pass
        super().mousePressEvent(event)


class DraggableTabBar(QTabBar):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self._drag_start_pos = None
        self._drag_on_tab = False
        self._dragged_tab_index = None
        self._detached = False

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            index = self.tabAt(event.position().toPoint())
            self._drag_on_tab = index != -1
            self._dragged_tab_index = index if self._drag_on_tab else None
            self._detached = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_on_tab and self._dragged_tab_index is not None:
            if self._maybe_handle_tab_drag(event):
                return
            super().mouseMoveEvent(event)
            return
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_start_pos is not None:
            distance = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                if self.parent_window.start_native_titlebar_drag(event.globalPosition().toPoint(), allow_child_widgets=True):
                    self._drag_start_pos = None
                    event.accept()
                    return
        super().mouseMoveEvent(event)

    def _maybe_handle_tab_drag(self, event: QMouseEvent):
        global_pos = event.globalPosition().toPoint()

        if self._detached:
            try:
                self.parent_window.start_native_titlebar_drag(global_pos, allow_child_widgets=True)
            except Exception:
                pass
            return True

        if event.buttons() & Qt.MouseButton.LeftButton:
            local_y = self.mapFromGlobal(global_pos).y()
            bar_rect = self.rect()
            outside_vertically = local_y < -DETACH_THRESHOLD_PX or local_y > bar_rect.height() + DETACH_THRESHOLD_PX
            if outside_vertically and self.count() > 1:
                self._detached = True
                try:
                    self.parent_window.detach_tab_to_new_window(self._dragged_tab_index, global_pos)
                except Exception:
                    self._detached = False
                return True
        return False

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_on_tab and self._dragged_tab_index is not None and not self._detached:
            global_pos = event.globalPosition().toPoint()
            target = window_registry.window_at_global_pos(global_pos, exclude=self.parent_window)
            if target is not None:
                try:
                    self.parent_window.reattach_tab_to_window(self._dragged_tab_index, target, global_pos)
                except Exception:
                    pass
        self._drag_start_pos = None
        self._drag_on_tab = False
        self._dragged_tab_index = None
        self._detached = False
        super().mouseReleaseEvent(event)

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setWidth(max(90, min(size.width(), 210)))
        return size


class DraggableToolBarLabelSpacer(QWidget):
    pass
