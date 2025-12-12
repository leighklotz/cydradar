# Example usage (paste into your main.py on the device):
#
# from cydr import CYD
# import utime
# from ui_components_mpy import RadarScope, DataTable, SampleAircraft, _cfg, BRIGHT_GREEN, BLACK
#
# cyd = CYD()
# fb = cyd.display
# fb.clear(BLACK)
#
# # sample aircraft dataset
# ac1 = SampleAircraft(callsign="ALFA01", lat=0.01, lon=0.00, track=45, speed=250, altitude=12000, distance=5.0, is_military=False)
# ac2 = SampleAircraft(callsign="BRAVO2", lat=-0.005, lon=0.02, track=270, speed=120, altitude=8000, distance=8.2, is_military=True)
# ac3 = SampleAircraft(callsign="CHAR3", lat=0.02, lon=-0.015, track=180, speed=350, altitude=30000, distance=12.5, is_military=False)
# aircraft_list = [ac1, ac2, ac3]
#
# radar = RadarScope(fb, center_x=120, center_y=80, radius=70, font=None)
# table = DataTable(fb, x=4, y=170, width=312, height=66, font=None)
#
# # single update (for testing)
# now = utime.ticks_ms()
# radar.draw(aircraft_list)
# table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
#
# # In a loop you would refresh periodically:
# # while True:
# #     aircraft_list = fetch_your_data()
# #     now = utime.ticks_ms()
# #     fb.clear(BLACK)
# #     radar.draw(aircraft_list)
# #     table.draw(aircraft_list, status="OK", last_update_ticks_ms=now)
# #     utime.sleep_ms(200)
#
# The module calls the CYD display API directly (no runtime guessing). It expects fb to be cyd.display,
# which provides methods such as: draw_lines, draw_line, draw_pixel, fill_circle, fill_rectangle,
# draw_rectangle, draw_text (with font), and draw_text8x8.
