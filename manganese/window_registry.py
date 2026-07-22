
_windows = []


def register(window):
    if window not in _windows:
        _windows.append(window)


def unregister(window):
    try:
        _windows.remove(window)
    except ValueError:
        pass


def all_windows():
    return list(_windows)


def window_at_global_pos(global_pos, exclude=None):
    for window in reversed(_windows):
        if window is exclude:
            continue
        try:
            if not window.isVisible():
                continue
            tab_bar = window.tabs.tabBar()
            local = tab_bar.mapFromGlobal(global_pos)
            if tab_bar.rect().contains(local):
                return window
        except RuntimeError:
            continue
    return None
