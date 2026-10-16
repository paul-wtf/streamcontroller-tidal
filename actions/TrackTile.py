import threading

from loguru import logger
from PIL import Image, ImageDraw


def _load_font():
    import globals as gl
    from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel

    defaults = gl.settings_manager.font_defaults
    label = KeyLabel(
        controller_input=None,
        font_name=defaults.get("font-family") or gl.fallback_font,
        font_size=TrackTile.FONT_SIZE,
        font_weight=round(defaults.get("font-weight") or 400),
        style=defaults.get("font-style") or "normal",
    )
    return (
        label.get_font(),
        tuple(defaults.get("font-color") or (255, 255, 255, 255)),
        round(defaults.get("outline-width") or 1),
        tuple(defaults.get("outline-color") or (0, 0, 0, 255)),
    )


def _load_svg(path: str, size: int) -> Image.Image:
    from src.backend.DeckManagement.HelperMethods import svg_to_pil

    return svg_to_pil(path, size, size)


class TrackTile:
    """Key image with text lines on a translucent bar; lines wider than the key scroll."""

    FONT_SIZE = 10
    FPS = 20
    HOLD_FRAMES = 30
    GAP = 20
    PADDING = 3
    LINE_SPACING = 2
    BAR_COLOR = (0, 0, 0, 150)

    def __init__(self, action):
        self._action = action
        self._lock = threading.Lock()
        self._style = None
        self._source = None
        self._base: Image.Image | None = None
        self._scale = 1.0
        self._lines: list[str] = []
        self._widths: list[float] = []
        self._frame = 0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def show(self, media_path: str, size: float, lines: list[str]):
        lines = [line for line in lines if line]
        key_size = tuple(self._action.deck_controller.get_key_image_size())
        source = (media_path, size, key_size)
        with self._lock:
            if source == self._source and lines == self._lines:
                return
        base = self._load_base(media_path, size, key_size)
        with self._lock:
            self._source = source
            self._base = base
            self._scale = size
            self._set_lines(lines)
        self._render()
        self._ensure_ticker()

    def set_lines(self, lines: list[str]):
        lines = [line for line in lines if line]
        with self._lock:
            if lines == self._lines or self._base is None:
                return
            self._set_lines(lines)
        self._render()
        self._ensure_ticker()

    def stop(self):
        self._stop.set()

    def _set_lines(self, lines: list[str]):
        font = self._get_style()[0]
        self._lines = lines
        self._widths = [font.getlength(line) for line in lines]
        self._frame = 0

    def _get_style(self):
        if self._style is None:
            self._style = _load_font()
        return self._style

    @staticmethod
    def _load_base(media_path: str, size: float, key_size: tuple[int, int]) -> Image.Image:
        if media_path.lower().endswith(".svg"):
            img = _load_svg(media_path, max(key_size))
        else:
            with Image.open(media_path) as src:
                img = src.convert("RGBA")
        img = img.convert("RGBA")
        return img.resize(key_size, Image.LANCZOS) if size >= 1 else img

    def _overflows(self) -> bool:
        if self._base is None:
            return False
        room = self._source[2][0] - 2 * self.PADDING
        return any(w > room for w in self._widths)

    def _ensure_ticker(self):
        with self._lock:
            if not self._overflows() or (self._thread and self._thread.is_alive()):
                return
            self._thread = threading.Thread(target=self._tick, daemon=True, name="TrackTileTicker")
            self._thread.start()

    def _tick(self):
        while not self._stop.wait(1 / self.FPS):
            with self._lock:
                if not self._overflows():
                    return
                self._frame += 1
            if self._action.get_is_present():
                self._render()

    def _compose(self) -> Image.Image | None:
        with self._lock:
            if self._base is None:
                return None
            base, scale, key_size = self._base, self._scale, self._source[2]
            lines = list(zip(self._lines, self._widths))
            frame = self._frame

        font, color, outline_width, outline_color = self._get_style()
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + self.LINE_SPACING
        bar_height = len(lines) * line_height + 2 * self.PADDING - self.LINE_SPACING if lines else 0
        top = key_size[1] - bar_height

        img = Image.new("RGBA", key_size, (0, 0, 0, 0))
        if scale >= 1:
            img.alpha_composite(base)
        else:
            side = round(min(min(key_size) * scale, top - self.PADDING))
            icon = base.resize((side, side), Image.LANCZOS)
            img.alpha_composite(icon, ((key_size[0] - side) // 2, (top - side) // 2))
        if not lines:
            return img

        bar = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(bar).rectangle((0, top, img.width, img.height), fill=self.BAR_COLOR)
        img.alpha_composite(bar)

        draw = ImageDraw.Draw(img)
        room = img.width - 2 * self.PADDING
        for i, (text, width) in enumerate(lines):
            y = top + self.PADDING + i * line_height + (ascent + descent) / 2
            style = dict(font=font, fill=color, stroke_width=outline_width, stroke_fill=outline_color)
            if width <= room:
                draw.text((img.width / 2, y), text, anchor="mm", **style)
                continue
            cycle = width + self.GAP
            offset = max(0, frame % (self.HOLD_FRAMES + round(cycle)) - self.HOLD_FRAMES)
            x = self.PADDING - offset
            draw.text((x, y), text, anchor="lm", **style)
            draw.text((x + cycle, y), text, anchor="lm", **style)
        return img

    def _render(self):
        try:
            img = self._compose()
            if img is not None:
                self._action.set_media(image=img, size=1.0)
        except Exception:
            logger.opt(exception=True).warning("TrackTile")
