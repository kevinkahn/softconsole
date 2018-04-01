import functools
import os
import subprocess
from collections import OrderedDict

import pygame

import config
import toucharea
import debug
import exitutils
from utilities import interval_str, wc
import logsupport
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
							OrderedDict([('shut', ('Shutdown Console', doexit)),
										 ('restart', ('Restart Console', doexit)),
										 ('shutpi', ('Shutdown Pi', doexit)), ('reboot', ('Reboot Pi', doexit)),
										 ('return', ('Return', None))]))  # proc filled in below due to circularity
	Beta = MaintScreenDesc('Versions',
						   OrderedDict([('stable', ('Use Stable Release', dobeta)),
										('beta', ('Use Beta Release', dobeta)),
										('release', ('Download release', dobeta)), ('fetch', ('Download Beta', dobeta)),
										('return', ('Return', None))]))  # proc filled in below due to circularity
	config.MaintScreen = MaintScreenDesc('Maintenance',
										 OrderedDict([('return', ('Exit Maintenance', gohome)),
													  ('log', ('Show Log', functools.partial(goto, LogDisp))),
													  ('beta', ('Select Version', functools.partial(goto, Beta))),
													  ('flags', ('Set Flags', None)),
													  # fixed below to break a dependency loop - this is key 3
													  ('exit', ('Exit/Restart', functools.partial(goto, Exits)))]))
	FlagsScreens = []
	nflags = len(debug.DbgFlags) + 3
	# will need key for each debug flag plus a return plus a loglevel up and loglevel down
	tmpDbgFlags = ["LogLevelUp", "LogLevelDown"] + debug.DbgFlags[:]  # temp copy of Flags
	flagspercol = config.screenheight // 120
	flagsperrow = config.screenwidth // 120
	flagoverrides = fixedoverrides.copy()
	flagoverrides.update(KeysPerColumn=flagspercol, KeysPerRow=flagsperrow)
	while nflags > 0:
		thisscrn = min(nflags, flagspercol*flagsperrow)
		nflags = nflags - flagspercol*flagsperrow + 1
		tmp = OrderedDict()
		for i in range(thisscrn - 1):  # leave space for next or return
			flg = tmpDbgFlags.pop(0)
			tmp[flg] = (flg, setdbg)  # setdbg gets fixed below to be actually callable
		if nflags > 0:  # will need another flag screen so build a "next"
			tmp['next'] = (
			'Next', functools.partial(goto, config.MaintScreen))  # this gets fixed below to be a real next
		else:
			tmp['return'] = ('Return', functools.partial(goto, config.MaintScreen))
		FlagsScreens.append(MaintScreenDesc('Flags', tmp, overrides=flagoverrides))
		FlagsScreens[-1].KeysPerColumn = flagspercol
		FlagsScreens[-1].KeysPerRow = flagsperrow

	for i in range(len(FlagsScreens) - 1):
		FlagsScreens[i].Keys['next'].Proc = functools.partial(goto, FlagsScreens[i + 1], FlagsScreens[i].Keys['next'])


	for s in FlagsScreens:
		debug.DebugFlagKeys.update(s.Keys)
		for kn, k in s.Keys.items():
			if kn in debug.DbgFlags:
				k.State = debug.dbgStore.GetVal(k.name)
				k.Proc = functools.partial(setdbg, k)
	debug.DebugFlagKeys["LogLevelUp"].Proc = functools.partial(adjloglevel, debug.DebugFlagKeys["LogLevelUp"])
	debug.DebugFlagKeys["LogLevelDown"].Proc = functools.partial(adjloglevel, debug.DebugFlagKeys["LogLevelDown"])
	debug.DebugFlagKeys["LogLevelUp"].SetKeyImages(
		("Log Detail", logsupport.LogLevels[logsupport.LogLevel] + '(' + str(logsupport.LogLevel) + ')', "Less"))
	debug.DebugFlagKeys["LogLevelDown"].SetKeyImages(
		("Log Detail", logsupport.LogLevels[logsupport.LogLevel] + '(' + str(logsupport.LogLevel) + ')', "More"))

	config.MaintScreen.Keys['flags'].Proc = functools.partial(goto, FlagsScreens[0], config.MaintScreen.Keys['flags'])
	Exits.Keys['return'].Proc = functools.partial(goto, config.MaintScreen, Exits.Keys['return'])
	Beta.Keys['return'].Proc = functools.partial(goto, config.MaintScreen, Beta.Keys['return'])

