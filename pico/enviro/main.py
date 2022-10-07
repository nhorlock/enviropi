'''
Particle Sensor Example

This example requires seperate MicroPython drivers for the PMS5003 particulate sensor.
(You can find it at https://github.com/pimoroni/pms5003-micropython )
or install from PyPi by searching for 'pms5003-micropython' in Thonny's 'Tools > Manage Packages'

'''
from picographics import PicoGraphics, DISPLAY_ENVIRO_PLUS
from pimoroni import RGBLED
from pms5003 import PMS5003
from pimoroni_i2c import PimoroniI2C
from breakout_ltr559 import BreakoutLTR559
from breakout_bme68x import BreakoutBME68X, STATUS_HEATER_STABLE


import machine
import time

print("""particle.py - Continuously print all data values.
and draw a pretty histogram on display
""")


# Configure the PMS5003 for Enviro+
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

def initialise_bme688(i2c):
    # Change this to match the location's pressure (hPa) at sea level
    bme = BreakoutBME68X(i2c, address=0x77)
    # bme.configure(FILTER_COEFF_63, STANDBY_TIME_500_MS, OVERSAMPLING_X16, OVERSAMPLING_X2, OVERSAMPLING_X1)
# TODO    bme.sea_level_pressure = sea_level_pressure
# TODO   bme.mode = adafruit_bme280.MODE_NORMAL

    #bme.standby_period = adafruit_bme280.STANDBY_TC_500
    #bme.iir_filter = adafruit_bme280.IIR_FILTER_X16
    #bme.overscan_pressure = adafruit_bme280.OVERSCAN_X16
    #bme.overscan_humidity = adafruit_bme280.OVERSCAN_X1
    #bme.overscan_temperature = adafruit_bme280.OVERSCAN_X2
    return bme

def initialise_i2c():
    PINS_BREAKOUT_GARDEN = {"sda": 4, "scl": 5}
    PINS_PICO_EXPLORER = {"sda": 20, "scl": 21}

    i2c = PimoroniI2C(**PINS_BREAKOUT_GARDEN)
    return i2c

display = PicoGraphics(display=DISPLAY_ENVIRO_PLUS)
display.set_backlight(1.0)

# Setup background
BG = display.create_pen(0, 0, 0)
TEXT = display.create_pen(255, 255, 255)
PM10 = display.create_pen(255, 0, 0)
PM25 = display.create_pen(255, 255, 0)
PM100 = display.create_pen(0, 255, 0)
PM125 = display.create_pen(255, 255, 0)
PM1000 = display.create_pen(255, 255, 0)
display.set_pen(BG)
display.clear()

def initialise_LED():
    # Setup RGB Led
    led = RGBLED(6, 7, 10, invert=True)
    led.set_rgb(0, 0, 0)
    return led

def initialise_ltr559(i2c):
    # set up connection with the ltr559
    ltr559 = BreakoutLTR559(i2c)
    return ltr559

# Drawing routines

def initialise_display():
    global display
    display.set_backlight(1.0)
    # Setup background
    display.clear()

def draw_background():
    display.set_pen(BG)
    display.clear()
    display.set_pen(TEXT)
    display.text("PicoMon v0.2", 5, 10, scale=3)


def draw_txt_overlay(sensor_data):
    display.set_pen(PM10)
    display.text("PM1.0: {0}".format(sensor_data.pm_ug_per_m3(1.0)), 5, 60, scale=3)
    display.set_pen(PM25)
    display.text("PM2.5: {0}".format(sensor_data.pm_ug_per_m3(2.5)), 5, 80, scale=3)
    display.set_pen(PM100)
    display.text("PM10: {0}".format(sensor_data.pm_ug_per_m3(10)), 5, 100, scale=3)


# settings
interval = 5 # seconds delay between readings
sea_level_pressure = 1013.25
readings = {}
display = PicoGraphics(display=DISPLAY_ENVIRO_PLUS)
initialise_display()
led = initialise_LED()

# Create library object using our Bus I2C port
i2c = initialise_i2c()
# microphone
# set up mic input
MIC_PIN = 26
# mic = ADC(Pin(26)) B0RK

pms5003 = initialise_pms5003()

bme = initialise_bme688(i2c)

# proximity and light 
ltr559 = initialise_ltr559(i2c)
# record the time that the sampling starts
# last_reading = time.monotonic()
# last_sec = time.monotonic()
num_idle_loops=0
num_loops=0
cum_noise=0

print("Setup complete..loop starting")
while True:
    num_loops += 1
    draw_background()
    if ltr559 is not None:
        readings["lux"] = ltr559.get_reading()[BreakoutLTR559.LUX]
    if bme is not None:
        temperature, pressure, humidity, gas, status, _, _ = bme.read()
        if status & STATUS_HEATER_STABLE:
            readings["temperature"] = temperature
            readings["pressure"] = pressure
            readings["humidity"] = humidity
            readings["gas_resistance"] = gas
    if pms5003 is not None:
        pms_reading = pms5003.read()
        readings["pm1"] = pms_reading.data[0]
        readings["pm2"] = pms_reading.data[1]
        readings["pm10"] = pms_reading.data[2]
        readings["pm1_atmos"] = pms_reading.data[0]
        readings["pm2_atmos"] = pms_reading.data[1]
        readings["pm10_atmos"] = pms_reading.data[2]
        # print(pms_reading)
        print(readings)

    draw_txt_overlay(pms_reading)
    display.update()
    time.sleep(0.5)