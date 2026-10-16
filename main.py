import os
import sys

# Plugin-Verzeichnis in sys.path eintragen, damit lokale Importe funktionieren
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder

from backend.TidalBackend import TidalBackend
from actions.PlayPauseAction.PlayPauseAction import PlayPauseAction
from actions.NextAction.NextAction import NextAction
from actions.PreviousAction.PreviousAction import PreviousAction
from actions.NowPlayingAction.NowPlayingAction import NowPlayingAction
from actions.ShuffleAction.ShuffleAction import ShuffleAction
from actions.LoopAction.LoopAction import LoopAction
from actions.CopyTidalLinkAction.CopyTidalLinkAction import CopyTidalLinkAction
from actions.CopySpotifyLinkAction.CopySpotifyLinkAction import CopySpotifyLinkAction
from actions.CopyYTMusicLinkAction.CopyYTMusicLinkAction import CopyYTMusicLinkAction
from actions.CopyYouTubeLinkAction.CopyYouTubeLinkAction import CopyYouTubeLinkAction
from actions.VolumeUpAction.VolumeUpAction import VolumeUpAction
from actions.VolumeDownAction.VolumeDownAction import VolumeDownAction


class TidalControllerPlugin(PluginBase):
    """
    StreamController-Plugin für Tidal-Musiksteuerung via TidaLuna WebSocket-API.
    Benötigt TidaLuna mit aktiviertem TidalAPI-Plugin.
    """

    def __init__(self):
        super().__init__()

        # Gemeinsame Backend-Instanz für alle Actions
        self.backend = TidalBackend()

        # Actions registrieren
        self.play_pause_holder = ActionHolder(
            plugin_base=self,
            action_base=PlayPauseAction,
            action_id="wtf_paul_TidalController::PlayPause",
            action_name="Play / Pause",
        )
        self.add_action_holder(self.play_pause_holder)

        self.next_holder = ActionHolder(
            plugin_base=self,
            action_base=NextAction,
            action_id="wtf_paul_TidalController::Next",
            action_name="Nächster Track",
        )
        self.add_action_holder(self.next_holder)

        self.previous_holder = ActionHolder(
            plugin_base=self,
            action_base=PreviousAction,
            action_id="wtf_paul_TidalController::Previous",
            action_name="Vorheriger Track",
        )
        self.add_action_holder(self.previous_holder)

        self.now_playing_holder = ActionHolder(
            plugin_base=self,
            action_base=NowPlayingAction,
            action_id="wtf_paul_TidalController::NowPlaying",
            action_name="Aktueller Track",
        )
        self.add_action_holder(self.now_playing_holder)

        self.shuffle_holder = ActionHolder(
            plugin_base=self,
            action_base=ShuffleAction,
            action_id="wtf_paul_TidalController::Shuffle",
            action_name="Zufallswiedergabe",
        )
        self.add_action_holder(self.shuffle_holder)

        self.loop_holder = ActionHolder(
            plugin_base=self,
            action_base=LoopAction,
            action_id="wtf_paul_TidalController::Loop",
            action_name="Wiederholen",
        )
        self.add_action_holder(self.loop_holder)

        self.copy_tidal_holder = ActionHolder(
            plugin_base=self,
            action_base=CopyTidalLinkAction,
            action_id="wtf_paul_TidalController::CopyTidalLink",
            action_name="Tidal-Link kopieren",
        )
        self.add_action_holder(self.copy_tidal_holder)

        self.copy_spotify_holder = ActionHolder(
            plugin_base=self,
            action_base=CopySpotifyLinkAction,
            action_id="wtf_paul_TidalController::CopySpotifyLink",
            action_name="Spotify-Link kopieren",
        )
        self.add_action_holder(self.copy_spotify_holder)

        self.copy_ytmusic_holder = ActionHolder(
            plugin_base=self,
            action_base=CopyYTMusicLinkAction,
            action_id="wtf_paul_TidalController::CopyYTMusicLink",
            action_name="YouTube Music-Link kopieren",
        )
        self.add_action_holder(self.copy_ytmusic_holder)

        self.copy_youtube_holder = ActionHolder(
            plugin_base=self,
            action_base=CopyYouTubeLinkAction,
            action_id="wtf_paul_TidalController::CopyYouTubeLink",
            action_name="YouTube-Link kopieren",
        )
        self.add_action_holder(self.copy_youtube_holder)

        self.volume_up_holder = ActionHolder(
            plugin_base=self,
            action_base=VolumeUpAction,
            action_id="wtf_paul_TidalController::VolumeUp",
            action_name="Lauter",
        )
        self.add_action_holder(self.volume_up_holder)

        self.volume_down_holder = ActionHolder(
            plugin_base=self,
            action_base=VolumeDownAction,
            action_id="wtf_paul_TidalController::VolumeDown",
            action_name="Leiser",
        )
        self.add_action_holder(self.volume_down_holder)

        self.register(
            plugin_name="Tidal Controller",
            github_repo="https://github.com/SpotifyNutzeer/streamcontroller-tidal",
            plugin_version="1.0.0",
            app_version="1.5.0-beta",
        )

        logger.info("TidalControllerPlugin: Initialisiert")
