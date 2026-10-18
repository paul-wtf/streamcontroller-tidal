import os
import threading
from loguru import logger
from src.backend.PluginManager.ActionBase import ActionBase

from actions.TrackTile import TrackTile


ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")


class PlayPauseAction(ActionBase):
    """Play/Pause-Taste – zeigt beim Spielen Cover-Art und Songtitel an."""

    def on_ready(self):
        # StreamController's default on_update() calls on_ready() again on every redraw.
        if getattr(self, "_tile", None) is None:
            self._tile = TrackTile(self)
        self._tile.invalidate()
        self._last_cover_url = None
        self.set_label("")
        self._update_ui(self.plugin_base.backend.state)
        self.plugin_base.backend.add_callback(self._on_state_change)

    def on_remove(self):
        self.plugin_base.backend.remove_callback(self._on_state_change)
        self._tile.stop()

    def on_key_down(self):
        self.plugin_base.backend.toggle()

    def _on_state_change(self, state):
        self._update_ui(state)

    def _update_ui(self, state):
        if not state.connected:
            self._last_cover_url = None
            self._tile.show(os.path.join(ASSETS, "disconnected.svg"), 0.75, ["Getrennt"])
            return

        lines = [state.track_artist, state.track_title] if state.track_title else []
        if state.is_playing and state.track_title:
            if state.cover_url != self._last_cover_url:
                self._last_cover_url = state.cover_url
                threading.Thread(target=self._load_cover, args=(lines,), daemon=True).start()
            else:
                self._tile.set_lines(lines)
        else:
            self._last_cover_url = None
            self._tile.show(os.path.join(ASSETS, "play.svg"), 0.75, lines)

    def _load_cover(self, lines):
        cover_path = self.plugin_base.backend.get_cover_art_path()
        if cover_path:
            try:
                self._tile.show(cover_path, 1.0, lines)
                return
            except Exception as exc:
                logger.warning(f"PlayPauseAction: Cover konnte nicht gesetzt werden – {exc}")
        self._tile.show(os.path.join(ASSETS, "pause.svg"), 0.75, lines)
