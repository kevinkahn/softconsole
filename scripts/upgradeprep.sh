#!/usr/bin/env bash

pip install configobj
 #--break-system-packages
pip install webcolors
 #--break-system-packages
pip install xmltodict
 #--break-system-packages
pip install smbus
 #--break-system-packages
pip install psutil
 #--break-system-packages
pip install aiohttp
# --break-system-packages
pip install --upgrade websocket-client
#--break-system-packages
pip install --upgrade wiringpi
#--break-system-packages
pip install --upgrade paho-mqtt
#--break-system-packages
pip install --upgrade python-dateutil
#--break-system-packages
#pip install darksky_weather
#--break-system-packages

if [ -e setupsystemd.py ]; then
  echo Initial install
  python setupsystemd.py
else
  echo Upgrade process
  python ../setupsystemd.py
  # this runs in previous version so the new python code is up a level
fi
cd alerts
wget https://github.com/ScrewLooseDan/softconsole_sensor_alert/raw/master/lightsensor.py
#mv lightsensor.py lightsensor.pyold
#sed "/import alerttasks/s/alerttasks/alertsystem.alerttasks as alerttasks/" lightsensor.pyold >lightsensor.py