# noinspection PyUnusedLocal
def setdbg(K, presstype):  # todo needs dynamic repaint
	debug.dbgStore.SetVal(K.name,not debug.dbgStore.GetVal(K.name))
	K.State = not K.State
	K.PaintKey()
	logsupport.Logs.Log("Debug flag ", K.name, ' = ', K.State, severity=ConsoleWarning)

# noinspection PyUnusedLocal
def adjloglevel(K, presstype):
	if K.name == "LogLevelUp":
		if logsupport.LogLevel < len(logsupport.LogLevels) - 1:
			logsupport.LogLevel += 1
	else:
		if logsupport.LogLevel > 0:
			logsupport.LogLevel -= 1
	debug.DebugFlagKeys["LogLevelUp"].SetKeyImages(
		("Log Detail", logsupport.LogLevels[logsupport.LogLevel] + '(' + str(logsupport.LogLevel) + ')', "Less"))
	debug.DebugFlagKeys["LogLevelDown"].SetKeyImages(
		("Log Detail", logsupport.LogLevels[logsupport.LogLevel] + '(' + str(logsupport.LogLevel) + ')', "More"))
	debug.DebugFlagKeys["LogLevelUp"].PaintKey()
	debug.DebugFlagKeys["LogLevelDown"].PaintKey()
	logsupport.Logs.Log("Log Level changed via ", K.name, " to ", logsupport.LogLevel, severity=ConsoleWarning)

# noinspection PyUnusedLocal
def gohome(K, presstype):  # neither peram used
	config.DS.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Maint exit', NavKeys=True)

# noinspection PyUnusedLocal
def goto(newscreen, K, presstype):
	config.DS.SwitchScreen(newscreen, 'Bright', 'Maint', 'Maint goto' + newscreen.name, NavKeys=False)

# noinspection PyUnusedLocal
def handleexit(K, YesKey, presstype):
	# YesKey, presstype are ignored in this use - needed by the key press invokation for other purposes
	exitutils.domaintexit(K.name)

# noinspection PyUnusedLocal
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
							 OrderedDict([('yes', (verifymsg, functools.partial(handleexit, K))),
										  ('no', ('Cancel', functools.partial(goto, config.MaintScreen)))]))
	config.DS.SwitchScreen(Verify, 'Bright', 'Maint', 'Verify exit', NavKeys=False)

# noinspection PyUnusedLocal
def dobeta(K, presstype):
	#todo fetch other tags; switch to versionselector
	K.State = not K.State
	K.PaintKey()
	if K.name == 'stable':
		subprocess.Popen('sudo rm /home/pi/usebeta', shell=True) #todo remove
		subprocess.Popen('sudo echo stable > /home/pi/versionselector', shell=True)
	elif K.name == 'beta':
		subprocess.Popen('sudo touch /home/pi/usebeta', shell=True) #todo remove
		subprocess.Popen('sudo echo beta > /home/pi/versionselector', shell=True)
	elif K.name == 'fetch':
		fetch_beta()
	elif K.name == 'release':
		fetch_stable()

	time.sleep(2)
	K.State = not K.State
	K.PaintKey()


