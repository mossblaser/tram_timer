import time

from machine import Pin
import network

import watchdog
from tram import Tram
from metrolink_api import get_next_station_departure


if __name__ == "__main__":
    from config import *
    
    pin = Pin(28, Pin.OUT)
    tram = Tram(
        pin,
        position_min_ns=position_min_ns,
        position_max_ns=position_max_ns,
    )
    
    for t in range(10, 0, -1):
        print(f"Starting watchdog in {t}...")
        time.sleep(1)
    watchdog.feed()
    
    print("Connecting to WiFi...")
    nic = network.WLAN(network.WLAN.IF_STA)
    nic.active(True)
    nic.connect(wifi_ssid, wifi_key)
    
    while True:
        try:
            print("Looking up tram times...")
            next_departure = get_next_station_departure(
                station=station,
                excluded_destinations=excluded_destinations,
                api_key=api_key,
            )
            print("Next tram:", next_departure, "min")
            if next_departure is not None and 0 <= next_departure <= 12:
                tram.move_to(next_departure)
            else:
                tram.move_to(13)
            watchdog.feed()
        except Exception as e:
            print("Error:", e)
        finally:
            time.sleep(10)
