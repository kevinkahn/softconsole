import pygame
import queue
from enum import Enum
import traceback,sys

CEvent = Enum('ConsoleEvent', 'FailSafePing ACTIVITYTIMER HubNodeChange ISYAlert ISYVar GeneralRepaint RunProc SchedEvent MouseDown MouseUp MouseMotion')



FailSafePing = pygame.USEREVENT
ACTIVITYTIMER = pygame.USEREVENT + 1
HubNodeChange = pygame.USEREVENT + 2  # Node state change in a current screen watched node on the ISY
ISYAlert = pygame.USEREVENT + 3  # Mpde state change in watched node for alerts
ISYVar = pygame.USEREVENT + 4  # Var value change for a watched variable on ISY
GeneralRepaint = pygame.USEREVENT + 5  # force a repaint of current screen
RunProc = pygame.USEREVENT + 6
SchedEvent = pygame.USEREVENT + 7 # Event scheduled by new timer system

names = {FailSafePing:'FailSafe', ACTIVITYTIMER:'ACTIVITYTIMER',HubNodeChange:'HUBNODECHANGE',ISYAlert:'ISYAlert',ISYVar:'ISYVar',
		 GeneralRepaint:'GeneralRepaint', RunProc:'RunProc', SchedEvent:'ScheduledEvent'}

NOEVENT = pygame.NOEVENT

ConsoleOpsQueue = queue.Queue() # master sequencer

def PostEvent(e):
	if e is None:
		print('Push None!')
		traceback.print_stack(file=sys.stdout)
	ConsoleOpsQueue.put(e)

def GetEvent():
	#print('Event Wait')
	evnt = ConsoleOpsQueue.get(block=True) # put the drop test here todo
	if evnt is None: print('Got a none from blockng get!')
	#print('Got Event: {}'.format(evnt))
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




def NewRepr(self):
		rep = '<Fastevent: {}'.format(names[self.type] if self.type in names else pygame.event.event_name(self.type))
		if hasattr(self, 'name'): rep = rep + ' name: {}'.format(self.name)
		if hasattr(self, 'inject'): rep = rep + ' inject: {}'.format(self.inject)
		if hasattr(self,'TargetTime'): rep = rep + ' TargetTime: {}'.format(self.TargetTime)
		if hasattr(self, 'alert'): rep = rep + ' alert: {}'.format(self.alert)
		return rep+'>'


#ConsoleEvent = pygame.event.Event
'''			
			(pygame.event.EventType):

	def __init__(self, eventyp, *args, **kwargs):
		pygame.event.EventType.__init__(eventyp, *args, **kwargs)

	def __repr__(self):
		rep = '<ConsoleEvent: {}'.format(names[self.type])
		if hasattr(self, 'name'): rep = rep + ' name: {}'.format(self.name)
		if hasattr(self, 'inject'): rep = rep + ' inject: {}'.format(self.inject)
		if hasattr(self,'TargetTime'): rep = rep + ' TargetTime: {}'.format(self.TargetTime)
		if hasattr(self, 'alert'): rep = rep + ' alert: {}'.format(self.alert)
		return rep+'>'
	def __str__(self):
		return self.__repr__()
'''

def PostControl(control, **kwargs):
	pygame.fastevent.post(pygame.event.Event(control, **kwargs))
