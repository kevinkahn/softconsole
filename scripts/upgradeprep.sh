#!/usr/bin/env bash

export PATH="/home/pi/pyenv/bin:$PATH"

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
pip install requests
pip install pillow
pip install pygame
#echo Setup Systemd
#pwd
#if [ -e setupsystemd.py ]; then
#  echo Initial install
#  python setupsystemd.py
#else
#  echo Upgrade process
#  python ../setupsystemd.py
#  # this runs in previous version so the new python code is up a level
#fi
#cd alerts
#wget https://github.com/ScrewLooseDan/softconsole_sensor_alert/raw/master/lightsensor.py
#mv lightsensor.py lightsensor.pyold
#sed "/import alerttasks/s/alerttasks/alertsystem.alerttasks as alerttasks/" lightsensor.pyold >lightsensor.py
