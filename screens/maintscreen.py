import functools
from collections import OrderedDict

from utils import displayupdate, hw
from guicore.switcher import SwitchScreen
import config
import debug
import logsupport
from screens import screen
import issuecommands
from logsupport import ConsoleWarning
from screens.maintscreenbase import MaintScreenDesc, fixedoverrides
import consolestatus
import screens.supportscreens as supportscreens
from keys.keyutils import DispOpt, ChooseType

MaintScreen = None


def SetUpMaintScreens():
	global MaintScreen
	screenset = []
	LogDisp = supportscreens.PagedDisplay('LocalLog', PickStartingSpot,
										  functools.partial(logsupport.LineRenderer, uselog=logsupport.Logs.log),
										  logsupport.Logs.PageTitle, config.sysStore.LogFontSize, 'white')
	screenset.append(LogDisp)

	Status = consolestatus.SetUpConsoleStatus()
	if Status is not None:
		screenset.append(Status)

	ExitMenu = OrderedDict()
	for cmd, action in issuecommands.cmdcalls.items():
		if issuecommands.Where.LocalMenuExits in action.where:
			ExitMenu[cmd] = (action.DisplayName, action.Proc, None, action.Verify)
	Exits = MaintScreenDesc('System Exit/Restart', ExitMenu)
	screenset.append(Exits)

	VersMenu = OrderedDict()
	VersMenuAdv = OrderedDict()
	for cmd, action in issuecommands.cmdcalls.items():
		if issuecommands.Where.LocalMenuVersions in action.where:
			VersMenu[cmd] = (action.DisplayName, action.Proc)
			VersMenuAdv[cmd] = (action.DisplayName, action.Proc)
		elif issuecommands.Where.LocalMenuVersionsAdv in action.where:
			VersMenuAdv[cmd] = (action.DisplayName, action.Proc)
	Versions = MaintScreenDesc('Version Control', VersMenu)
	VersionsAdv = MaintScreenDesc('Advanced Version Control', VersMenuAdv)
	screenset.append(Versions)
	screenset.append(VersionsAdv)

	FlagsScreens = []
	nflags = len(debug.DbgFlags) + 3
	# will need key for each debug flag plus a return plus a loglevel up and loglevel down
	# (label, tapproc, dbltapproc, verify, dispopts, defopts, var)
	loglevdispup = DispOpt(choosertype=ChooseType.rangeval, chooser=(0, 9), color=('gold', 'blue', 'black'),
						   deflabel=('Log Less', 'Detail', '$',))
	loglevdispdef = DispOpt(choosertype=ChooseType.rangeval, chooser=(0, 9), color=('gold', 'blue', 'black'),
							deflabel=('Log Bad', 'Level', '$'))
	logleveldispdn = []
	for i in range(len(logsupport.LogLevels)):
		logleveldispdn.append(DispOpt(choosertype=ChooseType.intval, chooser=i, color=('gold', 'blue', 'black'),
									  deflabel=('Log More', 'Detail', logsupport.LogLevels[i])))
	nextdisp = (
		DispOpt(choosertype=ChooseType.Noneval, chooser=None, color=('pink', 'blue', 'black'), deflabel=('Next',)),)
	debFlagInput = [("LogLevelUp", None, None, False, '', loglevdispup, "System:LogLevel"),
					("LogLevelDown", None, None, False, logleveldispdn, loglevdispdef, "System:LogLevel")]
	for f in debug.DbgFlags:
		debFlagInput.append((f, None, None, False,
							 (DispOpt(choosertype=ChooseType.stateval, chooser='state*on',
									  color=('gold', 'blue', 'white'), deflabel=(f,)),
							  DispOpt(choosertype=ChooseType.stateval, chooser='state*off',
									  color=('gold', 'blue', 'black'), deflabel=(f,))),
							 None, 'Debug:' + f))

	flagspercol = hw.screenheight // 120  # todo switch to new screen sizing
	flagsperrow = hw.screenwidth // 120
	flagoverrides = fixedoverrides.copy()
	flagoverrides.update(KeysPerColumn=flagspercol, KeysPerRow=flagsperrow)
	flagscreencnt = 0
	while nflags > 0:  # this needs to have a richer input where the flags have source of their state and a DispOpt
		thisscrn = min(nflags, flagspercol * flagsperrow)
		nflags = nflags - flagspercol * flagsperrow + 1
		tmp = OrderedDict()
		for i in range(thisscrn - 1):  # leave space for next or return
			n = debFlagInput[0][0]
			tmp[n] = debFlagInput.pop(0)

		if nflags > 0:  # will need another flag screen so build a "next"
			tmp['next'] = ('Next', None, None, False, nextdisp, None)
		# 'Next', functools.partial(goto, MaintScreen),False,'')  # this gets fixed below to be a real next
		FlagsScreens.append(MaintScreenDesc('Flags Setting ({})'.format(flagscreencnt), tmp,
											overrides=flagoverrides))  # this needs key descriptors passed in
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

	TopLevel = OrderedDict([('log', ('Show Log', functools.partial(screen.PushToScreen, LogDisp, 'Maint'))),
							('versions', ('Select Version', functools.partial(screen.PushToScreen, Versions, 'Maint'),
										  functools.partial(screen.PushToScreen, VersionsAdv, 'Maint'))),
							('flags', ('Set Flags', functools.partial(screen.PushToScreen, FlagsScreens[0], 'Maint')))])

	if Status is not None:
		TopLevel['status'] = ('Network Consoles', functools.partial(screen.PushToScreen, Status, 'Maint'))
	TopLevel['exit'] = ('Exit/Restart', functools.partial(screen.PushToScreen, Exits, 'Maint'))

	MaintScreen = MaintScreenDesc('Console Maintenance', TopLevel)

	for s in screenset:
		s.userstore.ReParent(MaintScreen)


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
def syncKeytoStore(storeitem, old, new, key, chgsource):
	key.State = new


# noinspection PyUnusedLocal
def setdbg(K):
	st = debug.dbgStore.GetVal(K.name)
	K.State = not st
	K.PaintKey()
	displayupdate.updatedisplay()
	debug.dbgStore.SetVal(K.name, not st)
	K.State = debug.dbgStore.GetVal(K.name)
	# this allows for case where flag gets reset by proc called servicing the set
	K.PaintKey()
	displayupdate.updatedisplay()
	logsupport.Logs.Log("Debug flag ", K.name, ' = ', K.State)


# noinspection PyUnusedLocal
def adjloglevel(K):
	if K.name == "LogLevelUp":
		if config.sysStore.LogLevel < len(logsupport.LogLevels) - 1:
			config.sysStore.LogLevel += 1
	else:
		if config.sysStore.LogLevel > 0:
			config.sysStore.LogLevel -= 1

	debug.DebugFlagKeys["LogLevelUp"].PaintKey()
	debug.DebugFlagKeys["LogLevelDown"].PaintKey()
	logsupport.Logs.Log("Log Level changed via ", K.name, " to ", config.sysStore.LogLevel, severity=ConsoleWarning)
	displayupdate.updatedisplay()


# noinspection PyUnusedLocal
def goto(newscreen):
	SwitchScreen(newscreen, 'Bright', 'Maint goto' + newscreen.name, newstate='Maint')


def PickStartingSpot():
	if config.sysStore.ErrorNotice != -1:
		startat = config.sysStore.ErrorNotice
		config.sysStore.ErrorNotice = -1
		consolestatus.ReportStatus('error ind cleared')
	else:
		startat = 0
	return startat
