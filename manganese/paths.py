import os


def app_data_dir():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "Manganese")
    else:
        path = os.path.expanduser("~/.manganese")
    os.makedirs(path, exist_ok=True)
    return path


def webengine_profile_dir():
    path = os.path.join(app_data_dir(), "WebProfile")
    os.makedirs(path, exist_ok=True)
    return path


def history_csv_path():
    return os.path.join(app_data_dir(), "history.csv")


def prefs_path():
    return os.path.join(app_data_dir(), "prefs.json")
