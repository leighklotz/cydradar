# MicroPython UI components for CYD-based ILI9341 displays

import math
import utime
from ili9341 import color565
from cfg import _cfg

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
        # print(f"self.fb.draw_rectangle({self.x=}, {self.y=}, {self.width=}, {self.height=}, {self.cfg.BRIGHT_GREEN=})")
        self.fb.draw_rectangle(self.x, self.y, self.width, self.height, self.cfg.BRIGHT_GREEN)

        # title
        title = "AIRCRAFT DATA"
        if self.table_font is not None:
            title_x = self.x + (self.width // 2) - (len(title) * self.table_font.width // 2)
            print(f"self.fb.draw_text({title_x=}, {self.y=} + 4, {title=}, {self.table_font=}, self.cfg.AMBER, self.cfg.BLACK)")
            self.fb.draw_text(title_x, self.y + 4, title, self.table_font, self.cfg.AMBER, self.cfg.BLACK)
        else:
            title_x = self.x + (self.width // 2) - (len(title) * 8 // 2)
            self.fb.draw_text8x8(title_x, self.y + 4, title, AMBER, background=self.cfg.BLACK)
            print(f"self.fb.draw_text8x8({title_x=}, {self.y=} + 4, {title=}, self.cfg.AMBER, background=self.cfg.BLACK)")

        # headers and column positions
        headers_y = self.y + 20
        headers = ["CALL", "ALT", "SPD", "DIST", "TRK", "SQUAWK"]
        total_width = self.width - 12
        col_widths = [0.23, 0.15, 0.15, 0.15, 0.15, 0.17]
        col_positions = []
        current_x = self.x + 6
        for ratio in col_widths:
            w = int(total_width * ratio)
            col_positions.append(current_x)
            current_x += w

        # draw headers
        for i, h in enumerate(headers):
            if self.table_font is not None:
                self.fb.draw_text(col_positions[i], headers_y, h, self.table_font, self.cfg.AMBER, self.cfg.BLACK)
            else:
                self.fb.draw_text8x8(col_positions[i], headers_y, h, self.cfg.AMBER, background=self.cfg.BLACK)

        # separator line
        self.fb.draw_line(self.x + 4, headers_y + self.table_font_h, self.x + self.width - 4, headers_y + self.table_font_h, self.cfg.DIM_GREEN)

        # rows (sorted by distance)
        sorted_ac = sorted(aircraft_list, key=lambda a: getattr(a, "distance", 9999))
        start_y = headers_y + self.table_font_h + 4
        row_h = self.table_font_h + 2
        y_pos = start_y
        for i, aircraft in enumerate(sorted_ac[: self.cfg.MAX_TABLE_ROWS]):
            print(f"table: {i=} {aircraft.__dict__}")
            y_pos = start_y + i * row_h
            color = self.cfg.RED if aircraft.is_military else self.cfg.BRIGHT_GREEN
            callsign = "{}".format(aircraft.callsign)[:8] if aircraft.callsign else aircraft.hex_code
            altitude = "{}".format(aircraft.altitude) if isinstance(aircraft.altitude, int) and aircraft.altitude > 0 else "-"
            speed = "{}".format(int(aircraft.speed))   if getattr(aircraft, "speed", 0) and aircraft.speed > 0 else "-"
            distance = "{:.1f}".format(aircraft.distance) if getattr(aircraft, "distance", 0) and aircraft.distance > 0 else "-"
            track = "{}°".format(int(aircraft.track)) if getattr(aircraft, "track", 0) and aircraft.track > 0 else "-"
            squawk = "{}".format(getattr(aircraft, "squawk", '-') or '-')
            cols = [callsign, altitude, speed, distance, track, squawk]
            for j, val in enumerate(cols):
                self.fb.draw_text(col_positions[j], y_pos, str(val)+'   ', self.table_font, color, self.cfg.BLACK)
        else:
            if i < self.cfg.MAX_TABLE_ROWS-1:
                y_pos += row_h
                self.fb.fill_rectangle(5, y_pos, self.width, row_h-5, self.cfg.BLACK)

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
            color = YELLOW if "UPDATING" in s else self.cfg.BRIGHT_GREEN
            if self.status_font is not None:
                self.fb.draw_text(self.x + 6, status_y + i * self.status_font_h, s, self.status_font, color, self.cfg.BLACK)
            else:
                self.fb.draw_text8x8(self.x + 6, status_y + i * self.status_font_h, s, color, background=self.cfg.BLACK)
