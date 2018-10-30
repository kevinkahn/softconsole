#!/usr/bin/env bash
#pip install configobj
#pip install webcolors
#pip install xmltodict
#pip install websocket-client
#pip install wiringpi
#pip install paho-mqtt
#pip install python-dateutil
#pip install future
pip3 install configobj
pip3 install webcolors
pip3 install xmltodict
pip3 install websocket-client
pip3 install wiringpi
pip3 install paho-mqtt
pip3 install python-dateutil
pip3 install future

if [ -e setupsystemd.py ]
then
    echo Initial install
    python setupsystemd.py
else
    echo Upgrade process
    python ../setupsystemd.py
    # this runs in previous version so the new python code is up a level
fi