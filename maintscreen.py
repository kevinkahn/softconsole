import functools
from collections import OrderedDict

import pygame

import config
import debug
import hw
import logsupport
import screen
import screens.__screens as screens
import timers
import toucharea
import utilities
import issuecommands
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

	ExitMenu = OrderedDict()
	for cmd, action in issuecommands.cmdcalls.items():
		if issuecommands.Where.LocalMenuExits in action.where:
			ExitMenu[cmd] = (action.DisplayName, action.Proc, action.Verify)
	ExitMenu['return'] = ('Return', screen.PopScreen)
	Exits = MaintScreenDesc('System Exit/Restart', ExitMenu)
	screenset.append(Exits)

	VersMenu = OrderedDict()
	for cmd, action in issuecommands.cmdcalls.items():
		if issuecommands.Where.LocalMenuVersions in action.where:
			VersMenu[cmd] = (action.DisplayName, action.Proc)
	# VersMenu[cmd] = (action.DisplayName, dobeta, 'addkey')
	VersMenu['return'] = ('Return', screen.PopScreen)
	Beta = MaintScreenDesc('Version Control', VersMenu)
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
		FlagsScreens.append(MaintScreenDesc('Flags Setting ({})'.format(flagscreencnt), tmp, overrides=flagoverrides))
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

	MaintScreen = MaintScreenDesc('Console Maintenance', TopLevel)

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
