# Tidal Controller — StreamController Plugin

Control Tidal playback from your [StreamController](https://github.com/core447/StreamController)
deck. The plugin talks to the local HTTP/WebSocket API of the TidaLuna plugin TidalAPI, so you
don't need a Tidal API key.

https://github.com/paul-wtf/streamcontroller-tidal

## Requirements

- [TidaLuna](https://github.com/Inrixia/TidaLuna) installed in Tidal desktop
- The **TidalAPI** plugin from [FireWall-code/TidaLuna-Plugins](https://github.com/FireWall-code/TidaLuna-Plugins), enabled in TidaLuna. To install it, open Luna Settings → Plugin Store → Install from URL and paste
  `https://github.com/FireWall-code/TidaLuna-Plugins/releases/download/latest/store.json`.
  Leave its auth token setting empty, since this plugin does not send a token yet.
- If the deprecated `@vmohammad/api` plugin is still installed, disable it. Both listen on port 24123.
- StreamController ≥ 1.1.1-alpha
- Python packages `websockets` and `requests` (installed automatically by StreamController)

## Available Actions

| Action | What it does |
|---|---|
| Play / Pause | Toggle playback |
| Next Track | Skip to the next track |
| Previous Track | Go back to the previous track |
| Now Playing | Show current track title and artist on the key |
| Shuffle | Toggle shuffle mode |
| Loop | Cycle through loop modes (off / one / all) |
| Volume Up | Increase Tidal volume |
| Volume Down | Decrease Tidal volume |
| Copy Tidal Link | Copy the Tidal URL of the current track to clipboard |
| Copy Spotify Link | Copy a Spotify link for the current track (via linkhop) |
| Copy YouTube Music Link | Copy a YouTube Music link for the current track (via linkhop) |
| Copy YouTube Link | Copy a YouTube link for the current track (via linkhop) |

## Installation

Install via the StreamController plugin manager (search for "Tidal Controller"), or place this
directory under StreamController's plugin path manually:

```
~/.var/app/com.core447.StreamController/data/plugins/wtf_paul_TidalController/
```

Then restart StreamController.

## Attribution

Inspired by [streamdeck-tidal-plugin](https://github.com/SpotifyNutzeer/streamdeck-tidal-plugin).
Cross-platform music links provided by [linkhop](https://linkhop.paul.wtf).

## License

GPL-2.0-only — see [LICENSE](LICENSE).

Copyright (C) 2026 Paul Reitmayer
