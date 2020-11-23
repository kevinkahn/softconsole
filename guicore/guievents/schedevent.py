from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import guicore.guiutils as guiutils
import logsupport
import time
import controlevents


def SchedEvent(event):
	if hasattr(event, 'eventvalid') and not event.eventvalid():
		guiutils.HBEvents.Entry('Ignore event that is no longer valid: {}'.format(repr(event)))
		return
	guiutils.HBEvents.Entry('Sched event {}'.format(repr(event)))
	eventnow = time.time()
	diff = eventnow - event.TargetTime
	if abs(diff) > controlevents.latencynotification:
		guiutils.HBEvents.Entry(
			'Event late by {} target: {} now: {}'.format(diff, event.TargetTime, eventnow))
		logsupport.Logs.Log('Timer late by {} seconds. Event: {}'.format(diff, repr(event)),
							hb=True, homeonly=True)
	event.proc(event)


EventDispatch[CEvent.SchedEvent] = SchedEvent
