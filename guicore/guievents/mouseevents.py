from guicore.displayscreen import EventDispatch, NewMouse
from enum import Enum
from controlevents import CEvent
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
import time
import utils.hw as hw
from utils.utilfuncs import safeprint

MouseStates = Enum('MouseStates', 'idle downwait upwait swallowup')

mousestate = MouseStates.idle
longtaptime = config.sysStore.LongTapTime / 1000
tapcount = 0
lastdowneventtime = 0
lastupeventtime = 0
lastmovetime = 0
mousemoved = False
pos = (0, 0)
motionpos = (0, 0)
longtap = False
handledlong = False
waitclearwindow = 1.2
waitcleartime = time.time()


def _MoveDist(x, y):
	return math.sqrt((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2)


screendiag = _MoveDist((hw.screenheight, hw.screenwidth), (0, 0))
uppercorner = _MoveDist((0, 0), (
hw.screenheight * .2, hw.screenwidth * .2))  # Define the upper corner as 20% circle at top left

dumptime = 0
eventseq = []
DumpEvents = False


def DumpEvent(event):
	global dumptime
	if DumpEvents: eventseq.append(
		(event.type, event.pos, lastdowneventtime, event.mtime, mousestate, longtap, tapcount))
	return


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
		tapcount += 1
		mousestate = MouseStates.upwait
	else:
		logsupport.Logs.Log('Got mouse down in unexpected state: {} ({})'.format(mousestate, event),
							severity=ConsoleWarning)
		mousestate = MouseStates.swallowup


def CheckLong(event, reason):
	global longtap, handledlong
	longtap = event.mtime - lastdowneventtime > longtaptime
	if DumpEvents: eventseq.append((reason, event.mtime - lastdowneventtime, waitcleartime))
	if longtap:
		config.resendidle = False
		ProcessTap(-1, pos)
		if DumpEvents: eventseq.append(('Early handle long', pos, tapcount))
		handledlong = True
		return True
	else:
		return False


def MouseUp(event):
	global mousestate, longtap, lastupeventtime, handledlong
	DumpEvent(event)
	lastupeventtime = event.mtime
	if mousestate == MouseStates.swallowup:
		# meaningless up event - probably on return from dim
		mousestate = MouseStates.idle
		longtap = False
	elif mousestate == MouseStates.upwait:
		# set up for next down
		config.resendidle = not CheckLong(event, 'Checklong on Up')
		mousestate = MouseStates.downwait
	else:
		# go back to base condition for new down
		logsupport.Logs.Log('Got mouse up in unexpected state: {} ({})'.format(mousestate, event),
							severity=ConsoleWarning)
		mousestate = MouseStates.idle
		longtap = False


def MouseIdle(event):
	global mousestate, longtap, tapcount, handledlong

	DumpEvent(event)
	if mousestate == MouseStates.swallowup:
		# long press timeout just ignore - will get another idle after the up
		return
	elif mousestate == MouseStates.upwait:
		config.resendidle = not CheckLong(event, 'Checklong on Idle')
	else:  # downwait or idle so process the tap/taps
		config.resendidle = False
		if handledlong:
			handledlong = False
			if DumpEvents: eventseq.append(('Clear handled long', tapcount, pos))
		else:
			ProcessTap(-1 if longtap else tapcount, pos)
		mousestate = MouseStates.idle
		longtap = False
		tapcount = 0
		return


def CompressMotion(event):
	global motionpos, lastmovetime, mousemoved
	if _MoveDist(motionpos, event.pos) > 2 or event.mtime - lastmovetime > 1:
		if DumpEvents: eventseq.append(
			('report', time.time(), event.pos, _MoveDist(motionpos, event.pos), event.mtime - lastmovetime))
		motionpos = event.pos
		lastmovetime = event.mtime
		mousemoved = True
		if config.AS.WatchMotion and (time.time() - waitcleartime > waitclearwindow or not config.noisytouch):
			config.AS.Motion(event.pos)
		else:
			if DumpEvents: eventseq.append(('Motion wait', time.time() - waitcleartime, waitcleartime))
	else:
		if DumpEvents: eventseq.append(
			('squash', time.time(), event.pos, _MoveDist(motionpos, event.pos), event.mtime - lastmovetime))

def MouseMotion(event):
	global mousestate
	DumpEvent(event)
	if mousestate in (MouseStates.idle,):
		# ignore random move events - appear to come from resistive screens
		return
	if mousestate not in (MouseStates.upwait, MouseStates.swallowup, MouseStates.downwait):
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


def ProcessTap(tapcnt, tappos):
	global motionpos, eventseq, waitcleartime
	if tapcnt == 0: return  # sometimes get spurious 0 tap because of a late idle event

	if time.time() - waitcleartime < waitclearwindow and config.noisytouch:
		if DumpEvents: eventseq.append(('Tap wait clear', waitcleartime, time.time() - waitcleartime))
		return

	if config.AS.WatchMotion:
		# if Motion active for screen all taps are single
		if DumpEvents: eventseq.append(('Force multi off', tapcnt))
		tapcnt = 1
	if DumpEvents:
		try:
			for r in eventseq:
				safeprint(r)
			safeprint('--------- {}'.format(tapcnt))
		except Exception as E:
			logsupport.Logs.Log('Development system disconnected ({})'.format(E))
		eventseq = []
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
		if DumpEvents: eventseq.append(('Tap to Maint', tapcnt))
		GoToMaint()
		return

	elif tapcnt >= 8:
		logsupport.Logs.Log('Runaway {} taps - likely hardware issue'.format(tapcnt),
							severity=ConsoleWarning, hb=True)
		return

	if mousemoved:
		if _MoveDist(tappos, (0, 0)) < uppercorner and _MoveDist(tappos,
																 motionpos) / screendiag > .70:
			if DumpEvents: eventseq.append(
				('Gesture to Maint', _MoveDist(tappos, (0, 0)), _MoveDist(tappos, motionpos) / screendiag))
			GoToMaint()
			return
		else:
			movlen = _MoveDist(tappos, motionpos)
			if DumpEvents: eventseq.append(
				('Gesture', tappos, motionpos, _MoveDist(tappos, (0, 0)), movlen, movlen / screendiag, tapcnt))
	# sending up a click - generate a dead time
	waitcleartime = time.time()

	if config.AS.Keys is not None:
		for K in config.AS.Keys.values():
			if K.touched(tappos):
				if DumpEvents: eventseq.append(('Press', tapcnt))
				K.Pressed(tapcnt)
				return

	for K in config.AS.NavKeys.values():
		if K.touched(tappos):
			K.Proc()
			return


if NewMouse:
	EventDispatch[CEvent.MouseDown] = MouseDown
	EventDispatch[CEvent.MouseUp] = MouseUp
	EventDispatch[CEvent.MouseMotion] = MouseMotion
	EventDispatch[CEvent.MouseIdle] = MouseIdle
