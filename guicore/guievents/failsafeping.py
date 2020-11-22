import time
import guicore.guiutils as guiutils
from guicore.displayscreen import EventDispatch
from controlevents import CEvent


def FailSafePing(event):
	guiutils.HBEvents.Entry(
		'Saw NOEVENT {} after injection at {}'.format(time.time() - event.inject, event.inject))


EventDispatch[CEvent.FailSafePing] = FailSafePing
