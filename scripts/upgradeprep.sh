#!/usr/bin/env bash

pip install configobj
pip install webcolors
pip install xmltodict
pip install smbus
pip install psutil
pip install aiohttp
pip install --upgrade websocket-client
pip install --upgrade wiringpi
pip install --upgrade paho-mqtt
pip install --upgrade python-dateutil
pip install --upgrade future
pip install darksky_weather

if [ -e setupsystemd.py ]
then
    echo Initial install
    python setupsystemd.py
else
    echo Upgrade process
    python ../setupsystemd.py
    # this runs in previous version so the new python code is up a level
fi
cd alerts
wget https://github.com/ScrewLooseDan/softconsole_sensor_alert/raw/master/lightsensor.py