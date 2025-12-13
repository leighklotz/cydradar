# MicroPython UI components for CYD-based ILI9341 displays

import math
import utime
from ili9341 import color565
from cfg import _cfg

class DataTable:
    """Aircraft data table component using CYD display primitives."""
    def __init__(self, fb, x, y, width, height,
                 table_font=None, status_font=None,
                 compact=False,
                 config=_cfg):
        """
        fb: cyd.display instance
        x,y,width,height: table rectangle
        font: XglcdFont-compatible font, or None to use draw_text8x8
        compact: omit the status stanza and just show the air traffic, etc.
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
        self.compact = compact
        # Store row layout for hit testing
        self.row_layout = []  # List of (hex_code, y_pos, row_height)
        # Text cache for write-through optimization
        self.text_cache = {}  # (x, y) -> text
        self.max_rows = 0  # Calculated dynamically

    def draw(self, aircraft_list, status, last_update_ticks_ms, selected_hex=None):
        """Render the table and status information."""
        # Clear row layout for this draw
        self.row_layout = []
        
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
            self.fb.draw_text8x8(title_x, self.y + 4, title, self.cfg.AMBER, background=self.cfg.BLACK)
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

        # Calculate maximum rows that can fit
        start_y = headers_y + self.table_font_h + 4
        row_h = self.table_font_h + 2
        
        # Calculate available space for rows
        if self.compact:
            available_height = self.height - (start_y - self.y) - 4
        else:
            # Reserve space for status footer
            status_lines = 5
            footer_height = status_lines * self.status_font_h + 8
            available_height = self.height - (start_y - self.y) - footer_height
        
        self.max_rows = max(1, int(available_height / row_h))
        
        # rows (sorted by distance)
        sorted_ac = sorted(aircraft_list, key=lambda a: getattr(a, "distance", 9999))
        num_rows = min(len(sorted_ac), self.max_rows)
        
        # Track which positions we're drawing to
        new_text_cache = {}
        
        for i, aircraft in enumerate(sorted_ac[:self.max_rows]):
            print(f"table: {i=} {aircraft.__dict__}")
            y_pos = start_y + i * row_h
            
            # Store row layout for hit testing
            self.row_layout.append((aircraft.hex_code, y_pos, row_h))
            
            # Draw yellow background for selected row
            is_selected = (selected_hex is not None and aircraft.hex_code == selected_hex)
            if is_selected:
                self.fb.fill_rectangle(self.x + 4, y_pos - 1, self.width - 8, row_h, self.cfg.YELLOW)
            else:
                # Clear background if not selected (to remove old highlighting)
                self.fb.fill_rectangle(self.x + 4, y_pos - 1, self.width - 8, row_h, self.cfg.BLACK)
            
            color = self.cfg.RED if aircraft.is_military else self.cfg.BRIGHT_GREEN
            callsign = "{}".format(aircraft.callsign)[:8] if aircraft.callsign else aircraft.hex_code
            altitude = "{}".format(aircraft.altitude) if isinstance(aircraft.altitude, int) and aircraft.altitude > 0 else "-"
            speed = "{}".format(int(aircraft.speed))   if getattr(aircraft, "speed", 0) and aircraft.speed > 0 else "-"
            distance = "{:.1f}".format(aircraft.distance) if getattr(aircraft, "distance", 0) and aircraft.distance > 0 else "-"
            track = "{}°".format(int(aircraft.track)) if getattr(aircraft, "track", 0) and aircraft.track > 0 else "-"
            squawk = "{}".format(getattr(aircraft, "squawk", '-') or '-')
            cols = [callsign, altitude, speed, distance, track, squawk]
            
            # Use black text on yellow background for selected row
            text_color = self.cfg.BLACK if is_selected else color
            bg_color = self.cfg.YELLOW if is_selected else self.cfg.BLACK
            
            for j, val in enumerate(cols):
                text_str = str(val) + '   '  # Add padding
                cache_key = (col_positions[j], y_pos)
                
                # Only draw if text changed or is selected (background changed)
                if is_selected or cache_key not in self.text_cache or self.text_cache[cache_key] != text_str:
                    self.fb.draw_text(col_positions[j], y_pos, text_str, self.table_font, text_color, bg_color)
                
                new_text_cache[cache_key] = text_str
        
        # Clear remaining rows
        if num_rows < self.max_rows:
            clear_y = start_y + num_rows * row_h
            clear_height = (self.max_rows - num_rows) * row_h
            self.fb.fill_rectangle(self.x + 4, clear_y, self.width - 8, clear_height, self.cfg.BLACK)
        
        # Update cache
        self.text_cache = new_text_cache

        if not self.compact:
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
                color = self.cfg.YELLOW if "UPDATING" in s else self.cfg.BRIGHT_GREEN
                if self.status_font is not None:
                    self.fb.draw_text(self.x + 6, status_y + i * self.status_font_h, s, self.status_font, color, self.cfg.BLACK)
                else:
                    self.fb.draw_text8x8(self.x + 6, status_y + i * self.status_font_h, s, color, background=self.cfg.BLACK)
    
    def clear_cache(self):
        """Clear the text cache, called when screen is cleared."""
        self.text_cache = {}

    def pick_hex(self, x, y):
        """
        Hit-test to find which aircraft row was tapped.
        Returns the hex_code of the aircraft, or None if no row was hit.
        Returns 'deselect' if touched in table area but not on a row (to deselect).
        """
        # Check if touch is within table bounds
        if x < self.x or x > self.x + self.width or y < self.y or y > self.y + self.height:
            return None
        
        # Check each row
        for hex_code, row_y, row_h in self.row_layout:
            if y >= row_y and y < row_y + row_h:
                return hex_code
        
        # Touch is in table but not on a row - signal deselect
        if self.row_layout:
            # Only return 'deselect' if touch is in the data area (below first row)
            first_row_y = self.row_layout[0][1]
            if y >= first_row_y:
                return 'deselect'
        
        return None
    
    def is_header_touch(self, x, y):
        """
        Check if touch is in the header area (title and column headers).
        Returns True if in header area (where layout change should happen).
        """
        # Check if touch is within table bounds
        if x < self.x or x > self.x + self.width or y < self.y or y > self.y + self.height:
            return False
        
        # Header area is from table top to just before first data row
        if self.row_layout:
            first_row_y = self.row_layout[0][1]
            return y < first_row_y
        
        # If no rows, entire table is header area
        return True
