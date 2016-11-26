#!/bin/bash

# MUST BE RUN as root:  sudo consoleprep.sh

# This script should take a current Jessie release and install support for PiTFT
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
# script prompts for system name and other options
#

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
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  echo
}

LogBanner "Pi setup Script"

#if [ -z "$1" ] || [ "$1" != --tee ]; then
#  $0 --tee "$@" | tee prep.log
#  exit $?
#else
#  shift
#fi

if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
#  exit
fi

ScreenType="XXX"
while [[ "$ScreenType" != "35r" && "$ScreenType" != "28c" && "$ScreenType" != "28r" ]]
do
  Get_val ScreenType "Which PiTFT (35r, 28c, 28r)?"
done
Get_val NodeName "What name for this system?"
Get_yn VNCstdPort "Install VNC/ssh on standard port (Y/N)?"
Get_yn Personal "Is this the developer personal system (Y/N) (risky to say Y if it not)?"
Get_yn AutoConsole "Autostart console (Y/N)?"
Get_yn InstallOVPN "Install OpenVPN (Y/N)?"
Get_yn InstallDDC "Install ddclient (Y/N)?"
#Get_yn InstallSamba "Install samba (Y/N)?"
Get_yn InstallWD "Install and start Watchdog (Y/N)?"

echo "Screen Type:                $ScreenType"
echo "NodeName:                   $NodeName"
echo "Developer system:           $Personal"
echo "Standard VNC port:          $VNCstdPort"
echo "Auto start Console on boot: $AutoConsole"
echo "Install OpenVPN:            $InstallOVPN"
echo "Install ddclient:           $InstallDDC"
#echo "Install Samba:              $InstallSamba"
echo "Install and start watchdog: $InstallWD"

Get_yn Go "Proceed?"
if [ "$Go" != "Y" ]
then
  exit 1
fi

dpkg-reconfigure tzdata

echo "System Preparation" > prep.log
date >> prep.log
echo "Screen Type:                $ScreenType" >> prep.log
echo "NodeName:                   $NodeName" >> prep.log
echo "Developer system:           $Personal" >> prep.log
echo "Standard VNC port:          $VNCstdPort" >> prep.log
echo "Auto start Console on boot: $AutoConsole" >> prep.log
echo "Install OpenVPN:            $InstallOVPN" >> prep.log
echo "Install ddclient:           $InstallDDC" >> prep.log
echo "Install and start watchdog: $InstallWD" >> prep.log
exec > >(tee -a prep.log)


LogBanner "Changing Node Name to: $NodeName"
mv -n /etc/hosts /etc/hosts.orig
sed s/raspberrypi/$NodeName/ /etc/hosts.orig > /etc/hosts
echo $NodeName > /etc/hostname
hostname $NodeName

LogBanner "System Options"

if [ $VNCstdPort != "Y" ]
then
  echo "VNC will be set up on port " $VNCstdPort
  echo "sshd will be moved to port " $VNCstdPort - 100
  SSHDport= $VNCstdPort - 100
  VNCport="-rfbport " $VNCstdPort
  sed s/22/$SSHDport/ /etc/ssh/sshd_config > /etc/ssh/sshd_config
else
  echo "VNC will be set up on its normal port"
  VNCport=""

fi

if [ $Personal == "Y" ]
then
    touch homesystem
    echo "Make Home System"
fi


# for later convenience install tightvncserver to the system to make it easy to get into the Pi since it is otherwise headless

LogBanner "Install tightvncserver"
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

LogBanner "Update/upgrade system"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade


# Get the one adafruit tool we need since this script uses the kali pitft support

cd /home/pi
wget raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-touch-cal

# Install the python packages needed for the console

LogBanner "Install stuff for console"
apt-get -y install python-dev

pip install --upgrade pip
pip install configobj
pip install webcolors
pip install xmltodict
pip install wiringpi
/usr/local/bin/pip install ISYlib

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
Pin: release n=wheezy
Pin-Priority: 900
" > /etc/apt/preferences.d/libsdl

#install

echo "Update to downgrade"
apt-get -y --force-yes update
echo "Install the downgrade"
apt-get -y --force-yes install libsdl1.2debian/wheezy

# third party has figured out PiTFT support for newer Debian distrs
# ref: https://whitedome.com.au/re4son/sticky-fingers-kali-pi/#TFT

LogBanner "Changes for PiTFT Support"
cd /usr/local/src
wget  -O re4son_kali-pi-tft_kernel_current.tar.xz http://whitedome.com.au/re4son/downloads/10452/
tar -xJf re4son_kali-pi-tft_kernel_current.tar.xz
cd re4son_kali-pi-tft*
echo "N" | ./install.sh

./re4son-pi-tft-setup -d

echo "Y N" | ./re4son-pi-tft-setup -t 35r

LogBanner "Configure the screen and calibrate"
# set vertical orientation
mv /boot/config.txt /boot/config.sav
sed s/rotate=90/rotate=0/ /boot/config.sav > /boot/config.txt
python /home/pi/adafruit-pitft-touch-cal -f -t $ScreenType -r 180

cd /home/pi/
LogBanner "Console Installation"
echo "-------Install Console-------" >> /home/pi/log.txt
date >> /home/pi/log.txt
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/setupconsole.py
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/githubutil.py
python setupconsole.py >> /home/pi/log.txt

rm setupconsole.* githubutil.*
chown pi /home/pi/log.txt

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]
then
  LogBanner "Set Console to Start at Boot"
  mv --backup=numbered /home/pi/consolestable/docs/rc.local /etc/rc.local
  chmod a+x /etc/rc.local
  chown root /etc/rc.local
  echo "Create configuration files in Console" >> /home/pi/TODO-installation
fi


# install OpenVPN
if [ "$InstallOVPN" == "Y" ]
then
  LogBanner "Install OpenVPN"
  apt-get -y install openvpn
  echo "Set up OpenVPN keys etc." >> /home/pi/TODO-installation
fi

# install ddclient
if [ "$InstallDDC" == "Y" ]
then
  LogBanner "Install ddclient"
  echo "
  ssl=yes
  protocol=googledomains
  login=<addfromgoogle>
  password=<addfromgoogle>
  use=????
  host.domain.tld
  " > /etc/ddclient.conf
  DEBIAN_FRONTEND=noninteractive apt-get -y install ddclient

  echo "Configure ddclient" >> /home/pi/TODO-installation
fi

# install watchdog
if [ "$InstallWD" == "Y" ]
then
  LogBanner "Install Watchdog"
  cd /home/pi
  mkdir watchdog
  cd watchdog
  wget https://github.com/kevinkahn/watchdoghandler/archive/1.1.tar.gz
  tar -zxls --strip-components=1 < 1.1.tar.gz
  bash ./WDsetup.sh
  echo "Edit watchdog yaml file as needed" >> /home/pi/TODO-installation
fi

LogBanner "Install and setup finished"

