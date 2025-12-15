# Modified for MicroPython from
# https://github.com/nicespoon/retro-adsb-radar/blob/main/data_fetcher.py
import requests
import time

from cfg import _cfg
from aircraft import Aircraft

class AircraftTracker:
    """Handles fetching aircraft data from dump1090"""
    def __init__(self):
        self.aircraft = []
        self.status = "INITIALISING"
        self.last_update = time.time()

    def fetch_data(self):
        """Fetch aircraft from local dump1090"""
        self.status = "SCANNING"
        self.last_update = time.time()
        try:
            print(f"Fetching aircraft data from {_cfg.DUMP1090_URL}")
            response = requests.get(_cfg.DUMP1090_URL, timeout=600)
            # micropython Error: Couldn't fetch aircraft data: 'Response' object has no attribute 'raise_for_status'
            if response.status_code >= 400:
                raise Exception(f"HTTP error: Status code {response.status_code}")
            data = response.json()
            n = len(data.get('aircraft', []))
            print(f"Fetched {n} aircraft")
            aircraft_list = []
            for ac_data in data.get('aircraft', []):
                ac = Aircraft.from_dict(ac_data)
                if ac:
                    aircraft_list.append(ac)
                    print(f"{ac_data=}")
            print(f"✅ Found {len(aircraft_list)} aircraft within {_cfg.RADIUS_NM}NM range")
            self.status = "ACTIVE" if self.aircraft else "NO CONTACTS"
            return aircraft_list
        except Exception as e:
            print(f"❌ Error: Couldn't fetch aircraft data: {e}; skipping")
            self.status = "FAILED"
            return []
