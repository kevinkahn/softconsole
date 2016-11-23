import os
import subprocess
import sys
import time

import config
from logsupport import ConsoleWarning
from maintscreen import Exit_Options


def dorealexit(K, YesKey, presstype):
	ExitKey = K.name
	if ExitKey == 'shut':
		Exit_Options("Manual Shutdown Requested", "Shutting Down")
	elif ExitKey == 'restart':
		Exit_Options("Console Restart Requested", "Restarting")
	elif ExitKey == 'shutpi':
		Exit_Options("Shutdown Pi Requested", "Shutting Down Pi")
	elif ExitKey == 'reboot':
		Exit_Options("Reboot Pi Requested", "Rebooting Pi")

	os.chdir(config.exdir)  # set cwd to be correct when dirs move underneath us so that scripts execute

	subprocess.Popen('nohup sudo /bin/bash -e scripts/consoleexit ' + ExitKey + ' ' + config.configfile + ' user',
					 shell=True)
	config.Ending = True
	sys.exit(0)


def errorexit(opt):
	if opt == 'restart':
		Exit_Options('Error restart', 'Error - Restarting')
	elif opt == 'reboot':
		consoleup = time.time() - config.starttime
		config.Logs.Log("Console was up: ", str(consoleup), severity=ConsoleWarning)
		print 'Up: ' + str(consoleup)
		if consoleup < 120:
			# never allow console to reboot the pi sooner than 120 seconds
			Exit_Options('Error Reboot Loop', 'Suppressed Reboot')
			opt = 'shut'  # just close the console - we are in a reboot loop
		else:
			Exit_Options('Error reboot', 'Error - Rebooting Pi')
	elif opt == 'shut':
		Exit_Options('Error Shutdown', 'Error Check Log')
	print opt

	os.chdir(config.exdir)  # set cwd to be correct when dirs move underneath us so that scripts execute

	subprocess.Popen('nohup sudo /bin/bash -e scripts/consoleexit ' + opt + ' ' + config.configfile + ' ' + ' error',
					 shell=True)
	config.Ending = True
	sys.exit(1)
