#!/home/pi/pyenv/bin/python -u

"""
This is run by systemd from /home/pi
and selects the version of console to actually use.
For now it looks for a file usebeta to select the beta version.  If a file versionselector exists that is used instead after prefixing with "console".
This might make some testing scenarios easier
"""
import datetime
from multiprocessing import set_start_method

set_start_method("spawn")

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
runlog = open('RunLog', 'a')
print('Run attempt at {}'.format(datetime.datetime.now()), file=runlog)
os.chdir(versdir)
if os.path.exists('../running'):
	print('Clear running')
	os.remove('../running')
	if os.path.exists('../running'):
		print('Running flag?')

while True:
	print('Try to start {}'.format(os.path.exists('../running')))
	consoleproc = subprocess.Popen(['python3', 'console.py'])
	consolepid = consoleproc.pid
	print('Proc = {}'.format(consolepid))
	time.sleep(10)  # some pis need 10 seconds - most don't
	if os.path.exists('../running'):
		print('Console running with pid: {}'.format(consolepid))
		break
	print('Console start hung - retry')
	print('   Failed at {}'.format(datetime.datetime.now()), file=runlog)
	consoleproc.send_signal(signal.SIGKILL)
	print('Sent signal')
	exit(35)

with open('../console.pid', 'w') as f:
	f.write(str(consolepid))
print('   Success at {}'.format(datetime.datetime.now()), file=runlog)
