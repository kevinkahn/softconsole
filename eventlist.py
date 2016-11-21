from heapq import *
import time
import pygame
from config import debugPrint

Tasks = None

class EventItem(object):
	# basic event has name,dt, abstime,target (screen, proc, something - needed for hash)
	def __init__(self, gpid, name, dt):
		self.gpid = gpid
		self.delay = dt  # delay in seconds
		self.abstime = time.time() + dt
		self.name = name
		self.deleted = False
		debugPrint('EventList', 'Item Created: ', self.gpid, self.name, self.delay)


	def __hash__(self):
		return hash((self.abstime, self.delay, self.gpid, self.name))

	def __eq__(self, other):
		if other == None:
			return False
		return (self.abstime, self.delay, self.gpid, self.name) == (
			other.abstime, other.delay, other.gpid, other.name)

	def __ne__(self, other):
		return not (self == other)

	def __repr__(self):
		return 'gpid: ' + str(self.gpid) + ' name: ' + self.name + ' delay: ' + str(self.delay) + ' del: ' + str(
			self.deleted)


class ScreenEventItem(EventItem):
	def __init__(self, gpid, name, dt, screen):
		EventItem.__init__(self, gpid, name, dt)
		self.screen = screen

	def __repr__(self):
		return EventItem.__repr__(self) + ' Scrren: ' + repr(self.screen.name)


class ProcEventItem(EventItem):
	def __init__(self, gpid, name, dt, proc):
		EventItem.__init__(self, gpid, name, dt)
		self.proc = proc

	def __repr__(self):
		return EventItem.__repr__(self) + ' Proc: ' + repr(self.proc)


class AlertEventItem(EventItem):
	def __init__(self, gpid, name, dt, alert):
		EventItem.__init__(self, gpid, name, dt)
		self.alert = alert

	def __repr__(self):
		return EventItem.__repr__(self) + ' Alert: ' + repr(self.alert)

class EventList(object):
	global faket
	def __init__(self):
		self.List = []
		self.finder = {}
		self.TASKREADY = pygame.event.Event(pygame.USEREVENT)

	def AddTask(self, item):
		debugPrint('EventList', 'Add: ', item.gpid, item.name, item.delay)
		self.finder[item] = item
		heappush(self.List, (item.abstime, item))
		X = self.TimeToNext()
		pygame.time.set_timer(self.TASKREADY.type, X)  #self.TimeToNext())


	def RemoveTask(self, item):
		debugPrint('EventList', 'Remove: ', item.gpid, item.name)
		self.finder[item].deleted = True

	def _TopItem(self):
		try:
			acttime, item = self.List[0]
			while item.deleted is True:
				debugPrint('EventList', 'Flush deleted: ', item.gpid, item.name)
				heappop(self.List)
				del self.finder[item]
				acttime, item = self.List[0]
			return (acttime, item)
		except IndexError:
			return None

	def TimeToNext(self):
		# time in milliseconds to next task
		T = self._TopItem()
		if T is not None:
			return int(round((T[0] - time.time())*1000))
		else:
			return 0

	def PopTask(self):
		epsilon = 0.01
		T = self._TopItem()
		if T is not None:
			DiffToSched = T[0] - time.time()
			if DiffToSched <= epsilon:  # task is due
				I = heappop(self.List)[1]
				del self.finder[I]
				nextdelay = self.TimeToNext()
				pygame.time.set_timer(self.TASKREADY.type, nextdelay)
				debugPrint('EventList', 'Pop: ', I.gpid, I.name, I.delay, ' Nextdelay: ', nextdelay)
				return I
			else:  # we are early for some reason so just repost a wakeup
				pygame.time.set_timer(self.TASKREADY.type, int(round(DiffToSched*1000 + .5)))
				debugPrint('EventList', 'Early wake: ', DiffToSched, self.List)
				return None
		else:
			pygame.time.set_timer(self.TASKREADY.type, 0)  # there is no next item
			debugPrint('EventList', 'Clear timer on list empty')
			return None

	def RemoveAllScreen(self, gpid):
		# remove all events where screen is this screen
		for e in self.finder:
			if e.gpid == gpid:
				self.RemoveTask(e)


				# add debug option to print (flag=timerq) name, screen.name, abstime, dt, deleted, hidden
				# add to create, add?, next, remove, remove all - will create lots of output = throttle sommehow?
