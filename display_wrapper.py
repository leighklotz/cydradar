"""
PicoGraphics display wrapper providing a CYD-compatible drawing API.

On the Pimoroni Presto (PicoGraphics), drawing is pen-based:
  - Colors are integer pen indices created via display.create_pen(r, g, b)
  - display.circle() is always filled; outline circles must be approximated
  - display.rectangle() is always filled; outlines need 4 lines
  - Text uses display.text(string, x, y, wordwrap, scale)

This module wraps a PicoGraphics instance and exposes the CYD/ILI9341-style
method names used throughout radar.py, scope.py, and datatable.py.
"""

import math


class PixelFont:
    """
    Lightweight font descriptor for PicoGraphics text drawing.

    PicoGraphics uses a built-in bitmap font; the 'scale' parameter controls
    the character size (each unit adds ~8 pixels of height and ~6 pixels of
    width per character).
    """
    def __init__(self, scale=1):
        self.scale = scale
        self.height = scale * 8   # 8 pixels per scale unit
        self.width = scale * 6    # ~6 pixels wide per character at scale 1


class PicoDisplay:
    """
    Wrapper around a PicoGraphics display instance that provides the
    CYD ILI9341-compatible drawing API used by scope.py and datatable.py.

    Color values passed to drawing methods should be PicoGraphics pen
    indices (integers returned by display.create_pen(r, g, b)).  As a
    convenience, (r, g, b) tuples are also accepted and will be converted
    on the fly, though pre-creating pens at start-up is preferred.
    """

    def __init__(self, display):
        """
        Args:
            display: a PicoGraphics instance (e.g. presto.display)
        """
        self._d = display
        self.width, self.height = display.get_bounds()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_pen(self, color):
        """Accept a pen index or an (r, g, b) tuple and set it as current pen."""
        if isinstance(color, tuple):
            color = self._d.create_pen(*color)
        self._d.set_pen(color)

    # ------------------------------------------------------------------
    # Public drawing API (CYD-compatible)
    # ------------------------------------------------------------------

    def draw_line(self, x1, y1, x2, y2, color):
        self._set_pen(color)
        self._d.line(x1, y1, x2, y2)

    def draw_circle(self, cx, cy, r, color):
        """Draw a circle outline using short line segments (PicoGraphics only has filled circles)."""
        self._set_pen(color)
        steps = max(16, r)
        angle_step = 2 * math.pi / steps
        prev_x = cx + r
        prev_y = cy
        for i in range(1, steps + 1):
            angle = i * angle_step
            next_x = int(cx + r * math.cos(angle))
            next_y = int(cy + r * math.sin(angle))
            self._d.line(int(prev_x), int(prev_y), next_x, next_y)
            prev_x = next_x
            prev_y = next_y

    def fill_circle(self, cx, cy, r, color):
        self._set_pen(color)
        self._d.circle(cx, cy, r)

    def draw_rectangle(self, x, y, w, h, color):
        """Draw a rectangle outline using 4 line segments."""
        self._set_pen(color)
        x1, y1 = x + w - 1, y + h - 1
        self._d.line(x, y, x1, y)
        self._d.line(x1, y, x1, y1)
        self._d.line(x1, y1, x, y1)
        self._d.line(x, y1, x, y)

    def fill_rectangle(self, x, y, w, h, color):
        self._set_pen(color)
        self._d.rectangle(x, y, w, h)

    def draw_text(self, x, y, text, font, color, background=None):
        """
        Draw text using PicoGraphics built-in font.

        Args:
            x, y: top-left pixel coordinates
            text: string to draw
            font: PixelFont instance (scale used for text size) or None for scale=1
            color: pen index or (r, g, b) tuple
            background: optional pen index or (r, g, b) tuple to clear behind text
        """
        scale = font.scale if font is not None else 1
        char_w = scale * 6
        text_w = len(text) * char_w
        text_h = scale * 8
        if background is not None:
            self._set_pen(background)
            self._d.rectangle(x, y, text_w, text_h)
        self._set_pen(color)
        self._d.text(str(text), x, y, -1, scale)

    def draw_text8x8(self, x, y, text, color, background=None):
        """Draw text using the default scale-1 font (8×8 equivalent)."""
        self.draw_text(x, y, text, None, color, background)

    def clear(self, color=None):
        """
        Clear the display.

        Args:
            color: optional pen index or (r, g, b) tuple to use as fill colour.
                   If None the currently active pen is used.
        """
        if color is not None:
            self._set_pen(color)
        self._d.clear()
