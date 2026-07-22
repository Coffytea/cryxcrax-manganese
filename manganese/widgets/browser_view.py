from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage


class CustomWebEnginePage(QWebEnginePage):
    parent_browser = None

    def createWindow(self, window_type):
        if self.parent_browser:
            self.parent_browser.add_tab(QUrl("about:blank"), "New Tab")
            new_browser = self.parent_browser.current_browser()
            return new_browser.page()

        return CustomWebEnginePage(self.profile(), self)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if url.scheme() == "mangan" and (url.host() or "").lower() == "action":
            if self.parent_browser is not None:
                self.parent_browser.handle_internal_action(url, self)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class BrowserView(QWebEngineView):

    def __init__(self, profile=None, parent_window=None, parent=None):
        super().__init__(parent)
        if profile:
            custom_page = CustomWebEnginePage(profile, self)
            custom_page.parent_browser = parent_window
            self.setPage(custom_page)
        self.parent_window = parent_window

    def contextMenuEvent(self, event):
        self._context_event = event
        self._context_global_pos = event.globalPos()

        local_pos = event.pos()

        js = f"""
        (function() {{
            var x = {local_pos.x()};
            var y = {local_pos.y()};
            var elem = document.elementFromPoint(x, y);
            if (!elem) elem = document.body;

            var imgUrl = '';
            var linkUrl = '';

            if (elem.tagName === 'IMG') {{
                imgUrl = elem.src || elem.currentSrc || '';
            }}
            if (elem.tagName === 'A') {{
                linkUrl = elem.href || '';
            }}

            var parent = elem;
            while (parent && !imgUrl) {{
                if (parent.tagName === 'IMG') {{
                    imgUrl = parent.src || parent.currentSrc || '';
                    break;
                }}
                parent = parent.parentElement;
            }}

            parent = elem;
            while (parent && !linkUrl) {{
                if (parent.tagName === 'A') {{
                    linkUrl = parent.href || '';
                    break;
                }}
                parent = parent.parentElement;
            }}

            return {{img: imgUrl, link: linkUrl}};
        }})();
        """

        def on_result(data):
            self._build_context_menu(data, self._context_global_pos)

        self.page().runJavaScript(js, on_result)

    def _build_context_menu(self, data, global_pos):
        menu = QMenu(self)

        if not data:
            data = {'img': '', 'link': ''}

        img_url = data.get('img', '')
        link_url = data.get('link', '')

        if img_url:
            action_copy_img = menu.addAction("Copy Image")
            action_copy_img.triggered.connect(lambda: self._copy_image_url(img_url))

            action_open_img = menu.addAction("Open Image in New Tab")
            action_open_img.triggered.connect(lambda: self._open_in_new_tab(img_url))

            action_save_img = menu.addAction("Save Image As")
            action_save_img.triggered.connect(lambda: self._save_image(img_url))

            menu.addSeparator()

        if link_url:
            action_copy_link = menu.addAction("Copy Link")
            action_copy_link.triggered.connect(lambda: self._copy_link(link_url))
            menu.addSeparator()

        inspect_action = menu.addAction("Inspect")
        def do_inspect():
            try:
                if self.parent_window:
                    self.parent_window.toggle_devtools()
                if hasattr(self, '_devtools') and self._devtools:
                    self._devtools.show()
                self.page().triggerAction(QWebEnginePage.WebAction.InspectElement)
            except Exception:
                pass
        inspect_action.triggered.connect(do_inspect)

        menu.exec(global_pos)

    def _copy_image_url(self, url):
        try:
            QGuiApplication.clipboard().setText(url)
        except Exception:
            pass

    def _copy_link(self, url):
        try:
            QGuiApplication.clipboard().setText(url)
        except Exception:
            pass

    def _open_in_new_tab(self, url):
        try:
            if self.parent_window:
                self.parent_window.add_tab(QUrl(url), "New Tab")
        except Exception:
            pass

    def _save_image(self, url):
        try:
            if self.parent_window:
                self.parent_window.save_image_as(url)
        except Exception as e:
            print(f"Error saving image: {e}")
