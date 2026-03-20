from presto import Presto

import micropython
import gc
import sys

import utime

from display_wrapper import PixelFont, PicoDisplay
from datatable import DataTable
from cfg import _cfg
from scope import RadarScope
from fetch import AircraftTracker

# Color attributes on _cfg that need to be converted to PicoGraphics pen indices.
_COLOR_ATTRS = ['BRIGHT_GREEN', 'DIM_GREEN', 'RED', 'AMBER', 'YELLOW', 'BLACK', 'WHITE']


class Radar:
    """
    Encapsulates the radar display logic, including scope and data table.
    Handles widget creation, updates, and styling.
    """
    MAX_RADAR_STYLE = 0
    SPLIT_SCREEN_STYLE = 1
    TABLE_ONLY_STYLE = 2

    def __init__(self, presto, display, config, status_font, table_font, aircraft_tracker):
        """
        Initializes the Radar object.

        Args:
            presto: the Presto device (used for touch and display update)
            display: PicoDisplay wrapper (used for drawing)
            config: The configuration object.
            status_font: PixelFont for status messages.
            table_font: PixelFont for the data table.
            aircraft_tracker: the source of data
        """
        self.presto = presto
        self.fb = display
        self.config = config
        self.status_font = status_font
        self.table_font = table_font
        self.radar_scope = None
        self.data_table = None
        self.style = 0
        self.selected_hex = None  # Currently selected aircraft
        self.just_selected_hex = None  # Aircraft that was just tapped (to show circle)
        self.aircraft_tracker = aircraft_tracker
        self.previous_aircraft = set()


    def create_widgets(self, style=1):
        """
        Creates the radar scope and data table widgets based on the specified style.

        Layout is calculated for a 480x480 Presto display.

        Args:
            style: The style to use for the widgets (0, 1, or 2).
        """
        self.style = style
        w = self.fb.width
        h = self.fb.height
        if style == self.MAX_RADAR_STYLE:
            # Large scope filling most of the square display, compact table below
            radius = w // 2 - 30
            cx = w // 2
            cy = radius + 10
            table_y = cy + radius + 10
            table_h = h - table_y - 5
            self.radar_scope = RadarScope(
                self.fb, center_x=cx, center_y=cy, radius=radius,
                font=self.status_font, config=self.config
            )
            self.data_table = DataTable(
                self.fb, x=5, y=table_y, width=w - 10, height=table_h,
                table_font=self.table_font, compact=True
            )
        elif style == self.SPLIT_SCREEN_STYLE:
            # Scope on top half, table on bottom half
            half_h = h // 2
            radius = half_h // 2 - 10
            cx = w // 2
            cy = half_h // 2
            self.radar_scope = RadarScope(
                self.fb, center_x=cx, center_y=cy, radius=radius,
                font=self.status_font, config=self.config
            )
            self.data_table = DataTable(
                self.fb, x=5, y=half_h, width=w - 10, height=half_h - 5,
                table_font=self.table_font, status_font=self.status_font
            )
        elif style == self.TABLE_ONLY_STYLE:
            # Full-screen table
            self.radar_scope = None
            self.data_table = DataTable(
                self.fb, x=5, y=5, width=w - 10, height=h - 10,
                table_font=self.table_font, status_font=self.status_font
            )
        else:
            raise ValueError(f"unknown {style=}")

    def switch_layout(self, s):
        self.create_widgets(s)
        # Selection persists across layout changes
        # Clear text cache when layout changes
        self.data_table.clear_cache()

    def _touch_read(self):
        """Read current touch position.  Returns (x, y) or (0, 0) if no touch."""
        self.presto.touch.poll()
        if self.presto.touch.state:
            return self.presto.touch.x, self.presto.touch.y
        return 0, 0

    def main(self):
        """
        Continuous scope loop. Call from REPL or main.
        """
        start = utime.ticks_ms()
        if self.radar_scope:
            self.radar_scope.draw_scope()

        # Touch coordinates persist across loop iterations
        # Read only at end during sleep polling for simplicity
        x, y = 0, 0

        while True:
            start_time = utime.ticks_ms()
            # Process touch event if we have one
            if x != 0 and y != 0:
                self.process_touch(x, y)

            aircraft_list = None
            gc.collect()
            # print(micropython.mem_info())
            aircraft_list = self.aircraft_tracker.fetch_data(max_craft=16)       # magic constants
            aircraft_to_label = aircraft_list[0:(self.data_table.max_rows or 5)] # magic constants

            now = utime.ticks_ms()

            x, y = self._touch_read()
            if x != 0 and y != 0:
                continue

            if self.radar_scope:
                self.radar_scope.draw_planes(aircraft_list, aircraft_to_label,
                                             self.previous_aircraft, selected_hex=self.selected_hex, just_selected_hex=self.just_selected_hex)
                x, y = self._touch_read()
                if x != 0 and y != 0:
                    self.presto.update()
                    continue

            if self.data_table:
                self.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=now, selected_hex=self.selected_hex)
                x, y = self._touch_read()
                if x != 0 and y != 0:
                    self.presto.update()
                    continue

            # Clear just_selected after first draw
            self.just_selected_hex = None

            self.previous_aircraft.update(craft.hex_code for craft in aircraft_list if craft.hex_code is not None)
            x, y = self._touch_read()
            if x != 0 and y != 0:
                self.presto.update()
                continue

            self.presto.update()

            # respect MIN_FETCH_TIME if the loop was faster; otherwise, do not delay
            end_time = utime.ticks_ms()
            loop_time = end_time - start_time
            waiting_time = _cfg.MIN_FETCH_TIME - loop_time
            if waiting_time > 0:
                self.touch_poll_wait(waiting_time)


    def touch_poll_wait(self, waiting_time = 1000):
        # Sleep with touch polling for better responsiveness
        # Reset touch coordinates, then poll during sleep
        x, y = 0, 0
        sleep_remaining = waiting_time
        sleep_chunk = 100
        while sleep_remaining > 0:
            utime.sleep_ms(min(sleep_chunk, sleep_remaining))
            sleep_remaining -= sleep_chunk

            # Check for touch during sleep - read touch only here
            x, y = self._touch_read()
            if x != 0 and y != 0:
                return (x,y)
        return (0,0)



    def process_touch(self, x, y):
        # Style 2 (full-screen table): any touch toggles layout, no selection
        if self.style == self.TABLE_ONLY_STYLE:
            print("fullscreen table touch - changing layout")
            self.fb.clear(_cfg.BLACK)
            s = (self.style + 1) % 3
            self.switch_layout(s)
            self.previous_aircraft = set()
            if self.radar_scope:
                self.radar_scope.draw_scope()
            start = utime.ticks_ms()
        # Other modes: check table for selection, elsewhere for layout toggle
        elif self.data_table.is_in_table_bounds(x, y):
            # Touch is within table bounds - handle selection only, never toggle layout
            picked_hex = self.data_table.pick_hex(x, y)
            if picked_hex == 'deselect':
                # Touch in table area but not on a row - deselect
                print("Deselecting aircraft")
                self.selected_hex = None
                self.just_selected_hex = None
            elif picked_hex:
                # Touch is on a table row - toggle selection
                if self.selected_hex == picked_hex:
                    # Same aircraft - deselect
                    print(f"Deselecting aircraft: {picked_hex}")
                    self.selected_hex = None
                    self.just_selected_hex = None
                else:
                    # Different aircraft - select and mark as just selected
                    print(f"Selected aircraft: {picked_hex}")
                    self.selected_hex = picked_hex
                    self.just_selected_hex = picked_hex
        elif self.radar_scope:
            # Touch is completely outside data table - toggle layout
            # left third -> rotate style left; right third; rotate style right; center-third: redisplay same style
            print("outside table touch - changing layout")
            self.fb.clear(_cfg.BLACK)
            s = self.style
            rr = self.radar_scope.radius / 3
            if ((x > (self.radar_scope.center_x - rr)) and
                (x < (self.radar_scope.center_x + rr)) and
                (y > (self.radar_scope.center_y - rr)) and
                (y < (self.radar_scope.center_y + rr))):
                nm = _cfg.RADIUS_NM
                nm = { 5:10, 10:15, 15:30, 30:50, 50:5 }.get(nm, 5)
                print(f"range touch {_cfg.RADIUS_NM=} {nm=}")
                _cfg.RADIUS_NM = nm
            elif x < (self.radar_scope.center_x - rr):
                s = (s - 1) % 3
            elif x > (self.radar_scope.center_x + rr):
                s = (s + 1) % 3
            self.switch_layout(s)
            self.previous_aircraft = set()
            if self.radar_scope:
                self.radar_scope.draw_scope()
            start = utime.ticks_ms()
        else:
            print(f"ignoring touch at {(x,y)=}")


class App:
    def __init__(self):
        # Initialize Presto (handles WiFi via EzWiFi reading secrets.py)
        self.presto = Presto()
        self.presto.connect()

        display_raw = self.presto.display

        # Convert config color tuples to PicoGraphics pen indices in-place
        for attr in _COLOR_ATTRS:
            rgb = getattr(_cfg, attr)
            if isinstance(rgb, tuple):
                setattr(_cfg, attr, display_raw.create_pen(*rgb))

        # Wrap the PicoGraphics display with the CYD-compatible API
        self.display = PicoDisplay(display_raw)

        # Clear screen with black
        self.display.clear(_cfg.BLACK)
        self.presto.update()

        # Fonts: PixelFont(scale=1) -> 8 px tall, ~6 px wide per character
        self.status_font = PixelFont(scale=1)
        self.table_font = PixelFont(scale=1)

        # Create the aircraft tracker
        self.aircraft_tracker = AircraftTracker()
        # Create radar object
        self.radar = Radar(self.presto, self.display, _cfg, self.status_font, self.table_font, self.aircraft_tracker)
        self.radar.create_widgets(Radar.MAX_RADAR_STYLE)

    def main(self):
        # display loop
        self.radar.main()

if __name__ == "__main__":
    app = App()
    app.main()
