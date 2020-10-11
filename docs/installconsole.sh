#!/bin/bash

# MUST BE RUN as root:  sudo installconsole.sh

# This script should take a with a TFT display and install the softconsole.
# It installs needed python packages and downgrades the sdllib to the stable Wheezy version for the
# touchscreen to work since sdllibn 2 breaks pygame.

function Get_yn() {
  # params: var, prompt
  read -p "$2 " resp
  case $resp in
  "Y" | "y")
    resp="Y"
    ;;
  "N" | "n")
    resp="N"
    ;;
  *) ;;

  esac
  eval $1="'$resp'"
}

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

# script can take 3 parameters to preanswer Personal and AutoConsole and beta
# this supports autorunning at reboot
SkipVerify=Y
if [ -n "$1" ]; then
  Personal=$1
else
  Get_yn Personal "Is this the developer personal system (Y/N) (risky to say Y if it not)?"
  SkipVerify=N
fi
if [ -n "$2" ]; then
  AutoConsole=$2
else
  Get_yn AutoConsole "Autostart console (Y/N)?"
  SkipVerify=N
fi

if [ -n "$3" ]; then
  InstallBeta=$3
else
  Get_yn InstallBeta "Download beta also? (Y/N)?"
  SkipVerify=N
fi

echo "-Developer system:           $Personal"
echo "-Auto start Console on boot: $AutoConsole"
echo "-Download beta:  $InstallBeta"

Go='N'
if [ "$SkipVerify" != "Y" ]; then
  Get_yn Go "Proceed?"
  if [ "$Go" != "Y" ]; then
    exit 1
  fi
fi
echo Start >/home/pi/prep.log
date >>/home/pi/prep.log
echo "Developer system:           $Personal" >>/home/pi/prep.log
echo "Auto start Console on boot: $AutoConsole" >>/home/pi/prep.log
echo "Download beta:  $InstallBeta" >>/home/pi/prep.log
exec > >(tee -a /home/pi/prep.log)
exec 2>&1

#echo stable > versionselector

echo 1 >/proc/sys/vm/drop_caches # try to avoid kswap problem

# Install the python packages needed for the console

LogBanner "Install stuff for console"

cd /home/pi/
LogBanner "Console Installation"
if [ $Personal == "Y" ]; then
  echo Get homerelease version of setupconsole and githubutil
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/setupconsole.py
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/githubutil.py
else
  echo Get currentrelease version of setupconsole and githubutil
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/setupconsole.py
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/githubutil.py
fi
if [ $InstallBeta == "Y" ]; then
  mv setupconsole.py consoleinstallleftovers/stable-setupconsole.py
  mv githubutil.py consoleinstallleftovers/stable-githubutil.py
  echo Get currentbeta version of setupconsole and githubutil
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentbeta/setupconsole.py
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentbeta/githubutil.py
fi

python -u setupconsole.py $InstallBeta

# in case this is a development system
#cp consolestable/scripts/python-sudo.sh .
#chmod a+x python-sudo.sh

if [ -e Consoleauth ]; then
  mv -f Consoleauth Console/cfglib/auth.cfg
fi
if [ -e ConsoleMinEx ]; then
  mv -f ConsoleMinEx Console/config.txt
fi

rm setupconsole.* githubutil.*

# set Console to start automatically at boot
if [ "$AutoConsole" == "Y" ]; then
  LogBanner "Set Console to Start at Boot"
  systemctl enable softconsole.service
else
  LogBanner "Set No Console Autostart at Boot"
fi

if [ -e /boot/auth ]; then
  mkdir /home/pi/Console/local
  mv -f /boot/auth/* /home/pi/Console/local
  rmdir /boot/auth
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
