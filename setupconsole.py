import os
import pwd, grp
import githubutil as U
import subprocess

# Set up directories

if os.getegid() <> 0:
	# Not running as root
	print "Must run as root"
	exit(999)

print "*** Setupconsole ***"
piuid = pwd.getpwnam('pi')[2]
pigrp = grp.getgrnam('pi')[2]
for pdir in ('Console', 'consolestable', 'consolebeta', 'consolerem'):
	try:
		os.mkdir(pdir)
		print "Created: ", pdir
	except:
		print "Already present: ", pdir
	os.chown(pdir, piuid, pigrp)

if os.path.exists('homesystem'):
	# personal system
	U.StageVersion('consolestable', 'homerelease', 'InitialInstall')
	print "Stage homerelease as stable"
else:
	U.StageVersion('consolestable', 'currentrelease', 'InitialInstall')
	print "Stage standard stable release"
U.InstallStagedVersion('consolestable')
print "Installed staged stable"

U.StageVersion('consolebeta', 'currentbeta', 'InitialInstall')
print "Stage current beta release"
U.InstallStagedVersion('consolebeta')
print "Installed staged beta"

# TODO personal setup?
subprocess.call("cp -r /home/pi/consolestable/'example configs'/* /home/pi/Console", shell=True)
ans = ""
while not ans in ('y', 'Y', 'n', 'N'):
	ans = raw_input("Set up minimal example system?")
if ans in ('y', 'Y'):
	go = ""
	while not go in ('y', 'Y'):
		ISYIP = raw_input("ISY IP address: ")
		ISYUSER = raw_input("ISY user name: ")
		ISYPWD = raw_input("ISY password: ")
		exswitch = raw_input("Example switch to use (ISY name): ")
		print "IP:      ", ISYIP
		print "USER:    ", ISYUSER
		print "PASSWORD:", ISYPWD
		print "SWITCH:  ", "[[" + exswitch + "]]"
		go = raw_input("OK? (y/n)")
	with open('/home/pi/Console/cfglib/auth.cfg', "w") as f:
		cfg = ("ISYaddr = " + ISYIP,
			   "ISYuser = " + ISYUSER,
			   "ISYpassword = " + ISYPWD,
			   "WunderKey = xxx",
			   "\n")
		f.write("\n".join(cfg))
	with open('/home/pi/Console/config.txt', 'w') as f:
		cfg = ('cfglib = cfglib',
			   'include = auth.cfg, myclock.cfg',
			   'HomeScreenName = test',
			   'PersistTO = 30',
			   'DimLevel = 5',
			   'DimTO = 15',
			   'DimIdleListNames = MyClock,',
			   'DimIdleListTimes = 20,',
			   'MainChain = test, MyClock',
			   '[test]',
			   'type = Keypad',
			   'label = My, Test',
			   '[[' + exswitch + ']]',
			   "\n")
		f.write("\n".join(cfg))
