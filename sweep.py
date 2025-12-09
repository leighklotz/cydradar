# sweep.py -- Radar sweep widget (updated)
# - Implements a sweep/segment drawing widget with a trailing faint-green trail
# - Restores and draws per-pip labels when illuminated
# - MicroPython-safe (no math.hypot); uses squared-distance tests where possible
#
# Usage:
#   from sweep import RadarSweepScope
#   radar = RadarSweepScope(fb, center_x=120, center_y=80, radius=70,
#                           segments=60, radius_step=2, trail_length=3,
#                           beam_color=None, static_color=None, bg_color=None,
#                           show_pip_labels=True)
#   radar.draw(aircraft_list)        # full draw or one sweep step depending on call
#   radar.draw(aircraft_list, sweep=False)  # full redraw
#   radar.step(aircraft_list)        # advance one sweep step (alias)
#   radar.sweep()                    # reuse last aircraft_list and advance one step
#
import math
import utime

# Default colors (16-bit RGB565 numeric values). If your code has color helpers,
# you can pass explicit numeric values when creating the RadarSweepScope instance.
# These defaults are green-ish placeholders; replace them if necessary.
DEFAULT_BEAM = 0x07E0    # bright green
DEFAULT_STATIC = 0x03A0  # dim green
DEFAULT_BG = 0x0000      # black
DEFAULT_MIL = 0xF800     # red for military

# --- RGB565 helpers (small, efficient) ---
def _rgb565_to_components(c):
    # returns integer (r5, g6, b5)
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return r, g, b

def _components_to_rgb565(r, g, b):
    # clamp and pack
    if r < 0: r = 0
    if r > 0x1F: r = 0x1F
    if g < 0: g = 0
    if g > 0x3F: g = 0x3F
    if b < 0: b = 0
    if b > 0x1F: b = 0x1F
    return (int(r) << 11) | (int(g) << 5) | int(b)

def _blend_rgb565(c_from, c_to, t):
    # Blend c_from -> c_to with t in [0..1]. Lightweight integer math.
    if t <= 0.0:
        return c_from
    if t >= 1.0:
        return c_to
    rf, gf, bf = _rgb565_to_components(c_from)
    rt, gt, bt = _rgb565_to_components(c_to)
    # compute blended components (use integer arithmetic)
    r = rf + int((rt - rf) * t)
    g = gf + int((gt - gf) * t)
    b = bf + int((bt - bf) * t)
    return _components_to_rgb565(r, g, b)

