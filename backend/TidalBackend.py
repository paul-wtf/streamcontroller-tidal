import asyncio
import json
import threading
import hashlib
import os
import tempfile
import subprocess
import time

import requests
from loguru import logger

try:
    import websockets
except ImportError:
    websockets = None


class TidalState:
    def __init__(self):
        self.is_playing: bool = False
        self.shuffle: bool = False
        self.repeat: int = 0          # 0=off, 1=all, 2=one
        self.track_title: str | None = None
        self.track_artist: str | None = None
        self.track_album: str | None = None
        self.cover_url: str | None = None
        self.track_url: str | None = None
        self.volume: int = 0
        self.connected: bool = False


class TidalBackend:
    """
    Verwaltet die WebSocket-Verbindung zu TidaLuna (@vmohammad/api Plugin).
    Endpoint: ws://127.0.0.1:24123/

    Gemeinsame Instanz für alle Actions, die über Callbacks über
    Statusänderungen informiert werden.
    """

    WS_URL = "ws://127.0.0.1:24123/"
    LINKHOP_URL = "https://linkhop.paul.wtf/api/v1/convert"
    RECONNECT_DELAY = 5
    # Felder, die _handle_message tatsaechlich auswertet. Wir abonnieren nur
    # diese, damit der Server nicht dauerhaft die komplette playQueue
    # mitstreamt (~490 KB/Nachricht, ~31 Mbit/s).
    SUBSCRIBE_FIELDS = [
        "playing", "shuffle", "repeatMode",
        "track", "artist", "album", "volume", "coverUrl",
    ]

    def __init__(self):
        self.state = TidalState()
        self._callbacks: list = []
        self._callbacks_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws = None
        self._cover_cache_dir = os.path.join(tempfile.gettempdir(), "streamcontroller_tidal_covers")
        os.makedirs(self._cover_cache_dir, exist_ok=True)

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="TidalBackendWS")
        self._thread.start()

    # ------------------------------------------------------------------ #
    # WebSocket-Thread                                                     #
    # ------------------------------------------------------------------ #

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._ws_loop())

    async def _ws_loop(self):
        while True:
            try:
                async with websockets.connect(self.WS_URL, ping_interval=20) as ws:
                    self._ws = ws
                    self.state.connected = True
                    logger.info("TidalBackend: WebSocket verbunden")
                    # all:True liefert beim Verbinden einmalig einen
                    # vollstaendigen Snapshot, damit die Kachel sofort den
                    # aktuellen Track zeigt. Direkt nach dem ersten Snapshot
                    # schalten wir per all:False auf SUBSCRIBE_FIELDS herunter,
                    # damit der Server nicht dauerhaft die playQueue streamt.
                    await ws.send(json.dumps({"action": "subscribe", "all": True, "fields": []}))
                    self._notify()

                    downgraded = False
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning(f"TidalBackend: Ungültige JSON-Nachricht: {raw!r}")
                            continue
                        self._handle_message(data)
                        # Nach dem ersten echten Snapshot den Firehose abschalten.
                        if not downgraded and isinstance(data, dict) and data.get("type") == "update":
                            await ws.send(json.dumps({
                                "action": "subscribe",
                                "all": False,
                                "fields": self.SUBSCRIBE_FIELDS,
                            }))
                            downgraded = True

            except Exception as exc:
                logger.warning(f"TidalBackend: Verbindungsfehler – {exc}")
            finally:
                self._ws = None
                self.state.connected = False
                self._notify()

            await asyncio.sleep(self.RECONNECT_DELAY)

    # ------------------------------------------------------------------ #
    # Nachrichtenverarbeitung                                              #
    # ------------------------------------------------------------------ #

    def _handle_message(self, data: dict):
        # TidaLuna sendet je nach Subscription zwei Formen:
        #   all:true  -> {"type":"update","all":true,"fields":{ ... }}        (Snapshot)
        #   all:false -> {"type":"update","all":false,"field":"x","value":y}  (Einzelfeld)
        # Wir abonnieren nach dem ersten Snapshot per all:false, deshalb MUESSEN
        # beide Formen behandelt werden – sonst werden alle weiteren Updates
        # ignoriert und die Kachel friert nach dem Start ein.
        if data.get("type") != "update":
            return

        if "fields" in data:
            f = data.get("fields") or {}
        elif "field" in data:
            f = {data["field"]: data.get("value")}
        else:
            f = {}
        changed = False

        # Wiedergabestatus: f["playing"] ist ein boolean
        if "playing" in f:
            playing = bool(f["playing"])
            if self.state.is_playing != playing:
                self.state.is_playing = playing
                changed = True

        # Shuffle
        if "shuffle" in f:
            shuffle = bool(f["shuffle"])
            if self.state.shuffle != shuffle:
                self.state.shuffle = shuffle
                changed = True

        # Repeat-Modus: 0=off, 1=all, 2=one
        if "repeatMode" in f:
            try:
                mode = int(f["repeatMode"])
            except (ValueError, TypeError):
                mode = 0
            if self.state.repeat != mode:
                self.state.repeat = mode
                changed = True

        # Track-Titel: f["track"]["title"]
        track = f.get("track") or {}
        if track.get("title"):
            if self.state.track_title != track["title"]:
                self.state.track_title = track["title"]
                changed = True

        # Künstler: f["artist"]["name"]
        artist_obj = f.get("artist") or {}
        artist_name = artist_obj.get("name") or track.get("artist", {}).get("name")
        if artist_name and self.state.track_artist != artist_name:
            self.state.track_artist = artist_name
            changed = True

        # Album-Titel: f["album"]["title"]
        album_obj = f.get("album") or {}
        album_title = album_obj.get("title") or track.get("album", {}).get("title")
        if album_title and self.state.track_album != album_title:
            self.state.track_album = album_title
            changed = True

        # Lautstärke
        if "volume" in f:
            try:
                vol = int(f["volume"])
            except (ValueError, TypeError):
                vol = 0
            if self.state.volume != vol:
                self.state.volume = vol
                changed = True

        # Cover-URL: direkt in f["coverUrl"]
        cover_url = f.get("coverUrl")
        if cover_url and self.state.cover_url != cover_url:
            self.state.cover_url = cover_url
            changed = True

        # Track-URL: f["track"]["url"]
        track_url = track.get("url")
        if track_url and self.state.track_url != track_url:
            self.state.track_url = track_url
            changed = True

        if changed:
            self._notify()

    # ------------------------------------------------------------------ #
    # Aktionen senden                                                      #
    # ------------------------------------------------------------------ #

    def send(self, payload: dict):
        if self._ws is None or self._loop is None:
            logger.warning("TidalBackend: Nicht verbunden – Aktion wird ignoriert")
            return
        asyncio.run_coroutine_threadsafe(
            self._send_async(json.dumps(payload)),
            self._loop,
        )

    async def _send_async(self, message: str):
        try:
            await self._ws.send(message)
        except Exception as exc:
            logger.error(f"TidalBackend: Sendefehler – {exc}")

    def toggle(self):
        self.send({"action": "toggle"})

    def next_track(self):
        self.send({"action": "next"})

    def previous_track(self):
        self.send({"action": "previous"})

    def set_shuffle(self, enabled: bool):
        self.send({"action": "setShuffleMode", "shuffle": enabled})

    def set_repeat(self, mode: int):
        self.send({"action": "setRepeatMode", "mode": mode})

    def volume_up(self):
        self._http_post("volume", {"volume": "+5"})

    def volume_down(self):
        self._http_post("volume", {"volume": "-5"})

    def _http_post(self, endpoint: str, body: dict):
        """Sendet einen HTTP-POST an die TidaLuna-API (http://localhost:24123/<endpoint>)."""
        threading.Thread(target=self._http_post_sync, args=(endpoint, body), daemon=True).start()

    def _http_post_sync(self, endpoint: str, body: dict):
        try:
            requests.post(f"http://127.0.0.1:24123/{endpoint}", json=body, timeout=5)
        except Exception as exc:
            logger.warning(f"TidalBackend: HTTP-POST /{endpoint} fehlgeschlagen – {exc}")

    # ------------------------------------------------------------------ #
    # Cover-Art                                                            #
    # ------------------------------------------------------------------ #

    def get_cover_art_path(self) -> str | None:
        url = self.state.cover_url
        if not url:
            return None
        ext = url.split(".")[-1].split("?")[0].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        fname = hashlib.md5(url.encode()).hexdigest() + "." + ext
        fpath = os.path.join(self._cover_cache_dir, fname)
        if not os.path.exists(fpath):
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                with open(fpath, "wb") as f:
                    f.write(resp.content)
            except Exception as exc:
                logger.warning(f"TidalBackend: Cover-Art konnte nicht heruntergeladen werden – {exc}")
                return None
        return fpath

    # ------------------------------------------------------------------ #
    # linkhop – plattformübergreifende Links                              #
    # ------------------------------------------------------------------ #

    # linkhop-Service-IDs. linkhop kennt kein reines YouTube – 'youtube'
    # wird über den YouTube-Music-Link abgebildet und dessen URL
    # (music.youtube.com/watch?v=...) auf www.youtube.com umgeschrieben.
    PLATFORM_KEYS = {
        "tidal":   "tidal",
        "spotify": "spotify",
        "ytmusic": "youtube_music",
        "youtube": "youtube_music",
    }

    def get_platform_link(self, platform: str) -> str | None:
        """
        Gibt den Musik-Link für die angegebene Plattform zurück.
        platform: 'tidal' | 'spotify' | 'ytmusic' | 'youtube'
        """
        url = self.state.track_url
        if not url:
            logger.warning("TidalBackend: Kein aktueller Track-URL bekannt")
            return None
        try:
            resp = requests.get(
                self.LINKHOP_URL,
                params={"url": url},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            key = self.PLATFORM_KEYS.get(platform, platform)

            # Der Quelldienst taucht nicht in 'targets' auf, sondern nur
            # als kanonische URL in 'source'.
            source = data.get("source", {})
            if source.get("service") == key:
                link = source.get("url")
            else:
                entry = data.get("targets", {}).get(key)
                if not entry or entry.get("status") not in ("ok", "ok_low"):
                    logger.warning(f"TidalBackend: Plattform '{platform}' nicht in linkhop-Antwort gefunden")
                    return None
                link = entry.get("url")

            if link and platform == "youtube":
                link = link.replace("music.youtube.com", "www.youtube.com")
            return link
        except Exception as exc:
            logger.error(f"TidalBackend: linkhop-Fehler – {exc}")
            return None

    # ------------------------------------------------------------------ #
    # Clipboard                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def copy_to_clipboard(text: str):
        try:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True, timeout=5)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        try:
            subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True, timeout=5)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        try:
            subprocess.run(["wl-copy"], input=text.encode(), check=True, timeout=5)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        logger.error("TidalBackend: Kein Clipboard-Tool gefunden (xclip / xsel / wl-copy)")

    # ------------------------------------------------------------------ #
    # Callback-Verwaltung                                                  #
    # ------------------------------------------------------------------ #

    def add_callback(self, cb):
        with self._callbacks_lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def remove_callback(self, cb):
        with self._callbacks_lock:
            try:
                self._callbacks.remove(cb)
            except ValueError:
                pass

    def _notify(self):
        with self._callbacks_lock:
            cbs = list(self._callbacks)
        for cb in cbs:
            try:
                cb(self.state)
            except Exception as exc:
                logger.error(f"TidalBackend: Callback-Fehler – {exc}")
