#!/usr/bin/python3
import argparse
import serial
import time
import os
from pathlib import Path
import sys
import datetime
import json
import requests # for luftdaten submission
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from w1thermsensor import W1ThermSensor
import logging

# global

dbhost = ""
port   = 0
user   = ""
pw     = ""
dbname = ""

luftdaten_update_frequency = 60
packets_global_update_frequency = 10
local_update_frequency = 5
luftdaten_send_time = 0
packets_global_send_time = 0

last_renewal = 0
token = None

ser = serial.Serial('/dev/ttyACM0',9600)



def get_iot_url():
    return "https://iot.packets.global:443"+ "/api/1.0/"

def get_serial_string(full=False):
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line[0:6] == 'Serial':
                if full:
                    return line.split(":")[1].strip()
                else:
                    return line.split(":")[1].strip()[-8:] # last 8 chars only please

def get_token_file():
    home = str(Path.home())
    iot_dir = home + "/.iot"
    token_file = iot_dir + "/token"
    return token_file

def read_token():
    global token
    logging.debug("Reading token")
    token_file = get_token_file()
    file = open(token_file, "r")
    token = json.load(file)

def write_token(token_data):
    global token
    token_file = get_token_file()
    if os.path.exists(token_file):
        os.remove(token_file)
        f = open(token_file, "x")
        f.write(token_data)
        f.close()
        logging.debug("Token written to " + token_file)
    token = json.loads(token_data)
def token_request(iot_user, iot_pw, iot_serial_number):
    logging.debug("token_request({},{},{})".format(iot_user, iot_pw, iot_serial_number))
    headers = {'content-type': 'application/json'}
    data = dict()
    data['username'] = iot_user
    data['password'] = iot_pw
    data['serialNumber'] = iot_serial_number

    token_api = get_iot_url() + 'token/request'
    request = requests.post(token_api, json=data, headers=headers, verify=False,
                          allow_redirects=False)
    response = request.text
    if len(response) > 0:
        text = json.dumps(json.loads(response), sort_keys=True, indent=4)
    else:
        text = "Empty response"
    logging.debug("IOT Token Req: {url} {req}->{resp}".format(url=token_api, req=data, resp=text))


    if request.status_code == 200:
        logging.debug("iot token request succeeded with {}".format(response))    
        write_token(response)
    else:
        logging.warning("iot token request failed with {}".format(response))    
        return False
    return True

def token_renew():
    global token
    headers = {'content-type': 'application/json'}
    data = dict()
    data['token'] = token
    renew_api = get_iot_url() + 'token/renew'
    request = requests.put(
                renew_api, 
                json=data,
                headers=headers, verify=False,
                allow_redirects=False)
    response = request.text
    if len(response) > 0:
        text = json.dumps(json.loads(response), sort_keys=True, indent=4)
    else:
        text = "Empty response"

    logging.debug("IOT Token Renew: {url} {req}->{resp}".format(url=renew_api, req=data, resp=text))

    if request.status_code == 200:
        logging.debug("IOT token renew: OK - {}")
    else:
        logging.warning("IOT token renew: {}".format(response))


def check_token_and_renew(force_renew=False):
    global last_renewal
    global token
    logging.debug("check_token_and_renew(force_renew={})".format(force_renew))
    renewal_period = 25
    try:
        if force_renew:
            logging.debug("Ignoring token on disk. requesting new token")
            if token_request("pete@packets.global", "foo123", get_serial_string(full=True)):
                last_renewal = time.monotonic()
            else:
                logging.error("Failed to get new token")
                return
    except json.JSONDecodeError:
        logging.error("Token read failed")

    if time.monotonic() > last_renewal + renewal_period :
        logging.debug("Need to renew token")
        token_renew()
        last_renewal = time.monotonic()
    else:
        logging.debug("Token still valid {}".format(token))


