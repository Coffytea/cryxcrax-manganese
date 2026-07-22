from PyQt6.QtCore import QBuffer, QByteArray
from PyQt6.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineUrlRequestJob


class ManganUrlSchemeHandler(QWebEngineUrlSchemeHandler):

    def __init__(self, browser_window, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window

    def requestStarted(self, job):
        try:
            url = job.requestUrl()
            page = (url.host() or "").lower()
            html = self.browser_window.build_internal_page(page, url)
            data = html.encode("utf-8")
            buf = QBuffer(self)
            buf.setData(QByteArray(data))
            buf.open(QBuffer.OpenModeFlag.ReadOnly)
            job.reply(b"text/html", buf)
        except Exception:
            try:
                job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            except Exception:
                pass
