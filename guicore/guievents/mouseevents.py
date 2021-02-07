from guicore.displayscreen import EventDispatch, NewMouse
from enum import Enum
from queue import Empty
from controlevents import CEvent, TimedGetEvent
import guicore.guiutils as guiutils
import debug
import logsupport
from logsupport import ConsoleWarning
import guicore.screenmgt as screenmgt
import guicore.switcher as switcher
import config
import screens.__screens as screens
from screens import screen, maintscreen
import math
import utils.hw as hw

MouseStates = Enum('MouseStates', 'idle downwait upwait swallowup')

mousestate = MouseStates.idle
longtaptime = config.sysStore.LongTapTime / 1000
tapcount = 0
lastdowneventtime = 0
lastmovetime = 0
mousemoved = False
pos = (0, 0)
motionpos = (0, 0)
longtap = False


def _MoveDist(x, y):
	return math.sqrt((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2)


screendiag = _MoveDist((hw.screenheight, hw.screenwidth), (0, 0))

dumptime = 0


def DumpEvent(event):
	global dumptime
	try:
		# print('Interval: {} Event: {} State: {} Long: {}'.format(event.mtime - dumptime, event, mousestate, longtap))
		dumptime = event.mtime
	except Exception:
		pass


def MouseDown(event):
	global mousestate, lastdowneventtime, tapcount, pos, motionpos, lastmovetime, mousemoved, longtap
	DumpEvent(event)
	guiutils.HBEvents.Entry('MouseDown {} @ {}'.format(str(event.pos), event.mtime))
	debug.debugPrint('Touch', 'MouseDown' + str(event.pos) + repr(event))
	# screen touch events; this includes touches to non-sensitive area of screen
	screenmgt.SetActivityTimer(config.AS.DimTO, 'Screen touch')
	# refresh non-dimming in all cases including non=sensitive areas
	# this refresh is redundant in some cases where the touch causes other activities

	if screenmgt.DimState() == 'Dim':
		# wake up the screen and if in a cover state go home swallow next Up
		config.sysStore.consolestatus = 'active'
		mousestate = MouseStates.swallowup
		if screenmgt.screenstate == 'Cover':
			switcher.SwitchScreen(screens.HomeScreen, 'Bright', 'Wake up from cover', newstate='Home')
		else:
			screenmgt.Brighten()  # if any other screen just brighten
		return  # wakeup touches are otherwise ignored

	if mousestate == MouseStates.idle:
		# initial down event and screen was not dim so the touch was meaningful
		pos = event.pos
		motionpos = pos
		mousemoved = False
		longtap = False
		tapcount = 1
		mousestate = MouseStates.upwait
		lastdowneventtime = event.mtime
		lastmovetime = event.mtime
	elif mousestate == MouseStates.downwait:
		# have seen at least one down then up
		lastdowneventtime = event.mtime
		tapcount += 1
		mousestate = MouseStates.upwait
	else:
		logsupport.Logs.Log('Got mouse down in unexpected state: {} ({})'.format(mousestate, event),
							severity=ConsoleWarning)
		mousestate = MouseStates.swallowup


def MouseUp(event):
	global mousestate, longtap
	DumpEvent(event)
	if mousestate == MouseStates.swallowup:
		# meaningless up event - probably on return from dim
		mousestate = MouseStates.idle
		longtap = False
	elif mousestate == MouseStates.upwait:
		# set up for next down
		longtap = event.mtime - lastdowneventtime > longtaptime
		mousestate = MouseStates.downwait
	else:
		# go back to base condition for new down
		logsupport.Logs.Log('Got mouse up in unexpected state: {} ({})'.format(mousestate, event),
							severity=ConsoleWarning)
		mousestate = MouseStates.idle
		longtap = False


def MouseIdle(event):
	global mousestate, longtap
	DumpEvent(event)
	if mousestate in (MouseStates.upwait, MouseStates.swallowup):
		# long press timeout just ignore - will get another idle after the up
		return
	else:  # downwait or idle so process the tap/taps
		if tapcount > 1 or not longtap:
			ProcessTap(tapcount, pos)
		else:
			# long tap
			# uppos = event.pos
			# dist = _MoveDist(uppos, pos)
			# print('Dn: {}  Up: {} Dist: {} Diag:{} Pct: {}'.format(pos, uppos, dist, screendiag, dist / screendiag))
			ProcessTap(-1, pos)
		mousestate = MouseStates.idle
		longtap = False
		return


def CompressMotion(event):
	global motionpos, lastmovetime, mousemoved
	if _MoveDist(motionpos, event.pos) > 10 or event.mtime - lastmovetime > 1:
		# print('Move to {} {} {}'.format(event.pos,_MoveDist(motionpos, event.pos),event.mtime - lastmovetime))
		motionpos = event.pos
		lastmovetime = event.mtime
		mousemoved = True
		if config.AS.WatchMotion:
			config.AS.Motion(event.pos)
	else:
		pass
	#print('Suppress at {} last {} {}'.format(event.pos, motionpos, _MoveDist(motionpos, event.pos)))


def MouseMotion(event):
	global mousestate
	DumpEvent(event)
	if mousestate == MouseStates.idle:
		# ignore random move events - appear to come from resistive screens
		return
	if mousestate not in (MouseStates.upwait, MouseStates.swallowup):
		logsupport.Logs.Log('Mouse motion while in odd state {} ({})'.format(mousestate, event),
							severity=ConsoleWarning)
		return
	CompressMotion(event)

def GoToMaint():
	if screenmgt.screenstate == 'Maint':
		# ignore if already in Maint
		logsupport.Logs.Log('Maintenance taps ignored - already in Maint mode')
		return
	# Go to maintenance
	logsupport.Logs.Log('Entering Console Maintenance')
	screen.PushToScreen(maintscreen.MaintScreen, newstate='Maint', msg='Push to Maint')
	return


def ProcessTap(tapcnt, pos):
	global motionpos
	# print('Process {} {}'.format(tapcnt,pos))
	if tapcnt == 3:
		if screenmgt.screenstate == 'Maint':
			# ignore triple taps if in maintenance mode
			logsupport.Logs.Log('Secondary chain taps ignored - in Maint mode')
			return
		# Switch screen chains
		if screens.HomeScreen != screens.HomeScreen2:  # only do if there is a real secondary chain
			if screenmgt.Chain == 0:
				screenmgt.Chain = 1
				switcher.SwitchScreen(screens.HomeScreen2, 'Bright', 'Chain switch to secondary',
									  newstate='NonHome')
			else:
				screenmgt.Chain = 0
				switcher.SwitchScreen(screens.HomeScreen, 'Bright', 'Chain switch to main',
									  newstate='Home')
		return

	elif 3 < tapcnt < 8:
		GoToMaint()
		return

	elif tapcnt >= 8:
		# print('Multitap {}'.format(tapcnt))
		logsupport.Logs.Log('Runaway {} taps - likely hardware issue'.format(tapcnt),
							severity=ConsoleWarning, hb=True)
		return

	if mousemoved:
		if _MoveDist(pos, (0, 0)) < 80 and _MoveDist(pos, motionpos) / screendiag > .70:
			GoToMaint()
			return
		else:
			pass
		# print('Not diag {} {} {} {}'.format(_MoveDist(pos, (0, 0)), _MoveDist(pos, motionpos), pos, motionpos))

	if config.AS.Keys is not None:
		for K in config.AS.Keys.values():
			if K.touched(pos):
				K.Pressed(tapcnt)
				return

	for K in config.AS.NavKeys.values():
		if K.touched(pos):
			K.Proc()
			return


if NewMouse:
	EventDispatch[CEvent.MouseDown] = MouseDown
	EventDispatch[CEvent.MouseUp] = MouseUp
	EventDispatch[CEvent.MouseMotion] = MouseMotion
	EventDispatch[CEvent.MouseIdle] = MouseIdle
