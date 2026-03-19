# Retro ADS-B Radar for Pimoroni Presto

This project implements a retro-style ADS-B radar display on the [Pimoroni Presto](https://shop.pimoroni.com/products/presto) (RP2350 + ST7701 480×480 touchscreen).

It fetches aircraft data from a local [dump1090](https://github.com/flightaware/dump1090) instance and visualizes them on a radar screen.  Adapted from the Raspberry Pi project [nicespoon/retro-adsb-radar](https://github.com/nicespoon/retro-adsb-radar), ported to MicroPython on the Pimoroni Presto.

## Features

*   **ADS-B Visualization:** Displays aircraft positions, altitude, speed, track, and callsign.
*   **Radar Scope:** Pips on a radar-style display with range rings and crosshairs.
*   **Aircraft Table:** Tabular listing of nearby aircraft with key information.
*   **Military Aircraft Identification:** Highlights military aircraft in red.
*   **Configurable:** Adjustable range, display colors, waypoints, and other settings.
*   **Touchscreen Controls:**
    *   Tap scope to switch layouts (left/center/right zones)
    *   Tap an aircraft row to select/deselect (yellow highlight)
    *   Tap elsewhere in table to deselect
    *   Selected aircraft highlighted in both table and scope

## Hardware Requirements

*   [Pimoroni Presto](https://shop.pimoroni.com/products/presto) (RP2350, 480×480 ST7701 display, capacitive touch)
*   WiFi connectivity (built-in on Presto)

## Software Requirements

*   [Pimoroni Presto MicroPython firmware](https://github.com/pimoroni/presto) (includes PicoGraphics, EzWiFi, and FT6236 touch driver)
*   [Thonny IDE](https://thonny.org/) (recommended for uploading and running files)

## Installation

### 1. Flash Firmware

Flash the latest Pimoroni Presto MicroPython firmware from the [Pimoroni Presto releases page](https://github.com/pimoroni/presto/releases).

### 2. Configure WiFi credentials

Create `secrets.py` based on `secrets.py.example`:

```python
WIFI_SSID = "your_network_name"
WIFI_PASSWORD = "your_network_password"
```

The Presto firmware reads `WIFI_SSID` and `WIFI_PASSWORD` (these exact uppercase names are required) from `secrets.py` in the root of the device.  Place this file at the **root** of the Presto filesystem (`/secrets.py`), not inside the `cydradar` subdirectory.

> **Do not commit `secrets.py` to version control!**

### 3. Copy the application files

Using Thonny (or another MicroPython file manager), create a `cydradar` directory on the Presto and upload all of the following files into it:

```
/cydradar/
    main.py
    radar.py
    scope.py
    datatable.py
    display_wrapper.py
    aircraft.py
    fetch.py
    utils.py
    cfg.py          ← copy from cfg.py.sample and edit
```

Do **not** place application files in the root directory (`/`) — the Presto may have other MicroPython software installed there.

### 4. Configure the application

Copy `cfg.py.sample` to `cfg.py` inside the `cydradar` directory and edit it:

```python
DUMP1090_URL = 'http://192.168.1.x:8080/aircraft.json'  # your dump1090 host
LAT = 37.4611                                            # your latitude
LON = -122.1150                                          # your longitude
RADIUS_NM = 15                                           # radar range
```

### 5. Run with Thonny

1. Open Thonny and connect to the Presto via USB.
2. Open `/cydradar/main.py` on the device.
3. Click **Run** (▶) — Thonny will execute `/cydradar/main.py` directly on the device.

`main.py` automatically adds `/cydradar` to `sys.path` so all module imports resolve correctly regardless of the working directory.

## Configuration (`cfg.py`)

| Parameter | Description |
|---|---|
| `DUMP1090_URL` | URL of your dump1090 JSON endpoint |
| `LAT`, `LON` | Your location (used for distance calculations) |
| `RADIUS_NM` | Radar display range in nautical miles |
| `TRAIL_MIN_LENGTH` / `TRAIL_MAX_LENGTH` | Pixel length range for aircraft track lines |
| `TRAIL_MAX_SPEED` | Speed (kts) at which trail reaches maximum length |
| `FETCH_INTERVAL` | Seconds between data fetches |
| `MIN_FETCH_TIME` | Minimum loop time in milliseconds |
| `MIL_PREFIX_LIST` | Hex code prefixes for military aircraft (shown in red) |
| `WAYPOINTS` | Dict of named waypoints `{name: (lat, lon)}` |
| Color constants | `BRIGHT_GREEN`, `DIM_GREEN`, `RED`, `AMBER`, `YELLOW`, `BLACK`, `WHITE` as `(r, g, b)` tuples |

## Usage

### Layout Modes

Tap the radar scope area to cycle through three layout modes:

1. **Mode 0 — Large Radar:** Full-width scope with a compact table below.
2. **Mode 1 — Split Screen:** Scope on the top half, full table on the bottom half.
3. **Mode 2 — Table Only:** Full-screen aircraft data table.

### Touch Interactions

| Touch area | Action |
|---|---|
| Radar scope — left third | Previous layout mode |
| Radar scope — right third | Next layout mode |
| Radar scope — center | Change radar range (cycles 5→10→15→30→50→5 NM) |
| Aircraft row | Select / toggle selection (yellow highlight) |
| Empty table area | Deselect current aircraft |

### Selection Behavior

*   Only one aircraft can be selected at a time.
*   Selected aircraft shows:
    *   Yellow background in the data table with black text
    *   Yellow track line on the radar scope
    *   Yellow highlight ring around the blip (on initial tap only)
    *   Callsign label always visible
*   Selection persists across layout changes and data updates.

## Code Overview

| File | Description |
|---|---|
| `main.py` | Entry point; adds `/cydradar` to `sys.path` and starts the app |
| `radar.py` | Main app logic: `App` (Presto init, pen setup) and `Radar` (layout, touch, draw loop) |
| `scope.py` | `RadarScope` — draws rings, crosshairs, aircraft blips and trails |
| `datatable.py` | `DataTable` — draws the aircraft data table |
| `display_wrapper.py` | `PicoDisplay` wrapper adapting PicoGraphics to the CYD-style drawing API; `PixelFont` descriptor |
| `aircraft.py` | `AircraftData` namedtuple and factory function |
| `fetch.py` | `AircraftTracker` — fetches JSON from dump1090 |
| `utils.py` | `calculate_distance_bearing()` — great-circle math |
| `cfg.py` | User configuration (copy from `cfg.py.sample`) |

## About ADS-B JSON

See [docs/ADSB.md](docs/ADSB.md) for details on the dump1090 JSON format.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
