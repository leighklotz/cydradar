### -*-mode: python-*-

import json

from cfg import _cfg
from utils import calculate_distance_bearing

class Aircraft:
    """Aircraft data from tar1090"""
    __slots__ = [ 'hex_code', 'callsign', 'category', 'squawk', 'lat', 'lon', 'altitude', 'speed', 'vert_rate', 'track', 'distance', 'bearing', 'is_military' ]


    def __init__(self, hex_code: str, callsign: str, category: str, squawk: str, lat: float, lon: float, altitude: int, speed: int, vert_rate: int, track: float, distance: float, bearing: float, is_military: bool = False):
        self.hex_code = hex_code
        self.callsign = callsign
        self.category = category
        self.squawk = squawk
        self.lat = lat
        self.lon = lon
        self.altitude = altitude
        self.speed = speed
        self.vert_rate = vert_rate
        self.track = track
        self.distance = distance
        self.bearing = bearing
        self.is_military = is_military

    @staticmethod
    def from_dict(data: dict):
        """Create an Aircraft object from a dictionary."""
        # todo: support packets without position?
        if 'lat' not in data or 'lon' not in data:
            return None
        lat, lon = data['lat'], data['lon']
        distance, bearing = calculate_distance_bearing(_cfg.LAT, _cfg.LON, lat, lon)
        if distance > _cfg.RADIUS_NM:
            return None
        hex_code = data.get('hex', '  ').lower()
        mil_prefixes = tuple(prefix.lower() for prefix in _cfg.MIL_PREFIX_LIST)
        is_military = hex_code.startswith(mil_prefixes)
        return Aircraft(
            hex_code=hex_code,
            callsign=data.get('flight', "").strip()[:8] or None,
            category=data.get('category', None),
            squawk = data.get('squawk', None),
            lat=lat, lon=lon,
            altitude=data.get('altitude', 0) or 0,
            speed=int(data.get('speed', 0) or 0),
            vert_rate=int(data.get('vert_rate', 0) or 0),
            track=data.get('track', 0) or 0,
            distance=distance,
            bearing=bearing,
            is_military=is_military
        )

