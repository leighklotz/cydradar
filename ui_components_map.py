# MicroPython UI components for CYD-based ILI9341 displays
# Example usage (paste into your main.py on the device):
#
# from cydr import CYD
# import utime
# from ui_components_mpy import RadarScope, DataTable, SampleAircraft, _cfg, BRIGHT_GREEN, BLACK
#
# cyd = CYD()
# fb = cyd.display
# fb.clear(BLACK)
#
# # sample aircraft dataset
# ac1 = SampleAircraft(callsign="ALFA01", lat=0.01, lon=0.00, track=45, speed=250, altitude=12000, distance=5.0, is_military=False)
# ac2 = SampleAircraft(callsign="BRAVO2", lat=-0.005, lon=0.02, track=270, speed=120, altitude=8000, distance=8.2, is_military=True)
# ac3 = SampleAircraft(callsign="CHAR3", lat=0.02, lon=-0.015, track=180, speed=350, altitude=30000, distance=12.5, is_military=False)
# aircraft_list = [ac1, ac2, ac3]
#
# radar = RadarScope(fb, center_x=120, center_y=80, radius=70, font=None)
# table = DataTable(fb, x=4, y=170, width=312, height=66, font=None)
#
# # single update (for testing)
# now = utime.ticks_ms()
# radar.draw(aircraft_list)
# table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
#
# # In a loop you would refresh periodically:
# # while True:
# #     aircraft_list = fetch_your_data()
# #     now = utime.ticks_ms()
# #     fb.clear(BLACK)
# #     radar.draw(aircraft_list)
# #     table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
# #     utime.sleep_ms(200)
#
# The module calls the CYD display API directly (no runtime guessing). It expects fb to be cyd.display,
# which provides methods such as: draw_lines, draw_line, draw_pixel, fill_circle, fill_rectangle,
# draw_rectangle, draw_text (with font), and draw_text8x8.

import math
import utime
from ili9341 import color565

# Color constants (16-bit RGB565 values)
BRIGHT_GREEN = color565(0, 255, 0)
DIM_GREEN = color565(0, 128, 0)
RED = color565(255, 0, 0)
AMBER = color565(255, 191, 0)
YELLOW = color565(255, 255, 0)
BLACK = color565(0, 0, 0)

class _cfg:
    LAT = 0.0
    LON = 0.0
    RADIUS_NM = 30
    TRAIL_MIN_LENGTH = 4
    TRAIL_MAX_LENGTH = 18
    TRAIL_MAX_SPEED = 600
    BLINK_MILITARY = True
    FETCH_INTERVAL = 5
    MAX_TABLE_ROWS = 8
    DEFAULT_FONT_HEIGHT = 8

# Simple sample Aircraft class for example usage and tests
class SampleAircraft:
    def __init__(self, callsign, lat, lon, track=0, speed=0, altitude=0, distance=0.0, is_military=False):
        self.callsign = callsign
        self.lat = lat
        self.lon = lon
        self.track = track
        self.speed = speed
        self.altitude = altitude
        self.distance = distance
        self.is_military = is_military

