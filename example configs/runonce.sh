cp /etc/fstab /etc/fstab.sav
sed /utf8,ro/s/,ro/,x-systemd.automount,ro/ /etc/fstab >/etc/fstab.new
cp /etc/fstab.new /etc/fstab
rm /etc/fstab.new
