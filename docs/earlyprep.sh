#!/bin/bash
#
# Meant to be put on boot file system when SD card is created then moved and run from pi home dir
#sudo passwd pi
#sudo raspi-config
echo "Make sure to set up network"
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
cd
wget https://raw.githubusercontent.com/kevinkahn/softconsole/master/docs/piprep.sh