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


#**************ROUTINES ADAPTED FROM RE4SON PITFT SETUP***************
# Specific to wave35 at this point
function info(){
    echo $2
}

function update_xorg_for_waveshare() {
    mkdir -p /etc/X11/xorg.conf.d

    cat > /etc/X11/xorg.conf.d/99-fbdev.conf <<EOF
Section "Device"
  Identifier "myfb"
  Driver "fbdev"
  Option "fbdev" "/dev/fb1"
EndSection
EOF
# for portrait screen from a run of xinput_calibrator on waveshare35 screen
    cat > /etc/X11/xorg.conf.d/99-calibration.conf <<EOF
Section "InputClass"
         Identifier "calibration"
         MatchProduct "ADS7846 Touchscreen"
         Option "SwapAxes" "0"
         Option "Calibration" "1155 1227 1408 1463"
EndSection
EOF

}

function update_x11profile_for_waveshare() {
    fbturbo_path="/usr/share/X11/xorg.conf.d/99-fbturbo.conf"
    if [ -e $fbturbo_path ]; then
        echo "Moving ${fbturbo_path} to ${target_homedir}"
        mv "$fbturbo_path" "$target_homedir"
    fi

    if grep -xq "export FRAMEBUFFER=/dev/fb1" "${target_homedir}/.profile"; then
        echo "Already had 'export FRAMEBUFFER=/dev/fb1'"
    else
        echo "Adding 'export FRAMEBUFFER=/dev/fb1'"
        date=`date`
        cat >> "${target_homedir}/.profile" <<EOF
# --- added by re4son-pi-tft-setup $date ---
export FRAMEBUFFER=/dev/fb1
# --- end re4son-pi-tft-setup $date ---
EOF
    fi
}

function update_udev_for_waveshare() {
   cat > /etc/udev/rules.d/95-ADS7846.rules <<EOF
SUBSYSTEM=="input", ATTRS{name}=="ADS7846 Touchscreen", ENV{DEVNAME}=="*event*", SYMLINK+="input/touchscreen"
EOF
}

function install_console_for_waveshare() {
    if ! grep -q 'fbcon=map:10 fbcon=font:VGA8x8' /boot/cmdline.txt; then
        info PI-TFT "Updating /boot/cmdline.txt"
        sed -i 's/rootwait/rootwait fbcon=map:10 fbcon=font:VGA8x8/g' "/boot/cmdline.txt"
    else
        info PI-TFT "/boot/cmdline.txt already updated"
    fi
    if [ ! -f /etc/kbd/config ]; then
        info PI-TFT "Creating /etc/kbd/config"
        mkdir -p /etc/kbd
        touch /etc/kbd/config
    fi
    sed -i 's/BLANK_TIME=.*/BLANK_TIME=0/g' "/etc/kbd/config"
}

function install_xserver_xorg_input_evdev_for_waveshare {
## Debian releases after early 2017 break touch input - this will fix it
    set +e
    info PI-TFT "Checking for xserver-xorg-input-evdev:"
    PKG_STATUS=$(dpkg-query -W --showformat='${Status}\n' xserver-xorg-input-evdev|grep "install ok installed")
    if [ "" == "$PKG_STATUS" ]; then
        info PI-TFT "**** Installing xserver-xorg-input-evdev package ****"
        info PI-TFT "No xserver-xorg-input-evdev. Installing it now."
        apt update
        apt install -y xserver-xorg-input-evdev
    fi
    if [ ! -f /usr/share/X11/xorg.conf.d/45-evdev.conf ]; then
            info PI-TFT "Creating /usr/share/X11/xorg.conf.d/45-evdev.conf"
            ln -s /usr/share/X11/xorg.conf.d/10-evdev.conf /usr/share/X11/xorg.conf.d/45-evdev.conf
    fi
    info PI-TFT "**** xserver-xorg-input-evdev package installed ****"
    set -e
}

#************** END ROUTINES ADAPTED FROM RE4SON PITFT SETUP***************



if [[ "$EUID" -ne 0 ]]
then
  echo "Must be run as root"
  exit
fi

cd /home/pi
LogBanner "This is the system setup script"
LogBanner "Connect WiFI if needed"
read -p "Press Enter to continue"
LogBanner "Install Python2/3 Compatibility Support"
echo "Note - installation switches system default Python to version 3"
echo "To undo this run 'sudo update-alternatives --config python' to select desired alternative"
LogBanner "Switch default Python to Python3"
update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2
update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
LogBanner "python3-pip"
apt-get install python3-pip -y

LogBanner "python3-pygame"
apt-get update
apt-get install python3-pygame -y
pip3 install future
pip3 install requests

echo "deb http://mirrordirector.raspbian.org/raspbian/ stretch main contrib non-free rpi firmware" >> /etc/apt/sources.list.d/raspi.list

LogBanner "Set Time Zone"
dpkg-reconfigure tzdata
LogBanner "Pi User Password"
sudo passwd pi

