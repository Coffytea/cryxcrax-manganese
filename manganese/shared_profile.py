import os

from PyQt6.QtWebEngineCore import QWebEngineProfile

from manganese.paths import webengine_profile_dir
from manganese.cookies import CookieTracker
from manganese.history import HistoryStore
from manganese.prefs import Prefs

_profile = None
_cookie_tracker = None
_history_store = None
_prefs = None
_mangan_scheme_handler = None
_downloads_list = None
_download_signal_connected = False


def get_shared_downloads_list():
    global _downloads_list
    if _downloads_list is None:
        _downloads_list = []
    return _downloads_list


def is_download_signal_connected():
    return _download_signal_connected


def mark_download_signal_connected():
    global _download_signal_connected
    _download_signal_connected = True


def get_mangan_scheme_handler():
    return _mangan_scheme_handler


def set_mangan_scheme_handler(handler):
    global _mangan_scheme_handler
    _mangan_scheme_handler = handler


def get_shared_profile(parent):
    global _profile, _cookie_tracker
    if _profile is not None:
        return _profile

    profile = QWebEngineProfile("Default", parent)
    profile.setPersistentStoragePath(webengine_profile_dir())
    profile.setCachePath(os.path.join(webengine_profile_dir(), "Cache"))
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )
    settings = profile.settings()
    settings.setAttribute(settings.WebAttribute.WebGLEnabled, True)
    settings.setAttribute(settings.WebAttribute.Accelerated2dCanvasEnabled, True)
    settings.setAttribute(settings.WebAttribute.PrintElementBackgrounds, True)
    try:
        settings.setAttribute(settings.WebAttribute.PdfViewerEnabled, True)
    except AttributeError:
        pass
    try:
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
    except AttributeError:
        pass

    _profile = profile
    _cookie_tracker = CookieTracker(profile)
    return _profile


def get_shared_cookie_tracker():
    return _cookie_tracker


def get_shared_history_store():
    global _history_store
    if _history_store is None:
        _history_store = HistoryStore()
    return _history_store


def get_shared_prefs():
    global _prefs
    if _prefs is None:
        _prefs = Prefs()
    return _prefs
