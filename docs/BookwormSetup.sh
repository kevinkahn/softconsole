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

LogBanner "Remember to do rpi-update first!"

DEBIAN_FRONTEND=noninteractive apt-get -y install python3-wget
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/getinstallinfo.py
LogBanner "Got getinstallinfo"
DEBIAN_FRONTEND=noninteractive apt-get -y install python3-full
LogBanner "Installed python3-full"
# make non-interactive
mkdir pyenv
mkdir .xdgdir
python -m venv /home/pi/pyenv
export PATH="/home/pi/pyenv/bin:$PATH"
pip install wget requests

python getinstallinfo.py
if [ $? -ne 0 ]; then
  echo "Exiting pisetup due to error in getinstallinfo"
  exit 1
fi

#TEMP!!!
cp /home/pi/consolebeta/scripts/softconsoleBW.service /usr/lib/systemd/system/softconsole.service
systemctl daemon-reload

DEBIAN_FRONTEND=noninteractive apt-get -y install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev libportmidi-dev libjpeg-dev python3-setuptools python3-dev python3-numpy
DEBIAN_FRONTEND=noninteractive apt-get -y install libegl-dev

LogBanner "Upgrade/Update System"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade

source installvals

LogBanner "Changing Node Name to: $NodeName"
mv -n /etc/hosts /etc/hosts.orig
sed s/raspberrypi/$NodeName/ /etc/hosts.orig >/etc/hosts
echo $NodeName >/etc/hostname
hostname $NodeName

LogBanner "Set Boot to Logged in CLI"
systemctl --quiet set-default multi-user.target
sed -i 's/^.*HandlePowerKey=.*$/#HandlePowerKey=poweroff/' /etc/systemd/logind.conf
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF
systemctl daemon-reload

#LogBanner "Set better LX Terminal parameters"
#sudo -u pi mkdir -p /home/pi/.config/lxterminal
#mv -f lxterminal.conf /home/pi/.config/lxterminal

#LogBanner "Enable vncserver"
# Need to run the vnc server under a real user or you get access issues; don't know why can't get the virtuald version to work
#mv /home/pi/vncserverpi.service /usr/lib/systemd/system
#systemctl enable vncserverpi
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
