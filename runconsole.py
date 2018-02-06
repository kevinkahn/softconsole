#!/usr/bin/python -u

"""
This is run by systemd from any /home/pi/xxx where xxx contains a softconsole source.  It moves up a directory level
and selects the version of console to actually use.
For now it looks for a file usebeta to select the beta version.  If a file versionselector exists that is used instead after prefixing with "console".
This might make some testing scenarios easier
"""

import subprocess, os

os.chdir('..')
if os.path.isfile('usebeta'):
	# use the beta version
	versdir = 'consolebeta'
else:
	# use the stable version
	versdir = 'consolestable'

if os.path.isfile('versionselector'):
	with open('versionselector','r') as f:
		vers = f.readline()
	versdir = 'console' + vers

os.chdir(versdir)
print('Using directory: ',versdir)

consolepid = subprocess.Popen('console.py').pid

with open('../console.pid','w') as f:
	f.write(str(consolepid))

