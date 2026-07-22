import json
import os

from manganese.paths import prefs_path

DEFAULT_ACCENT = {
    "dark": "#5b8cff",
    "light": "#3366ee",
}


class Prefs:
    def __init__(self):
        self._data = {}
        self._load()

    def _load(self):
        path = prefs_path()
        if not os.path.exists(path):
            self._data = {}
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def _save(self):
        path = prefs_path()
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            pass


    def get_accent_color(self, dark_mode):
        key = "accent_dark" if dark_mode else "accent_light"
        return self._data.get(key) or DEFAULT_ACCENT["dark" if dark_mode else "light"]

    def set_accent_color(self, dark_mode, hex_color):
        key = "accent_dark" if dark_mode else "accent_light"
        self._data[key] = hex_color
        self._save()

    def reset_accent_colors(self):
        self._data.pop("accent_dark", None)
        self._data.pop("accent_light", None)
        self._save()


    def get_new_tab_background(self):
        return self._data.get("new_tab_background")

    def set_new_tab_background(self, kind, value):
        self._data["new_tab_background"] = {"type": kind, "value": value}
        self._save()

    def clear_new_tab_background(self):
        self._data.pop("new_tab_background", None)
        self._save()


    def get_tab_suspension_enabled(self):
        return self._data.get("tab_suspension_enabled", True)

    def set_tab_suspension_enabled(self, enabled):
        self._data["tab_suspension_enabled"] = bool(enabled)
        self._save()
