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
import time
from screens import screen, maintscreen
import math
import utils.hw as hw

MouseStates = Enum('MouseStates', 'idle downwait upwait waitinguporlong swallowup')

mousestate = MouseStates.idle
longtaptime = 2
tapcount = 0
lastmeventtime = 0
lastmovetime = 0
mousemoved = False
pos = (0, 0)
motionpos = (0, 0)


def _MoveDist(x, y):
	return math.sqrt((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2)


screendiag = _MoveDist((hw.screenheight, hw.screenwidth), (0, 0))

dumptime = 0
def DumpEvent(event):
	global dumptime
	print('Interval: {} Event: {}'.format(event.mtime-dumptime,event))
	dumptime = event.mtime

def MouseDown(event):
	global mousestate, lastmeventtime, tapcount, pos, motionpos, lastmovetime, mousemoved
	DumpEvent(event)
	guiutils.HBEvents.Entry('MouseDown {} @ {}'.format(str(event.pos), event.mtime))
	debug.debugPrint('Touch', 'MouseDown' + str(event.pos) + repr(event))
	# screen touch events; this includes touches to non-sensitive area of screen
	screenmgt.SetActivityTimer(config.AS.DimTO, 'Screen touch')
	# refresh non-dimming in all cases including non=sensitive areas
	# this refresh is redundant in some cases where the touch causes other activities

	if mousestate != MouseStates.idle:
		logsupport.Logs.Log('Initial Mouse Down when not idle: {}'.format(mousestate), severity=ConsoleWarning)
		mousestate = MouseStates.idle

	if screenmgt.DimState() == 'Dim':
		# wake up the screen and if in a cover state go home swallow next Up
		config.sysStore.consolestatus = 'active'
		mousestate = MouseStates.swallowup
		if screenmgt.screenstate == 'Cover':
			switcher.SwitchScreen(screens.HomeScreen, 'Bright', 'Wake up from cover', newstate='Home')
		else:
			screenmgt.Brighten()  # if any other screen just brighten
		return  # wakeup touches are otherwise ignored

	# Screen was not Dim so the touch was meaningful
	pos = event.pos
	motionpos = pos
	mousemoved = False
	tapcount = 1
	mousestate = MouseStates.upwait
	lastmeventtime = time.time()
	lastmovetime = lastmeventtime
	maxtapinterval = config.sysStore.MultiTapTime / 1000
	while True:
		try:
			# print('Mousewait: {}'.format(maxtapinterval-(time.time()-lastmeventtime)))
			eventx = TimedGetEvent(
				maxtapinterval - (time.time() - lastmeventtime))  # if other events intervene this is technically wrong
		except Empty:
			if mousestate == MouseStates.upwait:
				mousestate = MouseStates.waitinguporlong
			elif mousestate == MouseStates.downwait:
				ProcessTap(tapcount, pos)
				mousestate = MouseStates.idle
			else:
				logsupport.Logs.Log('Weird mouse state {} in down timeout'.format(mousestate), severity=ConsoleWarning)
				mousestate = MouseStates.idle
			return
		# got a mouse event within multi window if up ignore and await the next down
		if eventx.type == CEvent.MouseDown:
			DumpEvent(eventx)
			lastmeventtime = time.time()
			if mousestate == MouseStates.upwait:
				logsupport.Logs.Log('Got Mouse Down while waiting for Up', severity=ConsoleWarning)
			elif mousestate == MouseStates.downwait:
				# multi tap
				tapcount += 1
				mousestate = MouseStates.upwait
		elif eventx.type == CEvent.MouseUp:
			DumpEvent(eventx)
			lastmeventtime = time.time()
			if mousestate == MouseStates.upwait:
				# just swallow
				mousestate = MouseStates.downwait
			else:
				logsupport.Logs.Log('Got Mouse Up while waiting for Down', severity=ConsoleWarning)


		elif eventx.type == CEvent.MouseMotion:
			DumpEvent(eventx)
			lastmeventtime = time.time()
			CompressMotion(eventx)
			guiutils.HBEvents.Entry('Mouse Motion: {}'.format(repr(eventx)))
		elif eventx.type == CEvent.MouseIdle:
			DumpEvent(eventx)
		else:
			guiutils.HBEvents.Entry('Defer' + repr(eventx))
			guiutils.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out


def MouseUp(event):
	global mousestate
	DumpEvent(event)
	if mousestate == MouseStates.swallowup:
		pass
	elif mousestate == MouseStates.waitinguporlong:
		if tapcount > 1 or time.time() - lastmeventtime < longtaptime:
			# either a multitap or short single tap
			print('Got tap {}'.format(tapcount))
			ProcessTap(tapcount, pos)
		else:
			# long tap
			print('Got long')
			uppos = event.pos
			dist = _MoveDist(uppos, pos)
			print('Dn: {}  Up: {} Dist: {} Diag:{} Pct: {}'.format(pos, uppos, dist, screendiag, dist / screendiag))
			ProcessTap(-1, pos)
	else:
		logsupport.Logs.Log('Weird mouse state in MouseUp {}'.format(mousestate), severity=ConsoleWarning)
	mousestate = MouseStates.idle
	return


def CompressMotion(event):
	global motionpos, lastmovetime, mousemoved
	if _MoveDist(motionpos, event.pos) > 20 or time.time() - lastmovetime > 1:
		print('Reportmove: {}, dist {} time: {}'.format(motionpos, _MoveDist(motionpos, event.pos),
														time.time() - lastmovetime))
		motionpos = event.pos
		lastmovetime = time.time()
		mousemoved = True
		if config.AS.WatchMotion:
			config.AS.Motion(event.pos)


def MouseMotion(event):
	DumpEvent(event)
	#logsupport.Logs.Log('Mouse motion while in state {} (Event: {})'.format(mousestate, event), severity=ConsoleWarning)

def MouseIdle(event):
	DumpEvent(event)
	return


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
		logsupport.Logs.Log('Runaway {} taps - likely hardware issue'.format(tapcnt),
							severity=ConsoleWarning, hb=True)
		return

	if mousemoved:
		if _MoveDist(pos, (0, 0)) < 80 and _MoveDist(pos, motionpos) / screendiag > .75:
			print('Maint')
			GoToMaint()
			return
		else:
			print('Not diag {} {} {} {}'.format(_MoveDist(pos, (0, 0)), _MoveDist(pos, motionpos), pos, motionpos))
			return

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
