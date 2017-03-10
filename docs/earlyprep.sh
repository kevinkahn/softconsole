#!/bin/bash
#
# Meant to be put on boot file system when SD card is created then moved and run from pi home dir
echo "Connect WiFI if needed"
read -p "Press any key to continue"
sudo passwd pi
echo "Expand File System and Set WiFi country"
read -p "Press any key to continue"
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
cd /home/pi
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/piprep.sh
chmod +x piprep.sh
sudo raspi-config
echo "Reboot now and then run piprep.sh as root"
echo " "