def send_to_luftdaten(values, id):
    luft_map = { 
        "pm1":"P0", 
        "pm2":"P2", 
        "pm10":"P1",
        "real_temp":"temperature",
        "humidity":"humidity",
        "pressure":"pressure"}

    global luftdaten_send_time

    now = time.monotonic()

    if now < luftdaten_send_time + luftdaten_update_frequency:
        return
    
    luftdaten_send_time = now

    pm_values = dict(i for i in values.items() if i[0] in ["pm1","pm2", "pm10"])
    temp_values = dict(i for i in values.items() if i[0] in ["humidity", "pressure", "real_temp"])

    pm_values_json = [{"value_type": luft_map[key], "value": val}
                      for key, val in pm_values.items()]
    temp_values_json = [{"value_type": luft_map[key], "value": val}
                        for key, val in temp_values.items()]

    try:   
        resp_1 = requests.post(
            "https://api.luftdaten.info/v1/push-sensor-data/",
            json={
                "software_version": "nhorlock/enviropi",
                "sensordatavalues": pm_values_json
            },
            headers={
                "X-PIN": "1",
                "X-Sensor": id,
                "Content-Type": "application/json",
                "cache-control": "no-cache"
            }
        )
    except requests.exceptions.ConnectionError as e:
        logging.warning('Sensor.Community (Luftdaten) PM Connection Error: {}'.format(e))
    except requests.exceptions.Timeout as e:
        logging.warning('Sensor.Community (Luftdaten) PM Timeout Error: {}'.format(e))
    except requests.exceptions.RequestException as e:
        logging.warning('Sensor.Community (Luftdaten) PM Request Error: {}'.format(e))

    try:
        resp_2 = requests.post(
            "https://api.luftdaten.info/v1/push-sensor-data/",
            json={
                "software_version": "nhorlock/enviropi",
                "sensordatavalues": temp_values_json
            },
            headers={
                "X-PIN": "11",
                "X-Sensor": id,
                "Content-Type": "application/json",
                "cache-control": "no-cache"
            }
        )
    except requests.exceptions.ConnectionError as e:
        logging.warning('Sensor.Community (Luftdaten) TMP Connection Error: {}'.format(e))
    except requests.exceptions.Timeout as e:
        logging.warning('Sensor.Community (Luftdaten) TMP Timeout Error: {}'.format(e))
    except requests.exceptions.RequestException as e:
        logging.warning('Sensor.Community (Luftdaten) TMP Request Error: {}'.format(e))

    if resp_1.ok and resp_2.ok:
        return True
    else:
        return False    

def send_to_iotpackets(values):
    global token
    global packets_global_send_time

    now = time.monotonic()

    if now < packets_global_send_time + packets_global_update_frequency:
        return
    
    packets_global_send_time = now

    url =  get_iot_url() + "collector/environment"
    logging.debug("Sending AQ data to {}".format(url))
    check_token_and_renew()
    headers = {'content-type': 'application/json'}
    location = { 'latitude': 51.15795109905, 'longitude': 0.88059872389}

    data = dict()
    data['token'] = token

    field_map = { 
        "real_temp":"temperature",
        "ucontroller_cpu_temp":"cpu_temperature",
        "humidity":"humidity",
        "pressure":"pressure",
        "OX_raw":"oxidising",
        "RED_raw":"reducing",
        "NH3_raw":"nh3",
        "pm1":"pm1_0ug_m3",
        "pm2":"pm2_5ug_m3",
        "pm10":"pm10_0ug_m3",
        "pm1_atmos":"pm1_0ug_m3_atmos",
        "pm2_atmos":"pm2_5ug_m3_atmos",
        "pm10_atmos":"pm10_0ug_m3_atmos",
        "lux":"lux",
    }
    iot_data  = dict((field_map[k], v) for (k, v) in values.items() if k in field_map.keys())
    data['environment_data'] = iot_data

    logging.debug("IOT: sending to {} with {}".format(url,data))
    try:   
        resp = requests.post(
            url + "collector/environment",
            data=json.dumps(data),
            headers=headers,
            verify=False,
            allow_redirects=False
        )
    except requests.exceptions.ConnectionError as e:
        logging.warning('iot.packets.global Connection Error: {}'.format(e))
    except requests.exceptions.Timeout as e:
        logging.warning('iot.packets.global Timeout Error: {}'.format(e))
    except requests.exceptions.RequestException as e:
        logging.warning('iot.packets.global Request Error: {}'.format(e))
    except Exception as e:
        logging.error('iot.packets.global Unexpected Error: {}'.format(e))

    if resp.ok:
        logging.debug("Resp OK from {} : {}".format(url,json.dumps(json.loads(resp.text), sort_keys=True, indent=4)))
        return True
    else:
        if resp.status_code == 401:
            check_token_and_renew(force_renew=True)
        if len(resp.text) > 0:
            text = json.dumps(json.loads(resp.text), sort_keys=True, indent=4)
        else:
            text = "Empty response"
        logging.warning("Response NOTOK from {} : {}".format(url,text))
        return False    

