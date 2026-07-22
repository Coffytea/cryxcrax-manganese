from collections import defaultdict
from PyQt6.QtNetwork import QNetworkCookie


def _domain_of(cookie):
    try:
        domain = cookie.domain()
    except Exception:
        domain = ""
    return domain.lstrip(".") or "(unknown)"


def _snapshot(cookie):
    return {
        "name": bytes(cookie.name()),
        "value": bytes(cookie.value()),
        "domain": cookie.domain(),
        "path": cookie.path(),
        "secure": cookie.isSecure(),
    }


def _rebuild_cookie(snapshot):
    cookie = QNetworkCookie(snapshot["name"], snapshot["value"])
    cookie.setDomain(snapshot["domain"])
    cookie.setPath(snapshot["path"])
    cookie.setSecure(snapshot["secure"])
    return cookie


class CookieTracker:

    def __init__(self, profile):
        self.profile = profile
        self._by_domain = defaultdict(dict)
        store = profile.cookieStore()
        store.cookieAdded.connect(self._on_added)
        store.cookieRemoved.connect(self._on_removed)
        try:
            store.loadAllCookies()
        except Exception:
            pass

    def _on_added(self, cookie):
        snap = _snapshot(cookie)
        domain = snap["domain"].lstrip(".") or "(unknown)"
        key = (snap["name"], snap["path"])
        self._by_domain[domain][key] = snap

    def _on_removed(self, cookie):
        snap = _snapshot(cookie)
        domain = snap["domain"].lstrip(".") or "(unknown)"
        key = (snap["name"], snap["path"])
        bucket = self._by_domain.get(domain)
        if not bucket:
            return
        bucket.pop(key, None)
        if not bucket:
            self._by_domain.pop(domain, None)

    def sites(self):
        return sorted((domain, len(cookies)) for domain, cookies in self._by_domain.items())

    def delete_site(self, domain):
        store = self.profile.cookieStore()
        for snap in list(self._by_domain.get(domain, {}).values()):
            try:
                store.deleteCookie(_rebuild_cookie(snap))
            except Exception:
                pass
        self._by_domain.pop(domain, None)

    def delete_all(self):
        self.profile.cookieStore().deleteAllCookies()
        self._by_domain.clear()
