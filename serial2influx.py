#!/usr/bin/python3
import serial
import time
import sys
import datetime
import json
from influxdb import InfluxDBClient

dbhost = "babbage.local"
port   = 8086
user   = "enviropi"
pw     = "enviropi"
dbname = "enviro_sensor_data"

ser = serial.Serial('/dev/ttyACM0',9600)

# Create the InfluxDB client object
store = InfluxDBClient(dbhost, port, user, pw, dbname)
#location = "neil's office"
location = "driveway"
device = "enviro+ arduino"
measurement = "environmental"
s = [0]
collecting = False
readings={}
while True:
#        print("ready to read")
        read_serial=ser.readline().decode("utf-8").strip()
#        print("read: {}".format(read_serial))
        if collecting:
            if read_serial == "END":
                collecting = False
                row = [ { "measurement":measurement,
                            "tags": { 
                                "location":location,
                                "device":device,
                            },
                            "time": int(time.time()),
                            "fields":readings
                        }
                    ]
                #print(json.dumps(row))
                store.write_points(row, time_precision='s')
            else:
                try:
                    k, v = read_serial.split("=")
                    if '.' in v:
                        readings[k]=float(v)
                    else:
                        readings[k]=int(v)
                except:
                    print("decode failed: {}".format(read_serial))
        else:
            if read_serial == "BEGIN":
                collecting = True
                readings = {}
            else:
                print(read_serial)
