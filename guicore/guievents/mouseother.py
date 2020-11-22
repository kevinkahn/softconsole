from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import guicore.guiutils as guiutils
import debug


# ignore for now - handle more complex gestures here if ever needed
def MouseOther(event):
	debug.debugPrint('Touch', 'Other mouse event {}'.format(event))


EventDispatch[CEvent.MouseUp] = MouseOther
EventDispatch[CEvent.MouseMotion] = MouseOther
