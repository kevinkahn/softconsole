import os
import subprocess
import time

import pygame

import config
import logsupport
from logsupport import ConsoleWarning, ConsoleError
import webcolors


def wc(clr, factor=0.0, layercolor=(255, 255, 255)):  # todo move this and interval str to a dependencyless file
	try:
		v = webcolors.name_to_rgb(clr)
	except ValueError:
		logsupport.Logs.Log('Bad color name: ' + str(clr), severity=ConsoleWarning)
		v = webcolors.name_to_rgb('black')

	return v[0] + (layercolor[0] - v[0]) * factor, v[1] + (layercolor[1] - v[1]) * factor, v[2] + (
				layercolor[2] - v[2]) * factor


def interval_str(sec_elapsed):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)

# Exit Codes:
# 1x: shutdown console (don't restart in systemd or script)
# 2x: shutdown pi (issue shutdown - systemd won't be involved)
# 3x: restart console (restart via systemd or via script)
# 4x: reboot pi (issue restart of pi - systemd won't be involved)

EARLYABORT     = 11
MAINTEXIT      = 12
ERRORDIE       = 13

MAINTPISHUT    = 21

MAINTRESTART   = 31
AUTORESTART    = 32
REMOTERESTART  = 33
ERRORRESTART   = 34
EXTERNALSIGTERM= 35 # from systemd on a stop or restart so could be either

MAINTPIREBOOT  = 41
REMOTEREBOOT   = 42
ERRORPIREBOOT  = 43


def EarlyAbort(scrnmsg):
	config.screen.fill(wc("red"))
	# this font is manually loaded into the fontcache to avoid log message on early abort before log is up
	# see fonts.py
	r = config.fonts.Font(40, '', True, True).render(scrnmsg, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
	pygame.display.update()
	print (time.strftime('%m-%d-%y %H:%M:%S'), scrnmsg)
	time.sleep(10)
	pygame.quit()
	# noinspection PyProtectedMember
	os._exit(EARLYABORT)


def Exit(ecode):
	consoleup = time.time() - config.starttime
	logsupport.Logs.Log("Console was up: ", interval_str(consoleup), severity=ConsoleWarning)
	with open(config.homedir + "/.RelLog", "a") as f:
		f.write('Exit ' + str(ecode) + '\n')
	os.chdir(config.exdir)  # set cwd to be correct when dirs move underneath us so that scripts execute

	logsupport.Logs.Log("Console Exiting - Ecode: " + str(ecode))

	print('Console exit with code: ' + str(ecode) + ' at ' + time.strftime('%m-%d-%y %H:%M:%S'))
	if ecode in range(10,20):
		# exit console without restart
		print("Shutdown")
	elif ecode in range(20,30):
		# shutdown the pi
		print("Shutdown the Pi")
		subprocess.Popen(['sudo', 'shutdown', '-P', 'now'])
	elif ecode in range(30,40):
		# restart the console
		if os.path.exists('/etc/systemd/system/multi-user.target.wants/softconsole.service'):
			# using systemd
			pass
		else:
			logsupport.Logs.Log('Using rc.local restart model - consider switching to systemd')
			subprocess.Popen('nohup sudo /bin/bash -e scripts/consoleexit ' + 'restart' +
							 ' ' + config.configfile + '>>' + config.homedir + '/log.txt 2>&1 &', shell=True)
	elif ecode in range(40,50):
		# reboot the pi
		subprocess.Popen(['sudo', 'shutdown', '-r', 'now'])
	else:
		# should never happen
		print('Undefined console exit code!  Code: ' + str(ecode))
		# reboot pi?
		pass

	config.ecode = ecode
	config.Running = False  # make sure the main loop ends even if this exit call returns

def domaintexit(ExitKey):
	if ExitKey == 'shut':
		ExitCode = MAINTEXIT
		Exit_Screen_Message("Manual Shutdown Requested", "Maintenance Request", "Shutting Down")
	elif ExitKey == 'restart':
		ExitCode = MAINTRESTART
		Exit_Screen_Message("Console Restart Requested", "Maintenance Request", "Restarting")
	elif ExitKey == 'shutpi':
		ExitCode = MAINTPISHUT
		Exit_Screen_Message("Shutdown Pi Requested", "Maintenance Request", "Shutting Down Pi")
	elif ExitKey == 'reboot':
		ExitCode = MAINTPIREBOOT
		Exit_Screen_Message("Reboot Pi Requested", "Maintenance Request", "Rebooting Pi")
	else:
		ExitCode = MAINTRESTART
		Exit_Screen_Message("Unknown Exit Requested", "Maintenance Error", "Trying a Restart")
	Exit(ExitCode)

def errorexit(opt):
	if opt == ERRORRESTART:
		Exit_Screen_Message('Error restart', 'Error', 'Restarting')
	elif opt == ERRORPIREBOOT:
		Exit_Screen_Message('Error reboot', 'Error', 'Rebooting Pi')
	elif opt == ERRORDIE:
		Exit_Screen_Message('Error Shutdown', 'Error', 'Not Restarting', 'Check Log')
	Exit(opt)

def Exit_Screen_Message(msg, scrnmsg1, scrnmsg2='', scrnmsg3=''):
	config.screen.fill(wc("red"))
	r = config.fonts.Font(40, '', True, True).render(scrnmsg1, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.2))
	r = config.fonts.Font(40, '', True, True).render(scrnmsg2, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
	r = config.fonts.Font(40, '', True, True).render(scrnmsg3, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.6))
	logsupport.Logs.Log(msg)
	pygame.display.update()
	time.sleep(5)


def FatalError(msg, restartopt='restart'):
	logsupport.Logs.Log(msg, severity=ConsoleError, tb=False) # include traceback
	Exit_Screen_Message(msg, 'Internal Error', msg)
	if restartopt == 'restart':
		ExitCode = ERRORRESTART
	else:
		ExitCode = ERRORDIE
	Exit(ExitCode)

