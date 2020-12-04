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
LogBanner "This is the console only setup script"

pip install --upgrade pip
pip install wget

wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/getinstallinfo.py

python getinstallinfo.py x
if [ $? -ne 0 ]; then
  echo "Exiting pisetup due to error in getinstallinfo"
  exit 1
fi

echo "deb http://mirrordirector.raspbian.org/raspbian/ stretch main contrib non-free rpi firmware" >>/etc/apt/sources.list.d/raspi.list

source installvals

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]; then
  LogBanner "Set Console to Start at Boot"
  systemctl enable softconsole.service
else
  LogBanner "Set No Console Autostart at Boot"
fi

rm githubutil.*
#mv adafruit* .consoleinstallleftovers
mv getinstallinfo.py .consoleinstallleftovers
mv installvals .consoleinstallleftovers
#mv adafinput .consoleinstallleftovers
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
