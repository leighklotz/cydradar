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

    def draw_aircraft(self, aircraft, x, y, pip_color, track_color, show_label=True, is_selected=False, draw_selection_circle=False):
        """Draw an aircraft marker, trail and callsign using CYD API directly."""
        # Draw yellow circle only when explicitly requested (on tap)
        if draw_selection_circle:
            self.fb.draw_circle(x, y, 6, self.cfg.YELLOW)
        
        # filled circle for aircraft
        if show_label:
            self.fb.fill_circle(x, y, 3, pip_color)
        else:
            # draw_pixel did not show up
            #self.fb.draw_pixel(x, y, pip_color) 
            self.fb.fill_circle(x, y, 2, pip_color)
        # projection line based on track and speed
        if getattr(aircraft, "track", 0) and aircraft.track > 0:
            track_rad = math.radians(aircraft.track)
            min_length = self.cfg.TRAIL_MIN_LENGTH
            max_length = self.cfg.TRAIL_MAX_LENGTH
            max_speed = self.cfg.TRAIL_MAX_SPEED
            trail_length = min_length + (max_length - min_length) * min(getattr(aircraft, "speed", 0), max_speed) / max_speed
            tx = int(x + trail_length * math.sin(track_rad))
            ty = int(y - trail_length * math.cos(track_rad))
            # Use yellow track for selected aircraft
            line_color = self.cfg.YELLOW if is_selected else track_color
            self.fb.draw_line(tx, ty, x, y, line_color)

        # callsign - prefer draw_text with font if provided, otherwise draw_text8x8
        # Draw label when: first seen OR when selection circle is being drawn (i.e., just tapped)
        if show_label or draw_selection_circle:
            callsign = aircraft.callsign
            if callsign is not None:
                # Use yellow for newly-tracked (selected) planes, green for newly-heard ones
                label_color = self.cfg.YELLOW if draw_selection_circle else pip_color
                if self.font is not None:
                    # draw_text(x, y, text, font, color, background)
                    self.fb.draw_text(x + 8, y - 12, callsign, self.font, label_color, self.cfg.BLACK)
                else:
                    # draw_text8x8(x, y, text, color, background=...)
                    self.fb.draw_text8x8(x + 8, y - 12, callsign, label_color, background=self.cfg.BLACK)

    def draw_planes(self, aircraft_list, previous_aircraft=None, selected_hex=None, just_selected_hex=None):
        """Draw planes
        
        Args:
            aircraft_list: List of aircraft to draw
            previous_aircraft: Set of previously drawn aircraft hex codes
            selected_hex: Currently selected aircraft hex code
            just_selected_hex: Aircraft that was just tapped (to draw selection circle)
        """

        # blink state for military blips
        blink_state = ((utime.ticks_ms() // 500) & 1) == 0

        for aircraft in aircraft_list:
            pos = self.lat_lon_to_screen(aircraft.lat, aircraft.lon)
            if pos:
                x, y = pos
                show_label = previous_aircraft is None or aircraft.hex_code not in previous_aircraft
                is_selected = (selected_hex is not None and aircraft.hex_code == selected_hex)
                draw_circle = (just_selected_hex is not None and aircraft.hex_code == just_selected_hex)
                if aircraft.is_military:
                    if not self.cfg.BLINK_MILITARY or blink_state:
                        self.draw_aircraft(aircraft, x, y, self.cfg.RED, self.cfg.DIM_GREEN, show_label=show_label, is_selected=is_selected, draw_selection_circle=draw_circle)
                else:
                    self.draw_aircraft(aircraft, x, y, self.cfg.BRIGHT_GREEN, self.cfg.DIM_GREEN, show_label=show_label, is_selected=is_selected, draw_selection_circle=draw_circle)

    def draw_scope(self):
        """Draw radar rings, crosshairs and aircraft. Does not clear entire screen."""
        # range rings as closed polylines using fb.draw_lines
        for ring in range(1, 4):
            start_ring_time = utime.ticks_ms()
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
            #print(coords)
            end_calc_time = utime.ticks_ms()
            self.fb.draw_lines(coords, self.cfg.DIM_GREEN)
            end_draw_time = utime.ticks_ms()
            print(f"calc={end_calc_time-start_ring_time}ms draw={end_draw_time-end_calc_time}ms")

            # label ring
            if self.cfg.LABEL_RING:
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
        if False:
            self.fb.fill_circle(self.center_x, self.center_y, 2, self.cfg.BRIGHT_GREEN)

