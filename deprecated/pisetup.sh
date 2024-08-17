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

exec > >(tee -a /home/pi/prep.log)
exec 2>&1

cd /home/pi
LogBanner "This is the system setup script"

pip3 install wget
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/getinstallinfo.py

python getinstallinfo.py
if [ $? -ne 0 ]; then
  echo "Exiting pisetup due to error in getinstallinfo"
  exit 1
fi

LogBanner "Upgrade/Update System"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade

source installvals

LogBanner "Changing Node Name to: $NodeName"
mv -n /etc/hosts /etc/hosts.orig
sed s/raspberrypi/$NodeName/ /etc/hosts.orig >/etc/hosts
echo $NodeName >/etc/hostname
hostname $NodeName

LogBanner "Set better LX Terminal parameters"
sudo -u pi mkdir -p /home/pi/.config/lxterminal
mv -f lxterminal.conf /home/pi/.config/lxterminal

LogBanner "Enable vncserver"
# Need to run the vnc server under a real user or you get access issues; don't know why can't get the virtuald version to work
mv /home/pi/vncserverpi.service /usr/lib/systemd/system
systemctl enable vncserverpi
#/etc/vnc/vncservice start vncserver-virtuald

cd /home/pi

LogBanner "Run screen specific install code"
source installscreencode
LogBanner "Completed screen specific install code"

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]; then
  LogBanner "Set Console to Start at Boot"
  systemctl enable softconsole.service
else
  LogBanner "Set No Console Autostart at Boot"
fi

rm githubutil.*
mv getinstallinfo.py .consoleinstallleftovers
mv installvals .consoleinstallleftovers
mv installscreencode .consoleinstallleftovers
mv *.log .consoleinstallleftovers
rm -r __pycache__

if [ "$Reboot" == "Y" ]; then

  LogBanner "Rebooting in 10 seconds"
  for i in 10 9 8 7 6 5 4 3 2 1; do
    echo Rebooting $i
    sleep 1
  done
  echo "Reboot . . ."
  reboot now
  sleep 15

fi

LogBanner "Chose to manually reboot, reboot system to clean up install"
