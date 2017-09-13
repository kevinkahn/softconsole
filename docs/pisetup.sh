#!/bin/bash
#
# Meant to be put on boot file system when SD card is created then run as root
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
  #echo >> /home/pi/earlyprep.log
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  #echo "----------------------------------------------------------" >> /home/pi/earlyprep.log
  #echo "----------------------------------------------------------" >> /home/pi/earlyprep.log
  echo "$1"
  #echo "$1" >> /home/pi/earlyprep.log
  date
  #date >> /home/pi/earlyprep.log
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  #echo "----------------------------------------------------------" >> /home/pi/earlyprep.log
  #echo "----------------------------------------------------------" >> /home/pi/earlyprep.log
  echo
  #echo >> /home/pi/earlyprep.log

}

if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
  exit
fi

cd /home/pi
LogBanner "Connect WiFI if needed"
read -p "Press Enter to continue"
sudo passwd pi
Get_val NodeName "What name for this system?"
Get_yn VNCstdPort "Install VNC/ssh on standard port (Y/N)?"

if [ "x$1" != "x" ]
then
  LogBanner "Extended setup requested"
  Get_yn InstallOVPN "Install OpenVPN (Y/N)?"
  Get_yn InstallDDC "Install ddclient (Y/N)?"
  #Get_yn InstallSamba "Install samba (Y/N)?"
  Get_yn InstallWD "Install and start Watchdog (Y/N)?"
else
  InstallOVPN=N
  InstallDDC=N
  InstallWD=N
fi

Get_yn Go "Proceed?"
if [ "$Go" != "Y" ]
then
  exit 1
fi
# redo asks

exec > >(tee -a /home/pi/earlyprep.log)

LogBanner "Force WiFi to US"
COUNTRY=US
if [ -e /etc/wpa_supplicant/wpa_supplicant.conf ]; then
    if grep -q "^country=" /etc/wpa_supplicant/wpa_supplicant.conf ; then
        sed -i --follow-symlinks "s/^country=.*/country=$COUNTRY/g" /etc/wpa_supplicant/wpa_supplicant.conf
    else
        sed -i --follow-symlinks "1i country=$COUNTRY" /etc/wpa_supplicant/wpa_supplicant.conf
    fi
else
    echo "country=$COUNTRY" > /etc/wpa_supplicant/wpa_supplicant.conf
fi
LogBanner "Fix Keyboard"
echo "
# Softconsole setup forced keyboard setting for US Standard

# Consult the keyboard(5) manual page.

XKBMODEL=\"pc105\"
XKBLAYOUT=\"us\"
XKBVARIANT=\"\"
XKBOPTIONS=\"\"
BACKSPACE=\"guess\"
" > /etc/default/keyboard
invoke-rc.d keyboard-setup start
udevadm trigger --subsystem-match=input --action=change

dpkg-reconfigure tzdata

LogBanner "Run raspi-config if you need non-US wifi, non-US keyboard, or other specials"
LogBanner "Turn on ssh"
touch /boot/ssh # turn on ssh

LogBanner "Changing Node Name to: $NodeName"
mv -n /etc/hosts /etc/hosts.orig
sed s/raspberrypi/$NodeName/ /etc/hosts.orig > /etc/hosts
echo $NodeName > /etc/hostname
hostname $NodeName

LogBanner "Set better LX Terminal parameters"
cd /home/pi/.config/lxterminal
echo "
/fontname/c \\
fontname = Monospace Bold 13
/bgcolor/c \\
bgcolor=#5ddb1a55f009
/fgcolor/c \\
fgcolor=#c63eef9a0c11
" > lxfix
cp lxterminal.conf lxterminal.conf.bak
sed -f lxfix lxterminal.conf.bak > lxterminal.conf

LogBanner "Install tightvncserver"
apt-get -y install tightvncserver
sudo -u pi tightvncserver
#apt-get -y install autocutsel


if [ $VNCstdPort != "Y" ]
then
  SSHDport=$(($VNCstdPort - 100))
  echo "VNC will be set up on port " $VNCstdPort
  echo "sshd will be moved to port " $SSHDport

  VNCport="-rfbport $VNCstdPort"
  cp /etc/ssh/sshd_config /etc/ssh/sshd_config.sav
  sed "/Port /s/.*/Port $SSHDport/" /etc/ssh/sshd_config.sav > /etc/ssh/sshd_config
else
  echo "VNC will be set up on its normal port"
  VNCport=""

fi

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
systemctl start tightvncserver.service

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
  wget https://github.com/kevinkahn/watchdoghandler/archive/1.2.tar.gz
  tar -zxls --strip-components=1 < 1.2.tar.gz
  bash ./WDsetup.sh
  echo "Edit watchdog yaml file as needed" >> /home/pi/TODO-installation
fi

cd /home/pi
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/installconsole.sh
chmod +x installconsole.sh

LogBanner "Install Display Setup Scripts"
cd /usr/local/src
## re4son current stable as of 8/29/2017 is 11299
wget  -O re4son-kernel_current.tar.xz https://whitedome.com.au/re4son/downloads/11299/
tar -xJf re4son-kernel_current.tar.xz

LogBanner "If on Pi3 or Pi0W answer Y when prompted to install BT/WiFi Drivers and when prompted to enable BT"
LogBanner "Expect long wait for BT and WiFi updates to finish installing"
cd re4son-kernel_4*
./install.sh



LogBanner "Choose Correct Display Type"
./re4son-pi-tft-setup -u
./re4son-pi-tft-setup -h
Get_val DisplayType "Enter display type: "
./re4son-pi-tft-setup -t $DisplayType # TODO coordinate this with the adafruit call below


# fixups = ads7846  orientation fixes in 99 cal

cd /home/pi
wget raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-touch-cal
chmod +x adafruit-pitft-touch-cal

LogBanner "Configure the screen and calibrate"
# set vertical orientation
mv /boot/config.txt /boot/config.sav
sed s/rotate=90/rotate=0/ /boot/config.sav > /boot/config.txt  # TODO need to pick rotation based on screen type
./adafruit-pitft-touch-cal -f -r 0 -t $DisplayType # TODO needs to work for waveshare screen

echo "Reboot now and then run installconsole.sh as root"


