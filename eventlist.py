from heapq import *
import time
import pygame
from config import debugPrint

# faket = 99
Tasks = None

class EventItem(object):
	def __init__(self, screen, id, name, dt, proc, hidden=False):
		self.screen = screen
		self.id = id
		self.delay = dt  # delay in seconds
		#self.abstime = faket + dt
		self.abstime = time.time() + dt
		self.proc = proc  # proc to call on event firing
		self.name = name
		self.hidden = hidden  # no need to exit previous screen
		self.deleted = False
		debugPrint('EventList', 'Item Created: ', self.screen.name, self.id, self.name, self.delay)


	def __hash__(self):
		return hash((self.abstime, self.delay, self.screen, self.name))

	def __eq__(self, other):
		if other == None:
			return False
		return (self.abstime, self.delay, self.screen, self.name) == (
		other.abstime, other.delay, other.screen, other.name)

	def __ne__(self, other):
		return not (self == other)


class EventList(object):
	global faket
	def __init__(self):
		self.List = []
		self.finder = {}
		self.TASKREADY = pygame.event.Event(pygame.USEREVENT)

	def AddTask(self, item):
		debugPrint('EventList', 'Add: ', item.screen.name, item.id, item.name, item.delay)
		self.finder[item] = item
		heappush(self.List, (item.abstime, item))
		X = self.TimeToNext()
		pygame.time.set_timer(self.TASKREADY.type, X)  #self.TimeToNext())


	def RemoveTask(self, item):
		debugPrint('EventList', 'Remove: ', item.screen, item.id, item.name)
		self.finder[item].deleted = True

	def _TopItem(self):
		try:
			acttime, item = self.List[0]
			while item.deleted is True:
				debugPrint('EventList', 'Flush deleted: ', item.screen, item.id, item.name)
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
				debugPrint('EventList', 'Pop: ', I.screen.name, I.id, I.name, I.delay, ' Nextdelay: ', nextdelay)
				return I
			else:  # we are early for some reason so just repost a wakeup
				pygame.time.set_timer(self.TASKREADY.type, int(round(DiffToSched*1000 + .5)))
				debugPrint('EventList', 'Early wake: ', DiffToSched, self.List)
				return None
		else:
			pygame.time.set_timer(self.TASKREADY.type, 0)  # there is no next item
			debugPrint('EventList', 'Clear timer on list empty')
			return None

	def RemoveAllScreen(self, screen):
		# remove all events where screen is this screen
		for e in self.finder:
			if e.screen == screen:
				self.RemoveTask(e)


				# add debug option to print (flag=timerq) name, screen.name, abstime, dt, deleted, hidden
				# add to create, add?, next, remove, remove all - will create lots of output = throttle sommehow?
