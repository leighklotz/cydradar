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
        self.row_hex_cache = {}  # y_pos -> (hex_code, is_selected) - tracks what's at each row
        self.max_rows = 0  # Calculated dynamically
        # Constants
        self.DEFAULT_ROW_STATE = (None, False)  # (hex_code, is_selected) for empty row

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
        headers_y = self.y + 16  # Reduced from 20 to fit more rows
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
            # Calculate status footer height dynamically
            status_info_lines = 5  # STATUS, CONTACTS, RANGE, INTERVAL, NEXT UPDATE
            footer_height = status_info_lines * self.status_font_h + 8
            available_height = self.height - (start_y - self.y) - footer_height
        
        self.max_rows = max(1, int(available_height / row_h))
        
        # rows (sorted by distance)
        sorted_ac = sorted(aircraft_list, key=lambda a: getattr(a, "distance", 9999))
        num_rows = min(len(sorted_ac), self.max_rows)
        
        # Track which positions we're drawing to
        new_text_cache = {}
        new_row_hex_cache = {}
        
        for i, aircraft in enumerate(sorted_ac[:self.max_rows]):
            print(f"table: {i=} {aircraft.__dict__}")
            y_pos = start_y + i * row_h
            
            # Store row layout for hit testing
            self.row_layout.append((aircraft.hex_code, y_pos, row_h))
            
            # Determine if this row needs background update
            is_selected = (selected_hex is not None and aircraft.hex_code == selected_hex)
            
            # Check if background needs to be updated
            # Only update if: hex_code changed at this y_pos OR selection state changed
            old_state = self.row_hex_cache.get(y_pos, self.DEFAULT_ROW_STATE)
            old_hex, old_selected = old_state
            needs_bg_update = (old_hex != aircraft.hex_code) or (old_selected != is_selected)
            
            if needs_bg_update:
                if is_selected:
                    self.fb.fill_rectangle(self.x + 4, y_pos - 1, self.width - 8, row_h, self.cfg.YELLOW)
                else:
                    self.fb.fill_rectangle(self.x + 4, y_pos - 1, self.width - 8, row_h, self.cfg.BLACK)
            
            # Track what's at this row position
            new_row_hex_cache[y_pos] = (aircraft.hex_code, is_selected)
            
            color = self.cfg.RED if aircraft.is_military else self.cfg.BRIGHT_GREEN
            # Format columns with appropriate widths
            # CALL: 8 chars left-aligned
            # ALT: 5 chars right-aligned (up to 99999 ft)
            # SPD: 3 chars right-aligned (up to 999 kts)
            # DIST: 4 chars right-aligned (up to 99.9 nm, or 99+ for 100+)
            # TRK: 4 chars right-aligned (0-359°)
            # SQUAWK: 4 chars left-aligned
            callsign = ("{:<8}".format(aircraft.callsign[:8]) if aircraft.callsign else "{:<8}".format(aircraft.hex_code[:8]))
            altitude = "{:>5}".format(aircraft.altitude) if isinstance(aircraft.altitude, int) and aircraft.altitude > 0 else "{:>5}".format("-")
            speed = "{:>3}".format(int(aircraft.speed)) if getattr(aircraft, "speed", 0) and aircraft.speed > 0 else "{:>3}".format("-")
            
            # Distance: show one decimal place up to 99.9, then show as integer 100+
            if getattr(aircraft, "distance", 0) and aircraft.distance > 0:
                if aircraft.distance < 100:
                    distance = "{:>4}".format("{:.1f}".format(aircraft.distance))
                else:
                    distance = "{:>3}+".format(int(aircraft.distance))[:4]
            else:
                distance = "{:>4}".format("-")
            
            # Track: show with degree symbol (track is 0-359)
            if getattr(aircraft, "track", 0) and aircraft.track > 0:
                track = "{:>3}°".format(int(aircraft.track))
            else:
                track = "{:>4}".format("-")
            
            # Squawk: handle None/empty safely
            squawk_val = getattr(aircraft, "squawk", None)
            if squawk_val is not None:
                squawk = "{:<4}".format(str(squawk_val)[:4])
            else:
                squawk = "{:<4}".format("-")
            
            cols = [callsign, altitude, speed, distance, track, squawk]
            
            # Use black text on yellow background for selected row
            text_color = self.cfg.BLACK if is_selected else color
            bg_color = self.cfg.YELLOW if is_selected else self.cfg.BLACK
            
            for j, val in enumerate(cols):
                # Fields are now properly sized with formatting, no extra padding needed
                text_str = val
                cache_key = (col_positions[j], y_pos)
                
                # Draw if: text changed OR background was just updated (which cleared the text)
                if needs_bg_update or cache_key not in self.text_cache or self.text_cache[cache_key] != text_str:
                    self.fb.draw_text(col_positions[j], y_pos, text_str, self.table_font, text_color, bg_color)
                
                new_text_cache[cache_key] = text_str
        
        # Clear remaining rows
        if num_rows < self.max_rows:
            clear_y = start_y + num_rows * row_h
            clear_height = (self.max_rows - num_rows) * row_h
            self.fb.fill_rectangle(self.x + 4, clear_y, self.width - 8, clear_height, self.cfg.BLACK)
        
        # Update caches
        self.text_cache = new_text_cache
        self.row_hex_cache = new_row_hex_cache

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
        self.row_hex_cache = {}

    def pick_hex(self, x, y):
        """
        Hit-test to find which aircraft row was tapped.
        Returns the hex_code of the aircraft, or None if no row was hit.
        Returns 'deselect' if touched in table area but not on a row (to deselect).
        """
        # Check if touch is within table bounds
        if x < self.x or x > self.x + self.width or y < self.y or y > self.y + self.height:
            return None
        
        # Check each row - use center of row for more forgiving hit detection
        for hex_code, row_y, row_h in self.row_layout:
            # Check if touch is within the row boundaries
            # row_y is the top of the text, we need to check the full row height
            if y >= (row_y - 1) and y < (row_y - 1 + row_h):
                return hex_code
        
        # Touch is in table but not on a row - signal deselect
        if self.row_layout:
            # Only return 'deselect' if touch is in the data area (below first row)
            first_row_y = self.row_layout[0][1]
            if y >= first_row_y:
                return 'deselect'
        
        return None
    

    
    def is_in_table_bounds(self, x, y):
        """
        Check if touch is anywhere within the table bounds (header or data area).
        Returns True if within table, False if outside.
        """
        return (x >= self.x and x < self.x + self.width and 
                y >= self.y and y < self.y + self.height)
