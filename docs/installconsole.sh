#!/bin/bash

# MUST BE RUN as root:  sudo installconsole.sh

# This script should take a with a TFT display and install the softconsole.
# It installs needed python packages and downgrades the sdllib to the stable Wheezy version for the
# touchscreen to work since sdllibn 2 breaks pygame.

# Before running this script you should load a current Jessie on the SD card, add earlyprep.sh to the /boot, and run earlyprep.sh
# to set up the system and display.

function Get_yn()
{
  # params: var, prompt
  read -p "$2 " resp
  case $resp in
    "Y" | "y")
      resp="Y" ;;
    "N" | "n")
      resp="N" ;;
    *)
      ;;
  esac
  eval $1="'$resp'"
}

function Get_val()
{
  # params: var, prompt
  read -p "$2 " resp
  eval $1="'$resp'"
}
function LogBanner()
{
  echo
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  echo "$1"
  date
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
}

LogBanner "Console Setup Script" > /home/pi/prep.log
if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
  exit
fi

# script can take 2 parameters to preanswer Personal and AutoConsole
# this supports autorunning at reboot
SkipVerify=Y
if [ -n "$1" ]
then
  Personal=$1
else
  Get_yn Personal "Is this the developer personal system (Y/N) (risky to say Y if it not)?"
  SkipVerify=N
fi
if [ -n "$2" ]
then
  AutoConsole=$2
else
  Get_yn AutoConsole "Autostart console (Y/N)?"
  SkipVerify=N
fi

echo "Developer system:           $Personal"
echo "Auto start Console on boot: $AutoConsole"

if [ "$SkipVerify" != "Y" ]
then
    Get_yn Go "Proceed?"
    if [ "$Go" != "Y" ]
    then
      exit 1
    fi
fi

date >> /home/pi/prep.log
echo "Developer system:           $Personal" >> /home/pi/prep.log
echo "Auto start Console on boot: $AutoConsole" >> /home/pi/prep.log
exec > >(tee -a /home/pi/prep.log)


if [ $Personal == "Y" ]
then
    touch homesystem
    echo "Make Home System"
fi

LogBanner "Update/upgrade system"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade

# Install the python packages needed for the console

LogBanner "Install stuff for console"
apt-get -y install python-dev

pip install --upgrade pip
pip install configobj
pip install webcolors
pip install xmltodict
pip install websocket-client
pip install wiringpi

# PiTFT touch using PyGame requires the older wheezy sdl library (long term problem that PyGame needs to resolve)

LogBanner "Setup to downgrade touch stuff to wheezy"
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
Pin: release n=stretch
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

cd /home/pi/
LogBanner "Console Installation"
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/setupconsole.py
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/githubutil.py
python -u setupconsole.py

if [ -e Consoleauth ]
then
  mv -f Consoleauth Console/cfglib/auth.cfg
fi
if [ -e ConsoleMinEx ]
then
  mv -f ConsoleMinEx Console/config.txt
fi

rm setupconsole.* githubutil.*

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]
then
  LogBanner "Set Console to Start at Boot"
  mv --backup=numbered /home/pi/consolestable/docs/rc.local /etc/rc.local
  chmod a+x /etc/rc.local
  chown root /etc/rc.local
  echo "Create configuration files in Console" >> /home/pi/TODO-installation
fi

LogBanner "Install and setup finished"
LogBanner "Rebooting in 5 seconds"
for i in 5 4 3 2 1
do
  echo Rebooting $i
  sleep 1
done
echo "Reboot . . ."
reboot now
