#!/bin/bash
#
# Meant to be put on boot file system when SD card is created then run as root

function LogBanner() {
  echo
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  echo "$1"
  date
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
}

if [[ "$EUID" -ne 0 ]]; then
  echo "Must be run as root"
  exit
fi

exec > >(tee -a /home/pi/earlyprep.log)
exec 2>&1

cd /home/pi
LogBanner "This is the system setup script"
LogBanner "Connect WiFI if needed"
mkdir consoleinstallleftovers
read -p "Press Enter to continue"

LogBanner "Install Python2/3 Compatibility Support"
echo "Note - installation switches system default Python to version 3"
echo "To undo this run 'sudo update-alternatives --config python' to select desired alternative"

LogBanner "Switch default Python to Python3"
update-alternatives --install /usr/bin/python python /usr/bin/python3 2
update-alternatives --install /usr/bin/python python /usr/bin/python2 1
update-alternatives --set python /usr/bin/python3

LogBanner "Set Time Zone"
dpkg-reconfigure tzdata
LogBanner "Pi User Password"
sudo passwd pi

wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/getinstallinfo.py
wget https://raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-touch-cal
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/adafruit-pitft.sh
chmod +x adafruit-pitft-touch-cal adafruit-pitft.sh

python getinstallinfo.py
if [ $? -ne 0]; then
  echo "Exiting pisetup due to error in getinstallinfo"
  exit 1
fi

LogBanner "Upgrade/Update System"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade

echo "deb http://mirrordirector.raspbian.org/raspbian/ stretch main contrib non-free rpi firmware" >>/etc/apt/sources.list.d/raspi.list

source installvals

if [ "$Personal" == "Y" ]; then
  echo Get homerelease versions of setup scripts
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/scripts/vncserverpi.service
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/scripts/lxterminal.conf
else
  # NOTE to test with current master version from github replace "currentrelease" with 'master'
  echo Get currentrelease version of setup scripts
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/scripts/vncserverpi.service
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/scripts/lxterminal.conf
# fix issue in adafruit install script as of 3/31/2018
fi
if [ "$InstallBeta" == "Y" ]; then
  echo use beta install scripts
  mv installconsole.sh consoleinstallleftovers/stable-installconsole.sh
  mv screeninstall.py consoleinstallleftovers/stable-screeninstall.py
  mv vncserverpi.service consoleinstallleftovers/stable-vncserverpi.service
  mv lxterminal.conf consoleinstallleftovers/stable-lxterminal.conf
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentbeta/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentbeta/scripts/vncserverpi.service
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentbeta/scripts/lxterminal.conf
fi

chmod +x installconsole.sh
chown pi:pi lxterminal.conf

LogBanner "Force WiFi to US"
COUNTRY=US
if [ -e /etc/wpa_supplicant/wpa_supplicant.conf ]; then
  if grep -q "^country=" /etc/wpa_supplicant/wpa_supplicant.conf; then
    sed -i --follow-symlinks "s/^country=.*/country=$COUNTRY/g" /etc/wpa_supplicant/wpa_supplicant.conf
  else
    sed -i --follow-symlinks "1i country=$COUNTRY" /etc/wpa_supplicant/wpa_supplicant.conf
  fi
else
  echo "country=$COUNTRY" >/etc/wpa_supplicant/wpa_supplicant.conf
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
" >/etc/default/keyboard
invoke-rc.d keyboard-setup start
udevadm trigger --subsystem-match=input --action=change

LogBanner "Run raspi-config if you need non-US wifi, non-US keyboard, or other specials"

LogBanner "Turn on ssh"
touch /boot/ssh # turn on ssh

LogBanner "Changing Node Name to: $NodeName"
mv -n /etc/hosts /etc/hosts.orig
sed s/raspberrypi/$NodeName/ /etc/hosts.orig >/etc/hosts
echo $NodeName >/etc/hostname
hostname $NodeName

LogBanner "Set better LX Terminal parameters"
sudo -u pi mkdir -p /home/pi/.config/lxterminal
mv -f lxterminal.conf /home/pi/.config/lxterminal

case $VNCstdPort in # if [ $VNCstdPort != "Y" ]
Y)
  echo "VNC will be set up on its normal port"
  su pi -c vncserver
  ;;
N)
  echo "No VNC will ne set up"
  ;;
*)
  su pi -c vncserver # create the Xvnc file in ~pi/.vnc/config.d so it can be modified below
  SSHDport=$(($VNCstdPort - 100))
  VNCConsole=$(($VNCstdPort - 1))
  echo "Virtual VNC will be set up on port " $VNCstdPort
  echo "sshd will be moved to port " $SSHDport
  cp /etc/ssh/sshd_config /etc/ssh/sshd_config.sav
  sed "/Port /s/.*/Port $SSHDport/" /etc/ssh/sshd_config.sav >/etc/ssh/sshd_config
  echo "RfbPort=$VNCstdPort" >>/home/pi/.vnc/config.d/Xvnc
  chown pi:pi /home/pi/.vnc/config.d/Xvnc
  ;;
