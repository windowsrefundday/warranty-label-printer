from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any

class BaseWebPlugin(ABC):
    """
    Abstract base class for web interface plugins.
    Allows modular extension of web UI, styling, client scripts, and custom API endpoints.
    """

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for the plugin (e.g. 'mobile_camera_scanner')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name for the plugin."""
        pass

    @property
    def icon(self) -> str:
        """Icon or emoji representing the plugin."""
        return "🔌"

    def get_css(self) -> str:
        """Return custom CSS to be injected into the main page head."""
        return ""

    def get_tab_button_html(self) -> str:
        """Return HTML for the navigation tab button."""
        return f'<button id="tab_{self.plugin_id}" class="tab-btn" onclick="switchTab(\'{self.plugin_id}\')">{self.icon} {self.name}</button>'

    @abstractmethod
    def get_content_html(self, host: str, port: int, public_url: Optional[str] = None) -> str:
        """Return HTML content for the main plugin view container."""
        pass


    def get_javascript(self) -> str:
        """Return custom JavaScript to be injected before </body>."""
        return ""

    def handle_api_get(self, path: str, query_params: Dict[str, Any]) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Handle plugin-specific GET requests (e.g., /api/plugins/<plugin_id>/...).
        Returns (http_status_code, json_payload_dict) or None if unhandled.
        """
        return None

    def handle_api_post(self, path: str, body_data: Dict[str, Any]) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Handle plugin-specific POST requests (e.g., /api/plugins/<plugin_id>/...).
        Returns (http_status_code, json_payload_dict) or None if unhandled.
        """
        return None
