import argparse
import json
import datetime
import requests

from influxdb import InfluxDBClient

def send_to_luftdaten(values, id):
    luft_map = { 
        "pm1":"P0",
        "pm2":"P2",
        "pm10":"P1",
        "real_temp":"temperature",
        "humidity":"humidity",
        "pressure":"pressure"}

    pm_values = dict(i for i in values.items() if i[0] in ["pm1", "pm2", "pm10"])
    temp_values = dict(i for i in values.items() if i[0] in ["humidity", "pressure", "real_temp"])

    pm_values_json = [{"value_type": luft_map[key], "value": val}
                      for key, val in pm_values.items()]
    temp_values_json = [{"value_type": luft_map[key], "value": val}
                        for key, val in temp_values.items()]
    try:
        resp_1 = requests.post(
            "https://api.luftdaten.info/v1/push-sensor-data/",
            json={
                "timestamp": values['time'],
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
    except Exception as e:
        print("Timeout {}".format(e))
        return False

    try:
        resp_2 = requests.post(
            "https://api.luftdaten.info/v1/push-sensor-data/",
            json={
                "timestamp": values['time'],
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
    except Exception as e:
        print("Timeout {}".format(e))
        return False

    if resp_1.ok and resp_2.ok:
        return True
    else:
        return False    


def main(dbhost='babbage.local', port=8086):
    """Instantiate a connection to the InfluxDB."""
    
    dbname = "enviro_sensor_data"
    user = 'enviropi'
    password = 'enviropi'
    query = 'select real_temp, humidity, pressure, pm1, pm10, pm2 from environmental where time< 1655036664000000000 and time > 1655005440000000000 order by time desc;'
    
    client = InfluxDBClient(dbhost, port, user, password, dbname)

    result  = client.query(query)
    for measurement in result.get_points():
        print(measurement.items())
        print("submitted: " + str(send_to_luftdaten(measurement, "raspi-24b3c744")))

if __name__ == "__main__":
    main()