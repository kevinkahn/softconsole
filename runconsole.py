#!/usr/bin/python3 -u

"""
This is run by systemd from /home/pi
and selects the version of console to actually use.
For now it looks for a file usebeta to select the beta version.  If a file versionselector exists that is used instead after prefixing with "console".
This might make some testing scenarios easier
"""

import os
import time
import subprocess
import signal

if os.path.isfile('versionselector'):
	with open('versionselector', 'r') as f:
		vers = f.readline().rstrip('\n')
	versdir = 'console' + vers
else:
	print('No Version Set!')
	exit(15)  # don't have systemd do a restart

print('Starting using directory: ' + versdir)
os.chdir(versdir)
if os.path.exists('../running'):
	os.remove('../running')

while True:
	consoleproc = subprocess.Popen(['python3', 'console.py'])
	consolepid = consoleproc.pid
	time.sleep(10)
	if os.path.exists('../running'):
		print('Console running with pid: {}'.format(consolepid))
		break
	print('Console start hung - retry')
	consoleproc.send_signal(signal.SIGINT)
	print('Semt signal')
	while consoleproc.poll() is None:
		print('Waiting termination')
		time.sleep(1)

with open('../console.pid', 'w') as f:
	f.write(str(consolepid))
