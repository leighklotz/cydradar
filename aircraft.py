### -*-mode: python-*-

import json

from cfg import _cfg
from utils import calculate_distance_bearing



SAMPLE_AIRCRAFT_JSON = """
{ "now" : 1765419480.0,
  "messages" : 145,
  "aircraft" : [
    {"hex":"a33eda","altitude":19650,"vert_rate":3392,"track":134,"speed":410,"mlat":[],"tisb":[],"messages":13,"seen":0.9,"rssi":-8.8},
    {"hex":"407993","squawk":"6532","flight":"BAW28K  ","lat":37.461090,"lon":-122.152600,"nucp":7,"seen_pos":0.7,"altitude":4550,"vert_rate":-896,"track":26,"speed":189,"category":"A5","mlat":[],"tisb":[],"messages":121,"seen":0.0,"rssi":-3.4},
    {"hex":"a55785","lat":37.323443,"lon":-122.295745,"nucp":7,"seen_pos":24.9,"altitude":13775,"vert_rate":2496,"track":136,"speed":389,"mlat":[],"tisb":[],"messages":11,"seen":23.5,"rssi":-6.9}
  ]
}
"""
class Aircraft:
    """Aircraft data from tar1090"""
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

def test_it():
    for data in json.loads(SAMPLE_AIRCRAFT_JSON)["aircraft"]:
        print(data)
        craft = Aircraft.from_dict(data)
        if craft is not None:
            print(f"=> {craft.__dict__}")
        else:
            print("=> None")
        print()

if __name__ == "__main__":
    test_it()
