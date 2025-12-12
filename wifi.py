import network
import time
import sys

import secrets

def connect_to_wifi():
    sta_if = network.WLAN()
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(secrets.wifi_ssid, secrets.wifi_password)
        # Wait for connection with a timeout
        for i in range(50): # Roughly 5 seconds
            if sta_if.isconnected():
                break
            time.sleep_ms(100)

    if sta_if.isconnected():
        print('network config:', sta_if.ifconfig())
        print("Connected successfully!")
    else:
        print("Failed to connect to WiFi")
