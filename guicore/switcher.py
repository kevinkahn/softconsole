import logsupport
from logsupport import ConsoleWarning, ConsoleError
import debug
import screens.__screens as screens
import config
from screens import screen
import traceback
import guicore.screenmgt as screenmgt


def SwitchScreen(NS, newdim, reason, *, newstate=None, AsCover=False, push=False, clear=False):
	if newstate is None: newstate = screenmgt.screenstate  # no state change
	if NS == screens.HomeScreen: screenmgt.Chain = 0  # force to Main chain in case coming from secondary
	oldname = 'None' if config.AS is None else config.AS.name
	screenmgt.HBScreens.Entry(
		'SwitchScreen old: {} new: {} chain: {} reason: {}'.format(oldname, NS.name, screenmgt.Chain, reason))
	if NS == config.AS:
		if NS.ScreenType not in ('Alert',):  # screens for which reinvokation can make sense
			debug.debugPrint('Dispatch', 'Null SwitchScreen: ', reason)
			logsupport.Logs.Log(
				'Null switchscreen for {}: {}'.format(NS.name, reason))
			if config.sysStore.versionname in ('development', 'homerelease'):
				logsupport.Logs.Log('Null switch stack:', severity=ConsoleWarning, hb=True)
				for L in traceback.format_stack():
					logsupport.Logs.Log(L.strip())
	if NS == screen.BACKTOKEN:
		if screenmgt.ScreenStack:
			NS = screenmgt.ScreenStack.pop()
		else:
			logsupport.Logs.Log('Screen BACK with empty stack', severity=ConsoleWarning, tb=True)
			NS = screens.HomeScreen
	elif NS == screen.HOMETOKEN:
		if screenmgt.ScreenStack:
			if len(screenmgt.ScreenStack) == 1:  # Home and Back would be the same so go to chain home
				NS = screens.HomeScreen
				screenmgt.ScreenStack[0].PopOver()
				screenmgt.ScreenStack = []
			else:
				NS = screenmgt.ScreenStack[0]
				for S in screenmgt.ScreenStack[1:]:
					S.PopOver()
				screenmgt.ScreenStack = []
		else:
			NS = screens.HomeScreen
			# noinspection PyUnresolvedReferences
			logsupport.Logs.Log('HOME from non stacked screen {}'.format(config.AS.name), severity=ConsoleWarning)
	elif NS == screen.SELFTOKEN:
		NS = config.AS
	else:
		if clear:
			for S in screenmgt.ScreenStack:
				S.PopOver()
			screenmgt.ScreenStack = []
		if push:
			screenmgt.ScreenStack.append(config.AS)

	NavKeys = NS.DefaultNavKeysShowing if not AsCover else False
	# noinspection PyUnresolvedReferences
	ASname = '*None*' if config.AS is None else config.AS.name
	screenmgt.HBScreens.Entry(
		NS.name + ' was ' + ASname + ' dim: ' + str(newdim) + ' state: ' + str(newstate) + ' reason: ' + str(
			reason))
	config.sysStore.CurrentScreen = NS.name
	oldstate = screenmgt.screenstate
	olddim = screenmgt.DimState()
	if NS == screens.HomeScreen:  # always force home state on move to actual home screen
		newstate = 'Home'

	if config.AS is not None and config.AS != NS:
		debug.debugPrint('Dispatch', "Switch from: ", config.AS.name, " to ", NS.name, "Nav=", NavKeys, ' State=',
						 oldstate + '/' + newstate + ':' + olddim + '/' + newdim, ' ', reason)
		config.AS.Active = False
		config.AS.ExitScreen(push)
	config.AS = NS
	config.AS.Active = True
	if newdim == 'Dim':
		screenmgt.Dim()
		if olddim == 'Dim':
			if newstate == 'Cover':
				# special case persist
				screenmgt.SetActivityTimer(screens.DimIdleTimes[0], reason + ' using cover time')
			else:
				screenmgt.SetActivityTimer(config.AS.PersistTO, reason)
		else:
			screenmgt.SetActivityTimer(config.AS.DimTO, reason)

	elif newdim == 'Bright':
		screenmgt.Brighten()
		screenmgt.SetActivityTimer(config.AS.DimTO, reason)
	else:
		pass  # leave dim as it

	config.AS.NavKeysShowing = NavKeys
	if NavKeys:
		if screenmgt.ScreenStack:
			nav = {'homekey': config.AS.homekey, 'backkey': config.AS.backkey}
		else:
			nav = {'prevkey': config.AS.prevkey, 'nextkey': config.AS.nextkey}
	else:
		nav = {}

	screenmgt.screenstate = newstate

	debug.debugPrint('Dispatch', "New watchlist(Main): " + str(config.AS.HubInterestList))

	# if OS == screenmgt.AS:
	#	safeprint('Double dispatch: {}'.format(screenmgt.AS.name))
	try:
		config.AS.InitDisplay(nav)
	except Exception as e:
		logsupport.Logs.Log('Screen display error: ', config.AS.name, ' ', repr(e), severity=ConsoleError)
		traceback.print_exc()