def send_data_to_influx(store, row):
    try:
        store.write_points(row, time_precision='s')
    except ConnectionError as e:
        logging.warning("Failed to connect to Influx host {}:{} - {}".format(dbhost, port, e))
    except InfluxDBClientError as e:
        if e.code == 404:
            logging.error("Database '{}' not found.".format(dbname))
        else:
            logging.error("Write InfluxDB client failed {}@{}:{} - {}".format(dbname,dbhost, port, e))
    except InfluxDBServerError as e:
            logging.error("Write InfluxDB server failed {}@{}:{} - {}".format(dbname,dbhost, port, e))

# Allow setting of basic config at command line.

logging.basicConfig(
    filename="enviropi.log",
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')
    
parser = argparse.ArgumentParser(description='Read data from arduino and send to store')
parser.add_argument('--dbhost', dest='dbhost', required=False, default="babbage.local",
                    help="The IP or resolvable hostname of the influx data base")
parser.add_argument('--dbport', dest='port', required=False, default=8086, 
                    help="The port number for the influx data base")
parser.add_argument("--user", dest='user', required=False, default="enviropi",
                    help="the influx username")
parser.add_argument("--pass", dest='pw', required=False, default="enviropi",
                    help="the influx password")
parser.add_argument("--dbname", dest='dbname', required=False, default="enviro_sensor_data",
                    help="the influx database that will be used.")
args = parser.parse_args()

dbhost = args.dbhost
port   = args.port
user   = args.user
pw     = args.pw
dbname = args.dbname

# Create the InfluxDB client object
store = InfluxDBClient(dbhost, port, user, pw, dbname)
therm = W1ThermSensor()

location = "driveway"
device = "enviro+ arduino"
measurement = "environmental"
s = [0]
collecting = False
luft_device = "raspi-" + get_serial_string()
readings={}

# Log Raspberry Pi serial and Wi-Fi status
logging.info("Luftdaten Logging as : {}".format(luft_device))
logging.info("Influx as : {}:{} {}/{}".format(dbhost, port, user, pw))


logging.info("""serial2influx.py - Reads multiple sensors from enviro feather board, combines with independent temperature and sends to
influx for storage. Also sends data to the luftdaten API endpoints.
""")

logging.debug("checking token at startup")
check_token_and_renew(force_renew=True) # if we have a token file renew that else request one

while True:
    try:
        read_serial=ser.readline().decode("utf-8").strip()
    except serial.serialutil.SerialException as e:
        logging.warning("Warning: Exception caught on serial read [{}]".format(e))
    else:
        # logging.debug("read: {}".format(read_serial))
        if collecting:
            if read_serial == "END":
                real_temp = therm.get_temperature()
                collecting = False
                readings["real_temp"]=real_temp
                row = [ { "measurement":measurement,
                            "tags": { 
                                "location":location,
                                "device":device,
                            },
                            "time": int(time.time()),
                            "fields":readings
                        }
                    ]
                logging.debug("Data received: {}".format(json.dumps(row)))
                send_data_to_influx(store, row)
                send_to_iotpackets(readings)
                send_to_luftdaten(readings, luft_device)
            else:
                try:
                    k, v = read_serial.split("=")
                    if '.' in v:
                        readings[k]=float(v)
                    else:
                        readings[k]=int(v)
                except Exception as e:
                    logging.warning("decode failed: [{}] exception [{}]".format(read_serial, e))
        else:
            if read_serial == "BEGIN":
                collecting = True
                readings = {}
            else:
                logging.debug("data outside of BEGIN/END: " + read_serial)
