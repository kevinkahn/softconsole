import os
import pwd, grp
import githubutil as U
import subprocess

# Set up directories

if os.getegid() != 0:
	# Not running as root
	print("Must run as root")
	exit(999)

print("*** Setupconsole ***")
piuid = pwd.getpwnam('pi')[2]
pigrp = grp.getgrnam('pi')[2]
for pdir in ('Console', 'consolestable', 'consolebeta', 'consolerem'):
	# noinspection PyBroadException
	try:
		os.mkdir(pdir)
		print("Created: "+ str(pdir))
	except:
		print("Already present: "+ str(pdir))
	os.chown(pdir, piuid, pigrp)

if os.path.exists('homesystem'):
	# personal system
	U.StageVersion('consolestable', 'homerelease', 'InitialInstall')
	print("Stage homerelease as stable")
else:
	U.StageVersion('consolestable', 'currentrelease', 'InitialInstall')
	print("Stage standard stable release")
U.InstallStagedVersion('consolestable')
print("Installed staged stable")

# U.StageVersion('consolebeta', 'currentbeta', 'InitialInstall')
# print("Stage current beta release")
# U.InstallStagedVersion('consolebeta')
# print("Installed staged beta")

if os.path.exists('homesystem'):
	os.mkdir('consolecur')
	os.chown('consolecur', piuid, pigrp)
# U.StageVersion('consolecur', 'currenttest', 'InitialInstall')
# print("Stage test version")
# U.InstallStagedVersion('consolecur')
# print("Installed test version")
# U.StageVersion('consolerem', '*live*', 'InitialInstall')
# print("Stage live development version")
# U.InstallStagedVersion('consolerem')
#print("Installed live development version")


subprocess.call("cp -r /home/pi/consolestable/'example configs'/* /home/pi/Console", shell=True)
