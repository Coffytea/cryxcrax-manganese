import csv
import os

from PyQt6.QtCore import QDateTime

from manganese.paths import history_csv_path

_FIELDNAMES = ["visited_at", "title", "url"]


class HistoryStore:
    def __init__(self):
        self.entries = []
        self._load()

    def _load(self):
        path = history_csv_path()
        if not os.path.exists(path):
            self.entries = []
            return
        entries = []
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dt = QDateTime.fromString(row["visited_at"], "yyyy-MM-ddTHH:mm:ss")
                        if not dt.isValid():
                            continue
                        entries.append({
                            "title": row.get("title") or row.get("url", ""),
                            "url": row["url"],
                            "dt": dt,
                        })
                    except Exception:
                        continue
        except Exception:
            entries = []
        self.entries = entries

    def add(self, title, url):
        dt = QDateTime.currentDateTime()
        self.entries.append({"title": title, "url": url, "dt": dt})

        path = history_csv_path()
        file_exists = os.path.exists(path)
        try:
            with open(path, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "visited_at": dt.toString("yyyy-MM-ddTHH:mm:ss"),
                    "title": title,
                    "url": url,
                })
        except Exception:
            pass

    def clear(self):
        self.entries = []
        path = history_csv_path()
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def delete_entry(self, url, visited_at_str):
        self.entries = [
            e for e in self.entries
            if not (e["url"] == url and e["dt"].toString("yyyy-MM-ddTHH:mm:ss") == visited_at_str)
        ]
        self._rewrite()

    def _rewrite(self):
        path = history_csv_path()
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
                writer.writeheader()
                for e in self.entries:
                    writer.writerow({
                        "visited_at": e["dt"].toString("yyyy-MM-ddTHH:mm:ss"),
                        "title": e["title"],
                        "url": e["url"],
                    })
            os.replace(tmp_path, path)
        except Exception:
            pass
