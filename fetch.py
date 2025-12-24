# Modified for MicroPython from
# https://github.com/nicespoon/retro-adsb-radar/blob/main/data_fetcher.py

import time
import requests

from cfg import _cfg
from aircraft import Aircraft

class AircraftTracker:
    """Handles fetching aircraft data from dump1090"""
    __slots__ = [ 'status', 'last_update' ]

    def __init__(self):
        self.status = "INITIALISING"
        self.last_update = time.time()

    def fetch_data(self, max_craft=100):
        """Fetch aircraft from local dump1090"""
        self.status = "SCANNING"
        self.last_update = time.time()
        try:
            print(f"Fetching aircraft data from {_cfg.DUMP1090_URL}")
            response = requests.get(_cfg.DUMP1090_URL, timeout=10)
            if response.status_code >= 400:
                raise Exception(f"HTTP error: Status code {response.status_code}")
            data = response.json()
            n_aircraft = len(data.get('aircraft', []))
            print(f"Fetched {n_aircraft=}/{max_craft=}")
            aircraft_list = []
            for ac_data in data.get('aircraft', [])[0:max_craft]:
                ac = Aircraft.from_dict(ac_data)
                if ac:
                    aircraft_list.append(ac)
                    print(f"{ac_data=}")
            print(f"✅ Collected {len(aircraft_list)} <= {max_craft=} aircraft within {_cfg.RADIUS_NM}NM range")
            self.status = "ACTIVE" if len(aircraft_list) > 0 else "NO CONTACTS"
            return aircraft_list
        except Exception as e:
            print(f"❌ Error: Couldn't fetch aircraft data: {e}; skipping")
            self.status = "FAILED"
            return []
