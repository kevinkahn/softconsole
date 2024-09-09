import signal
import subprocess
import sys
from datetime import datetime

import config
from guicore.screencallmanager import pg

import historybuffer
import logsupport
from utils import timers, fonts, displayupdate, hw
from logsupport import ConsoleError
from utils.utilfuncs import *

# Exit Codes:
# 1x: shutdown console (don't restart in systemd or script)
# 2x: shutdown pi (issue shutdown - systemd won't be involved)
# 3x: restart console (restart via systemd or via script)
# 4x: reboot pi (issue restart of pi - systemd won't be involved)

EARLYABORT = 11
MAINTEXIT = 12
ERRORDIE = 13
REMOTEEXIT = 14

MAINTPISHUT = 21
REMOTEPISHUT = 22

MAINTRESTART = 31
AUTORESTART = 32
REMOTERESTART = 33
ERRORRESTART = 34
EXTERNALSIGTERM = 35  # from systemd on a stop or restart so could be either
WATCHDOGTERM = 36
EXTERNALSIGINT = 37

MAINTPIREBOOT = 41
REMOTEPIREBOOT = 42
ERRORPIREBOOT = 43


def listthreads(lines):
	return ' ,'.join([i.name for i in lines])


reasonmap = {signal.SIGTERM: ('termination signal', EXTERNALSIGTERM),
			 signal.SIGINT: ('interrupt signal', EXTERNALSIGINT),
			 signal.SIGUSR1: ('watchdog termination', WATCHDOGTERM)}


def exitlogging():
	safeprint('----------------- Exit Logging')

	# logsupport.Logs.Log("Exittime threads: {}".format(listthreads(threading.enumerate())))
	# if config.hooks.exit_code not in (
	if config.ecode not in (
			EARLYABORT, MAINTEXIT, MAINTPISHUT, REMOTEPISHUT, MAINTRESTART, AUTORESTART, REMOTERESTART, EXTERNALSIGTERM,
			MAINTPIREBOOT, REMOTEPIREBOOT):
		# logsupport.Logs.Log("Exiting with history trace (", repr(config.ecode), ')')
		historybuffer.DumpAll('Exit Trace', time.strftime('%m-%d-%y %H:%M:%S'))
	# else:
	#logsupport.Logs.Log("Exiting without history trace")
	time.sleep(1)  # let messages get out
	logsupport.LoggerQueue.put((logsupport.Command.CloseHlog, 'Exit Logging'))


def EarlyAbort(scrnmsg, screen=True):
	if screen and hw.screen is not None:
		hw.screen.fill(wc("red"))
		# this font is manually loaded into the fontcache to avoid log message on early abort before log is up
		# see fonts.py
		hw.GoBright(100)
		r = fonts.fonts.Font(40, '', True, True).render(scrnmsg, 0, wc("white"))
		hw.screen.blit(r, ((hw.screenwidth - r.get_width()) / 2, hw.screenheight * .4))
		displayupdate.updatedisplay()
	safeprint(scrnmsg)
	time.sleep(10)
	logsupport.Logs.livelog = False
	timers.ShutTimers(scrnmsg)
	pg.quit()
	# noinspection PyProtectedMember
	hw.CleanUp()
	sys.exit(EARLYABORT)


def Exit(ecode, immediate=False):
	consoleup = time.time() - config.sysStore.ConsoleStartTime
	logsupport.Logs.Log("Console was up: ", interval_str(consoleup))
	with open("{}/.RelLog".format(config.sysStore.HomeDir), "a") as f:
		print(
			f"  --->  At {datetime.fromtimestamp(config.sysStore.ConsoleStartTime).strftime('%c')}"
			f" Exit code {ecode} was up {interval_str(consoleup)}", file=f)
	os.chdir(config.sysStore.ExecDir)  # set cwd to be correct when dirs move underneath us so that scripts execute
	logsupport.Logs.Log("Console Exiting - Ecode: " + str(ecode))
	if config.sysStore.Watchdog_pid != 0:
		os.kill(config.sysStore.Watchdog_pid, signal.SIGUSR1)
	safeprint('Console exit with code: ' + str(ecode) + ' at ' + time.strftime('%m-%d-%y %H:%M:%S'))
	if ecode in range(10, 20):
		# exit console without restart
		safeprint("Shutdown")
	elif ecode in range(20, 30):
		# shutdown the pi
		safeprint("Shutdown the Pi")
		subprocess.Popen(['sudo', 'shutdown', '-P', 'now'])
	elif ecode in range(30, 40):
		# restart the console
		if os.path.exists('/etc/systemd/system/multi-user.target.wants/softconsole.service'):
			# using systemd
			pass
		else:
			logsupport.Logs.Log('Using rc.local restart model - consider switching to systemd')
			subprocess.Popen('nohup sudo /bin/bash -e scripts/consoleexit ' + 'restart' +
							 ' ' + config.sysStore.configfile + '>>' + config.sysStore.HomeDir + '/log.txt 2>&1 &',
							 shell=True)
	elif ecode in range(40, 50):
		# reboot the pi
		subprocess.Popen(['sudo', 'shutdown', '-r', 'now'])
	else:
		# should never happen
		safeprint('Undefined console exit code!  Code: ' + str(ecode))
		# reboot pi?
		pass
	if immediate:
		logsupport.Logs.Log("Immediate Exit: ", str(ecode), tb=False)
		logsupport.EndAsyncLog()
		time.sleep(.1)
		logsupport.Logs.Log("Async log close issued")
		config.running = False
		pg.display.quit()
		pg.quit()
		hw.CleanUp()
		# noinspection PyProtectedMember
		os._exit(ecode)  # use this vs sys.exit to avoid atexit interception
	else:
		config.ecode = ecode
		config.Running = False  # make sure the main loop ends even if this exit call returns


def errorexit(opt):
	if opt == ERRORRESTART:
		Exit_Screen_Message('Error restart', 'Error', 'Restarting')
	elif opt == ERRORPIREBOOT:
		Exit_Screen_Message('Error reboot', 'Error', 'Rebooting Pi')
	elif opt == ERRORDIE:
		Exit_Screen_Message('Error Shutdown', 'Error', 'Not Restarting', 'Check Log')
	config.terminationreason = 'error'
	Exit(opt, immediate=True)


def Exit_Screen_Message(msg, scrnmsg1, scrnmsg2='', scrnmsg3=''):
	config.Exiting = True
	hw.screen.fill(wc("red"))
	r = fonts.fonts.Font(40, '', True, True).render(scrnmsg1, 0, wc("white"))
	hw.screen.blit(r, ((hw.screenwidth - r.get_width()) / 2, hw.screenheight * .2))
	r = fonts.fonts.Font(40, '', True, True).render(scrnmsg2, 0, wc("white"))
	hw.screen.blit(r, ((hw.screenwidth - r.get_width()) / 2, hw.screenheight * .4))
	r = fonts.fonts.Font(40, '', True, True).render(scrnmsg3, 0, wc("white"))
	hw.screen.blit(r, ((hw.screenwidth - r.get_width()) / 2, hw.screenheight * .6))
	logsupport.Logs.Log(msg)
	displayupdate.updatedisplay()
	time.sleep(5)


def FatalError(msg):
	logsupport.Logs.Log(msg, severity=ConsoleError, tb=False)  # include traceback
	Exit_Screen_Message(msg, 'Internal Error', msg)
	Exit(ERRORRESTART, immediate=True)
