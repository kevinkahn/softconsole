from heapq import *
import time
import pygame
from config import debugPrint

Tasks = None

class EventItem(object):
	# basic event has name,dt, abstime,target (screen, proc, something - needed for hash)
	def __init__(self, gpid, name):
		self.gpid = gpid
		# self.delay = -1  # delay in seconds filled in when added to list
		self.abstime = 0  # set when added
		self.name = name
		self.deleted = False

	def __hash__(self):
		return id(self)  # hash((self.delay, self.gpid, self.name))

	def __eq__(self, other):
		if other == None:
			return False
		return (self.abstime, self.gpid, self.name) == (
			other.abstime, other.gpid, other.name)

	def __ne__(self, other):
		return not (self == other)

	def __repr__(self):
		return 'gpid: ' + str(self.gpid) + ' name: ' + self.name + ' del: ' + str(
			self.deleted)


class ProcEventItem(EventItem):
	def __init__(self, gpid, name, proc):
		EventItem.__init__(self, gpid, name)
		self.proc = proc
		debugPrint('EventList', ' Proc Item Created: ', self)

	def __repr__(self):
		return EventItem.__repr__(self) + ' Proc: ' + repr(self.proc)


class AlertEventItem(EventItem):
	def __init__(self, gpid, name, alert):
		EventItem.__init__(self, gpid, name)
		self.alert = alert
		debugPrint('EventList', ' Alert Item Created: ', self)

	def __repr__(self):
		return EventItem.__repr__(self) + ' Alert: ' + repr(self.alert)

class EventList(object):
	def __init__(self):
		self.BaseTime = 0
		self.List = []
		self.finder = {}
		self.TASKREADY = pygame.event.Event(pygame.USEREVENT)

	def PrettyTime(self, t):
		return t - self.BaseTime

	def PrettyList(self, list):
		plist = ''
		for t, item in enumerate(list):
			plist = plist + '\n--------------------' + str(t) + str(self.PrettyTime(item[0])) + str(item)

	def RelNow(self):
		return time.time() - self.BaseTime

	def AddTask(self, item, dt):
		if self.BaseTime == 0: self.BaseTime = time.time()
		debugPrint('EventList', self.RelNow(), ' Add: ', dt, item)
		self.finder[item] = item
		item.abstime = time.time() + dt
		heappush(self.List, (item.abstime, item))
		pygame.time.set_timer(self.TASKREADY.type, self.TimeToNext())


	def RemoveTask(self, item):
		debugPrint('EventList', self.RelNow(), ' Remove: ', item)
		self.finder[item].deleted = True

	def _TopItem(self):
		try:
			acttime, item = self.List[0]
			while item.deleted is True:
				debugPrint('EventList', self.RelNow(), ' Flush deleted: ', item)
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
				debugPrint('EventList', self.RelNow(), ' Pop: ', I, ' Nextdelay: ', nextdelay)
				return I
			else:  # we are early for some reason so just repost a wakeup
				pygame.time.set_timer(self.TASKREADY.type, int(round(DiffToSched*1000 + .5)))
				debugPrint('EventList', self.RelNow(), ' Early wake: ', DiffToSched, self.PrettyList(self.List))
				return None
		else:
			pygame.time.set_timer(self.TASKREADY.type, 0)  # there is no next item
			debugPrint('EventList', self.RelNow(), ' Clear timer on list empty')
			return None

	def RemoveAllScreen(self, gpid):
		# remove all events where screen is this screen
		for e in self.finder:
			if e.gpid == gpid:
				self.RemoveTask(e)


				# add debug option to print (flag=timerq) name, screen.name, abstime, dt, deleted, hidden
				# add to create, add?, next, remove, remove all - will create lots of output = throttle sommehow?
