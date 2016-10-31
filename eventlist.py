from heapq import *
import time


class EventItem(object):
	def __init__(self, queue, screen, name, dt, proc, hidden=False):
		self.screen = screen
		self.delay = dt
		self.abstime = time.time() + dt
		self.proc = proc  # proc to call on event firing
		self.name = name
		self.hidden = hidden  # no need to exit previous screen
		self.deleted = False
		queue.AddTask(self)

	def __hash__(self):
		return hash(self)

	def __eq__(self, other):
		return (self.abstime, self) == (other.abstime, other)

	def __ne__(self, other):
		return not (self == other)


class EventList(object):
	def __init__(self):
		self.List = []
		self.finder = {}

	def AddTask(self, item):
		self.finder[item] = item
		heappush(self.List, (item.abstime, item))

	def RemoveTask(self, item):
		entry = self.finder.pop(item)
		item.deleted = True

	def NextTask(self):
		while self.List:
			time, item = heappop(self.List)
			if item.deleted is False:
				del self.finder[item]
				return item

	def RemoveAllScreen(self, screen):
		# remove all events where screen is this screen
		for e in self.finder:
			if e.screen == screen:
				self.RemoveTask(e)


				# add debug option to print (flag=timerq) name, screen.name, abstime, dt, deleted, hidden
				# add to create, add?, next, remove, remove all - will create lots of output = throttle sommehow?