esac
LogBanner "Setup Virtual VNC Service"

if [ $VNCstdPort == "N" ]; then
  echo "VNC service file installation skipped"
else
  echo "VNC service file installed"
  mv /home/pi/vncserverpi.service /usr/lib/systemd/system
fi

# Save initial rc.local to restore after helper scripts run
cp /etc/rc.local /etc/rc.local.hold # helper script below screws up rc.local

cd /home/pi

if [[ $(cat /etc/issue) == *"Linux 10"* ]]; then
  #    LogBanner "Adjust adafruit scritp for Buster (now fixed in Adafruit as of 7/2019)"
  #    sed -isav 's/evtest tslib libts\-bin/evtest tslib/' adafruit-pitft.sh
  #    sed  -isav '/evtest tslib/a  apt-get install -y libts-bin' adafruit-pitft.sh
  echo "$ScreenType"B >.Screentype
else
  sed -isav s/fb0/fb1/ /usr/share/X11/xorg.conf.d/99-fbturbo.conf
  echo $ScreenType >.Screentype
fi

LogBanner "Run screen specific install code"
source installscreencode
LogBanner "Completed screen specific install code"

#case $ScreenType in
#  28r|28c|35r)
#   ./adafruit-pitft.sh < adafinput
#    raspi-config nonint do_boot_behaviour B4 # set boot to desktop already logged in
#  ;;
#  pi7)
#    LogBanner "7 Inch Pi Screen"
#    if [ $Flip7 == 'Y' ]
#    then
#        echo "lcd_rotate=2" >> /boot/config.txt
#    fi
#    ;;
#  wave35)
#    LogBanner "Install Waveshare screen"
#    echo "Following link as of 8//30/18"
#    wget https://www.waveshare.com/w/upload/3/34/LCD-show-180331.tar.gz
#    tar xvf LCD-show-*.tar.gz
#    cd LCD-show 90
#    chmod +x LCD35-show
#    sed -i 's/sudo reboot/echo skip sudo reboot/' "LCD35-show"
#    ./LCD35-show 90
#    cd ..
#
#    echo "Update pointercal"
#    cat > /etc/pointercal <<EOF
#5729 138 -1857350 78 8574 -2707152 65536
#EOF

# 5672 -28 -1130318 -203 8466 -1835732 65536

#    echo "Finished waveshare install"
#    ;;
#  *)
#    LogBanner "User installed screen"
#    echo Screen type: $ScreenType
#    ;;
#esac

mv --backup=numbered /etc/rc.local.hold /etc/rc.local
chmod +x /etc/rc.local
#echo "# Dummy entry to keep this file from being recreated in Stretch" > /usr/share/X11/xorg.conf.d/99-fbturbo.conf
#cat /usr/share/X11/xorg.conf.d/99-fbturbo.conf

LogBanner "Reboot now installconsole.sh will autorun as root unless aborted"
echo "Install will set Personal $Personal and AutoConsole $AutoConsole"

if [ "$Reboot" == "Y" ]; then

  LogBanner "Rebooting in 10 seconds"
  for i in 10 9 8 7 6 5 4 3 2 1; do
    echo Rebooting $i
    sleep 1
  done
  echo "Reboot . . ."
  cd /home/pi
  mv .bashrc .bashrc.real
  cat >.bashrc <<EOF
cd /home/pi
source .bashrc.real
cp .bashrc .bashrc.sav
mv -f .bashrc.real .bashrc
touch /home/pi/CONSOLEINSTALLRUNNING
sleep 15 # delay to allow X system to startup for next command (is this long enough in a Pi0)
#DISPLAY=:0.0 x-terminal-emulator -t "Console Install" --geometry=40x17 -e sudo bash /home/pi/doinstall.sh 2>> /home/pi/di.log
sudo bash /home/pi/doinstall.sh 2>> /home/pi/di.log
EOF
  cat >doinstall.sh <<EOF
echo Autorunning console install in 10 second - ctl-c to stop
for i in 10 9 8 7 6 5 4 3 2 1
    do
      echo installconsole.sh start in \$i
      sleep 1
    done
sudo bash -c "echo 1 > /proc/sys/vm/drop_caches"  # trying to avoid the kswap issue
sudo bash ./installconsole.sh $Personal $AutoConsole $InstallBeta
EOF
  reboot now
fi
LogBanner "Chose to manually reboot and run installconsole.sh"
