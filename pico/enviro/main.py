## Pi Pico + Enviro+ pack
# each loop will read all the sensors and send K=V data off of the device (default is USB)
# derived form the arduino environ+ example in this repo
#

import math
import gc

# import board
# import busio
from breakout_bme68x import BreakoutBME68X, STATUS_HEATER_STABLE
from pimoroni_i2c import PimoroniI2C
from picographics import PicoGraphics, DISPLAY_ENVIRO_PLUS
from pimoroni import RGBLED
from pms5003 import PMS5003
from breakout_ltr559 import BreakoutLTR559

import machine
import time

# import analogio
# import displayio
# import pulseio
# import terminalio
# import microcontroller

# settings
interval = 5 # seconds delay between readings
sea_level_pressure = 1013.25

def initialise_i2c():
    PINS_BREAKOUT_GARDEN = {"sda": 4, "scl": 5}
    PINS_PICO_EXPLORER = {"sda": 20, "scl": 21}

    i2c = PimoroniI2C(**PINS_BREAKOUT_GARDEN)
    return i2c

def initialise_bme688(i2c):
    # Change this to match the location's pressure (hPa) at sea level
    bme = BreakoutBME68X(i2c, address=0x77)
    bme.sea_level_pressure = sea_level_pressure
    bme.mode = adafruit_bme280.MODE_NORMAL
    bme.standby_period = adafruit_bme280.STANDBY_TC_500
    bme.iir_filter = adafruit_bme280.IIR_FILTER_X16
    bme.overscan_pressure = adafruit_bme280.OVERSCAN_X16
    bme.overscan_humidity = adafruit_bme280.OVERSCAN_X1
    bme.overscan_temperature = adafruit_bme280.OVERSCAN_X2
    return bme280

def initialise_pms5003():
    # Configure the PMS5003 for Enviro+
    pms5003 = PMS5003(
        uart=machine.UART(1, tx=machine.Pin(8), rx=machine.Pin(9), baudrate=9600),
        pin_enable=machine.Pin(3),
        pin_reset=machine.Pin(2),
        mode="active"
    )
    try:
        pms5003.read()
    except Exception as e:
        print(e)
        print("Particulate sensor not found.")
        return None
    return pms5003

def initialise_ltr559(i2c):
    # set up connection with the ltr559
    ltr559 = BreakoutLTR559(i2c)
    return ltr559

# Create library object using our Bus I2C port
i2c = initialise_i2c()

# pressure, humidity, temp
bme280 = initialise_bme688(i2c)
# particulates
pms5003 = initialise_pms5003()
# gas needs no initialisation
# proximity and light 
ltr559 = initialise_ltr559(i2c)

# microphone
# set up mic input
MIC_PIN = 26
mic = ADC(Pin(26))

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

        num_idle_loops=0
        num_loops=0
        cum_noise=0
    else:
        cum_noise += abs(mic.read_u16()-32768)
        num_idle_loops+=1
    # update the last_sec time

