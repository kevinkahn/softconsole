import queue
import time
from enum import Enum

import psutil

import config
import logsupport

# noinspection PyArgumentList
CEvent = Enum('ConsoleEvent',
			  'FailSafePing ACTIVITYTIMER HubNodeChange ISYAlert ISYVar GeneralRepaint RunProc SchedEvent MouseDown MouseUp MouseMotion')

ConsoleOpsQueue = queue.Queue()  # master sequencer

latencynotification = 1000 # notify if a loop latency is greater than this
LateTolerance = 4 # for my systems


def PostEvent(e):
	if e is None:
		logsupport.Logs.Log('Pushing None event to queue', severity=logsupport.ConsoleError, tb=True, hb=True)
	cpu = psutil.Process(config.Console_pid).cpu_times()
	e.addtoevent(QTime=time.time(), usercpu=cpu.user, syscpu=cpu.system)
	ConsoleOpsQueue.put(e)


def GetEvent():
	global latencynotification
	evnt = ConsoleOpsQueue.get(block=True)
	if evnt is None: logsupport.Logs.Log('Got none from blocking get', severity=logsupport.ConsoleError, hb=True)
	cpu = psutil.Process(config.Console_pid).cpu_times()
	if time.time() - evnt.QTime > latencynotification:
		logsupport.DevPrint(
			'Long on queue: {} user: {} system: {} event: {}'.format(time.time() - evnt.QTime, cpu.user - evnt.usercpu,
																	 cpu.system - evnt.syscpu, evnt))
		logsupport.Logs.Log('Long on queue {} (user: {} sys: {}) event: {}'.format(time.time() - evnt.QTime,
								cpu.user - evnt.usercpu, cpu.system - evnt.syscpu, evnt),
								severity=logsupport.ConsoleWarning, hb=True, localonly=True, homeonly=True)
	if time.time() - evnt.QTime < 2: # cleared any pending long waiting startup events
		if config.versionname in ('development', 'homerelease') and (latencynotification != LateTolerance):  # after some startup stabilisation sensitize latency watch if my system
			latencynotification = LateTolerance
			logsupport.DevPrint('Set latency tolerance: {}'.format(latencynotification))
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

	def __repr__(self):
		rep = '<ConsoleEvent: {}'.format(self.type.name)
		for atr, val in self.__dict__.items():
			rep = rep + ' {}={}'.format(atr, val)
		return rep + '>'

	def __str__(self):
		return self.__repr__()

	def addtoevent(self, **kwargs):
		self.__dict__.update(**kwargs)
