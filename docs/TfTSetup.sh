#!/bin/bash
#
# Meant to be put on boot file system when SD card is created then run pi

function LogBanner() {
  echo
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
  echo "$1"
  date
  echo "----------------------------------------------------------"
  echo "----------------------------------------------------------"
}

if [[ "$EUID" -eq 0 ]]; then
  echo "Do not run as root"
  exit
fi

exec > >(tee -a /home/pi/prep.log)
exec 2>&1

cd /home/pi
LogBanner "This is the system setup script for console  for user pi"

  LogBanner "If BookWorm: Remember to do rpi-update first!"
  sleep 5
  LogBanner "Continuing . . ."


if DEBIAN_FRONTEND=noninteractive sudo apt-get -y install python3-wget ; then
  echo Wget install ok
else
  echo Error installing wget
  exit
fi

wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/getinstallinfo.py

LogBanner "Install python3-full"
if DEBIAN_FRONTEND=noninteractive sudo apt-get -y install python3-full ; then
  echo Python3 install ok
else
  echo Python3 install error
  exit
fi

LogBanner "Create Virtual Python Environment"
mkdir pyenv
mkdir .xdgdir
python -m venv /home/pi/pyenv --system-site-packages
export PATH="/home/pi/pyenv/bin:$PATH"
pip install wget requests

python getinstallinfo.py
if [ $? -ne 0 ]; then
  echo "Exiting pisetup due to error in getinstallinfo"
  exit 1
fi

source installvals

LogBanner "Install SDL2 stuff"
if DEBIAN_FRONTEND=noninteractive sudo apt-get -y install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev libportmidi-dev libjpeg-dev python3-setuptools python3-dev python3-numpy libegl-dev ; then
  echo SDL2 install ok
else
  echo SDL2 install error
  exit
fi

LogBanner "Upgrade/Update System"
sudo apt-get update
DEBIAN_FRONTEND=noninteractive sudo apt-get -y upgrade


if [ Z$NodeName != Z ]; then
  LogBanner "Changing Node Name to: $NodeName"
  sudo mv -n /etc/hosts /etc/hosts.orig
  sudo sed s/raspberrypi/$NodeName/ /etc/hosts.orig >/etc/hosts
  sudo echo $NodeName >/etc/hostname
  sudo hostname $NodeName
else
  NodeName=`hostname`
  LogBanner "Leaving Node Name as:  $NodeName"
fi

LogBanner "Set Boot to Logged in CLI"
sudo systemctl --quiet set-default multi-user.target
sudo sed -i 's/^.*HandlePowerKey=.*$/#HandlePowerKey=poweroff/' /etc/systemd/logind.conf
cat > tempautoLogin << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF
sudo cp tempautoLogin /etc/systemd/system/getty@tty1.service.d/autologin.conf
rm tempautoLogin
sudo systemctl daemon-reload

#LogBanner "Enable vncserver"
# Need to run the vnc server under a real user or you get access issues; don't know why can't get the virtuald version to work
#mv /home/pi/vncserverpi.service /usr/lib/systemd/system
#systemctl enable vncserverpi
#/etc/vnc/vncservice start vncserver-virtuald

cd /home/pi

LogBanner "Run screen specific install code"
source pyenv/bin/activate
source installscreencode
deactivate

LogBanner "Completed screen specific install code"

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]; then
  LogBanner "Set Console to Start at Boot"
  sudo systemctl enable softconsole.service
else
  LogBanner "Set No Console Autostart at Boot"
fi

LogBanner "Add pi to root group"
sudo usermod -aG root pi

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
  sudo reboot now
  sleep 15

fi

LogBanner "Chose to manually reboot, reboot system to clean up install"
