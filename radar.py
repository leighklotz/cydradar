# Adapted from https://github.com/nicespoon/retro-adsb-radar
# Modified for ESP32 MicroPython from RPi Python
#
# Updated to use the sweep widget in sweep.py and to avoid known compatibility issues:
# - Performs one full redraw at startup (radar.draw(..., sweep=False))
# - Uses radar.step(...) per frame to advance the beam (passes aircraft_list and draw_labels)
# - Catches KeyboardInterrupt to stop cleanly in REPL
# - Uses utime.ticks_ms() for table timestamps

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
# from sweep import RadarSweepScope

# initialize display
cyd = CYD(display_width=240, display_height=320, rotation=180)
fb = cyd.display
fb.clear(_cfg.BLACK)

# sample aircraft dataset

status_font = XglcdFont('fonts/Neato5x7.c', 5, 7, letter_count=223)
table_font = XglcdFont('fonts/FixedFont5x8.c', 5, 8, letter_count=223)
radar = RadarScope(fb, center_x=120, center_y=80, radius=70, font=status_font, config=_cfg)
table = DataTable(fb, x=4, y=170, width=236, height=150, 
                  table_font=table_font, status_font=status_font)
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
    now = utime.ticks_ms()
    radar.draw(aircraft_list)
    table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
    return now

def sweep_loop(step_delay_ms=30):
    """
    Continuous sweep loop. Call from REPL or main.
    step_delay_ms: ms to sleep between steps (tune for appearance vs CPU)
    """
    # do an initial full redraw to ensure background & ring labels are present
    aircraft_list = fetch_your_data()
    radar.draw(aircraft_list, sweep=False)  # full redraw once at startup
    table.draw(aircraft_list, status="OK", last_update_ticks_ms=utime.ticks_ms())

    try:
        while True:
            now = utime.ticks_ms()
            aircraft_list = fetch_your_data()
            # advance by one segment (show pip labels when illuminated)
            radar.step(aircraft_list)
            # refresh the table with the same timestamp for a consistent UI
            table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
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
    radar.draw_scope()
    while True:
        x, y = cyd.touches()
        aircraft_list = fetch_your_data()
        now = utime.ticks_ms()
        if x != 0 and y != 0:
            print("clearing screen")
            fb.clear(_cfg.BLACK)
            radar.draw_scope()
            start = now
            previous_aircraft = set()

        radar.draw_planes(aircraft_list, previous_aircraft)
        table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
        if once: break
        previous_aircraft.update(craft.hex_code for craft in aircraft_list if craft.hex_code is not None)
        utime.sleep_ms(1000)


# Example: run a few steps for testing
if __name__ == "__main__":
    # RadarScope:
    now = single_update()
    # RadarSweepScope:
    # sweep_loop(step_delay_ms=30)
    # scope_loop()

