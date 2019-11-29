import queue
import time
from enum import Enum
import timers

import psutil
import historybuffer

import config
import logsupport

# noinspection PyArgumentList
CEvent = Enum('ConsoleEvent',
			  'FailSafePing ACTIVITYTIMER HubNodeChange ISYAlert ISYVar GeneralRepaint RunProc SchedEvent MouseDown MouseUp MouseMotion')

ConsoleOpsQueue = queue.Queue()  # master sequencer

latencynotification = 1000 # notify if a loop latency is greater than this
LateTolerance = 2.5  # for my systems
QLengthTrigger = 5

HBControl = historybuffer.HistoryBuffer(80, 'Control')


def PostEvent(e):
	if e is None:
		logsupport.Logs.Log('Pushing None event to queue', severity=logsupport.ConsoleError, tb=True, hb=True)
		return
	cpu = psutil.Process(config.sysStore.Console_pid).cpu_times()
	e.addtoevent(QTime=time.time(), usercpu=cpu.user, syscpu=cpu.system)
	ConsoleOpsQueue.put(e)
	HBControl.Entry('Post {} queuesize: {}'.format(e,ConsoleOpsQueue.qsize()))


def GetEvent():
	global latencynotification
	qs = ConsoleOpsQueue.qsize()
	if qs > QLengthTrigger:
		tq = ConsoleOpsQueue.queue
		HBControl.Entry('Long queue {}: {}'.format(qs, tq))
		print('Queue({}: {}'.format(qs, tq))
	try:
		evnt = ConsoleOpsQueue.get(block=True,timeout=120) # timeout is set to twice the failsafe injection time so should never see it
	except queue.Empty:
		logsupport.DevPrint('Queue wait timeout')
		HBControl.Entry("Main loop timeout - inserting ping event")
		evnt = ConsoleEvent(CEvent.FailSafePing,inject=time.time(),QTime=time.time())
		logsupport.Logs.Log('Main queue timeout', severity=logsupport.ConsoleWarning, hb=True)
	if evnt is None: logsupport.Logs.Log('Got none from blocking get', severity=logsupport.ConsoleError, hb=True)
	cpu = psutil.Process(config.sysStore.Console_pid).cpu_times()
	HBControl.Entry("Get: {} queuesize: {}".format(evnt,qs))

	now = time.time()
	if qs >= logsupport.queuedepthmax:
		logsupport.queuedepthmax = qs
		logsupport.queuedepthmaxtime = now
	if qs >= logsupport.queuedepthmax24:
		logsupport.queuedepthmax24 = qs
		logsupport.queuedepthmax24time = now

	qt = time.time() - evnt.QTime
	if qt > logsupport.queuetimemax:
		logsupport.queuetimemax = qt
		logsupport.queuetimemaxtime = now
	if qt > logsupport.queuetimemax24:
		logsupport.queuetimemax24 = qt
		logsupport.queuetimemax24time = now

	if qt > latencynotification:
		HBControl.Entry(
			'Long on queue: {} user: {} system: {} event: {}'.format(time.time() - evnt.QTime, cpu.user - evnt.usercpu,
																	 cpu.system - evnt.syscpu, evnt))
		if not timers.LongOpInProgress:
			logsupport.Logs.Log('Long on queue {} (user: {} sys: {}) event: {}'.format(time.time() - evnt.QTime,
								cpu.user - evnt.usercpu, cpu.system - evnt.syscpu, evnt),
								hb=True, homeonly=True)
	if time.time() - evnt.QTime < 2: # cleared any pending long waiting startup events
		if config.sysStore.versionname in ('development', 'homerelease') and (latencynotification != LateTolerance):  # after some startup stabilisation sensitize latency watch if my system
			latencynotification = LateTolerance
			logsupport.queuedepthmax = 0
			logsupport.queuetimemax = 0
	# logsupport.DevPrint('Set latency tolerance: {}'.format(latencynotification))
	return evnt


def GetEventNoWait():
	try:
		evnt = ConsoleOpsQueue.get(block=False)
	except queue.Empty:
		evnt = None
	return evnt


class ConsoleEvent(object):

	def __init__(self, eventtyp, **kwargs):
		self.__dict__ = kwargs
		self.type = eventtyp

	# if not hasattr(self, 'node'): self.node = None

	def __repr__(self):
		rep = '<ConsoleEvent: {}'.format(self.type.name)
		for atr, val in self.__dict__.items():
			rep = rep + ' {}={}'.format(atr, val)
		return rep + '>'

	def __str__(self):
		return self.__repr__()

	def addtoevent(self, **kwargs):
		self.__dict__.update(**kwargs)
