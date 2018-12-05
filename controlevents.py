import pygame

TASKREADY = pygame.USEREVENT
ACTIVITYTIMER = pygame.USEREVENT + 1
HubNodeChange = pygame.USEREVENT + 2  # Node state change in a current screen watched node on the ISY
ISYAlert = pygame.USEREVENT + 3  # Mpde state change in watched node for alerts
ISYVar = pygame.USEREVENT + 4  # Var value change for a watched variable on ISY
GeneralRepaint = pygame.USEREVENT + 5  # force a repaint of current screen
RunProc = pygame.USEREVENT + 6

NOEVENT = pygame.NOEVENT


def PostControl(control, **kwargs):
	pygame.fastevent.post(pygame.event.Event(control, **kwargs))
