import os
import sys
import ssl
import wifi
import socketpool
import adafruit_requests
import json
import time

import board
from board import *

import analogio
from analogio import *

import digitalio
from digitalio import *

adc = analogio.AnalogIn(A0) # Grove - Rotary Angle Sensor (Rotary Potentiometer) - Seeed Studio
ldr = analogio.AnalogIn(A1) # Grove - Light Sensor
button = digitalio.DigitalInOut(board.GP18) # Grove - Button
button.direction = digitalio.Direction.INPUT
elgato_ip = "192.168.178.151"
elgato_port = "9123"

print("Connecting to WiFi")
try:
    # Connect to the WIFI, use settings.toml to configure SSID and Password
    wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))
    print("Connected to WiFi")
except Exception as e:
    # Handle connection error
    # For this example we will simply print a message and exit the program
    print("Failed to connect, adorting.")
    print("Error:\n", str(e))
    sys.exit()
print("IP address is", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
session = adafruit_requests.Session(pool, ssl.create_default_context())
elgato_url = "http://" + elgato_ip +":"+ elgato_port + "/elgato/lights"
#print (elgato_url)
old_change = 0 #sync the ldr and potmeter

while True:
    brightness = (round(2*(ldr.value)/1000))
    print ("Brightness:" + str(brightness))
    temperature = (round((145+(adc.value / 65535.0) * 200)))
    print ("Temperature:"+ str(temperature)) # temperature of 143 = 7000K 344 = 2900K 
    switch = (button.value)
    print ("Switch:" + str(int(switch)))
    new_change = brightness + temperature + switch
    print (new_change)
    if (old_change != new_change): #Only send a request when something has changed
        old_change = new_change
        ResponseGet = session.get(elgato_url) # example response: {"numberOfLights":1,"lights":[{"on":1,"brightness":89,"temperature":176}]}
        JsonResp = ResponseGet.json()
        for item in JsonResp["lights"]:
            on = item.get('on')
        payload = json.dumps({
		  "lights": [
		    {
			  "on": on ^ switch, # Exclusive OR (XOR) on the currect state and the switch for toggle.
			  "brightness": brightness,
			  "temperature": temperature
            }
		  ],
		  "numberOfLights": 1
		})
        headers = {
          'Content-Type': 'application/json'
		}
        response = session.put(elgato_url, headers=headers, data=payload) # put the JSON payload into the light 
        time.sleep(0.5) # Don't overwhelm the elgato API

