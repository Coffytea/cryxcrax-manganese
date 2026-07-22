import os
from PyQt6.QtCore import QObject, pyqtSignal, QDateTime


class DownloadItem(QObject):
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, download_item, target_path):
        super().__init__()
        self.download_item = download_item
        self.target_path = target_path
        self.filename = os.path.basename(target_path)
        self.is_finished = False
        self.is_paused = False
        self.total_bytes = download_item.totalBytes()
        self.received_bytes = 0
        self.started_at = QDateTime.currentDateTime()
