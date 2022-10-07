## Air Quality Data over LoraWAN
### Problem
LoRa is the ideal distribution network for remotely deployed Air Qality sensors being long-range, lower power and in many cases not needed a subscription. However, the bandwidth is very limited. 

For our air quality monitoring needs we have a minimal data set that comprises
PM1, PM2.5 and PM10 particulate matter readings.

| Field name | size |bytes| description |
|:-------|:----|----:|:-------|
|Time|64 bit integer|8|Time of reading (this may be replaced by the LoRaWAN packet time?)
|Temp|double|8|Ambient Temperature
|DeviceTemp|double|8|Device Temperature
|Gas|64-bit integer|8|Gas sensor resistance
|PM1|64-bit integer|8|1 um particles
|PM2.5|64-bit integer|8|2.5 um particles
|PM10|64-bit integer|8|10 um particles
|Humidity|double|8|Humidity
|Pressure|double|8|Pressure
|Lux|double|8|Light levels
|Total||80

[The Things Network Limitations page](https://www.thethingsnetwork.org/docs/lorawan/limitations/) suggests the following.
```
Payload should be as small as possible. This means that you should not send JSON or plain (ASCII) text,
but instead encode your data as binary data. 
This is made really easy with the Cayenne Low Power Payload format which is fully supported by The Things Network.

Interval between messages should be in the range of several minutes, so be smart with your data. 
You could for example transmit a min|avg|max every 5 minutes, or you could only transmit when you sensor
value changed more than a certain threshold or have it triggered by motion or another event.

Data Rate should be as fast as possible to minimize your airtime. SF7BW125 is usually a good place to start,
as it consumes the least power and airtime. If you need more range, you can slowly increase until you have enough.
You can also enable adaptive data rate (ADR), the network will then be able to automatically optimize your data rate.
```

Cayenne LPP suggests that a payload can safely be sent consisting of up to 51 bytes. However, this would appear to depend on the LORA network setup which has the ability to restrict this as low as 11 bytes.
```
Depending on the LoRa frequency plan and data rate used, the maximum payload varies. 
It’s safe to send up to 51 bytes of payload.
```

[More details on LORA networking and Cayenne](https://developers.mydevices.com/cayenne/docs/lora/#lora-cayenne-low-power-payload)

