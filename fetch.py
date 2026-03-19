# Modified for MicroPython from
# https://github.com/nicespoon/retro-adsb-radar/blob/main/data_fetcher.py

import time
import urequests as requests

from cfg import _cfg
from aircraft import create_aircraft_data

class AircraftTracker:
    """Handles fetching aircraft data from dump1090"""
    def __init__(self):
        self.status = "INITIALISING"
        self.last_update = time.time()

    def fetch_data(self, max_craft=100):
        """Fetch aircraft from local dump1090"""
        self.status = "SCANNING"
        self.last_update = time.time()
        response = None
        try:
            print(f"Fetching aircraft data from {_cfg.DUMP1090_URL}")
            response = requests.get(_cfg.DUMP1090_URL, timeout=10)
            if response.status_code >= 400:
                raise Exception(f"HTTP error: Status code {response.status_code=} {response.reason=}")
            content_length = response.headers.get('Content-Length', None)
            print(f"response {content_length=}")
            print(f"response {response.text=}")
            data = response.json()
            n_aircraft = len(data.get('aircraft', []))
            print(f"Fetched {n_aircraft=}/{max_craft=}")
            aircraft_list = []
            for ac_data in data.get('aircraft', [])[0:max_craft]:
                ac = create_aircraft_data(ac_data)
                if ac:
                    aircraft_list.append(ac)
                    print(f"{ac_data=}")
            print(f"✅ Collected {len(aircraft_list)} <= {max_craft=} aircraft within {_cfg.RADIUS_NM}NM range")
            self.status = "ACTIVE" if len(aircraft_list) > 0 else "NO CONTACTS"
            return aircraft_list
        except Exception as e:
            print(f"❌ Error: Couldn't fetch aircraft data: {e}; skipping")
            if response:
                print("response.text", response.text())
            self.status = "FAILED"
            return []
        finally:
            if response:
                try:
                    response.close()
                except Exception as e:
                    print(f"❌ Error: Couldn't close http connection; skipping")

                    
