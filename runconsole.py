#!/usr/bin/python3 -u

"""
This is run by systemd from /home/pi
and selects the version of console to actually use.
For now it looks for a file usebeta to select the beta version.  If a file versionselector exists that is used instead after prefixing with "console".
This might make some testing scenarios easier
"""

import os
import subprocess

if os.path.isfile('usebeta'):
	# use the beta version
	versdir = 'consolebeta'
else:
	# use the stable version
	versdir = 'consolestable'

if os.path.isfile('versionselector'):
	with open('versionselector', 'r') as f:
		vers = f.readline().rstrip('\n')
	versdir = 'console' + vers

print('Starting using directory: ' + versdir)
os.chdir(versdir)

consolepid = subprocess.Popen(['python3', 'console.py']).pid

with open('../console.pid', 'w') as f:
	f.write(str(consolepid))
