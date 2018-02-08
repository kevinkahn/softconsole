import subprocess, os

print('Setup systemd')
os.chmod('/home/pi/consolestable/runconsole.py', 0o555)
os.chmod('/home/pi/consolestable/console.py',0o555)
subprocess.call('cp -f /home/pi/consolestable/scripts/softconsole.service /usr/lib/systemd/system', shell=True)
subprocess.call('systemctl daemon-reload', shell=True)
