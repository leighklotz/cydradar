from cydr import CYD

import utime
import random
import json

from xglcd_font import XglcdFont
from datatable import DataTable
from aircraft import Aircraft
from cfg import _cfg
from radarscope import RadarScope
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

    def create_widgets(self, style=1):
        """
        Creates the radar scope and data table widgets based on the specified style.

        Args:
            style: The style to use for the widgets (0, 1, or 2).
        """
        self.style = style
        if style == 0:
            # Max-sized scope on top and shorter table below
            self.radar_scope = RadarScope(
                self.fb, center_x=120, center_y=118, radius=118,
                font=self.status_font, config=self.config
            )
            self.data_table = DataTable(
                self.fb, x=4, y=236, width=236, height=80,
                table_font=self.table_font, compact=True
            )
        elif style == 1:
            # Split screen, even sized scope on top and table below
            self.radar_scope = RadarScope(
                self.fb, center_x=120, center_y=80, radius=70,
                font=self.status_font, config=self.config
            )
            self.data_table = DataTable(
                self.fb, x=4, y=170, width=236, height=150,
                table_font=self.table_font, status_font=self.status_font
            )
        elif style == 2:
            # Only Table
            self.radar_scope = None
            self.data_table = DataTable(
                self.fb, x=4, y=4, width=236, height=312,
                table_font=self.table_font, status_font=self.status_font
            )
        else:
            raise ArgumentException(f"unknown {style=}")

    def update(self, aircraft_list):
        """
        Updates the radar display with new aircraft data.

        Args:
            aircraft_list: A list of Aircraft objects.
        """
        now = utime.ticks_ms()
        if self.radar_scope:
            self.radar_scope.draw_scope()
            self.radar_scope.draw_planes(aircraft_list, selected_hex=self.selected_hex)
        self.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=now, selected_hex=self.selected_hex)

    def next_layout(self):
        s = (self.style + 1) % 3
        self.create_widgets(s)

# initialize display
cyd = CYD(display_width=240, display_height=320, rotation=180)
fb = cyd.display
fb.clear(_cfg.BLACK)

# sample aircraft dataset

status_font = XglcdFont('fonts/Neato5x7.c', 5, 7, letter_count=223)
table_font = XglcdFont('fonts/FixedFont5x8.c', 5, 8, letter_count=223)
radar = Radar(fb, _cfg, status_font, table_font)
radar.create_widgets(0)  # Initial style
aircraft_tracker = AircraftTracker()


def fetch_your_data():
    return aircraft_tracker.fetch_data()


def single_update():
    """
    Do a single update:
    - full initial redraw done once via radar.draw(..., sweep=False)
    - subsequent calls can use radar.step(...) (advances one segment)
    """
    aircraft_list = fetch_your_data()
    radar.update(aircraft_list)
    return utime.ticks_ms()


def sweep_loop(step_delay_ms=30):
    """
    Continuous sweep loop. Call from REPL or main.
    step_delay_ms: ms to sleep between steps (tune for appearance vs CPU)
    """
    # do an initial full redraw to ensure background & ring labels are present
    aircraft_list = fetch_your_data()
    if radar.radar_scope:
        radar.radar_scope.draw_scope()
        radar.radar_scope.draw_planes(aircraft_list, selected_hex=radar.selected_hex)  # full redraw once at startup
    radar.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=utime.ticks_ms(), selected_hex=radar.selected_hex)

    try:
        while True:
            now = utime.ticks_ms()
            aircraft_list = fetch_your_data()
            # refresh scope and planes
            if radar.radar_scope:
                radar.radar_scope.draw_planes(aircraft_list, selected_hex=radar.selected_hex)
            # refresh the table with the same timestamp for a consistent UI
            radar.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=now, selected_hex=radar.selected_hex)
            utime.sleep_ms(step_delay_ms)
    except KeyboardInterrupt:
        # stop cleanly in REPL
        print("Sweep stopped by user")


def scope_loop(once=False):
    """
    Continuous scope loop. Call from REPL or main.
    """
    start = utime.ticks_ms()
    previous_aircraft = set()
    if radar.radar_scope:
        radar.radar_scope.draw_scope()
    while True:
        x, y = cyd.touches()
        aircraft_list = fetch_your_data()
        now = utime.ticks_ms()
        if x != 0 and y != 0:
            # Check if touch is on data table
            picked_hex = radar.data_table.pick_hex(x, y)
            if picked_hex:
                # Touch is on a table row - select that aircraft
                print(f"Selected aircraft: {picked_hex}")
                radar.selected_hex = picked_hex
            else:
                # Touch is elsewhere (scope area) - toggle layout
                print("clearing screen")
                fb.clear(_cfg.BLACK)
                print("next layout")
                radar.next_layout()
                if radar.radar_scope:
                    radar.radar_scope.draw_scope()
                start = now
                previous_aircraft = set()

        if radar.radar_scope:
            radar.radar_scope.draw_planes(aircraft_list, previous_aircraft, selected_hex=radar.selected_hex)
        radar.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=now, selected_hex=radar.selected_hex)
        if once:
            break
        previous_aircraft.update(
            craft.hex_code for craft in aircraft_list if craft.hex_code is not None
        )
        utime.sleep_ms(1000)


# Example: run a few steps for testing
if __name__ == "__main__":
    # RadarScope:
    now = single_update()
    # RadarSweepScope:
    # sweep_loop(step_delay_ms=30)
    # scope_loop()
