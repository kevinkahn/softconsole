from guicore.displayscreen import EventDispatch
import guicore.guiutils as guiutils
from controlevents import CEvent
import debug
import logsupport
from logsupport import ConsoleDetail, ConsoleWarning
import timers
import alertsystem.alerttasks as alerttasks
import guicore.switcher as switcher
import screens.__screens as screens

TimerName = 0


def AlertEvents(event):
	global TimerName
	guiutils.HBEvents.Entry('Var or Alert' + repr(event))
	evtype = 'variable' if event.type == CEvent.ISYVar else 'node'
	debug.debugPrint('Dispatch', 'ISY ', evtype, ' change', event)
	alert = event.alert
	if alert.state in ('Armed', 'Init'):
		if alert.trigger.IsTrue():  # alert condition holds
			if alert.trigger.delay != 0:  # delay invocation
				alert.state = 'Delayed'
				debug.debugPrint('Dispatch', "Post with delay:", alert.name, alert.trigger.delay)
				TimerName += 1
				alert.timer = timers.OnceTimer(alert.trigger.delay, start=True,
											   name='MainLoop' + str(TimerName),
											   proc=alerttasks.HandleDeferredAlert, param=alert)
			else:  # invoke now
				alert.state = 'FiredNoDelay'
				debug.debugPrint('Dispatch', "Invoke: ", alert.name)
				alert.Invoke()  # either calls a proc or enters a screen and adjusts alert state appropriately
		else:
			if alert.state == 'Armed':
				# condition cleared after alert rearmed  - timing in the queue?
				logsupport.Logs.Log('Anomolous Trigger clearing while armed: ', repr(alert),
									severity=ConsoleDetail, hb=True)
			else:
				alert.state = 'Armed'
				logsupport.Logs.Log('Initial var value for trigger is benign: ', repr(alert),
									severity=ConsoleDetail)
	elif alert.state == 'Active' and not alert.trigger.IsTrue():  # alert condition has cleared and screen is up
		debug.debugPrint('Dispatch', 'Active alert cleared', alert.name)
		alert.state = 'Armed'  # just rearm the alert
		switcher.SwitchScreen(screens.HomeScreen, 'Dim', 'Cleared alert', newstate='Home')
	elif alert.state == 'Active' and alert.trigger.IsTrue():  # alert condition changed but is still true
		pass
	elif ((alert.state == 'Delayed') or (alert.state == 'Deferred')) and not alert.trigger.IsTrue():
		# condition changed under a pending action (screen or proc) so just cancel and rearm
		if alert.timer is not None:
			alert.timer.cancel()
			alert.timer = None
		else:
			logsupport.DevPrint('Clear with no timer?? {}'.format(repr(alert)))
		debug.debugPrint('Dispatch', 'Delayed event cleared before invoke', alert.name)
		alert.state = 'Armed'
	else:
		logsupport.Logs.Log("Anomolous change situation  State: ", alert.state, " Alert: ", repr(alert),
							" Trigger IsTue: ",
							alert.trigger.IsTrue(), severity=ConsoleWarning, hb=True)
		debug.debugPrint('Dispatch', 'ISYVar/ISYAlert passing: ', alert.state, alert.trigger.IsTrue(),
						 event,
						 alert)


# Armed and false: irrelevant report
# Active and true: extaneous report - can happen if value changes but still is in range of true
# Delayed or deferred and true: redundant report

EventDispatch[CEvent.ISYVar] = AlertEvents
EventDispatch[CEvent.ISYAlert] = AlertEvents
