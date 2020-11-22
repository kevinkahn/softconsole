from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import guicore.guiutils as guiutils
import debug
import config
import logsupport
from logsupport import ConsoleWarning


def HubNodeChange(event):
	guiutils.HBEvents.Entry('Hub Change: {}'.format(repr(event)))
	debug.debugPrint('Dispatch', 'Hub Change Event', event)
	if hasattr(event, 'node'):
		if hasattr(event, 'varinfo'):
			print('Event with both var and node {}'.format(event))
			logsupport.Logs.Log('Event with both var and node {}'.format(event),
								severity=ConsoleWarning)
		config.AS.NodeEvent(event)
	elif hasattr(event, 'varinfo'):
		config.AS.VarEvent(event)
	else:
		debug.debugPrint('Dispatch', 'Bad Node Change Event: ', event)
		logsupport.Logs.Log('Node Change Event missing node and varinfo: {} '.format(event),
							severity=ConsoleWarning)


EventDispatch[CEvent.HubNodeChange] = HubNodeChange
