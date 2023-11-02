# pico
Controlling the Elgato Key Light Air with a Raspberry Pi Pico
In this article, I’ll describe how I’ve hooked-up a Raspberry Pi Pico with an Elgato Key Light Air by accessing its REST API through CircuitPython.

The Elgato Key Light Air provides WLAN enabled studio lightning for presentations and video productions. I’m using it for my training online course deliveries. The panel has 80 premium OSRAM LEDS, which provide a total output of 1400 lumen. It’s shipped with the Control Center app to switch on/off, adjust brightness, and fine-tune color temperature.


Recently, I bought a Raspberry Pi Pico W with a Grove starter kit. This kit has some challenging projects, but I decided to postpone them. I started with integrating my Elgato Key Light Air with the Pi Pico, and using it to control my light, instead of using the Control Center app.



The Grove starter kit shield is fitted with a button, light, and rotary angle sensor. These sensors will be used to control the power, brightness, and color of the Elgato Key Light Air.



The Pi Pico W is mounted on top of the shield and equipped with a built-in WiFi adapter. The first step is to set up a WLAN connection and hook up the Pi Pico to my home WiFi. Initially, I flashed the Pico W with MicroPython uf2 firmware, but I had some trouble getting information from the Elgato API. It seems stalling, and didn’t come back with a JSON reply.
​
I decided to give the CircuitPython firmware from Adafruit a try. Adafruit has a long history with Edge Computing. You can find all kinds of electronics and kits on their website. They offer several libraries, guides including support, and some great examples for the Pi Pico.

CircuitPython and MicroPython are quite similar, they are both Python 3 variants optimized to run on micro-controllers. However, there are architectural differences between both interpreters. 

CircuitPython automatically starts code.py when the Pi Pico is powered on. OS settings like the WiFi username and password are stored in the settings.toml file. It also has a lib directory, which is used for storing additional libraries. All these files are accessible through a Pi Pico CIRCUITPY mounted USB drive. 

Before we start coding, we first must copy the adafruit_requests.mpy library to the lib directory on the “CIRCUITPY” drive. This library contains the adafruit_requests module used for putting and getting a JSON body from Elgato’s Key Light Air REST API.

Another big difference between CircuitPython and MicroPython is the IDE. We’ve to step away from Thonny’s Python IDE and install the Mu Editor. This editor supports CircuitPython and connects to the Raspberry Pi Pico over USB. It’s a pretty nice IDE. I’ve switched to dark mode and zoomed out a little bit. You can learn more about Mu at codewith.mu.

In the first part of the code, I’m importing the necessary libraries. I’m using some standard Python libraries, like JSON and Time, and a few specific ones, for setting up WiFi and a web session to communicate with the board and the light.

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

There are two libraries, analogio and digitalio used for getting values from the starter kit’s switch, light sensor, and pot meter.

adc = analogio.AnalogIn(A0) # Grove - Rotary Angle Sensor (Rotary Potentiometer) - Seeed Studio
ldr = analogio.AnalogIn(A1) # Grove - Light Sensor
button = digitalio.DigitalInOut(board.GP18) # Grove - Button
button.direction = digitalio.Direction.INPUT
elgato_ip = "192.168.178.151"
elgato_port = "9123"

Now the initialization takes place. The “adc” variable is used to store the value of the rotary potentiometer. “ldr” stores the value of light sensor, the “button” is used for toggling the on/off switch. For digital IO, we must specify the direction INPUT. Finally, the Elgato IP address and port number are set.  

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

For establishing the WiFi connection, I’ve used an example from Captain make. This website offers tons of cool projects, including how to connect Raspberry Pi Pico W to the Internet using CircuitPython.

pool = socketpool.SocketPool(wifi.radio)
session = adafruit_requests.Session(pool, ssl.create_default_context())
elgato_url = "http://" + elgato_ip +":"+ elgato_port + "/elgato/lights"
#print (elgato_url)
old_change = 0 #sync the ldr and potmeter

The next part was the most challenging, interacting with Elgato’s REST API. The Adafruit’s CircuitPython Internet Test was a great help.

First, we need to setup a session and provide the URL. I’m also initializing the variable old_change by setting it 0. This variable detects any changes in the sensors by comparing the current and past values. We only have to post a JSON body when something has changed. 

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

With the “while True:” command, we’re creating an infinite loop. All code within this loop must be indented with 4 spaces. A quick tip from my side: never use tabs to indent.

Within the loop, there is a section that calculates the JSON values and detects if there are any changes in the sensors by comparing the current value with the new value in the enclosed if statement.

Calculating brightness temperature and the on/off switch is the next challenge. These values come from the sensors and must be converted into Elgato’s API range. The following string is retrieved via the browser with: http://192.168.178.151:9123/elgato/lights

{"numberOfLights":1,"lights":[{"on":1,"brightness":100,"temperature":344}]}

This JSON reply contains the maximum numbers. Now we must convert the LDR sensor into a brightness value. When it’s dark, the light sensor generates a value of nearly 0. In bright sunlight, it generates a value of 45000. I figured, if we use the following formula round(2*(ldr.value)/1000)) by dividing the light sensors value by 1000, and multiplying this by 2, we get a JSON value between 0-100.

The pot-meter’s value comes from a voltage measured in 16 bits; the maximum value is 65535. This value must be used to calculate the color temperature. A temperature of 143 equals 7000K and 344 equals 2900K. The following formula calculates a JSON value with an offset of 145 and a ceiling of 345: (round((145+(adc.value / 65535.0) * 200))).

I’m using the button to toggle on/off by retrieving the current status of the light with a session.get. This value is used to calculate an exclave OR with the status of the button. 

0 – 0 = 0 : Light stays off when the button isn’t pressed.
1 – 0 = 1 : Light is on, but the button isn’t pressed, so it stays on.
0 – 1 = 1 : Light is off. And the button is pressed so light is switched on.
1 – 1 = 0 : Light is on, and a button is pressed, so light is switched off.

Now the JSON payload must be generated, so we can send these values to the Elgato light. This is only done when there is a change in the values of the pot meter, light sensor, or button. This change is calculated by adding the values into new_change. The first run, new change is always different from old_change so we’re posting the payload and making old_change equal to new_change.
In the next loop, when nothing has changed, it simply skips the post section.

The payload was generated by Postman. Christian Mohn pointed me at a cool feature that allows you to translate a REST API call into Python. Finally, the response command is posting the payload using the session with the URL and headers. I also put in a sleep "time.sleep(0.5)" to avoid dendering (dutch for thundering) when the button is pressed a bit too long, and avoid too many REST calls against the Key Light Air. 

All in all, this was a great experience. I had moments when I was banging my head against the wall, especially with getting values from a nested JSON body. I also lost a lot of time with syntax errors caused by tabs. The Mu editor offers a Check and Tidy option to find and correct those errors, among other checks. I’ve posted the code on GitHub, feel free to make changes or report errors.

​
