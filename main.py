import time                   # Allows use of time.sleep() for delays
import pycom                  # Base library for Pycom devices
import ubinascii              # Needed to run any MicroPython code
import machine                # Interfaces with hardware components
import micropython            # Needed to run any MicroPython code
import config                 # Where the user's sensitive data is stored
from network import WLAN      # For operation of WiFi network
from umqtt import MQTTClient  # For use of MQTT protocol to talk to Adafruit IO
from machine import Pin       # Pin object to configure pins
from machine import ADC       # ADC object to configure reading values
ADC_PIN = 'P15'               # Pin for moisture sensor

# Wireless network
WIFI_SSID = config.WIFI_NAME
WIFI_PASS = config.WIFI_PASSWORD

# Adafruit IO (AIO) configuration
AIO_SERVER = "io.adafruit.com"
AIO_PORT = config.AIO_PORT
AIO_USER = config.AIO_USER
AIO_KEY = config.AIO_KEY
AIO_CLIENT_ID = ubinascii.hexlify(machine.unique_id())  # Can be anything
AIO_CONTROL_FEED = config.AIO_CONTROL_FEED
AIO_TOMATO_PLANT_FEED = config.AIO_TOMATO_PLANT_FEED

# END SETTINGS

# RGBLED
# Disable the on-board heartbeat (blue flash every 4 seconds)
# We'll use the LED to respond to messages from Adafruit IO
pycom.heartbeat(False)
time.sleep(0.1) # Workaround for a bug.
                # Above line is not actioned if another
                # process occurs immediately afterwards
pycom.rgbled(0xff0000)  # Status red = not working


# WIFI
# We need to have a connection to WiFi for Internet access
wlan = WLAN(mode=WLAN.STA)
wlan.connect(WIFI_SSID, auth=(WLAN.WPA2, WIFI_PASS), timeout=5000)

while not wlan.isconnected():    # Code waits here until WiFi connects
    machine.idle()

print("Connected to Wifi")
pycom.rgbled(0xffd7000) # Status orange: partially working

# FUNCTIONS

# Function to respond to messages from Adafruit IO
def sub_cb(topic, msg):          # sub_cb means "callback subroutine"
    print((topic, msg))          # Outputs the message that was received. Debugging use.
    if msg == b"ON":             # If message says "ON" ...
        pycom.rgbled(0xffffff)   # ... then LED on
    elif msg == b"OFF":          # If message says "OFF" ...
        pycom.rgbled(0x000000)   # ... then LED off
    else:                        # If any other message is received ...
        print("Unknown message") # ... do nothing but output that it happened.

def send_moisture_value(moisture_value):
    print("Publishing: {0} to {1} ... ".format(moisture_value, AIO_TOMATO_PLANT_FEED), end='')
    try:
        client.publish(topic=AIO_TOMATO_PLANT_FEED, msg=str(moisture_value))
        print("DONE")
    except Exception as e:
        print("FAILED")

# Use the MQTT protocol to connect to Adafruit IO
client = MQTTClient(AIO_CLIENT_ID, AIO_SERVER, AIO_PORT, AIO_USER, AIO_KEY)

# Subscribed messages will be delivered to this callback
client.set_callback(sub_cb)
client.connect()
client.subscribe(AIO_CONTROL_FEED)
print("Connected to %s, subscribed to %s topic" % (AIO_SERVER, AIO_CONTROL_FEED))

pycom.rgbled(0x00ff00) # Status green: online to Adafruit IO

    # Function to print information about the plant's soil moisture
def check_plant(sensor_reading):
    LOW_VALUE  = 35 # Definitions of break points values from the soil moist sensor
    HIGH_VALUE = 70
    if sensor_reading >= LOW_VALUE and sensor_reading <= HIGH_VALUE: # If value is between 1000-2500, print text below and activate green LED
        print("Woooa! Perfect, between {0}-{1} is the target range, your plant will thrive!".format(LOW_VALUE, HIGH_VALUE))
    elif LOW_VALUE > sensor_reading: # If value is below 1000, print text below and activate yellow LED
        print("Hmm! Below {0} is too wet, this is not an aquarium my friend".format(LOW_VALUE))
    elif HIGH_VALUE < sensor_reading: # If value is over 2500, print text below and activate red LED
        print("Ooof! Over {0} is too dry, your plant will die a slow and painful death".format(HIGH_VALUE))
    else: # If an error is suspected, blink all LED lights and print text below
        print("This is a tricky one, it might be a bit too dry or a bit too wet, or something spooky's happening. Check all connections / wires and try again")

def moist_sensor(pin):
    time.sleep(3600) # Let the program sleep for X amount of seconds before continue to execute
    print("")
    adc = ADC()
    apin = adc.channel(pin=pin, attn=ADC.ATTN_11DB)
    value = apin.value()
    moisture = ((value / 4096) * 100)
    print('Moisture: ' + str(moisture))
    return moisture

try:                      # Code between try: and finally: may cause an error
                          # so ensure the client disconnects the server if
                          # that happens.
    while 1:              # Repeat this loop forever
        client.check_msg()# Action a message if one is received. Non-blocking.
        result = moist_sensor(ADC_PIN) # Retrieve the value from the connected PIN
        send_moisture_value(result) # The result is sent to the function
        check_plant(result) # Print out information about the soil value

finally:                  # If an exception is thrown ...
    client.disconnect()   # ... disconnect the client and clean up.
    client = None
    wlan.disconnect()
    wlan = None
    pycom.rgbled(0x000022)# Status blue: stopped
    print("Disconnected from Adafruit IO.")
