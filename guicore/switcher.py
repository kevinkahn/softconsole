import logsupport
from logsupport import ConsoleWarning, ConsoleError
import debug
import screens.__screens as screens
import config
import screen
import traceback
import guicore.screenmgt as screenmgt


def SwitchScreen(NS, newdim, reason, *, newstate=None, AsCover=False, push=False, clear=False):
	if newstate is None: newstate = screenmgt.screenstate  # no state change
	if NS == screens.HomeScreen: screenmgt.Chain = 0  # force to Main chain in case coming from secondary
	oldname = 'None' if screenmgt.AS is None else screenmgt.AS.name
	screenmgt.HBScreens.Entry(
		'SwitchScreen old: {} new: {} chain: {} reason: {}'.format(oldname, NS.name, screenmgt.Chain, reason))
	if NS == screenmgt.AS:
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
	elif NS == screen.HOMETOKEN:  # todo add PoppedOver for the stack items
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
			logsupport.Logs.Log('HOME from non stacked screen {}'.format(screenmgt.AS.name), severity=ConsoleWarning)
	elif NS == screen.SELFTOKEN:
		NS = screenmgt.AS
	else:
		# simple switch - if there is an existing stack should it be cleared? Probably not unless in stack traverses are prohibited todo
		if clear:
			for S in screenmgt.ScreenStack:
				S.PopOver()
			screenmgt.ScreenStack = []
		if push:
			screenmgt.ScreenStack.append(screenmgt.AS)

	NavKeys = NS.DefaultNavKeysShowing if not AsCover else False
	# noinspection PyUnresolvedReferences
	ASname = '*None*' if screenmgt.AS is None else screenmgt.AS.name
	screenmgt.HBScreens.Entry(
		NS.name + ' was ' + ASname + ' dim: ' + str(newdim) + ' state: ' + str(newstate) + ' reason: ' + str(
			reason))
	config.sysStore.CurrentScreen = NS.name
	oldstate = screenmgt.screenstate
	olddim = screenmgt.DimState()
	if NS == screens.HomeScreen:  # always force home state on move to actual home screen
		newstate = 'Home'

	if screenmgt.AS is not None and screenmgt.AS != NS:
		debug.debugPrint('Dispatch', "Switch from: ", screenmgt.AS.name, " to ", NS.name, "Nav=", NavKeys, ' State=',
						 oldstate + '/' + newstate + ':' + olddim + '/' + newdim, ' ', reason)
		screenmgt.AS.Active = False
		screenmgt.AS.ExitScreen(
			push)  # todo should we call exit even on same screen recall? add via push and add PoppedOver
	screenmgt.AS = NS
	screenmgt.AS.Active = True
	if newdim == 'Dim':
		screenmgt.Dim()
		if olddim == 'Dim':
			if newstate == 'Cover':
				# special case persist
				screenmgt.SetActivityTimer(screens.DimIdleTimes[0], reason + ' using cover time')
			else:
				screenmgt.SetActivityTimer(screenmgt.AS.PersistTO, reason)
		else:
			screenmgt.SetActivityTimer(screenmgt.AS.DimTO, reason)

	elif newdim == 'Bright':
		screenmgt.Brighten()
		screenmgt.SetActivityTimer(screenmgt.AS.DimTO, reason)
	else:
		pass  # leave dim as it

	screenmgt.AS.NavKeysShowing = NavKeys
	if NavKeys:
		if screenmgt.ScreenStack:
			nav = {'homekey': screenmgt.AS.homekey, 'backkey': screenmgt.AS.backkey}
		else:
			nav = {'prevkey': screenmgt.AS.prevkey, 'nextkey': screenmgt.AS.nextkey}
	else:
		nav = {}

	screenmgt.screenstate = newstate

	debug.debugPrint('Dispatch', "New watchlist(Main): " + str(screenmgt.AS.HubInterestList))

	# if OS == screenmgt.AS:
	#	print('Double dispatch: {}'.format(screenmgt.AS.name))
	try:
		screenmgt.AS.InitDisplay(nav)
	except Exception as e:
		logsupport.Logs.Log('Screen display error: ', screenmgt.AS.name, ' ', repr(e), severity=ConsoleError)
		traceback.print_exc()
# todo should this be just logged and return to home?
