from PyQt6.QtCore import QTimer, QUrl

SUSPEND_AFTER_MS = 10 * 60 * 1000


class TabSuspender:

    def __init__(self, is_internal_url, enabled=True):
        self._is_internal_url = is_internal_url
        self.enabled = enabled
        self._timers = {}
        self._suspended_urls = {}

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            for timer in self._timers.values():
                timer.stop()

    def register_tab(self, browser):
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda b=browser: self._suspend(b))
        self._timers[browser] = timer

    def unregister_tab(self, browser):
        timer = self._timers.pop(browser, None)
        if timer is not None:
            timer.stop()
        self._suspended_urls.pop(browser, None)

    def on_active_tab_changed(self, all_browsers, active_browser):
        for browser in all_browsers:
            timer = self._timers.get(browser)
            if timer is None:
                continue
            if browser is active_browser:
                timer.stop()
                self._wake(browser)
            elif self.enabled:
                timer.start(SUSPEND_AFTER_MS)

    def _suspend(self, browser):
        try:
            url = browser.url()
        except RuntimeError:
            return
        if browser in self._suspended_urls:
            return
        if not url.isValid() or url.toString() in ("", "about:blank"):
            return
        if self._is_internal_url(url.toString()):
            return
        self._suspended_urls[browser] = url
        try:
            browser.setUrl(QUrl("about:blank"))
        except RuntimeError:
            pass

    def _wake(self, browser):
        url = self._suspended_urls.pop(browser, None)
        if url is None:
            return
        try:
            browser.setUrl(url)
        except RuntimeError:
            pass

    def is_suspended(self, browser):
        return browser in self._suspended_urls
