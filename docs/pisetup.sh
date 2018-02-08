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
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/installconsole.sh
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/installconsoleSDL.sh
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/getsetupinfo.py
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/scripts/vncserverpi.service
chmod +x installconsole.sh

LogBanner "Set Time Zone"
# seed the timezone dialog
echo 'US/Pacific-New' > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
dpkg-reconfigure tzdata
LogBanner "Pi User Password"
sudo passwd pi
LogBanner "VNC Service Password"
vncpasswd -service
Get_val NodeName "What name for this system?"
Get_yn VNCstdPort "Install VNC/ssh on standard port (Y/N)?"
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
Get_yn Reboot "Automatically reboot to continue install after system setup?"
python getsetupinfo.py

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



echo "Authentication=VncAuth" >> /root/.vnc/config.d/vncserver-x11
echo "Encryption=PreferOff" >> /root/.vnc/config.d/vncserver-x11
su pi -c vncserver # create the Xvnc file in ~pi/.vnc/config.d so it can be modified below; until reboot vnc on 5900
if [ $VNCstdPort != "Y" ]
then
  SSHDport=$(($VNCstdPort - 100))
  VNCConsole=$(($VNCstdPort - 1))
  echo "Console VNC will be set up on port " $VNCConsole
  echo "Virtual VNC will be set up on port " $VNCstdPort
  echo "sshd will be moved to port " $SSHDport
  cp /etc/ssh/sshd_config /etc/ssh/sshd_config.sav
  sed "/Port /s/.*/Port $SSHDport/" /etc/ssh/sshd_config.sav > /etc/ssh/sshd_config
  echo "RfbPort=$VNCstdPort" >> /home/pi/.vnc/config.d/Xvnc
  chown pi /home/pi/.vnc/config.d/Xvnc
  echo "RfbPort=$VNCConsole" >> /root/.vnc/config.d/vncserver-x11
else
  echo "VNC will be set up on its normal port"
fi
LogBanner "Setup Virtual VNC Service"

mv /home/pi/vncserverpi.service /usr/lib/systemd/system
systemctl enable vncserverpi.service
systemctl enable vncserver-x11-serviced.service
systemctl start vncserver-x11-serviced.service

# Save initial rc.local to restore after helper scripts run
cp /etc/rc.local /etc/rc.local.hold # helper script below screws up rc.local

if [ "$InstallOVPN" == "Y" ]
then
  LogBanner "Install OpenVPN"
  apt-get -y install openvpn
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
fi

cd /home/pi

wget raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-touch-cal
wget raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-helper
wget https://raw.githubusercontent.com/adafruit/Adafruit-PiTFT-Helper/master/adafruit-pitft-helper2.sh
chmod +x adafruit-pitft-helper2.sh
chmod +x adafruit-pitft-touch-cal adafruit-pitft-helper

echo $ScreenType > .Screentype
case $ScreenType in
  28r|28c|35r)
  case $ScreenType in
    28r)
    LogBanner "Run PiTFT Helper 28r"
    echo 1 > tmp
    ;;
    28c)
    LogBanner "Run PiTFT Helper 28c"
    echo 3 > tmp
    ;;
    35r)
    LogBanner "Run PiTFT Helper 35r"
    echo 4 > tmp
    ;;
    esac
  cat >> tmp <<EOF
4
N
N
EOF
  ./adafruit-pitft-helper2.sh < tmp
  raspi-config nonint do_boot_behaviour B4 # set boot to desktop already logged in
  cp installconsoleSDL.sh installconsole.sh
  sed -isav s/fb0/fb1/ /usr/share/X11/xorg.conf.d/99-fbturbo.conf
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
    cp installconsoleSDL.sh installconsole.sh
    ;;
  wave35)
    LogBanner "Install Waveshare screen"
    echo "Get the screen driver and move to /boot/overlays"
    wget raw.githubusercontent.com/kevinkahn/softconsole/master/screensupport/waveshare35a-overlay.dtb
    mv waveshare35a-overlay.dtb /boot/overlays/waveshare35a.dtbo
    chmod 755 /boot/overlays/waveshare35a.dtbo
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
sleep 15 # delay to allow X system to startup for next command (is this long enough in a Pi0)
DISPLAY=:0.0 x-terminal-emulator -t "Console Install" --geometry=40x17 -e sudo bash /home/pi/doinstall.sh 2>> /home/pi/di.log
EOF
    cat > doinstall.sh << EOF
echo Autorunning console install in 10 second - ctl-c to stop
for i in 10 9 8 7 6 5 4 3 2 1
    do
      echo installconsole.sh start in \$i
      sleep 1
    done
sudo bash ./installconsole.sh $Personal $AutoConsole
EOF
    reboot now
fi
LogBanner "Chose to manually reboot and run installconsole.sh"