from guicore.displayscreen import EventDispatch
from controlevents import CEvent, GetEventNoWait
import guicore.guiutils as guiutils
import debug
import logsupport
from logsupport import ConsoleWarning
import guicore.screenmgt as screenmgt
import guicore.switcher as switcher
import config
import screens.__screens as screens
import time
import screen
import maintscreen


def MouseDown(event):
	guiutils.HBEvents.Entry('MouseDown' + str(event.pos))
	debug.debugPrint('Touch', 'MouseDown' + str(event.pos) + repr(event))
	# screen touch events; this includes touches to non-sensitive area of screen
	screenmgt.SetActivityTimer(config.AS.DimTO, 'Screen touch')
	# refresh non-dimming in all cases including non=sensitive areas
	# this refresh is redundant in some cases where the touch causes other activities

	if screenmgt.DimState() == 'Dim':
		# wake up the screen and if in a cover state go home
		config.sysStore.consolestatus = 'active'
		if screenmgt.screenstate == 'Cover':
			switcher.SwitchScreen(screens.HomeScreen, 'Bright', 'Wake up from cover', newstate='Home')
		else:
			screenmgt.Brighten()  # if any other screen just brighten
		return  # wakeup touches are otherwise ignored

	# Screen was not Dim so the touch was meaningful
	pos = event.pos
	tapcount = 1
	time.sleep(config.sysStore.MultiTapTime / 1000)
	while True:
		eventx = GetEventNoWait()
		if eventx is None:
			break
		elif eventx.type == CEvent.MouseDown:
			guiutils.HBEvents.Entry('Follow MouseDown: {}'.format(repr(eventx)))
			debug.debugPrint('Touch', 'Follow MouseDown' + str(event.pos) + repr(event))
			tapcount += 1
			time.sleep(config.sysStore.MultiTapTime / 1000)
		else:
			if eventx.type in (CEvent.MouseUp, CEvent.MouseMotion):
				debug.debugPrint('Touch', 'Other event: {}'.format(repr(eventx)))
				guiutils.HBEvents.Entry('Mouse Other: {}'.format(repr(eventx)))
			else:
				guiutils.HBEvents.Entry('Defer' + repr(eventx))
				guiutils.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out
	# Future add handling for hold here with checking for MOUSE UP etc.
	if tapcount == 3:
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

	elif 3 < tapcount < 8:
		if screenmgt.screenstate == 'Maint':
			# ignore if already in Maint
			logsupport.Logs.Log('Maintenance taps ignored - already in Maint mode')
			return
		# Go to maintenance
		logsupport.Logs.Log('Entering Console Maintenance')
		screen.PushToScreen(maintscreen.MaintScreen, newstate='Maint', msg='Push to Maint')
		return
	elif tapcount >= 8:
		logsupport.Logs.Log('Runaway {} taps - likely hardware issue'.format(tapcount),
							severity=ConsoleWarning, hb=True)
		return

	if config.AS.Keys is not None:
		for K in config.AS.Keys.values():
			if K.touched(pos):
				K.Pressed(tapcount)

	for K in config.AS.NavKeys.values():
		if K.touched(pos):
			K.Proc()


EventDispatch[CEvent.MouseDown] = MouseDown
