from cydr import CYD

import utime
import random
import json

from xglcd_font import XglcdFont
from datatable import DataTable
from aircraft import Aircraft
from cfg import _cfg
from scope import RadarScope
from fetch import AircraftTracker


class Radar:
    """
    Encapsulates the radar display logic, including scope and data table.
    Handles widget creation, updates, and styling.
    """

    def __init__(self, fb, config, status_font, table_font):
        """
        Initializes the Radar object.

        Args:
            fb: The framebuffer object for drawing.
            config: The configuration object.
            status_font: The font for status messages.
            table_font: The font for the data table.
        """
        self.fb = fb
        self.config = config
        self.status_font = status_font
        self.table_font = table_font
        self.radar_scope = None
        self.data_table = None
        self.style = 0
        self.selected_hex = None  # Currently selected aircraft
        self.just_selected_hex = None  # Aircraft that was just tapped (to show circle)
        self.MAX_RADAR_STYLE = 0
        self.SPLIT_SCREEN_STYLE = 1
        self.TABLE_ONLY_STYLE = 2

    def create_widgets(self, style=1):
        """
        Creates the radar scope and data table widgets based on the specified style.

        Args:
            style: The style to use for the widgets (0, 1, or 2).
        """
        self.style = style
        if style == self.MAX_RADAR_STYLE:
            # Max-sized scope on top and shorter table below
            self.radar_scope = RadarScope(
                self.fb, center_x=120, center_y=116, radius=116,
                font=self.status_font, config=self.config
            )
            self.data_table = DataTable(
                self.fb, x=4, y=234, width=236, height=86,
                table_font=self.table_font, compact=True
            )
        elif style == self.SPLIT_SCREEN_STYLE:
            # Split screen, even sized scope on top and table below
            self.radar_scope = RadarScope(
                self.fb, center_x=120, center_y=80, radius=70,
                font=self.status_font, config=self.config
            )
            self.data_table = DataTable(
                self.fb, x=4, y=170, width=236, height=150,
                table_font=self.table_font, status_font=self.status_font
            )
        elif style == self.TABLE_ONLY_STYLE:
            # Only Table
            self.radar_scope = None
            self.data_table = DataTable(
                self.fb, x=4, y=4, width=236, height=312,
                table_font=self.table_font, status_font=self.status_font
            )
        else:
            raise ArgumentException(f"unknown {style=}")

    def switch_layout(self, s):
        self.create_widgets(s)
        # Selection persists across layout changes
        # Clear text cache when layout changes
        self.data_table.clear_cache()

# initialize display
cyd = CYD(display_width=240, display_height=320, rotation=180)
fb = cyd.display
fb.clear(_cfg.BLACK)

# sample aircraft dataset

status_font = XglcdFont('fonts/Neato5x7.c', 5, 7, letter_count=223)
table_font = XglcdFont('fonts/FixedFont5x8.c', 5, 8, letter_count=223)
radar = Radar(fb, _cfg, status_font, table_font)
radar.create_widgets(radar.MAX_RADAR_STYLE)
aircraft_tracker = AircraftTracker()

def fetch_your_data():
    return aircraft_tracker.fetch_data()

def scope_loop(once=False):
    """
    Continuous scope loop. Call from REPL or main.
    """
    start = utime.ticks_ms()
    previous_aircraft = set()
    if radar.radar_scope:
        radar.radar_scope.draw_scope()
        if _cfg.WAYPOINTS:
            radar.radar_scope.draw_waypoints(_cfg.WAYPOINTS)

    # Touch coordinates persist across loop iterations
    # Read only at end during sleep polling for simplicity
    x, y = 0, 0
    
    while True:
        # Process touch event if we have one
        if x != 0 and y != 0:
            process_touch(x, y)

        aircraft_list = fetch_your_data()
        now = utime.ticks_ms()

        if radar.radar_scope:
            radar.radar_scope.draw_planes(aircraft_list, previous_aircraft, selected_hex=radar.selected_hex, just_selected_hex=radar.just_selected_hex)

        if radar.data_table:
            radar.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=now, selected_hex=radar.selected_hex)

        # Clear just_selected after first draw
        radar.just_selected_hex = None

        previous_aircraft.update(craft.hex_code for craft in aircraft_list if craft.hex_code is not None)
        
        if once:
            break

        x,y = touch_poll_wait()

def touch_poll_wait():
    # Sleep with touch polling for better responsiveness
    # Reset touch coordinates, then poll during sleep
    x, y = 0, 0
    sleep_remaining = 1000
    sleep_chunk = 100
    while sleep_remaining > 0:
        utime.sleep_ms(min(sleep_chunk, sleep_remaining))
        sleep_remaining -= sleep_chunk
            
        # Check for touch during sleep - read touch only here
        x, y = cyd.touches()
        if x != 0 and y != 0:
            return (x,y)
    return (0,0)

def process_touch(x, y):
    # Style 2 (full-screen table): any touch toggles layout, no selection
    if radar.style == radar.TABLE_ONLY_STYLE:
        print("fullscreen table touch - changing layout")
        fb.clear(_cfg.BLACK)
        s = (radar.style + 1) % 3
        radar.switch_layout(s)
        if radar.radar_scope:
            radar.radar_scope.draw_scope()
        start = utime.ticks_ms()
        previous_aircraft = set()
    # Other modes: check table for selection, elsewhere for layout toggle
    elif radar.data_table.is_in_table_bounds(x, y):
        # Touch is within table bounds - handle selection only, never toggle layout
        picked_hex = radar.data_table.pick_hex(x, y)
        if picked_hex == 'deselect':
            # Touch in table area but not on a row - deselect
            print("Deselecting aircraft")
            radar.selected_hex = None
            radar.just_selected_hex = None
        elif picked_hex:
            # Touch is on a table row - toggle selection
            if radar.selected_hex == picked_hex:
                # Same aircraft - deselect
                print(f"Deselecting aircraft: {picked_hex}")
                radar.selected_hex = None
                radar.just_selected_hex = None
            else:
                # Different aircraft - select and mark as just selected
                print(f"Selected aircraft: {picked_hex}")
                radar.selected_hex = picked_hex
                radar.just_selected_hex = picked_hex
    elif radar.radar_scope:
        # Touch is completely outside data table - toggle layout
        # left third -> rotate style left; right third; rotate style right; center-third: redisplay same style
        print("outside table touch - changing layout")
        fb.clear(_cfg.BLACK)
        s = radar.style
        rr = radar.radar_scope.radius / 3
        if x < (radar.radar_scope.center_x - rr):
            s = (s - 1) % 3
        elif x > (radar.radar_scope.center_x + rr):
            s = (s + 1) % 3
        radar.switch_layout(s)
        if radar.radar_scope:
            radar.radar_scope.draw_scope()
        start = utime.ticks_ms()
        previous_aircraft = set()
    else:
        printf("ignoring touch at {(x,y)=}")
