import os
import threading
from loguru import logger
from src.backend.PluginManager.ActionBase import ActionBase


ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")


class CopyTidalLinkAction(ActionBase):
    """Kopiert den Tidal-Link des aktuellen Tracks in die Zwischenablage."""

    def on_ready(self):
        self.set_media(media_path=os.path.join(ASSETS, "copy_tidal.svg"), size=0.75)
        self.set_label("Tidal", font_size=12)

    def on_key_down(self):
        threading.Thread(target=self._copy_link, daemon=True).start()

    def _copy_link(self):
        backend = self.plugin_base.backend
        url = backend.state.track_url
        if not url:
            logger.warning("CopyTidalLinkAction: Kein Track-URL verfügbar")
            return

        # Versuche direkten Tidal-Link; als Fallback linkhop nutzen
        if "tidal.com" in url or url.startswith("tidal://"):
            link = url
        else:
            link = backend.get_platform_link("tidal") or url

        if link:
            backend.copy_to_clipboard(link)
            logger.info(f"CopyTidalLinkAction: Link kopiert – {link}")
        else:
            logger.warning("CopyTidalLinkAction: Tidal-Link nicht gefunden")
