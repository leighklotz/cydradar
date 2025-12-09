import math
import utime

class RadarScope:
    """Radar display component using CYD display primitives (expects fb=cyd.display)."""
    def __init__(self, fb, center_x, center_y, radius, font=None, config=None):
        """
        fb: cyd.display instance
        center_x, center_y: center pixel coordinates on the display
        radius: radius in pixels for the radar circle
        font: XglcdFont-compatible font, or None to use draw_text8x8
        config: configuration object
        """
        self.fb = fb
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.font = font
        self.cfg = config

    def lat_lon_to_screen(self, lat, lon):
        """Convert lat/lon to screen coordinates (same math as original pygame code)."""
        lat_km = (lat - self.cfg.LAT) * 111
        lon_km = (lon - self.cfg.LON) * 111 * math.cos(math.radians(self.cfg.LAT))
        range_km = self.cfg.RADIUS_NM * 1.852
        x = self.center_x + (lon_km / range_km) * self.radius
        y = self.center_y - (lat_km / range_km) * self.radius
        dx = x - self.center_x
        dy = y - self.center_y
        if dx * dx + dy * dy <= self.radius * self.radius:
            return int(x), int(y)
        return None

    def draw_aircraft(self, aircraft, x, y, colour):
        """Draw an aircraft marker, trail and callsign using CYD API directly."""
        # filled circle for aircraft
        self.fb.fill_circle(x, y, 5, colour)

        # trail line based on track and speed
        if getattr(aircraft, "track", 0) and aircraft.track > 0:
            track_rad = math.radians(aircraft.track)
            min_length = self.cfg.TRAIL_MIN_LENGTH
            max_length = self.cfg.TRAIL_MAX_LENGTH
            max_speed = self.cfg.TRAIL_MAX_SPEED
            trail_length = min_length + (max_length - min_length) * min(getattr(aircraft, "speed", 0), max_speed) / max_speed
            tx = int(x - trail_length * math.sin(track_rad))
            ty = int(y + trail_length * math.cos(track_rad))
            self.fb.draw_line(tx, ty, x, y, colour)

        # callsign - prefer draw_text with font if provided, otherwise draw_text8x8
        callsign = str(aircraft.callsign)
        if self.font is not None:
            # draw_text(x, y, text, font, color, background)
            self.fb.draw_text(x + 8, y - 12, callsign, self.font, colour, self.cfg.BLACK)
        else:
            # draw_text8x8(x, y, text, color, background=...)
            self.fb.draw_text8x8(x + 8, y - 12, callsign, colour, background=self.cfg.BLACK)

    def draw(self, aircraft_list):
        """Draw radar rings, crosshairs and aircraft. Does not clear entire screen."""
        # range rings as closed polylines using fb.draw_lines
        for ring in range(1, 4):
            ring_radius = int((ring / 3) * self.radius)
            coords = []
            step = 30  # degree step for ring points (smaller = smoother, slower)
            for deg in range(0, 360 + step, step):
                rad = math.radians(deg % 360)
                px = int(self.center_x + ring_radius * math.cos(rad))
                py = int(self.center_y + ring_radius * math.sin(rad))
                coords.append([px, py])
            # ensure loop closed
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            print(coords)
            self.fb.draw_lines(coords, self.cfg.DIM_GREEN)

            # label ring
            range_nm = int((ring / 3) * self.cfg.RADIUS_NM)
            label = "{}NM".format(range_nm)
            if self.font is not None:
                self.fb.draw_text(self.center_x + ring_radius - 20, self.center_y + 5, label, self.font, self.cfg.DIM_GREEN, self.cfg.BLACK)
            else:
                self.fb.draw_text8x8(self.center_x + ring_radius - 20, self.center_y + 5, label, self.cfg.DIM_GREEN, background=self.cfg.BLACK)

        # crosshairs - two straight lines
        self.fb.draw_line(self.center_x - self.radius, self.center_y, self.center_x + self.radius, self.center_y, self.cfg.DIM_GREEN)
        self.fb.draw_line(self.center_x, self.center_y - self.radius, self.center_x, self.center_y + self.radius, self.cfg.DIM_GREEN)

        # center mark
        self.fb.fill_circle(self.center_x, self.center_y, 2, self.cfg.BRIGHT_GREEN)

        # blink state for military blips
        blink_state = ((utime.ticks_ms() // 500) & 1) == 0

        for aircraft in aircraft_list:
            pos = self.lat_lon_to_screen(aircraft.lat, aircraft.lon)
            if pos:
                x, y = pos
                if aircraft.is_military:
                    if not self.cfg.BLINK_MILITARY or blink_state:
                        self.draw_aircraft(aircraft, x, y, self.cfg.RED)
                else:
                    self.draw_aircraft(aircraft, x, y, self.cfg.BRIGHT_GREEN)

