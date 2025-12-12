# https://github.com/nicespoon/retro-adsb-radar/blob/main/utils.py

import math

def calculate_distance_bearing(lat1: float, lon1: float, lat2: float, lon2: float):
    """Calculate distance in nautical miles and bearing in degrees"""
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    distance_km = 2 * math.asin(math.sqrt(a)) * 6371
    distance_nm = distance_km * 0.539957
    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    return distance_nm, bearing
