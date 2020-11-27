from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import guicore.guiutils as guiutils


def RunProc(event):
	if hasattr(event, 'params'):
		guiutils.HBEvents.Entry('Run procedure {} with params {}'.format(event.name, event.params))
		event.proc(event.params)
	else:
		guiutils.HBEvents.Entry('Run procedure {}'.format(event.name))
		event.proc()


EventDispatch[CEvent.RunProc] = RunProc
