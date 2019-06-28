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
function InList()
{
  [[ $1 =~ (^|[[:space:]])$2($|[[:space:]]) ]] && return 1 || return 0
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


if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
  exit
fi

exec > >(tee -a /home/pi/earlyprep.log)
exec 2>&1

cd /home/pi
LogBanner "This is the system setup script"
LogBanner "Connect WiFI if needed"
read -p "Press Enter to continue"

LogBanner "Upgrade/Update System"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade

LogBanner "Install Python2/3 Compatibility Support"
echo "Note - installation switches system default Python to version 3"
echo "To undo this run 'sudo update-alternatives --config python' to select desired alternative"

LogBanner "Switch default Python to Python3"
update-alternatives --install /usr/bin/python python /usr/bin/python3 2
update-alternatives --install /usr/bin/python python /usr/bin/python2 1
update-alternatives --set python /usr/bin/python3

LogBanner "Python Compatibility Lib"

pip install future

echo "deb http://mirrordirector.raspbian.org/raspbian/ stretch main contrib non-free rpi firmware" >> /etc/apt/sources.list.d/raspi.list

LogBanner "Set Time Zone"
dpkg-reconfigure tzdata
LogBanner "Pi User Password"
sudo passwd pi

Get_val NodeName "What name for this system?"
Get_yn VNCstdPort "Install VNC on standard port (Y/N/alt port number)?"
Get_yn Personal "Is this the developer personal system (Y/N) (bit risky to say Y if it not)?"
Get_yn InstallBeta "Download current beta as well as stable? (usually waste of time)"
Get_yn AutoConsole "Autostart console (Y/N)?"

Get_yn InstallScreen Do you want to install a known screen (Alternative is to install any screen drivers yourself)?
if [ "$InstallScreen" == "Y" ]
    Screens="28r 28c 35r pi7"
    ScreenType="--"

    until [ $ScreenType != "--" ]
    do
      Get_val ScreenType "What type screen($Screens)?"
      InList "$Screens" "$ScreenType"
      if [ $? -ne 1 ]
      then
        echo Not a valid screen type
        ScreenType="--"
      fi
    done
    if [ $ScreenType == 'pi7' ]
    then
      Get_yn Flip7 "Flip 7 inch screen so power at top? (Y/N)"
    fi
else
    Get_val ScreenType "What is your screen type?"
fi


Get_yn Reboot "Automatically reboot to continue install after system setup?"

if [ "$Personal" == "Y" ]
then
  echo Get homerelease versions of setup scripts
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/getsetupinfo.py
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/scripts/vncserverpi.service
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/scripts/lxterminal.conf
else
  # NOTE to test with current master version from github replace "currentrelease" with 'master'
  echo Get currentrelease version of setup scripts
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/getsetupinfo.py
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/scripts/vncserverpi.service
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/scripts/lxterminal.conf
# fix issue in adafruit install script as of 3/31/2018
fi

chmod +x installconsole.sh
chown pi:pi lxterminal.conf

python getsetupinfo.py

Get_yn Go "Proceed?"
if [ "$Go" != "Y" ]
then
  exit 1
fi


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

LogBanner "Run raspi-config if you need non-US wifi, non-US keyboard, or other specials"

LogBanner "Turn on ssh"
touch /boot/ssh # turn on ssh

LogBanner "Changing Node Name to: $NodeName"
mv -n /etc/hosts /etc/hosts.orig
sed s/raspberrypi/$NodeName/ /etc/hosts.orig > /etc/hosts
echo $NodeName > /etc/hostname
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
    sed "/Port /s/.*/Port $SSHDport/" /etc/ssh/sshd_config.sav > /etc/ssh/sshd_config
    echo "RfbPort=$VNCstdPort" >> /home/pi/.vnc/config.d/Xvnc
    chown pi:pi /home/pi/.vnc/config.d/Xvnc
    ;;
esac
LogBanner "Setup Virtual VNC Service"

if [ $VNCstdPort == "N" ]
then
    echo "VNC service file installation skipped"
else
    echo "VNC service file installed"
    mv /home/pi/vncserverpi.service /usr/lib/systemd/system
fi

# Save initial rc.local to restore after helper scripts run
cp /etc/rc.local /etc/rc.local.hold # helper script below screws up rc.local

cd /home/pi

wget https://raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-touch-cal
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/adafruit-pitft.sh
chmod +x adafruit-pitft-touch-cal adafruit-pitft.sh
UseWheezy='N'

echo $ScreenType > .Screentype
case $ScreenType in
  28r|28c|35r)
  case $ScreenType in
    28r)
    LogBanner "Run PiTFT Helper 28r"
    echo 1 > tmp
    echo 4 >> tmp # rotation
    echo Y >> tmp # pi console to pitft
    echo N >> tmp # don't reboot
    ;;
    28c)
    LogBanner "Run PiTFT Helper 28c"
    echo 3 > tmp
    echo 2 >> tmp # rotation
    echo Y >> tmp # pi console to pitft
    echo N >> tmp # don't reboot
    ;;
    35r)
    LogBanner "Run PiTFT Helper 35r"
    echo 4 > tmp
    echo 4 >> tmp # rotation
    echo Y >> tmp # pi console to pitft
    echo N >> tmp # don't reboot
    ;;
    esac

  ./adafruit-pitft.sh < tmp
  raspi-config nonint do_boot_behaviour B4 # set boot to desktop already logged in
  sed -isav s/fb0/fb1/ /usr/share/X11/xorg.conf.d/99-fbturbo.conf
  ;;
  pi7)
    LogBanner "7 Inch Pi Screen"
    if [ $Flip7 == 'Y' ]
    then
        echo "lcd_rotate=2" >> /boot/config.txt
    fi
    ;;
  wave35)
    LogBanner "Install Waveshare screen"
    echo "Following link as of 8//30/18"
    wget https://www.waveshare.com/w/upload/3/34/LCD-show-180331.tar.gz
    tar xvf LCD-show-*.tar.gz
    cd LCD-show 90
    chmod +x LCD35-show
    sed -i 's/sudo reboot/echo skip sudo reboot/' "LCD35-show"
    ./LCD35-show 90
    cd ..

    echo "Update pointercal"
    cat > /etc/pointercal <<EOF
