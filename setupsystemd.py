import subprocess, os

print('Setup systemd')
os.chmod('runconsole.py', 0o555)
os.chmod('console.py',0o555)
subprocess.call('cp -f scripts/softconsole.service /usr/lib/systemd/system', shell=True)
subprocess.call('systemctl daemon-reload', shell=True)
