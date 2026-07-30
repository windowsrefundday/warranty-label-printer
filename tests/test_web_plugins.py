import unittest
from typing import Dict, Any, Tuple, Optional

from interfaces.plugins.base import BaseWebPlugin
from interfaces.plugins.manager import WebPluginManager
from interfaces.plugins.mobile_camera_scanner import MobileCameraScannerPlugin, get_local_ip
from interfaces.web import WebInterfaceHandler


class DummyPlugin(BaseWebPlugin):
    @property
    def plugin_id(self) -> str:
        return "dummy_plugin"

    @property
    def name(self) -> str:
        return "Dummy Test Plugin"

    @property
    def icon(self) -> str:
        return "🧪"

    def get_css(self) -> str:
        return ".dummy-class { color: red; }"

    def get_content_html(self, host: str, port: int, public_url: Optional[str] = None) -> str:
        return f'<div class="dummy">Host: {host}:{port}</div>'


    def get_javascript(self) -> str:
        return "console.log('dummy plugin');"

    def handle_api_get(self, path: str, query_params: Dict[str, Any]) -> Optional[Tuple[int, Dict[str, Any]]]:
        if path == "/api/plugins/dummy_plugin/test":
            return 200, {"ok": True}
        return None


class WebPluginTests(unittest.TestCase):
    def test_plugin_manager_registration_and_aggregation(self):
        manager = WebPluginManager()
        plugin = DummyPlugin()
        manager.register_plugin(plugin)

        self.assertEqual(len(manager.list_plugins()), 1)
        self.assertIn(".dummy-class", manager.get_all_css())
        self.assertIn("tab_dummy_plugin", manager.get_all_tab_buttons())
        self.assertIn("dummy_pluginSection", manager.get_all_content_html("127.0.0.1", 9191))
        self.assertIn("console.log('dummy plugin');", manager.get_all_javascript())

    def test_plugin_manager_api_dispatch(self):
        manager = WebPluginManager()
        manager.register_plugin(DummyPlugin())

        res = manager.dispatch_api_get("/api/plugins/dummy_plugin/test", {})
        self.assertIsNotNone(res)
        assert res is not None
        self.assertEqual(res[0], 200)
        self.assertEqual(res[1], {"ok": True})

        unhandled = manager.dispatch_api_get("/api/plugins/dummy_plugin/unknown", {})
        self.assertIsNone(unhandled)

    def test_mobile_camera_scanner_plugin(self):
        plugin = MobileCameraScannerPlugin()
        self.assertEqual(plugin.plugin_id, "mobile_camera_scanner")
        self.assertIn("Phone Camera Scanner", plugin.name)

        css = plugin.get_css()
        self.assertIn(".viewfinder-container", css)
        self.assertIn(".reticle-box", css)

        html = plugin.get_content_html("192.168.1.100", 9191)
        self.assertIn("mobileCameraVideo", html)
        self.assertIn("btnToggleCamera", html)
        self.assertIn("btnFlipCamera", html)
        self.assertIn("btnTorch", html)
        self.assertIn("autoPrintOnScan", html)

        js = plugin.get_javascript()
        self.assertIn("MobileCameraScannerPluginController", js)
        self.assertIn("BarcodeDetector", js)

        status, payload = plugin.handle_api_get("/api/plugins/mobile_camera_scanner/info", {}) or (0, {})
        self.assertEqual(status, 200)
        self.assertTrue(payload.get("success"))
        self.assertIn("local_ip", payload)

    def test_get_local_ip(self):
        ip = get_local_ip()
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) > 0)

    def test_web_handler_renders_registered_plugins(self):
        html = WebInterfaceHandler.get_html_page(port=9191)
        self.assertIn("tab_mobile_camera_scanner", html)
        self.assertIn("mobile_camera_scannerSection", html)
        self.assertIn("mobileCameraVideo", html)
        self.assertIn("MobileCameraScannerPluginController", html)
