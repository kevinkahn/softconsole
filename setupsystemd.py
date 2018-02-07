import subprocess, os

if not os.path.isfile('/usr/lib/systemd/system/softconsole.service'):
	# softconsole not yet using systemd so do the conversion
	pass
	# restore rc local
	# determine if autostart


print('Setup systemd')
os.chmod('runconsole.py', 0o555)
os.chmod('console.py',0o555)
subprocess.call('cp -f scripts/softconsole.service /usr/lib/systemd/system', shell=True)
subprocess.call('systemctl daemon-reload', shell=True)



# enable service, make sure versionselector exists and init it to stable
# todo add to upgrade the rc fixups if needed; if no service file previously force a pi reboot once?