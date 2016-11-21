import subprocess
from collections import OrderedDict
import os
import functools

import pygame
import webcolors

import config
import toucharea
from config import debugPrint
from utilities import interval_str

wc = webcolors.name_to_rgb
from logsupport import ConsoleError, ConsoleWarning
import time
import sys
import utilities
import screen
import githubutil as U

fixedoverrides = {'CharColor': 'white', 'BackgroundColor': 'royalblue', 'label': ['Maintenance'], 'DimTO': 60,
				  'PersistTO': 5}


def SetUpMaintScreens():
	LogDisp = LogDisplayScreen()
	Exits = MaintScreenDesc('Exits',
							OrderedDict(
								[('shut', ('Shutdown Console', doexit)), ('restart', ('Restart Console', doexit)),
								 ('shutpi', (('Shutdown Pi'), doexit)), ('reboot', (('Reboot Pi'), doexit)),
								 ('return', ('Return', None))]))  # proc filled in below due to circularity
	Beta = MaintScreenDesc('Versions',
						   OrderedDict([('stable', (('Use Stable Release'), dobeta)), ('beta', (('Use Beta Release'), dobeta)),
										('release', (('Download release'), dobeta)), ('fetch', (('Download Beta'), dobeta)),
										('return', ('Return', None))]))  # proc filled in below due to circularity
	config.MaintScreen = MaintScreenDesc('Maintenance',
										 OrderedDict([('return', ('Exit Maintenance', gohome)),
													  ('log', ('Show Log', functools.partial(goto, LogDisp))),
													  ('beta', ('Select Version', functools.partial(goto, Beta))),
													  ('flags', ('Set Flags', None)),
													  # fixed below to break a dependency loop - this is key 3
													  ('exit', ('Exit/Restart', functools.partial(goto, Exits)))]))
	tmp = OrderedDict()
	for flg in config.DbgFlags:
		tmp[flg] = (flg, setdbg)  # setdbg gets fixed below to be actually callable
	tmp['return'] = ('Return', functools.partial(goto, config.MaintScreen))
	DebugFlags = MaintScreenDesc('Flags', tmp)
	for kn, k in DebugFlags.Keys.iteritems():
		if kn in config.Flags:
			k.State = config.Flags[k.name]
			k.Proc = functools.partial(setdbg, k)

	config.MaintScreen.Keys['flags'].Proc = functools.partial(goto, DebugFlags, config.MaintScreen.Keys['flags'])
	Exits.Keys['return'].Proc = functools.partial(goto, config.MaintScreen, Exits.Keys['return'])
	Beta.Keys['return'].Proc = functools.partial(goto, config.MaintScreen, Beta.Keys['return'])


def setdbg(K, presstype):
	config.Flags[K.name] = not config.Flags[K.name]
	K.State = config.Flags[K.name]
	K.PaintKey()
	config.Logs.Log("Debug flag ", K.name, ' = ', K.State, severity=ConsoleWarning)
	# Let the daemon know about flags change
	config.toDaemon.put(('flagchange', K.name, config.Flags[K.name]))


def gohome(K, presstype):  # neither peram used
	config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Maint exit', NavKeys=True)


def goto(screen, K, presstype):
	config.DS.SwitchScreen(screen, 'Bright', 'Maint', 'Maint goto', NavKeys=False)

def doexit(K, presstype):
	if K.name == 'shut':
		verifymsg = 'Do Console Shutdown'
	elif K.name == 'restart':
		verifymsg = 'Do Console Restart'
	elif K.name == 'shutpi':
		verifymsg = 'Do Pi Shutdown'
	else:
		verifymsg = 'Do Pi Reboot'
	Verify = MaintScreenDesc('Verify',
							 OrderedDict([('yes', (verifymsg, functools.partial(dorealexit, K))),
										  ('no', ('Cancel', functools.partial(goto, config.MaintScreen)))]))
	config.DS.SwitchScreen(Verify, 'Bright', 'Maint', 'Verify exit', NavKeys=False)


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


