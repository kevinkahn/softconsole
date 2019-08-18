import functools
import os
import subprocess
import time
from collections import OrderedDict

import pygame

import config
import debug
import githubutil as U
import hw
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
from exitutils import MAINTEXIT, Exit_Screen_Message, MAINTRESTART, MAINTPISHUT, MAINTPIREBOOT, Exit
from logsupport import ConsoleWarning, ReportStatus, UpdateGlobalErrorPointer
from maintscreenbase import MaintScreenDesc, fixedoverrides
import consolestatus

MaintScreen = None


def SetUpMaintScreens():
	global MaintScreen
	screenset = []
	LogDisp = LogDisplayScreen()
	screenset.append(LogDisp)

	Status = consolestatus.SetUpConsoleStatus()
	screenset.append(Status)

	Exits = MaintScreenDesc('Exits',
							OrderedDict([('shut', ('Shutdown Console', doexit, 'addkey')),
										 ('restart', ('Restart Console', doexit, 'addkey')),
										 ('shutpi', ('Shutdown Pi', doexit, 'addkey')),
										 ('reboot', ('Reboot Pi', doexit, 'addkey')),
										 ('return', ('Return', screen.PopScreen))]))
	screenset.append(Exits)

	Beta = MaintScreenDesc('Versions',
						   OrderedDict([('stable', ('Use Stable Release', dobeta, 'addkey')),
										('beta', ('Use Beta Release', dobeta, 'addkey')),
										('dev', ('Use Dev Release',dobeta,'addkey')),
										('release', ('Download release', dobeta, 'addkey')),
										('fetch', ('Download Beta', dobeta, 'addkey')),
										('fetchdev', ('Download Dev', dobeta, 'addkey')),
										('return', ('Return', screen.PopScreen))]))
	screenset.append(Beta)

	FlagsScreens = []
	nflags = len(debug.DbgFlags) + 3
	# will need key for each debug flag plus a return plus a loglevel up and loglevel down
	tmpDbgFlags = ["LogLevelUp", "LogLevelDown"] + debug.DbgFlags[:]  # temp copy of Flags
	flagspercol = hw.screenheight // 120  # todo switch to new screen sizing
	flagsperrow = hw.screenwidth // 120
	flagoverrides = fixedoverrides.copy()
	flagoverrides.update(KeysPerColumn=flagspercol, KeysPerRow=flagsperrow)
	flagscreencnt = 0
	while nflags > 0:
		thisscrn = min(nflags, flagspercol * flagsperrow)
		nflags = nflags - flagspercol * flagsperrow + 1
		tmp = OrderedDict()
		for i in range(thisscrn - 1):  # leave space for next or return
			flg = tmpDbgFlags.pop(0)
			tmp[flg] = (flg, setdbg)  # setdbg gets fixed below to be actually callable
		if nflags > 0:  # will need another flag screen so build a "next"
			tmp['next'] = (
				'Next', functools.partial(goto, MaintScreen))  # this gets fixed below to be a real next
		else:
			tmp['return'] = ('Return', screen.PopScreen)
		FlagsScreens.append(MaintScreenDesc('Flags' + str(flagscreencnt), tmp, overrides=flagoverrides))
		flagscreencnt += 1
		FlagsScreens[-1].KeysPerColumn = flagspercol
		FlagsScreens[-1].KeysPerRow = flagsperrow

	for i in range(len(FlagsScreens) - 1):
		FlagsScreens[i].Keys['next'].Proc = functools.partial(goto, FlagsScreens[i + 1])

	for s in FlagsScreens:
		screenset.append(s)
		debug.DebugFlagKeys.update(s.Keys)
		for kn, k in s.Keys.items():
			if kn in debug.DbgFlags:
				k.State = debug.dbgStore.GetVal(k.name)
				debug.dbgStore.AddAlert(k.name, (syncKeytoStore, k))
				k.Proc = functools.partial(setdbg, k)
	debug.DebugFlagKeys["LogLevelUp"].Proc = functools.partial(adjloglevel, debug.DebugFlagKeys["LogLevelUp"])
	debug.DebugFlagKeys["LogLevelDown"].Proc = functools.partial(adjloglevel, debug.DebugFlagKeys["LogLevelDown"])
	debug.DebugFlagKeys["LogLevelUp"].SetKeyImages(
		("Log Detail", logsupport.LogLevels[logsupport.LogLevel] + '(' + str(logsupport.LogLevel) + ')', "Less"))
	debug.DebugFlagKeys["LogLevelDown"].SetKeyImages(
		("Log Detail", logsupport.LogLevels[logsupport.LogLevel] + '(' + str(logsupport.LogLevel) + ')', "More"))

	TopLevel = OrderedDict([('return', ('Exit Maintenance', gohome)),
							('log', ('Show Log', functools.partial(screen.PushToScreen, LogDisp, 'Maint'))),
							('beta', ('Select Version', functools.partial(screen.PushToScreen, Beta, 'Maint'))),
							('flags', ('Set Flags', functools.partial(screen.PushToScreen, FlagsScreens[0], 'Maint')))])

	if Status is not None: TopLevel['status'] = (
	'Network Consoles', functools.partial(screen.PushToScreen, Status, 'Maint'))
	TopLevel['exit'] = ('Exit/Restart', functools.partial(screen.PushToScreen, Exits, 'Maint'))

	MaintScreen = MaintScreenDesc('Maintenance', TopLevel)

	for s in screenset:
		s.userstore.ReParent(MaintScreen)
	config.sysStore.AddAlert("GlobalLogViewTime", CheckIfLogSeen)


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
def CheckIfLogSeen(storeitem, old, new, param, chgsource):
	logsupport.Logs.Log('GlobalErrReset: new: {}  was {}'.format(new, config.sysStore.FirstUnseenErrorTime))
	if config.sysStore.ErrorNotice != -1:
		if new <= config.sysStore.FirstUnseenErrorTime:
			logsupport.Logs.Log('Cleared Error Indicator')
			config.sysStore.ErrorNotice = -1
			config.sysStore.FirstUnseenErrorTime = new  # first possible unseen is now
		else:
			logsupport.Logs.Log(
				'Error Indicator not cleared, possible unseen at {}'.format(config.sysStore.FirstUnseenErrorTime))


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
def syncKeytoStore(storeitem, old, new, key, chgsource):
	key.State = new


