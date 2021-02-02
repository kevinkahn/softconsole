from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import debug


# ignore for now - handle more complex gestures here if ever needed
def MouseOther(event):
	debug.debugPrint('Touch', 'Other mouse event {}'.format(event))


if CEvent.MouseUp not in EventDispatch:
	EventDispatch[CEvent.MouseUp] = MouseOther
if CEvent.MouseMotion not in EventDispatch:
	EventDispatch[CEvent.MouseMotion] = MouseOther
if CEvent.MouseIdle not in EventDispatch:
	EventDispatch[CEvent.MouseIdle] = MouseOther