class DataTable:
    """Aircraft data table component using CYD display primitives."""
    def __init__(self, fb, x, y, width, height,
                 table_font=None, status_font=None,
                 config=_cfg):
        """
        fb: cyd.display instance
        x,y,width,height: table rectangle
        font: XglcdFont-compatible font, or None to use draw_text8x8
        """
        self.fb = fb
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.table_font = table_font
        self.status_font = status_font
        self.cfg = config
        self.table_font_h = getattr(table_font, "height", config.DEFAULT_FONT_HEIGHT)
        self.status_font_h = getattr(status_font, "height", config.DEFAULT_FONT_HEIGHT)

    def draw(self, aircraft_list, status, last_update_ticks_ms):
        """Render the table and status information."""
        # border
        print(f"self.fb.draw_rectangle({self.x=}, {self.y=}, {self.width=}, {self.height=}, {BRIGHT_GREEN=})")
        self.fb.draw_rectangle(self.x, self.y, self.width, self.height, BRIGHT_GREEN)

        # title
        title = "AIRCRAFT DATA"
        if self.table_font is not None:
            title_x = self.x + (self.width // 2) - (len(title) * self.table_font.width // 2)
            print(f"self.fb.draw_text({title_x=}, {self.y=} + 4, {title=}, {self.table_font=}, AMBER, BLACK)")
            self.fb.draw_text(title_x, self.y + 4, title, self.table_font, AMBER, BLACK)
        else:
            title_x = self.x + (self.width // 2) - (len(title) * 8 // 2)
            self.fb.draw_text8x8(title_x, self.y + 4, title, AMBER, background=BLACK)
            print(f"self.fb.draw_text8x8({title_x=}, {self.y=} + 4, {title=}, AMBER, background=BLACK)")

        # headers and column positions
        headers_y = self.y + 20
        headers = ["CALL", "ALT", "SPD", "DIST", "TRK"]
        total_width = self.width - 12
        col_widths = [0.25, 0.25, 0.15, 0.2, 0.15]
        col_positions = []
        current_x = self.x + 6
        for ratio in col_widths:
            w = int(total_width * ratio)
            col_positions.append(current_x)
            current_x += w

        # draw headers
        for i, h in enumerate(headers):
            if self.table_font is not None:
                self.fb.draw_text(col_positions[i], headers_y, h, self.table_font, AMBER, BLACK)
            else:
                self.fb.draw_text8x8(col_positions[i], headers_y, h, AMBER, background=BLACK)

        # separator line
        self.fb.draw_line(self.x + 4, headers_y + self.table_font_h, self.x + self.width - 4, headers_y + self.table_font_h, DIM_GREEN)

        # rows (sorted by distance)
        sorted_ac = sorted(aircraft_list, key=lambda a: getattr(a, "distance", 9999))
        start_y = headers_y + self.table_font_h + 4
        row_h = self.table_font_h + 2
        for i, aircraft in enumerate(sorted_ac[: self.cfg.MAX_TABLE_ROWS]):
            y_pos = start_y + i * row_h
            colour = RED if aircraft.is_military else BRIGHT_GREEN
            callsign = "{}".format(aircraft.callsign)[:8]
            altitude = "{}".format(aircraft.altitude) if isinstance(aircraft.altitude, int) and aircraft.altitude > 0 else "N/A"
            speed = "{}".format(int(aircraft.speed)) if getattr(aircraft, "speed", 0) and aircraft.speed > 0 else "N/A"
            distance = "{:.1f}".format(aircraft.distance) if getattr(aircraft, "distance", 0) and aircraft.distance > 0 else "N/A"
            track = "{}°".format(int(aircraft.track)) if getattr(aircraft, "track", 0) and aircraft.track > 0 else "N/A"
            cols = [callsign, altitude, speed, distance, track]
            for j, val in enumerate(cols):
                if self.table_font is not None:
                    self.fb.draw_text(col_positions[j], y_pos, str(val), self.table_font, colour, BLACK)
                else:
                    self.fb.draw_text8x8(col_positions[j], y_pos, str(val), colour, background=BLACK)

        # footer status
        military_count = sum(1 for a in aircraft_list if a.is_military)
        if last_update_ticks_ms:
            elapsed = (utime.ticks_ms() - last_update_ticks_ms) / 1000.0
        else:
            elapsed = 9999.0
        countdown = max(0, self.cfg.FETCH_INTERVAL - elapsed)
        countdown_text = "{:02d}S".format(int(countdown)) if countdown > 0 else "UPDATING"
        status_info = [
            "STATUS: {}".format(status),
            "CONTACTS: {} ({} MIL)".format(len(aircraft_list), military_count),
            "RANGE: {}NM".format(self.cfg.RADIUS_NM),
            "INTERVAL: {}S".format(self.cfg.FETCH_INTERVAL),
            "NEXT UPDATE: {}".format(countdown_text),
        ]
        status_y = self.y + self.height - (len(status_info) * self.status_font_h) - 4
        for i, s in enumerate(status_info):
            colour = YELLOW if "UPDATING" in s else BRIGHT_GREEN
            if self.status_font is not None:
                self.fb.draw_text(self.x + 6, status_y + i * self.status_font_h, s, self.status_font, colour, BLACK)
            else:
                self.fb.draw_text8x8(self.x + 6, status_y + i * self.status_font_h, s, colour, background=BLACK)