5729 138 -1857350 78 8574 -2707152 65536
EOF

# 5672 -28 -1130318 -203 8466 -1835732 65536

    echo "Finished waveshare install"
    ;;
  *)
    LogBanner "User installed screen"
    echo Screen type: $ScreenType
    ;;
esac

mv --backup=numbered /etc/rc.local.hold /etc/rc.local
chmod +x /etc/rc.local
#echo "# Dummy entry to keep this file from being recreated in Stretch" > /usr/share/X11/xorg.conf.d/99-fbturbo.conf
#cat /usr/share/X11/xorg.conf.d/99-fbturbo.conf

LogBanner "Reboot now installconsole.sh will autorun as root unless aborted"
echo "Install will set Personal $Personal and AutoConsole $AutoConsole"

if [ "$Reboot" == "Y" ]
then

    LogBanner "Rebooting in 10 seconds"
    for i in 10 9 8 7 6 5 4 3 2 1
    do
      echo Rebooting $i
      sleep 1
    done
    echo "Reboot . . ."
    cd /home/pi
    mv .bashrc .bashrc.real
    cat > .bashrc << EOF
cd /home/pi
source .bashrc.real
cp .bashrc .bashrc.sav
mv -f .bashrc.real .bashrc
touch /home/pi/CONSOLEINSTALLRUNNING
sleep 15 # delay to allow X system to startup for next command (is this long enough in a Pi0)
#DISPLAY=:0.0 x-terminal-emulator -t "Console Install" --geometry=40x17 -e sudo bash /home/pi/doinstall.sh 2>> /home/pi/di.log
sudo bash /home/pi/doinstall.sh 2>> /home/pi/di.log
EOF
    cat > doinstall.sh << EOF
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