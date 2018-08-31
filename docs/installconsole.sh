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

function UseWheezyVersion()
{
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

}

LogBanner "Console Setup Script" > /home/pi/prep.log
if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
  exit
fi

# script can take 3 parameters to preanswer Personal and AutoConsole and specify Wheezy touch
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

if [ -n "$3" ]
then
  UseWheezy=$3
else
  Get_yn UseWheezy "Use Wheezy SDL for oddball screens (Y/N)?"
  SkipVerify=N
fi

echo "Developer system:           $Personal"
echo "Auto start Console on boot: $AutoConsole"
echo "Downgrade touch to Wheezy:  $UseWheezy"

Go='N'
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
exec 2>&1

echo stable > versionselector

if [ $Personal == "Y" ]
then
    touch homesystem
    #echo cur > versionselector  # todo delete
    echo "Make Home System"
fi

#LogBanner "Update/upgrade system"
#apt-get update
#DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
echo 1 > /proc/sys/vm/drop_caches # try to avoid kswap problem

# Install the python packages needed for the console

LogBanner "Install stuff for console"
#apt-get -y install python-dev
#apt-get -y install python3-dev
#LogBanner "Switch default Python to Python3"
#update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2

pip install --upgrade pip
pip3 install --upgrade pip

pip3 install homeassistant # do it here to avoid conflicts in versions later

if [ $UseWheezy == "Y" ]
then
    LogBanner "Old Wheezy Touch system requested"
    UseWheezyVersion
fi

cd /home/pi/
LogBanner "Console Installation"
if [ $Personal == "Y" ]
then
    echo Get homerelease version of setupconsole and githubutil
    wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/setupconsole.py
    wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/githubutil.py
else
    echo Get currentrelease version of setupconsole and githubutil
    wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/setupconsole.py
    wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/githubutil.py
fi

python -u setupconsole.py

# in case this is a development system
cp consolestable/scripts/python-sudo.sh .
chmod a+x python-sudo.sh

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
  systemctl enable softconsole.service
else
  LogBanner "Set No Console Autostart at Boot"
fi

if [ -e /boot/auth ]
then
  mv -f /boot/auth/* /home/pi/Console/cfglib
  rmdir /boot/auth
fi

if [ -e /usr/lib/systemd/system/vncserverpi.service ]
then
  LogBanner "Enable VNC"
  systemctl enable vncserverpi
fi

mkdir consoleinstallleftovers
mv prep.log earlyprep.log consoleinstallleftovers
mv adafruit* consoleinstallleftovers
rm tmp
rm getsetupinfo.py
rm doinstall.sh
mv installc* consoleinstallleftovers
mv di.log    consoleinstallleftovers

LogBanner "Install and setup finished"
rm -f /home/pi/CONSOLEINSTALLRUNNING
LogBanner "Rebooting in 5 seconds"
for i in 5 4 3 2 1
do
  echo Rebooting $i
  sleep 1
done
echo "Reboot . . ."
reboot now