# noinspection PyUnusedLocal
def setdbg(K):
	st = debug.dbgStore.GetVal(K.name)
	K.State = not st
	K.PaintKey()
	pygame.display.update()
	debug.dbgStore.SetVal(K.name, not st)
	K.State = debug.dbgStore.GetVal(K.name)
	# this allows for case where flag gets reset by proc called servicing the set
	K.PaintKey()
	pygame.display.update()
	logsupport.Logs.Log("Debug flag ", K.name, ' = ', K.State)


# noinspection PyUnusedLocal
def adjloglevel(K):
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
	pygame.display.update()


# noinspection PyUnusedLocal
def gohome():  # neither peram used
	logsupport.Logs.Log('Exiting Maintenance Screen')
	# timers.EndLongOp('maintenance')
	screens.DS.SwitchScreen(screens.HomeScreen, 'Bright', 'Maint exit', newstate='Home')


# noinspection PyUnusedLocal
def goto(newscreen):
	screens.DS.SwitchScreen(newscreen, 'Bright', 'Maint goto' + newscreen.name, newstate='Maint')

# noinspection PyUnusedLocal
def handleexit(K):
	# YesKey are ignored in this use - needed by the key press invokation for other purposes
	domaintexit(K.name)


# noinspection PyUnusedLocal
def doexit(K):
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
										  ('no', ('Cancel', functools.partial(goto, MaintScreen)))]))
	screens.DS.SwitchScreen(Verify, 'Bright', 'Verify exit', newstate='Maint')