def fetch_stable():
	basedir = os.path.dirname(config.exdir)

	# noinspection PyBroadException
	try:
		if os.path.exists(basedir + '/homesystem'):
			# personal system
			logsupport.Logs.Log("New version fetch(homerelease)")
			print ("New Version Fetch Requested (homesystem)")
			U.StageVersion(basedir + '/consolestable', 'homerelease', 'RequestedDownload')
		else:
			logsupport.Logs.Log("New version fetch(currentrelease)")
			print ("New Version Fetch Requested (currentrelease)")
			U.StageVersion(basedir + '/consolestable', 'currentrelease', 'RequestedDownload')
		U.InstallStagedVersion(basedir + '/consolestable')
		logsupport.Logs.Log("Staged version installed in consolestable")
	except:
		logsupport.Logs.Log('Failed release download', severity=ConsoleWarning)


def fetch_beta():
	basedir = os.path.dirname(config.exdir)
	logsupport.Logs.Log("New version fetch(currentbeta)")
	print ("New Version Fetch Requested (currentbeta)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consolebeta', 'currentbeta', 'RequestedDownload')
		U.InstallStagedVersion(basedir + '/consolebeta')
		logsupport.Logs.Log("Staged version installed in consolebeta")
	except:
		logsupport.Logs.Log('Failed beta download', severity=ConsoleWarning)


class LogDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		self.item = 0
		self.pageno = -1
		self.PageStartItem = [0]
		screen.BaseKeyScreenDesc.__init__(self, None, 'LOG')
		self.Keys = {'nextpage': toucharea.TouchPoint('nextpage', (config.screenwidth/2, 3*config.screenheight/4),
													  (config.screenwidth, config.screenheight), proc=self.NextPage),
					 'prevpage': toucharea.TouchPoint('prevpage', (config.screenwidth/2, config.screenheight/4),
													  (config.screenwidth, config.screenheight/2), proc=self.PrevPage)}
		self.name = 'Log'
		utilities.register_example("LogDisplayScreen", self)

	# noinspection PyUnusedLocal
	def NextPage(self, presstype):
		if self.item >= 0:
			self.pageno += 1
			self.item = logsupport.Logs.RenderLog(self.BackgroundColor, start=self.item)
			if self.pageno + 1 == len(self.PageStartItem):
				self.PageStartItem.append(self.item)
		else:
			config.DS.SwitchScreen(config.MaintScreen, 'Bright', 'Maint', 'Done showing log', NavKeys=False)

	# noinspection PyUnusedLocal
	def PrevPage(self, presstype):
		if self.pageno > 0:
			self.pageno -= 1
			self.item = logsupport.Logs.RenderLog(self.BackgroundColor, start=self.PageStartItem[self.pageno])
		else:
			config.DS.SwitchScreen(config.MaintScreen, 'Bright', 'Maint', 'Done showing log', NavKeys=False)

	def InitDisplay(self, nav):
		debug.debugPrint('Main', "Enter to screen: ", self.name)
		super(LogDisplayScreen, self).InitDisplay(nav)
		logsupport.Logs.Log('Entering Log Screen')
		self.item = 0
		self.PageStartItem = [0]
		self.pageno = -1
		self.NextPage(0)

class MaintScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, name, keys, overrides=fixedoverrides):
		self.TitleFontSize = 0
		self.SubFontSize = 0

		debug.debugPrint('Screen', "Build Maintenance Screen")
		screen.BaseKeyScreenDesc.__init__(self, overrides, name)
		utilities.LocalizeParams(self, None, '-', TitleFontSize=40, SubFontSize=25)
		for k, kt in keys.items():
			NK = toucharea.ManualKeyDesc(self, k, [kt[0]], 'gold', 'black', 'red', KOn='black', KOff='red')
			if kt[1] is not None:
				NK.Proc = functools.partial(kt[1], NK)
			self.Keys[k] = NK
		topoff = self.TitleFontSize + self.SubFontSize
		self.LayoutKeys(topoff, config.screenheight - 2*config.topborder - topoff)
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

	def InitDisplay(self, nav):
		debug.debugPrint('Main', "Enter to screen: ", self.name)
		logsupport.Logs.Log('Entering Maintenance Screen: ' + self.name)
		super(MaintScreenDesc, self).InitDisplay(nav)
		self.ShowScreen()