Get_val NodeName "What name for this system?"
Get_yn VNCstdPort "Install access on standard port (Y/N/alt port number)?"
Get_yn Personal "Is this the developer personal system (Y/N) (bit risky to say Y if it not)?"
Get_yn AutoConsole "Autostart console (Y/N)?"

Screens="28r 28c 35r wave35 custom pi7"
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

#Get_yn CON "Would you like the console to appear on the PiTFT display?"
#Get_yn Reboot "Automatically reboot to continue install after system setup?"
Reboot="N"

if [ "$Personal" == "Y" ]
then
  echo Get homerelease versions of setup scripts
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/homerelease/getsetupinfo.py
  chmod +x installconsole.sh
else
  # NOTE to test with current master version from github replace "currentrelease" with 'master'
  echo Get currentrelease version of setup scripts
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/docs/installconsole.sh
  wget https://raw.githubusercontent.com/kevinkahn/softconsole/currentrelease/getsetupinfo.py
  chmod +x installconsole.sh
# fix issue in adafruit install script as of 3/31/2018
fi

python getsetupinfo.py
update-alternatives --set python /usr/bin/python2.7

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

exec > >(tee -a /home/pi/earlyprep.log)
exec 2>&1


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

case $VNCstdPort in # if [ $VNCstdPort != "Y" ]
  Y)
    echo "SSH will be set up on its normal port"
    ;;
  N)
    echo "No VNC will ne set up"
    ;;
  *)
    LogBanner "VNC Service Password"
    SSHDport=$(($VNCstdPort - 100))
    echo "sshd will be moved to port " $SSHDport
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.sav
    sed "/Port /s/.*/Port $SSHDport/" /etc/ssh/sshd_config.sav > /etc/ssh/sshd_config
    ;;
esac

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
    ;;
    28c)
    LogBanner "Run PiTFT Helper 28c"
    echo 3 > tmp
    echo 2 >> tmp # rotation
    echo Y >> tmp # pi console to pitft
    ;;
    35r)
    LogBanner "Run PiTFT Helper 35r"
    echo 4 > tmp
    echo 4 >> tmp # rotation
    echo Y >> tmp # pi console to pitft
    ;;
    esac

  ./adafruit-pitft.sh < tmp
  #raspi-config nonint do_boot_behaviour B4 # set boot to desktop already logged in
  #sed -isav s/fb0/fb1/ /usr/share/X11/xorg.conf.d/99-fbturbo.conf
  ;;
  custom)
    LogBanner "No Screen Configured - do it manually for custom screen before reboot"
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
    echo "Get the screen driver and move to /boot/overlays"
    wget raw.githubusercontent.com/kevinkahn/softconsole/master/screensupport/waveshare35a-overlay.dtb
    mv waveshare35a-overlay.dtb /boot/overlays/waveshare35a.dtbo
    chmod 755 /boot/overlays/waveshare35a.dtbo
    UseWheezy='Y'
    echo "Edit /boot/config.txt"
    cat >> /boot/config.txt <<EOF

# --- added by softconsole setup $date ---
dtparam=spi=on
dtparam=i2c1=on
dtparam=i2c_arm=on
dtoverlay=waveshare35a,rotate=0
###########################################
####  Overclocking the micro sdcard    ####
#### Uncomment  84 for Raspberry Pi 2  ####
# dtparam=sd_overclock=84
#### Uncomment 100 for Raspberry Pi 3  ####
# dtparam=sd_overclock=100
###########################################
# --- end softconsole setup $date ---
EOF

    echo "Update xorg"
    update_xorg_for_waveshare
    echo "Update X11 Profile"
    update_x11profile_for_waveshare
    echo "Update udev"
    update_udev_for_waveshare
    echo "Update pointercal"
    cat > /etc/pointercal <<EOF
5729 138 -1857350 78 8574 -2707152 65536
EOF

    #if $CON
    #  then
    #    echo "Updating console to PiTFT..."
    #    install_console_for_waveshare
    #  fi
    echo "Install xserver xorg input evdev"
    install_xserver_xorg_input_evdev_for_waveshare
    echo "Finished waveshare install"
    ;;
  *)
    LogBanner "Screen Selection Error!!!"
    exit 99
    ;;
esac

LogBanner "Install Fonts, SDL"
apt-get install fonts-noto -y
apt-get install fontconfig -y
apt-get install libsdl1.2-dev -y
apt-get install libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev libsdl2-mixer-dev -y

update-alternatives --set python /usr/bin/python3.5

mv --backup=numbered /etc/rc.local.hold /etc/rc.local
chmod +x /etc/rc.local
#echo "# Dummy entry to keep this file from being recreated in Stretch" > /usr/share/X11/xorg.conf.d/99-fbturbo.conf
#cat /usr/share/X11/xorg.conf.d/99-fbturbo.conf

LogBanner "Reboot now installconsole.sh will autorun as root unless aborted"
echo "Run Install with Personal $Personal and AutoConsole $AutoConsole"


LogBanner "Manually reboot and run installconsole.sh"