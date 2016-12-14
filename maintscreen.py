import functools
import os
import subprocess
from collections import OrderedDict

import pygame
import webcolors

import config
import debug
import toucharea
from debug import debugPrint
from exitutils import dorealexit
from utilities import interval_str

wc = webcolors.name_to_rgb
from logsupport import ConsoleWarning
import time
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
	for flg in debug.DbgFlags:
		tmp[flg] = (flg, setdbg)  # setdbg gets fixed below to be actually callable
	tmp['return'] = ('Return', functools.partial(goto, config.MaintScreen))
	DebugFlags = MaintScreenDesc('Flags', tmp)
	for kn, k in DebugFlags.Keys.iteritems():
		if kn in debug.Flags:
			k.State = debug.Flags[k.name]
			k.Proc = functools.partial(setdbg, k)

	config.MaintScreen.Keys['flags'].Proc = functools.partial(goto, DebugFlags, config.MaintScreen.Keys['flags'])
	Exits.Keys['return'].Proc = functools.partial(goto, config.MaintScreen, Exits.Keys['return'])
	Beta.Keys['return'].Proc = functools.partial(goto, config.MaintScreen, Beta.Keys['return'])


def setdbg(K, presstype):
	debug.Flags[K.name] = not debug.Flags[K.name]
	K.State = debug.Flags[K.name]
	K.PaintKey()
	config.Logs.Log("Debug flag ", K.name, ' = ', K.State, severity=ConsoleWarning)
	# Let the daemon know about flags change
	config.toDaemon.put(('flagchange', K.name, debug.Flags[K.name]))


def gohome(K, presstype):  # neither peram used
	config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Maint exit', NavKeys=True)


def goto(screen, K, presstype):
	config.DS.SwitchScreen(screen, 'Bright', 'Maint', 'Maint goto' + screen.name, NavKeys=False)

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
		try:
			U.StageVersion(basedir + '/consolebeta', 'currentbeta', 'RequestedDownload')
			U.InstallStagedVersion(basedir + '/consolebeta')
		except:
			config.Logs.Log('Failed beta download', severity=ConsoleWarning)
	# subprocess.Popen('sudo /bin/bash -e scripts/getcurrentbeta', shell=True)
	elif K.name == 'release':
		print "----------------------------------------"
		try:
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
		except:
			config.Logs.Log('Failed release download', severity=ConsoleWarning)

	time.sleep(2)
	K.State = not K.State
	K.PaintKey()


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
			NK = toucharea.ManualKeyDesc(self, k, [kt[0]], 'gold', 'black', 'red', KOn='black', KOff='red')
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
