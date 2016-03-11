#!/bin/bash

# MUST BE RUN as root:  sudo consoleprep.sh
# parameter is the type of display: 35r (tested), 28c (not tested), 28c (not tested)

# This script should take a current Jessie release and install the adafruit stuff for the 3.5" PiTFT
# It also installs needed python packages and downgrades the sdllib to the stable Wheezy version for the
# touchscreen to work since sdllib 2 breaks pygame.

# Before running this script you should load a current Jessie on the SD card and boot; connect WiFi as appropriate if necessary;
# run raspi-config and expand the file system and update things as needed under the adv settings and REBOOT

# get this script with:
# wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/consoleprep.sh
# chmod +x this script
# script will prompt for Timezone info
# script installs tightvncserver as a convenience - this installation will prompt for a vnc password
# script may ask for permission to use more file system space - always say y
#

case $1 in
  "35r")
    echo "3.5 inch resistive touch screen" ;;
  "28c")
    echo "2.8 inch capacitive touch screen - currently untested" ;;
  "28r")
    echo "2.8 inch resistive touch screen currently untested";;
  *)
    echo "unknown or missing display parameter"
    exit 1 ;;
esac



dpkg-reconfigure tzdata

# for later convenience install tightvncserver to the system to make it easy to get into the Pi since it is otherwise headless
mkdir Console
mkdir consolerem
mkdir consolestable
mkdir consolebeta
chown pi Console consolerem consolestable consolebeta


apt-get -y install tightvncserver
sudo -u pi tightvncserver
apt-get -y install autocutsel

echo "
[Unit]
Description=TightVNC remote desktop server
After=sshd.service

[Service]
Type=dbus
ExecStart=/usr/bin/tightvncserver :0 -geometry 1280x1024 -name \"RPi2LQ\" -rfbport 8723
User=pi
Type=forking

[Install]
WantedBy=multi-user.target
" > /etc/systemd/system/tightvncserver.service

systemctl daemon-reload && sudo systemctl enable tightvncserver.service


apt-get -y update
apt-get -y upgrade



curl -SLs https://apt.adafruit.com/add-pin | sudo bash
apt-get install raspberrypi-bootloader
apt-get install adafruit-pitft-helper

adafruit-pitft-helper -t $1

pip install --upgrade pip
pip install configobj
pip install webcolors
pip install xmltodict
/usr/local/bin/pip install ISYlib

#enable wheezy package sources
echo "deb http://archive.raspbian.org/raspbian wheezy main
" > /etc/apt/sources.list.d/wheezy.list

#set stable as default package source (currently jessie)
echo "APT::Default-release \"stable\";
" > /etc/apt/apt.conf.d/10defaultRelease

#set the priority for libsdl from wheezy higher then the jessie package
echo "Package: libsdl1.2debian
Pin: release n=jessie
Pin-Priority: -10
Package: libsdl1.2debian
Pin: release n=wheezy
Pin-Priority: 900
" > /etc/apt/preferences.d/libsdl
#install
apt-get -y update
apt-get -y --force-yes install libsdl1.2debian/wheezy

# set vertical orientation
mv /boot/config.txt /boot/config.sav
sed s/rotate=90/rotate=180/ /boot/config.sav > /boot/config.txt
adafruit-pitft-touch-cal -f -t $1 -r 180



cd /home/pi/
echo "-----Get Current Release-----" >> /home/pi/log.txt
date >> /home/pi/log.txt
wget https://github.com/kevinkahn/softconsole/archive/v1.1.tar.gz >> /home/pi/log.txt
tar -zx < v1.1.tar.gz >> /home/pi/log.txt
rm -fr consolestable
mv softconsole-1.1 consolestable
rm -f v1.1.tar.gz
echo "-------Get Beta Release------"
wget https://github.com/kevinkahn/softconsole/archive/currentbeta.tar.gz >>  /home/pi/log.txt
tar -zx < currentbeta.tar.gz >> /home/pi/log.txt
rm -fr consolebeta
mv softconsole-currentbeta consolebeta
rm -f currentbeta.tar.gz
echo "-----Done with Fetch -----" /home/pi/log.txt
chown pi /home/pi/log.txt