# noinspection PyUnusedLocal
def dobeta(K):
	# Future fetch other tags; switch to versionselector
	K.State = not K.State
	K.PaintKey()
	pygame.display.update()
	if K.name == 'stable':
		subprocess.Popen('sudo rm /home/pi/usebeta', shell=True)  # Deprecate remove
		subprocess.Popen('sudo echo stable > /home/pi/versionselector', shell=True)
	elif K.name == 'beta':
		subprocess.Popen('sudo touch /home/pi/usebeta', shell=True)  # Deprecate remove
		subprocess.Popen('sudo echo beta > /home/pi/versionselector', shell=True)
	elif K.name == 'dev':
		subprocess.Popen('sudo echo dev > /home/pi/versionselector', shell=True)
	elif K.name == 'fetch':
		fetch_beta()
	elif K.name=='fetchdev':
		fetch_dev()
	elif K.name == 'release':
		fetch_stable()

	time.sleep(2)
	K.State = not K.State
	K.PaintKey()
	pygame.display.update()


def fetch_stable():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt stable", hold=1)
	# noinspection PyBroadException
	try:
		if os.path.exists(basedir + '/homesystem'):
			# personal system
			logsupport.Logs.Log("New version fetch(homerelease)")
			logsupport.DevPrint("New Version Fetch Requested (homesystem)")
			U.StageVersion(basedir + '/consolestable', 'homerelease', 'Maint Dnld')
		else:
			logsupport.Logs.Log("New version fetch(currentrelease)")
			logsupport.DevPrint("New Version Fetch Requested (currentrelease)")
			U.StageVersion(basedir + '/consolestable', 'currentrelease', 'Maint Dnld')
		U.InstallStagedVersion(basedir + '/consolestable')
		logsupport.Logs.Log("Staged version installed in consolestable")
	except:
		logsupport.Logs.Log('Failed release download', severity=ConsoleWarning)
	ReportStatus("done stable", hold=2)


