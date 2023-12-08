from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import guicore.guiutils as guiutils
import debug
import config
import guicore.screenmgt as screenmgt
import guicore.switcher as switcher
import screens.__screens as screens
import logsupport
from logsupport import ConsoleWarning


# noinspection PyUnusedLocal
def ACTIVITYTIMER(event):
	debug.debugPrint('Dispatch', 'Activity timer fired State=', screenmgt.screenstate, '/', screenmgt.DimState())

	if screenmgt.DimState() == 'Bright':
		guiutils.HBEvents.Entry('ActivityTimer(Bright) state: {}'.format(screenmgt.screenstate))
		config.sysStore.consolestatus = 'idle'
		screenmgt.Dim()
		screenmgt.SetActivityTimer(config.AS.PersistTO, 'Go dim and wait persist')
	else:
		guiutils.HBEvents.Entry('ActivityTimer(non-Bright) state: {}'.format(screenmgt.screenstate))
		if screenmgt.screenstate == 'NonHome':
			switcher.SwitchScreen(screens.HomeScreen, 'Dim', 'Dim nonhome to dim home', newstate='Home', clear=True)
		elif screenmgt.screenstate == 'Home':
			switcher.SwitchScreen(screens.DimIdleList[0], 'Dim', 'Go to cover', newstate='Cover',
								  AsCover=True, clear=True)
			# rotate covers - save even if only 1 cover
			screens.DimIdleList = screens.DimIdleList[1:] + [screens.DimIdleList[0]]
			screens.DimIdleTimes = screens.DimIdleTimes[1:] + [screens.DimIdleTimes[0]]
		elif screenmgt.screenstate == 'Cover':
			if len(screens.DimIdleList) > 1:
				switcher.SwitchScreen(screens.DimIdleList[0], 'Dim', 'Go to next cover',
									  newstate='Cover', AsCover=True, clear=True)
				screens.DimIdleList = screens.DimIdleList[1:] + [screens.DimIdleList[0]]
				screens.DimIdleTimes = screens.DimIdleTimes[1:] + [screens.DimIdleTimes[0]]
		elif screenmgt.screenstate == 'Maint':
			# No activity on Maint screens so go home
			switcher.SwitchScreen(screens.HomeScreen, 'Dim', 'Dim maint to dim home', newstate='Home',
								  clear=True)
		else:  # Maint or Alert - just ignore the activity action
			# logsupport.Logs.Log('Activity timer fired while in state: {}'.format(gui.state),severity=ConsoleWarning)
			logsupport.Logs.Log('Activity timeout in unknown state: {}'.format(screenmgt.screenstate),
								severity=ConsoleWarning, hb=True)


EventDispatch[CEvent.ACTIVITYTIMER] = ACTIVITYTIMER
