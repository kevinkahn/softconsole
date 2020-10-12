import grp
import os
import pwd
import subprocess
import sys

import githubutil as U

downloadbeta = 'N'
if len(sys.argv) == 2:
	downloadbeta = sys.argv[1]
# Set up directories

if os.getegid() != 0:
	# Not running as root
	print("Must run as root")
	exit(999)

print("*** Setupconsole ***")
piuid = pwd.getpwnam('pi')[2]
pigrp = grp.getgrnam('pi')[2]
for pdir in ('Console', 'consolestable', 'consolebeta', 'consolerem', 'consoledev', 'Console/cfglib'):
	# noinspection PyBroadException
	try:
		os.mkdir(pdir)
		print("Created: " + str(pdir))
	except:
		print("Already present: " + str(pdir))
	os.chown(pdir, piuid, pigrp)

if os.path.exists('homesystem'):
	# personal system
	U.StageVersion('consolestable', 'homerelease', 'Initial Install')
	print("Stage homerelease as stable")
else:
	U.StageVersion('consolestable', 'currentrelease', 'Initial Install')
	print("Stage standard stable release")
U.InstallStagedVersion('consolestable')
print("Installed staged stable")

if downloadbeta == 'Y':
	U.StageVersion('consolebeta', 'currentbeta', 'Initial Install')
	print('Stage beta also')
	U.InstallStagedVersion('consolebeta')
	print('Intalled staged beta')

if os.path.exists('homesystem'):
	os.mkdir('consolecur')
	os.chown('consolecur', piuid, pigrp)

subprocess.call("cp -r /home/pi/consolestable/'example configs'/* /home/pi/Console", shell=True)
