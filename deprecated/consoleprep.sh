#!/bin/bash

# MUST BE RUN as root:  sudo consoleprep.sh
# parameter is the type of display: 35r (tested), 28c, 28c (not tested)
# second parameter is the hostname for this rpi - this will be used to name this node and as the title in the vnc server
#  if left blank default "raspberrypi" will be used
# third parameter uses a nonstandard VNC port non blank
# fourth parameter if non null indicates personal system (uses special release - don't suggest you try this)

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
if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
  exit
fi

NodeName="raspberrypi"

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

if [ -n $2 ]
then
  NodeName=$2
  echo "Changing Node Name to: $NodeName"
  mv -n /etc/hosts /etc/hosts.orig
  sed s/raspberrypi/$NodeName/ /etc/hosts.orig > /etc/hosts
  echo $NodeName > /etc/hostname
  hostname $NodeName
fi

if [ -z $3 ]
then
  echo "VNC will be set up on its normal port"
  VNCport=""
else
  echo "VNC will be set up on port 8723"
  VNCport="-rfbport 8723"
fi

if [ -n $4 ]
then
    touch homesystem
fi

dpkg-reconfigure tzdata

# for later convenience install tightvncserver to the system to make it easy to get into the Pi since it is otherwise headless

echo "Install tightvncserver"
apt-get -y install tightvncserver
sudo -u pi tightvncserver
apt-get -y install autocutsel

echo "Create tightvnc service files"
echo "
[Unit]
Description=TightVNC remote desktop server
After=sshd.service

[Service]
Type=dbus
ExecStart=/usr/bin/tightvncserver :1 -geometry 1280x1024 -name $NodeName $VNCport
User=pi
Type=forking

[Install]
WantedBy=multi-user.target
" > /etc/systemd/system/tightvncserver.service

echo "Start tightvncserver service"
systemctl daemon-reload && sudo systemctl enable tightvncserver.service

echo "Update system"
apt-get update
echo "Upgrade system"
apt-get -y upgrade


echo "Add adafruit"
curl -SLs https://apt.adafruit.com/add-pin | sudo bash
echo "Install bootloader"
apt-get -y install raspberrypi-bootloader
echo "Install pitft helper"
apt-get -y install adafruit-pitft-helper

echo "Run helper"
adafruit-pitft-helper -t $1

echo "Install stuff for console"
apt-get -y install python-dev

pip install --upgrade pip
pip install configobj
pip install webcolors
pip install xmltodict
pip install wiringpi
/usr/local/bin/pip install ISYlib

echo "Setup to downgrade touch stuff to wheezy"
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

echo "Update to downgrade"
apt-get -y --force-yes update
echo "Install the downgrade"
apt-get -y --force-yes install libsdl1.2debian/wheezy

echo "Configure the screen and calibrate"
# set vertical orientation
mv /boot/config.txt /boot/config.sav
sed s/rotate=90/rotate=180/ /boot/config.sav > /boot/config.txt
adafruit-pitft-touch-cal -f -t $1 -r 180



cd /home/pi/
echo "-------Install Console-------" >> /home/pi/log.txt
date >> /home/pi/log.txt
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/setupconsole.py
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/githubutil.py
python setupconsole.py >> /home/pi/log.txt
shutdown

rm setupconsole.py, githubutil.py
chown pi /home/pi/log.txt

