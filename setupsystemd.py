import subprocess, os

print('Setup systemd')
# the following odd code handles getting the right source directory whether running from within it or from a
# subdirectory like previousversion during updates.  When running in initial install we are in the directory whereas
# when doing an update we are down a directory
targetdir = '/' + '/'.join(os.getcwd().split('/')[1:4])
print('Dir: ' + targetdir)
os.chmod(targetdir + '/runconsole.py', 0o555)
os.chmod(targetdir + '/console.py',0o555)
# noinspection PyBroadException
try:
	os.mkdir('/usr/lib/systemd/system')
	# make it in case it isn't already there
except:
	pass
subprocess.call('cp -f ' + targetdir + '/scripts/softconsole.service /usr/lib/systemd/system', shell=True)
subprocess.call('systemctl daemon-reload', shell=True)
