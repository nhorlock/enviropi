## A consolidated sensor reading script
# each loop will read all the sensors and send K=V data over USB
# Based upon adafruit and pimoroni examples
#

"""
Example showing how the BME280 library can be used to set the various
parameters supported by the sensor.
Refer to the BME280 datasheet to understand what these parameters do
"""
import time
import math
import gc

import board
import busio
import adafruit_bme280
import analogio
import displayio
import pulseio
import terminalio
import microcontroller

from adafruit_display_text import label

import pimoroni_physical_feather_pins
from pimoroni_circuitpython_adapter import not_SMBus
from pimoroni_envirowing import gas, screen

from pimoroni_ltr559 import LTR559
from pimoroni_pms5003 import PMS5003

# settings
interval = 5 # seconds delay between readings
sea_level_pressure = 1013.25

def initialise_bme280(i2c):
    # Change this to match the location's pressure (hPa) at sea level
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
    bme280.sea_level_pressure = sea_level_pressure
    bme280.mode = adafruit_bme280.MODE_NORMAL
    bme280.standby_period = adafruit_bme280.STANDBY_TC_500
    bme280.iir_filter = adafruit_bme280.IIR_FILTER_X16
    bme280.overscan_pressure = adafruit_bme280.OVERSCAN_X16
    bme280.overscan_humidity = adafruit_bme280.OVERSCAN_X1
    bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X2
    return bme280

def initialise_pms5003():
    # set up the pms5003
    pms5003 = PMS5003()
    try:
        pms5003.read()
        is_pms5003 = True
    except Exception as e:
        print(e)
        print("Particualte sensor not found.")
        return None
    return pms5003

def initialise_ltr559():
    # set up connection with the ltr559
    i2c_dev = not_SMBus(I2C=i2c)
    ltr559 = LTR559(i2c_dev=i2c_dev)
    return ltr559

def initialise_screen():
    display = screen.Screen()
    # Make the display context
    splash = displayio.Group(max_size=10)
    display.show(splash)

    color_bitmap = displayio.Bitmap(160, 80, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0x00FF00 # Bright Green

    bg_sprite = displayio.TileGrid(color_bitmap,
                                pixel_shader=color_palette,
                                x=0, y=0)
    splash.append(bg_sprite)

    # Draw a smaller inner rectangle
    inner_bitmap = displayio.Bitmap(50, 50, 1)
    inner_palette = displayio.Palette(1)
    inner_palette[0] = 0xAA0088 # Purple
    inner_sprite = displayio.TileGrid(inner_bitmap,
                                    pixel_shader=inner_palette,
                                    x=10, y=10)
    splash.append(inner_sprite)
    return splash

splash = initialise_screen()
# Create library object using our Bus I2C port
i2c = busio.I2C(board.SCL, board.SDA)

# pressure, humidity, temp
bme280 = initialise_bme280(i2c)
# particulates
pms5003 = initialise_pms5003()
# gas needs no initialisation
# proximity and light 
ltr559 = initialise_ltr559()

# microphone
# set up mic input
mic = analogio.AnalogIn(pimoroni_physical_feather_pins.pin8())

# The sensor will need a moment to gather initial readings
time.sleep(1)

# record the time that the sampling starts
last_reading = time.monotonic()
last_sec = time.monotonic()
num_idle_loops=0
num_loops=0
cum_noise=0
while True:
    num_loops+=1
    # if 1 second has passed
    # if interval time has passed since last reading
    if last_reading + interval < time.monotonic():
        # take readings
        # take the light reading
        readings={}
        readings["lux"] = ltr559.get_lux()
        # temp etc
        readings["ucontroller_cpu_temp"] = microcontroller.cpu.temperature
        readings["temperature"] = bme280.temperature
        readings["pressure"] = bme280.pressure
        readings["humidity"] = bme280.humidity
        #altitude = bme280.altitude # uncomment for altitude estimation
        # gases
        gas_reading = gas.read_all()
        readings["OX"]=gas_reading._OX.value * (gas_reading._OX.reference_voltage/65535)
        readings["RED"]=gas_reading._RED.value * (gas_reading._RED.reference_voltage/65535)
        readings["NH3"]=gas_reading._NH3.value * (gas_reading._NH3.reference_voltage/65535)
        readings["OX_raw"]=gas_reading._OX.value
        readings["RED_raw"]=gas_reading._RED.value
        readings["NH3_raw"]=gas_reading._NH3.value

        # get the sound readings (number of samples over the threshold / total number of samples taken) and apply a logarithm function to them to represent human hearing
        readings["sound_level"] = cum_noise/num_idle_loops
        readings["num_loops"] = num_loops
        readings["num_idle_loops"] = num_idle_loops

        if pms5003 is not None:
            # take readings
            pms_reading = pms5003.read()
            readings["pm1"] = pms_reading.data[0]
            readings["pm2"] = pms_reading.data[1]
            readings["pm10"] = pms_reading.data[2]
            readings["pm1_atmos"] = pms_reading.data[0]
            readings["pm2_atmos"] = pms_reading.data[1]
            readings["pm10_atmos"] = pms_reading.data[2]
        print("BEGIN")
        for k in readings.keys():
            print("{}={}".format(k, readings[k]))
        print("END")
        # record the time that this reading was taken
        last_reading = time.monotonic()
        # Draw a label
        text = "upd:{}".format(last_reading)
        text_area = label.Label(terminalio.FONT, text=text, color=0xFFFF00, x=30, y=64)
        splash[-1] = text_area
        num_idle_loops=0
        num_loops=0
        cum_noise=0
    else:
        cum_noise += abs(mic.value-32768)
        num_idle_loops+=1
    # update the last_sec time

