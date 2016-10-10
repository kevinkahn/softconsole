#!/bin/bash

# MUST BE RUN as root:  sudo consoleprep.sh
# parameter is the type of display: 35r (tested), 28c (tested), 28r (not tested)
# second parameter is the hostname for this rpi - this will be used to name this node and as the title in the vnc server
#  if left blank default "raspberrypi" will be used
# third parameter uses a nonstandard VNC port non blank
# fourth parameter if non null indicates personal system (uses special release - don't suggest you try this)

# This script should take a current Jessie release and install the adafruit stuff for the 3.5" PiTFT
# It also installs needed python packages and downgrades the sdllib to the stable Wheezy version for the
# touchscreen to work since sdllibn 2 breaks pygame.

# Before running this script you should load a current Jessie on the SD card and boot; connect WiFi as appropriate if necessary;
# run raspi-config and expand the file system and update things as needed under the adv settings and REBOOT

# get this script with:
# wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/consoleprep2.sh
# (or https://goo.gl/5V1HtG)
# chmod +x this script
# script will prompt for Timezone info
# script installs tightvncserver as a convenience - this installation will prompt for a vnc password
# script may ask for permission to use more file system space - always say y
#

# install watchdog
cd /home/pi
echo "------Get Watchdog-------"
wget https://github.com/kevinkahn/watchdoghander/archive/1.0.tar.gz
tar -zxls --strip-components=1 < '1.0.tar.gz

echo "Install/setup finished -- set up config.txt file and reboot to start console"

