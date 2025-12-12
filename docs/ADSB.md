**General ADS-B Concepts**

* **ADS-B (Automatic Dependent Surveillance – Broadcast):** A surveillance technology where aircraft determine their position via satellite navigation (GPS) and periodically broadcast it, along with other information, allowing other aircraft and ground stations to see their position.
* **ADSB (1090ES):**  The primary ADS-B transmission method, using the 1090 MHz Extended Squitter signal.  This is what most of the data here comes from.
* **TIS-B (Traffic Information Service – Broadcast):** A service that rebroadcasts ADS-B data from other aircraft, especially useful for aircraft without ADS-B Out (or to improve coverage).  It also includes surveillance information from ground stations.
* **MLAT (Multilateration):** A technique that calculates an aircraft's position by measuring the difference in arrival times of signals from the aircraft to multiple ground receivers.  It's used when ADS-B signals are weak or unavailable.

**Fields Explained (based on the provided data):**

1.  **`hex` (Hexadecimal Address):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** A unique 24-bit identifier for each aircraft.  Think of it like an aircraft's "address" on the ADS-B network.  The `~` prefix indicates a TIS-B message.

2.  **`flight` (Flight Number):**
    *   **Source:** ADSB
    *   **Description:** The callsign or flight number of the aircraft (e.g., "UAL2305").  This is how you identify the airline and specific flight.

3.  **`squawk` (Squawk Code):**
    *   **Source:** ADSB
    *   **Description:** A four-digit octal code set by the pilot on the transponder.  It's used for identification and to indicate the aircraft's operating mode.  Common codes include:
        *   1200:  VFR (Visual Flight Rules)
        *   7700: Emergency
        *   7600: Lost Communications
        *   7500: Hijacking
        *   Other codes are assigned by Air Traffic Control.

4.  **`lat` (Latitude):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The aircraft's latitude in decimal degrees.

5.  **`lon` (Longitude):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The aircraft's longitude in decimal degrees.

6.  **`altitude` (Altitude):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The aircraft's altitude in feet (above mean sea level).

7.  **`vert_rate` (Vertical Rate):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The aircraft's rate of climb or descent in feet per minute (positive for climbing, negative for descending).

8.  **`track` (Track Angle):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The aircraft's heading in degrees (0-359), representing the direction the aircraft is pointing.

9.  **`speed` (Speed):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The aircraft's ground speed in knots (nautical miles per hour).

10. **`category` (Aircraft Category):**
    *   **Source:** ADSB
    *   **Description:**  Indicates the type of aircraft based on its wingspan and wake turbulence characteristics.
        *   A3: Medium aircraft
        *   A5: Heavy aircraft

11. **`nucp` (Number of CPM Messages):**
    *   **Source:** ADSB
    *   **Description:** Number of CPM (Code of Practice Management) messages received.

12. **`seen_pos` (Seen Position):**
    *   **Source:** ADSB
    *   **Description:**  A value indicating the quality of the position fix. Higher values generally indicate a more accurate and reliable position.

13. **`messages` (Number of Messages):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** The total number of ADS-B messages received from this aircraft.

14. **`seen` (Seen Time):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:**  The time (in seconds) since the aircraft was last seen.

15. **`rssi` (Received Signal Strength Indicator):**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** A measure of the signal strength of the received ADS-B message (in dBm).  Lower (more negative) values indicate a weaker signal.

16. **`type`:**
    *   **Source:** ADSB, TIS-B, MLAT
    *   **Description:** Indicates the type of ADS-B message.
        *   `adsr_icao`: Standard ADS-B message.
        *   `tisb_other`: TIS-B message containing information about other aircraft.

17. **`mlat`:**
    *   **Source:** MLAT
    *   **Description:** An empty list in this case, indicating that MLAT data is not available for these aircraft.

18. **`tisb`:**
    *   **Source:** TIS-B
    *   **Description:** An empty list in this case, indicating that TIS-B data is not available for these aircraft.

**Important Notes:**

*   **Data Accuracy:**  ADS-B data is generally accurate, but it's subject to errors (e.g., GPS inaccuracies, signal interference).
*   **Coverage:** ADS-B coverage depends on the altitude of the aircraft and the location of ground stations.
*   **Data Interpretation:**  Understanding the context of the data is crucial. For example, a low `rssi` value might indicate that the aircraft is far away or that there's interference.
