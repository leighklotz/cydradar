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

from xglcd_font import XglcdFont
from ui_components_map import DataTable, SampleAircraft, _cfg

# from sweep import RadarSweepScope
from radarscope import RadarScope

# initialize display
cyd = CYD(display_width=240, display_height=320, rotation=0)
fb = cyd.display
fb.clear(_cfg.BLACK)

# sample aircraft dataset
def rand_pos():
    return random.uniform(-0.5, 0.5)

def ac1(): return SampleAircraft(callsign="ALFA01", lat=rand_pos(), lon=rand_pos(), track=45, speed=250, altitude=12000, distance=5.0, is_military=False)
def ac2(): return SampleAircraft(callsign="BRAVO2", lat=rand_pos(), lon=rand_pos(), track=270, speed=120, altitude=8000, distance=8.2, is_military=True)
def ac3(): return SampleAircraft(callsign="CHAR3", lat=rand_pos(), lon=rand_pos(), track=180, speed=350, altitude=30000, distance=12.5, is_military=False)

status_font = XglcdFont('fonts/Neato5x7.c', 5, 7, letter_count=223)
table_font = XglcdFont('fonts/FixedFont5x8.c', 5, 8, letter_count=223)

# create radar sweep widget (tune segments/radius_step/trail_length for performance/appearance)
#radar = RadarSweepScope(fb, 120, 80, 70, segments=10, radius_step=2, trail_length=0, show_pip_labels=True)
#radar = RadarSweepScope(fb, 120, 80, 70, segments=0, radius_step=2, trail_length=0, show_pip_labels=True)

radar = RadarScope(fb, center_x=120, center_y=80, radius=70, font=status_font, config=_cfg)

# data table
# table = DataTable(fb, x=4, y=170, width=312, height=66, font=None)
table = DataTable(fb, x=4, y=170, width=236, height=150, 
                  table_font=table_font, status_font=status_font)

def fetch_your_data():
    # Replace with real data fetch. Returning the sample list here.
    return [ac1(), ac2(), ac3()]

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

def scope_loop():
    """
    Continuous scope loop. Call from REPL or main.
    """
    # do an initial full redraw to ensure background & ring labels are present
    aircraft_list = fetch_your_data()
    radar.draw(aircraft_list)  # full redraw once at startup
    table.draw(aircraft_list, status="OK", last_update_ticks_ms=utime.ticks_ms())

    try:
        while True:
            now = utime.ticks_ms()
            aircraft_list = fetch_your_data()
            radar.draw(aircraft_list)
            table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
    except KeyboardInterrupt:
        # stop cleanly in REPL
        print("Scope stopped by user")

# Example: run a few steps for testing
if __name__ == "__main__":
    # RadarScope:
    now = single_update()
    # RadarSweepScope:
    # sweep_loop(step_delay_ms=30)
    # scope_loop()

