from guicore.displayscreen import EventDispatch
from controlevents import CEvent
import guicore.guiutils as guiutils
import debug
import config


def GeneralRepaint(event):
	guiutils.HBEvents.Entry('General Repaint: {}'.format(repr(event)))
	debug.debugPrint('Dispatch', 'General Repaint Event', event)
	config.AS.ReInitDisplay()


EventDispatch[CEvent.GeneralRepaint] = GeneralRepaint