def dobeta(K, presstype):
	basedir = os.path.dirname(config.exdir)
	K.State = not K.State
	K.PaintKey()
	if K.name == 'stable':
		subprocess.Popen('sudo rm /home/pi/usebeta', shell=True)
	elif K.name == 'beta':
		subprocess.Popen('sudo touch /home/pi/usebeta', shell=True)
	elif K.name == 'fetch':
		config.Logs.Log("New version fetch(currentbeta)")
		print "----------------------------------------"
		print "New Version Fetch Requested (currentbeta)"
		U.StageVersion(basedir + '/consolebeta', 'currentbeta', 'RequestedDownload')
		U.InstallStagedVersion(basedir + '/consolebeta')
	# subprocess.Popen('sudo /bin/bash -e scripts/getcurrentbeta', shell=True)
	elif K.name == 'release':
		print "----------------------------------------"
		if os.path.exists(basedir + '/homesystem'):
			# personal system
			config.Logs.Log("New version fetch(homerelease)")
			print "New Version Fetch Requested (homesystem)"
			U.StageVersion(basedir + '/consolestable', 'homerelease', 'RequestedDownload')
		else:
			config.Logs.Log("New version fetch(currentrelease)")
			print "New Version Fetch Requested (currentrelease)"
			U.StageVersion(basedir + '/consolestable', 'currentrelease', 'RequestedDownload')
		U.InstallStagedVersion(basedir + '/consolestable')


	time.sleep(2)
	K.State = not K.State
	K.PaintKey()


def Exit_Options(msg, scrnmsg):
	config.screen.fill(wc("red"))
	r = config.fonts.Font(40, '', True, True).render(scrnmsg, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
	config.Logs.Log(msg)
	pygame.display.update()
	time.sleep(2)


class LogDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		screen.BaseKeyScreenDesc.__init__(self, None, 'LOG')
		self.Keys = {'nextpage': toucharea.TouchPoint('nextpage', (config.screenwidth/2, config.screenheight/2),
													  (config.screenwidth, config.screenheight), proc=self.NextPage)}
		self.NodeWatch = []
		self.name = 'Log'
		utilities.register_example("LogDisplayScreen", self)

	def NextPage(self, presstype):
		if self.item >= 0:
			self.item = config.Logs.RenderLog(self.BackgroundColor, start=self.item)
		else:
			config.DS.SwitchScreen(config.MaintScreen, 'Bright', 'Maint', 'Done showing log', NavKeys=False)

	def EnterScreen(self):
		debugPrint('Main', "Enter to screen: ", self.name)
		config.Logs.Log('Entering Log Screen')
		self.item = 0
		self.NodeWatch = []

	def InitDisplay(self, nav):
		super(LogDisplayScreen, self).InitDisplay(nav)
		self.item = 0
		self.NextPage(0)

class MaintScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, name, keys):
		debugPrint('Screen', "Build Maintenance Screen")
		screen.BaseKeyScreenDesc.__init__(self, fixedoverrides, name)
		utilities.LocalizeParams(self, None, '-', TitleFontSize=40, SubFontSize=25)
		for k, kt in keys.iteritems():
			NK = toucharea.ManualKeyDesc(k, [kt[0]], 'gold', 'black', 'red', KOn='black', KOff='red')
			if kt[1] is not None:
				NK.Proc = functools.partial(kt[1], NK)
			self.Keys[k] = NK
		topoff = self.TitleFontSize + self.SubFontSize
		self.LayoutKeys(topoff, config.screenheight - 2*config.topborder - topoff)
		self.NodeWatch = []
		self.DimTO = 60
		self.PersistTO = 1  # setting to 0 would turn off timer and stick us here
		utilities.register_example("MaintScreenDesc", self)

	def ShowScreen(self):
		self.PaintBase()
		r = config.fonts.Font(self.TitleFontSize, '', True, True).render("Console Maintenance", 0, wc(self.CharColor))
		rl = (config.screenwidth - r.get_width())/2
		config.screen.blit(r, (rl, config.topborder))
		r = config.fonts.Font(self.SubFontSize, '', True, True).render(
			"Up: " + interval_str(time.time() - config.starttime),
			0, wc(self.CharColor))
		rl = (config.screenwidth - r.get_width())/2
		config.screen.blit(r, (rl, config.topborder + self.TitleFontSize))
		self.PaintKeys()
		pygame.display.update()

	def EnterScreen(self):
		debugPrint('Main', "Enter to screen: ", self.name)
		config.Logs.Log('Entering Maintenance Screen: ' + self.name)

	def InitDisplay(self, nav):
		super(MaintScreenDesc, self).InitDisplay(nav)
		self.ShowScreen()
