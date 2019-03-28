import pygame


TASKREADY = pygame.USEREVENT
ACTIVITYTIMER = pygame.USEREVENT + 1
HubNodeChange = pygame.USEREVENT + 2  # Node state change in a current screen watched node on the ISY
ISYAlert = pygame.USEREVENT + 3  # Mpde state change in watched node for alerts
ISYVar = pygame.USEREVENT + 4  # Var value change for a watched variable on ISY
GeneralRepaint = pygame.USEREVENT + 5  # force a repaint of current screen
RunProc = pygame.USEREVENT + 6
SchedEvent = pygame.USEREVENT + 7 # Event scheduled by new timer system

names = {TASKREADY:'TASK', ACTIVITYTIMER:'ACTIVITYTIMER',HubNodeChange:'HUBNODECHANGE',ISYAlert:'ISYAlert',ISYVar:'ISYVar',
		 GeneralRepaint:'GeneralRepaint', RunProc:'RunProc', SchedEvent:'ScheduledEvent'}

NOEVENT = pygame.NOEVENT


def NewRepr(self):
		rep = '<ConsoleEvent: {}'.format(names[self.type] if self.type in names else pygame.event.event_name(self.type))
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
