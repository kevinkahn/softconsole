#!/bin/bash

# MUST BE RUN as root:  sudo installconsole.sh

# This script should take a with a TFT display and install the softconsole.
# It installs needed python packages and downgrades the sdllib to the stable Wheezy version for the
# touchscreen to work since sdllibn 2 breaks pygame.

function LogBanner() {
  echo
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  echo "$1"
  date
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
}

LogBanner "Console Setup Script" >/home/pi/prep.log
if [[ "$EUID" -ne 0 ]]; then
  echo "Must be run as root"
  exit
fi

echo Start >/home/pi/prep.log
date >>/home/pi/prep.log
exec > >(tee -a /home/pi/prep.log)
exec 2>&1

cd /home/pi/
LogBanner "Finish Console Installation"
source installvals

rm setupconsole.* githubutil.*

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]; then
  LogBanner "Set Console to Start at Boot"
  systemctl enable softconsole.service
else
  LogBanner "Set No Console Autostart at Boot"
fi

if [ -e /usr/lib/systemd/system/vncserverpi.service ]; then
  LogBanner "Enable VNC"
  systemctl enable vncserverpi
fi

mv prep.log earlyprep.log consoleinstallleftovers
mv adafruit* consoleinstallleftovers
mv getinstallinfo.py consoleinstallleftovers
mv doinstall.sh consoleinstallleftovers
mv installc* consoleinstallleftovers
mv installvals consoleinstallleftovers
mv adafinput consoleinstallleftovers
mv di.log consoleinstallleftovers
mv installscreencode consoleinstallleftovers

LogBanner "Install and setup finished"
rm -f /home/pi/CONSOLEINSTALLRUNNING
LogBanner "Rebooting in 5 seconds"
for i in 5 4 3 2 1; do
  echo Rebooting $i
  sleep 1
done
echo "Reboot . . ."
reboot now
