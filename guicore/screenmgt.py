import hw
import config
from controlevents import CEvent, ConsoleEvent
import historybuffer
import timers

dim = 'Bright'


def Dim():
	global dim
	dim = 'Dim'
	hw.GoDim(int(config.sysStore.DimLevel))


def Brighten():
	global dim
	dim = 'Bright'
	hw.GoBright(int(config.sysStore.BrightLevel))


def DimState():
	return dim


ScreenStack = []
screenstate = 'Home'
HBScreens = historybuffer.HistoryBuffer(20, 'Screens')  # history buffer for screen activities
Chain = 0  # which screen chain is active 0: Main chain 1: Secondary Chain

ActivityTimer = timers.ResettableTimer(name='ActivityTimer', start=True)
activityseq = 0


def SetActivityTimer(timeinsecs, dbgmsg):
	global activityseq
	activityseq += 1
	ActivityTimer.set(ConsoleEvent(CEvent.ACTIVITYTIMER, seq=activityseq, msg=dbgmsg), timeinsecs)