class RadarSweepScope:
    def __init__(
        self,
        fb,
        center_x,
        center_y,
        radius,
        segments=60,
        radius_step=2,
        beam_color=None,
        static_color=None,
        bg_color=None,
        mil_color=None,
        trail_length=3,
        show_pip_labels=True,
        font=None,
        draw_ring_labels=False
    ):
        """
        fb: display object (must implement draw_line, fill_circle, draw_text8x8, draw_lines, draw_rectangle)
        center_x, center_y, radius: geometry
        segments: number of angular wedges
        radius_step: pixel step for wedge fill
        beam_color/static_color/bg_color/mil_color: numeric RGB565 colors (optional)
        trail_length: number of trailing segments to keep as a dim trail (0 disables)
        show_pip_labels: draw short callsign label when a pip is illuminated
        font: optional font object; if provided, draw_text will be used
        draw_ring_labels: optionally draw distance labels on the sweep display
        """
        self.fb = fb
        self.center_x = int(center_x)
        self.center_y = int(center_y)
        self.radius = int(radius)
        self.segments = max(3, int(segments))
        self.radius_step = max(1, int(radius_step))
        self.trail_length = max(0, int(trail_length))
        self.show_pip_labels = bool(show_pip_labels)
        self.font = font
        self.draw_ring_labels = draw_ring_labels

        self.beam_color = beam_color if beam_color is not None else DEFAULT_BEAM
        self.static_color = static_color if static_color is not None else DEFAULT_STATIC
        self.bg_color = bg_color if bg_color is not None else DEFAULT_BG
        self.mil_color = mil_color if mil_color is not None else DEFAULT_MIL

        # sweep internal state
        self._cur_seg = 0
        self._bg_drawn = False

        # cached last aircraft list so step()/sweep() can be called without args
        self._last_aircraft_list = None

        # precompute trig and bounds
        self._seg_angle = 2 * math.pi / self.segments
        self._seg_trig = []
        for i in range(self.segments):
            sa = i * self._seg_angle
            ea = (i + 1) * self._seg_angle
            self._seg_trig.append((math.cos(sa), math.sin(sa), math.cos(ea), math.sin(ea)))

        # precompute trail colors (blend beam -> static)
        if self.trail_length > 0:
            self._trail_colors = []
            for j in range(1, self.trail_length + 1):
                # t rises as j increases -> farther segments are closer to static color
                t = j / (self.trail_length + 1)
                self._trail_colors.append(_blend_rgb565(self.beam_color, self.static_color, t))
        else:
            self._trail_colors = []

        # draw background once
        self._draw_static_background()

    def _draw_static_background(self):
        if self._bg_drawn:
            return
        fb = self.fb
        cx = self.center_x
        cy = self.center_y
        r = self.radius

        # draw ring bodies using fill_circle if available
        if False and hasattr(fb, "fill_circle"):
            fb.fill_circle(cx, cy, r, self.static_color)
            fb.fill_circle(cx, cy, r - 3, self.bg_color)
            # smaller rings
            fb.fill_circle(cx, cy, int(r * 2 / 3), self.static_color)
            fb.fill_circle(cx, cy, int(r * 2 / 3) - 2, self.bg_color)
            fb.fill_circle(cx, cy, int(r * 1 / 3), self.static_color)
            fb.fill_circle(cx, cy, int(r * 1 / 3) - 2, self.bg_color)
        else:
            # fallback: draw coarse polylines for rings
            step = 30
            for rr in (r, int(r * 2 / 3), int(r * 1 / 3)):
                coords = []
                for deg in range(0, 360 + step, step):
                    rad = math.radians(deg % 360)
                    coords.append([int(cx + rr * math.cos(rad)), int(cy + rr * math.sin(rad))])
                if coords and coords[0] != coords[-1]:
                    coords.append(coords[0])
                fb.draw_lines(coords, self.static_color)

        # crosshairs and center dot
        fb.draw_line(cx - r, cy, cx + r, cy, self.static_color)
        fb.draw_line(cx, cy - r, cx, cy + r, self.static_color)
        fb.fill_circle(cx, cy, 2, self.static_color)

        if self.draw_ring_labels:
            # ring labels (draw once)
            labels = [ "{}NM".format(int(i * 1/3 * 30)) for i in (3, 2, 1) ]  # approximate labels (adjust as needed)
            # place labels near rightmost edge of each ring
            for rr, label in zip((r, int(r * 2 / 3), int(r * 1 / 3)), labels):
                lx = cx + rr - 20
                ly = cy + 5
                if self.font is not None and hasattr(self.fb, "draw_text"):
                    self.fb.draw_text(lx, ly, label, self.font, self.static_color, self.bg_color)
                else:
                    try:
                        self.fb.draw_text8x8(lx, ly, label, self.static_color, background=self.bg_color)
                    except TypeError:
                        self.fb.draw_text8x8(lx, ly, label, self.static_color)

        self._bg_drawn = True

    def _angle_of_point(self, x, y):
        return (math.atan2(y - self.center_y, x - self.center_x) + 2 * math.pi) % (2 * math.pi)

    def _inside_radius_sq(self, x, y):
        dx = x - self.center_x
        dy = y - self.center_y
        return dx * dx + dy * dy <= self.radius * self.radius

    def _aircraft_screen_pos(self, ac):
        """
        Map aircraft lat/lon to screen coords. This widget uses a simple centered scale:
        sx = cx + lon * (radius * 2)
        sy = cy - lat * (radius * 2)
        This matches prior simple mapping used in examples. If you have geospatial mapping
        requirements, replace this mapping accordingly.
        """
        sx = int(self.center_x + ac.lon * (self.radius * 2))
        sy = int(self.center_y - ac.lat * (self.radius * 2))
        if self._inside_radius_sq(sx, sy):
            return sx, sy
        return None

    def _fill_segment(self, seg_idx, color):
        fb = self.fb
        cx = self.center_x
        cy = self.center_y
        cos_s, sin_s, cos_e, sin_e = self._seg_trig[seg_idx]
        for rr in range(0, self.radius + 1, self.radius_step):
            x1 = cx + int(rr * cos_s)
            y1 = cy + int(rr * sin_s)
            x2 = cx + int(rr * cos_e)
            y2 = cy + int(rr * sin_e)
            fb.draw_line(x1, y1, x2, y2, color)

    def _restore_static_for_segment(self, seg_idx):
        """
        Re-draw static elements so rings/crosshairs/labels remain visible after clearing.
        For simplicity we redraw full rings and crosshair (cheap relative to clearing large regions).
        """
        fb = self.fb
        cx = self.center_x
        cy = self.center_y
        # coarse rings
        step = 30
        for rr in (self.radius, int(self.radius * 2 / 3), int(self.radius * 1 / 3)):
            coords = []
            for deg in range(0, 360 + step, step):
                rad = math.radians(deg % 360)
                coords.append([int(cx + rr * math.cos(rad)), int(cy + rr * math.sin(rad))])
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            fb.draw_lines(coords, self.static_color)
        # crosshair
        fb.draw_line(cx - self.radius, cy, cx + self.radius, cy, self.static_color)
        fb.draw_line(cx, cy - self.radius, cx, cy + self.radius, self.static_color)
        fb.fill_circle(cx, cy, 2, self.static_color)
        if self.draw_ring_labels:
            # ring labels (redraw)
            # todo: eliminate duplicate code
            labels = [ "{}NM".format(int(i * 1/3 * 30)) for i in (3, 2, 1) ]
            for rr, label in zip((self.radius, int(self.radius * 2 / 3), int(self.radius * 1 / 3)), labels):
                lx = cx + rr - 20
                ly = cy + 5
                if self.font is not None and hasattr(self.fb, "draw_text"):
                    self.fb.draw_text(lx, ly, label, self.font, self.static_color, self.bg_color)
                else:
                    try:
                        self.fb.draw_text8x8(lx, ly, label, self.static_color, background=self.bg_color)
                    except TypeError:
                        self.fb.draw_text8x8(lx, ly, label, self.static_color)

    def draw_aircraft_marker(self, ac, x, y, color):
        # small filled marker and short callsign (used on illumination)
        if hasattr(self.fb, "fill_circle"):
            self.fb.fill_circle(x, y, 3, color)
        else:
            self.fb.draw_line(x, y, x + 1, y, color)
        # draw trail line (same heuristic as prior widgets)
        if getattr(ac, "track", 0) and ac.track > 0:
            tr = math.radians(ac.track)
            min_len = 4
            max_len = 18
            max_speed = 600
            trail_len = min_len + (max_len - min_len) * min(getattr(ac, "speed", 0), max_speed) / max_speed
            tx = int(x - trail_len * math.sin(tr))
            ty = int(y + trail_len * math.cos(tr))
            self.fb.draw_line(tx, ty, x, y, color)
        # label when illuminated
        if self.show_pip_labels:
            lab = str(ac.callsign)[:6]
            if self.font is not None and hasattr(self.fb, "draw_text"):
                self.fb.draw_text(x + 6, y - 8, lab, self.font, color, self.bg_color)
            else:
                try:
                    self.fb.draw_text8x8(x + 6, y - 4, lab, color, background=self.bg_color)
                except TypeError:
                    self.fb.draw_text8x8(x + 6, y - 4, lab, color)

    def draw(self, aircraft_list, sweep=True):
        """
        draw(...):
          - sweep=True (default): advance beam by one segment, draw beam + trailing fade,
            illuminate pips only when beam reaches them.
          - sweep=False: full redraw of static background and all pips (non-sweep).
        """
        # cache the aircraft list so step()/sweep() can be called without args
        self._last_aircraft_list = aircraft_list

        fb = self.fb
        cx = self.center_x
        cy = self.center_y
        seg = self._cur_seg

        if not sweep:
            # full redraw
            self._draw_static_background()
            # draw all aircraft as persistent pips
            blink_state = ((utime.ticks_ms() // 500) & 1) == 0
            for ac in aircraft_list:
                pos = self._aircraft_screen_pos(ac)
                if not pos:
                    continue
                x, y = pos
                if getattr(ac, "is_military", False):
                    # blink logic (if you have external cfg, you can plug it in)
                    color = self.mil_color if True else self.beam_color
                    if hasattr(ac, "is_military") and ac.is_military:
                        if not blink_state:
                            color = self.beam_color
                    self.draw_aircraft_marker(ac, x, y, color)
                else:
                    self.draw_aircraft_marker(ac, x, y, self.beam_color)
            return

        # Sweep mode:
        # 1) Determine which segment to erase (beyond trail) and clear it to bg, restore static elements
        if self.trail_length > 0:
            erase_seg = (seg - 1 - self.trail_length) % self.segments
            self._fill_segment(erase_seg, self.bg_color)
            self._restore_static_for_segment(erase_seg)
            # draw trailing segments from furthest->nearest behind the beam
            for j in range(self.trail_length):
                trail_seg = (seg - 1 - j) % self.segments
                color = self._trail_colors[j] if j < len(self._trail_colors) else self.static_color
                self._fill_segment(trail_seg, color)
        else:
            prev_seg = (seg - 1) % self.segments
            self._fill_segment(prev_seg, self.bg_color)
            self._restore_static_for_segment(prev_seg)

        # 2) draw active beam segment (bright)
        self._fill_segment(seg, self.beam_color)

        # 3) illuminate pips that lie in this segment
        blink_state = ((utime.ticks_ms() // 500) & 1) == 0
        for ac in aircraft_list:
            pos = self._aircraft_screen_pos(ac)
            if not pos:
                continue
            x, y = pos
            ang = self._angle_of_point(x, y)
            idx = int(ang / self._seg_angle) % self.segments
            if idx == seg:
                # pick mil vs normal color and blink if needed
                if getattr(ac, "is_military", False):
                    color = self.mil_color if True else self.beam_color
                else:
                    color = self.beam_color
                self.draw_aircraft_marker(ac, x, y, color)

        # advance sweep
        self._cur_seg = (seg + 1) % self.segments

    # Convenience aliases -------------------------------------------------
    def step(self, aircraft_list=None):
        """
        Advance the sweep by one segment. If aircraft_list is None, re-use the last list
        previously passed to draw()/step()/sweep(). Raises ValueError if no list available.
        """
        if aircraft_list is None:
            aircraft_list = self._last_aircraft_list
        if aircraft_list is None:
            raise ValueError("No aircraft_list provided and no cached list available; pass aircraft_list to step() or call draw(aircraft_list) first.")
        return self.draw(aircraft_list, sweep=True)

    def sweep(self, aircraft_list=None):
        """Alias for step(...)."""
        return self.step(aircraft_list)