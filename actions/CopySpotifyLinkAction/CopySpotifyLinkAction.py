import os
import threading
from loguru import logger
from src.backend.PluginManager.ActionBase import ActionBase


ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")


class CopySpotifyLinkAction(ActionBase):
    """Kopiert den Spotify-Link des aktuellen Tracks (via linkhop) in die Zwischenablage."""

    def on_ready(self):
        self.set_media(media_path=os.path.join(ASSETS, "copy_spotify.svg"), size=0.75)
        self.set_label("Spotify", font_size=12)

    def on_key_down(self):
        threading.Thread(target=self._copy_link, daemon=True).start()

    def _copy_link(self):
        backend = self.plugin_base.backend
        link = backend.get_platform_link("spotify")
        if link:
            backend.copy_to_clipboard(link)
            logger.info(f"CopySpotifyLinkAction: Link kopiert – {link}")
        else:
            logger.warning("CopySpotifyLinkAction: Spotify-Link nicht gefunden")
