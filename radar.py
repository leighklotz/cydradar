from cydr import CYD

import micropython

import utime

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
    MAX_RADAR_STYLE = 0
    SPLIT_SCREEN_STYLE = 1
    TABLE_ONLY_STYLE = 2

    __slots__ = [ 'cyd', 'fb', 'config', 'status_font', 'table_font', 'radar_scope', 'data_table', 'style', 'selected_hex', 'just_selected_hex', 'aircraft_tracker',
                  'previous_aircraft' ]

    def __init__(self, cyd, config, status_font, table_font, aircraft_tracker):
        """
        Initializes the Radar object.

        Args:
            cyd: the cyd device
            fb: The framebuffer object for drawing.
            config: The configuration object.
            status_font: The font for status messages.
            table_font: The font for the data table.
            aircraft_tracker: the source of data
        """
        self.cyd = cyd
        self.fb = cyd.display
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
            aircraft_list = self.aircraft_tracker.fetch_data(max_craft=40)
            aircraft_to_label = aircraft_list[0:(self.data_table.max_rows or 5)]
            # print(f"aircraft_list={len(aircraft_list)} aircraft_to_label={len(aircraft_to_label)}")
            now = utime.ticks_ms()

            if self.radar_scope:
                self.radar_scope.draw_planes(aircraft_list, aircraft_to_label,
                                             self.previous_aircraft, selected_hex=self.selected_hex, just_selected_hex=self.just_selected_hex)

            # poll
            x, y = self.cyd.touches()
            if x != 0 and y != 0:
                continue

            if self.data_table:
                self.data_table.draw(aircraft_list, status="OK", last_update_ticks_ms=now, selected_hex=self.selected_hex)

            # Clear just_selected after first draw
            self.just_selected_hex = None

            self.previous_aircraft.update(craft.hex_code for craft in aircraft_list if craft.hex_code is not None)
            # print(f"* len(self.previous_aircraft)={len(self.previous_aircraft)}")
            # print(micropython.mem_info())

            # x,y = self.touch_poll_wait()
            x, y = self.cyd.touches()
            end_time = utime.ticks_ms()
            print(f"loop time { end_time - start_time }ms")

#    def touch_poll_wait(self, t):
#        # Sleep with touch polling for better responsiveness
#        # Reset touch coordinates, then poll during sleep
#        x, y = 0, 0
#        sleep_remaining = 1000
#        sleep_chunk = 100
#        while sleep_remaining > 0:
#            utime.sleep_ms(min(sleep_chunk, sleep_remaining))
#            sleep_remaining -= sleep_chunk
#
#            # Check for touch during sleep - read touch only here
#            x, y = self.cyd.touches()
#            if x != 0 and y != 0:
#                return (x,y)
#        return (0,0)

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
            printf("ignoring touch at {(x,y)=}")


class App:
    __slots__ = [ 'cyd', 'status_font', 'table_font', 'aircraft_tracker', 'radar' ]

    def __init__(self):
        # initialize display
        self.cyd = CYD(display_width=240, display_height=320, rotation=180)
        self.cyd.display.clear(_cfg.BLACK)

        self.status_font = XglcdFont('fonts/Neato5x7.c', 5, 7, letter_count=223)
        self.table_font = XglcdFont('fonts/FixedFont5x8.c', 5, 8, letter_count=223)

        # Create the aircraft tracker
        self.aircraft_tracker = AircraftTracker()
        # create radar object
        self.radar = Radar(self.cyd, _cfg, self.status_font, self.table_font, self.aircraft_tracker)
        self.radar.create_widgets(Radar.MAX_RADAR_STYLE)

    def main(self):
        # display loop
        self.radar.main()

if __name__ == "__main__":
    app = App()
    app.main()
