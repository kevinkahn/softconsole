import time
import queue
from enum import Enum
import traceback,sys
import config, hw
import psutil
import logsupport



CEvent = Enum('ConsoleEvent', 'FailSafePing ACTIVITYTIMER HubNodeChange ISYAlert ISYVar GeneralRepaint RunProc SchedEvent MouseDown MouseUp MouseMotion')

ConsoleOpsQueue = queue.Queue() # master sequencer

firsttime = True

def PostEvent(e):
	if e is None:
		print('Push None!')
		traceback.print_stack(file=sys.stdout)
	cpu = psutil.Process(config.Console_pid).cpu_times()
	e.addtoevent(QTime=time.time(),usercpu = cpu.user, syscpu = cpu.system)
	ConsoleOpsQueue.put(e)

def GetEvent():
	global firsttime
	#print('Event Wait')
	evnt = ConsoleOpsQueue.get(block=True) # put the drop test here todo
	if evnt is None: print('Got a none from blockng get!')
	#print('Got Event: {}'.format(evnt))
	if hw.hostname in ('rpi-kck','rpi-dev7'):
		cpu = psutil.Process(config.Console_pid).cpu_times()
		if time.time() - evnt.QTime > 1.5:
			print('Long on queue: {} user: {} system: {} event: {}'.format(time.time()-evnt.QTime, cpu.user - evnt.usercpu, cpu.system - evnt.syscpu, evnt))
			if not firsttime:
				logsupport.Logs.Log('Long on queue (user: {} sys: {}) event: {}'.format(time.time()-evnt.QTime, cpu.user - evnt.usercpu, cpu.system - evnt.syscpu, evnt),severity=logsupport.ConsoleWarning,hb=True)
			firsttime = False # todo hack
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
			rep = rep + ' {}={}'.format(atr,val)
		return rep+'>'

	def __str__(self):
		return self.__repr__()

	def addtoevent(self,**kwargs):
		self.__dict__.update(**kwargs)