def fetch_beta():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt beta", hold=1)
	logsupport.Logs.Log("New version fetch(currentbeta)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consolebeta', 'currentbeta', 'Maint Dnld')
		U.InstallStagedVersion(basedir + '/consolebeta')
		logsupport.Logs.Log("Staged version installed in consolebeta")
	except:
		logsupport.Logs.Log('Failed beta download', severity=ConsoleWarning)
	ReportStatus("done beta", hold=2)

def fetch_dev():
	basedir = os.path.dirname(config.sysStore.ExecDir)
	ReportStatus("updt dev", hold=1)
	logsupport.Logs.Log("New version fetch(currentdev)")
	# noinspection PyBroadException
	try:
		U.StageVersion(basedir + '/consoledev', '*live*', 'Maint Dnld')
		U.InstallStagedVersion(basedir + '/consoledev')
		logsupport.Logs.Log("Staged version installed in consoledev")
	except:
		logsupport.Logs.Log('Failed beta download', severity=ConsoleWarning)
	ReportStatus("done dev", hold=2)


class LogDisplayScreen(screen.BaseKeyScreenDesc):
	def __init__(self):
		screen.BaseKeyScreenDesc.__init__(self, None, 'LOG')
		self.NavKeysShowing = False
		self.DefaultNavKeysShowing = False
		self.state = 'init'  # init: new entry to logs; scroll: doing error scroll manual: user control
		self.startat = 0  # where in log page starts
		self.startpage = 0
		self.item = 0
		self.pageno = -1
		self.PageStartItem = [0]
		self.Keys = {'nextpage': toucharea.TouchPoint('nextpage', (hw.screenwidth / 2, 3 * hw.screenheight / 4),
													  (hw.screenwidth, hw.screenheight / 2), proc=self.NextPage),
					 'prevpage': toucharea.TouchPoint('prevpage', (hw.screenwidth / 2, hw.screenheight / 4),
													  (hw.screenwidth, hw.screenheight / 2),
													  proc=self.PrevPage)}
		self.name = 'Log'
		utilities.register_example("LogDisplayScreen", self)

	# noinspection PyUnusedLocal
	def NextPage(self):
		if self.item >= 0:
			self.pageno += 1
			self.startpage = self.item
			screens.DS.SwitchScreen(screen.SELFTOKEN, 'Bright', 'Scroll Next', newstate='Maint')
		else:
			if self.state != 'scroll':
				self.state = 'init'
				screens.DS.SwitchScreen(screen.BACKTOKEN, 'Bright', 'Done (next) showing log', newstate='Maint')
			else:
				self.state = 'manual'

	# noinspection PyUnusedLocal
	def PrevPage(self):
		if self.pageno > 0:
			self.pageno -= 1
			self.startpage = self.PageStartItem[self.pageno]
			screens.DS.SwitchScreen(screen.SELFTOKEN, 'Bright', 'Scroll Prev', newstate='Maint')
		else:
			self.state = 'init'
			screens.DS.SwitchScreen(screen.BACKTOKEN, 'Bright', 'Done (prev) showing log', newstate='Maint')

	def InitDisplay(self, nav):
		self.BackgroundColor = 'maroon'
		if self.state == 'init':
			debug.debugPrint('Main', "Enter to screen: ", self.name)
			super(LogDisplayScreen, self).InitDisplay(nav)
			logsupport.Logs.Log('Entering Log Screen')
			self.startat = 0
			self.startpage = 0
			self.item = 0
			self.pageno = -1
			self.PageStartItem = [0]
			if config.sysStore.ErrorNotice != -1:
				self.state = 'scroll'
				self.startat = config.sysStore.ErrorNotice
				config.sysStore.ErrorNotice = -1
			else:
				self.state = 'manual'
				self.startat = 0
			UpdateGlobalErrorPointer()
			self.item = 0
			self.PageStartItem = [0]
			self.pageno = -1
		if self.state == 'scroll':
			if (self.item < self.startat) and (
					self.item != -1):  # if first error not yet up and not last page go to next page
				timers.OnceTimer(.25, start=True, name='LogPage{}'.format(self.item), proc=self.LogSwitch)
			else:
				self.state = 'manual'
		else:
			pass
		self.item = logsupport.Logs.RenderLog(self.BackgroundColor, start=self.startpage, pageno=self.pageno + 1)
		if self.pageno + 1 == len(self.PageStartItem):  # if first time we saw this page remember its start pos
			self.PageStartItem.append(self.item)

	def LogSwitch(self, event):
		self.NextPage()


def domaintexit(ExitKey):
	if ExitKey == 'shut':
		ReportStatus('shutting down', hold=1)
		ExitCode = MAINTEXIT
		Exit_Screen_Message("Manual Shutdown Requested", "Maintenance Request", "Shutting Down")
	elif ExitKey == 'restart':
		ReportStatus('restarting', hold=1)
		ExitCode = MAINTRESTART
		Exit_Screen_Message("Console Restart Requested", "Maintenance Request", "Restarting")
	elif ExitKey == 'shutpi':
		ReportStatus('pi shutdown', hold=1)
		ExitCode = MAINTPISHUT
		Exit_Screen_Message("Shutdown Pi Requested", "Maintenance Request", "Shutting Down Pi")
	elif ExitKey == 'reboot':
		ReportStatus('pi reboot', hold=1)
		ExitCode = MAINTPIREBOOT
		Exit_Screen_Message("Reboot Pi Requested", "Maintenance Request", "Rebooting Pi")
	else:
		ReportStatus('unknown maintenance restart', hold=1)
		ExitCode = MAINTRESTART
		Exit_Screen_Message("Unknown Exit Requested", "Maintenance Error", "Trying a Restart")
	config.terminationreason = 'manual request'
	Exit(ExitCode)
