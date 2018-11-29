from heapq import *
import time
import pygame
import debug
import logsupport
from logsupport import ConsoleError
import historybuffer

Tasks = None

class EventItem(object):
	# basic event has name,dt, abstime,target (screen, proc, something - needed for hash)
	def __init__(self, gpid, name):
		self.gpid = gpid
		# self.delay = -1  # delay in seconds filled in when added to list
		self.abstime = 0  # set when added
		self.name = name
		self.deleted = False
		self.onlist = False

	def __hash__(self):
		return id(self)  # hash((self.delay, self.gpid, self.name))

	def __eq__(self, other):
		if other is None:
			return False
		return (self.abstime, self.gpid, self.name) == (
			other.abstime, other.gpid, other.name)

	def __ne__(self, other):
		return not (self == other)

	def __repr__(self):
		return 'ID:' + str(id(self)) + ' gpid: ' + str(self.gpid) + ' name: ' + self.name + ' del: ' + str(
			self.deleted) + ' onlist: ' + str(self.onlist) + ' abstm: ' + str(self.abstime)

	def OnList(self):
		return self.onlist


class ProcEventItem(EventItem):
	def __init__(self, gpid, name, proc):
		EventItem.__init__(self, gpid, name)
		self.proc = proc
		debug.debugPrint('EventList', ' Proc Item Created: ', self)

	def __repr__(self):
		return EventItem.__repr__(self) + ' Proc: ' + repr(self.proc)


class AlertEventItem(EventItem):
	def __init__(self, gpid, name, alert):
		EventItem.__init__(self, gpid, name)
		self.alert = alert
		debug.debugPrint('EventList', ' Alert Item Created: ', self)

	def __repr__(self):
		return EventItem.__repr__(self) + ' Alert: ' + repr(self.alert)

class EventList(object):
	def __init__(self):
		self.BaseTime = 0
		self.List = []
		self.finder = {}
		self.TASKREADY = pygame.event.Event(pygame.USEREVENT,{})
		self.HB = historybuffer.HistoryBuffer(100, 'EventList')
		# todo think this could just be the int constant and remove .type below where used

	def StartLongOp(self):
		self.HB.Entry('StartLongOp')
		pygame.time.set_timer(self.TASKREADY.type, 0)

	def EndLongOp(self):
		self.HB.Entry('EndLongOp')
		pygame.time.set_timer(self.TASKREADY.type, self.TimeToNext())

	def PrettyTime(self, t):
		return t - self.BaseTime

	def PrettyList(self, inlist):
		plist = ''
		for t, item in enumerate(inlist):
			plist = plist + '\n--------------------' + str(t) + ' : ' + str(self.PrettyTime(item[0])) + str(item)
		return plist

	def RelNow(self):
		return time.time() - self.BaseTime

	def AddTask(self, evnt, dt):
		self.HB.Entry('AddTask: ' + repr(evnt) + ' DeltaT: ' + str(dt))
		if self.BaseTime == 0: self.BaseTime = time.time()

		self.finder[id(evnt)] = evnt
		for i in self.List:
			if i[1] == evnt:
				logsupport.Logs.Log("Event add task error: ", repr(evnt), severity=ConsoleError, hb=True)
		evnt.abstime = time.time() + dt
		evnt.deleted = False
		evnt.onlist = True
		heappush(self.List, (evnt.abstime, evnt))
		T = self.TimeToNext()
		debug.debugPrint('EventList', self.RelNow(), ' Add: ', dt, evnt, T)
		# debug.debugPrint('EventList', self.RelNow(), ' Add: ', dt, item,T,self.PrettyList(self.List))
		pygame.time.set_timer(self.TASKREADY.type, T)

	def RemoveTask(self, evnt):
		self.HB.Entry('RemoveTask: ' + repr(evnt))
		debug.debugPrint('EventList', self.RelNow(), ' Remove: ', evnt)
		try:
			self.finder[id(evnt)].deleted = True
		except Exception:
			self.HB.Entry('Not on List')
			debug.debugPrint('EventList', self.RelNow(), ' Remove item not on list: : ', evnt)

	def _TopItem(self):
		try:
			acttime, evnt = self.List[0]
			while evnt.deleted is True:
				debug.debugPrint('EventList', "PRE", self.List)
				debug.debugPrint('EventList', self.RelNow(), ' Flush deleted: ', evnt)
				heappop(self.List)
				evnt.onlist = False
				debug.debugPrint('EventList', "POST", self.List)
				try:
					del self.finder[id(evnt)]
				except KeyError:
					debug.debugPrint('EventList', self.RelNow(), 'Extra delete?', evnt)
				acttime, evnt = self.List[0]
			return acttime, evnt
		except IndexError:
			return None

	def TimeToNext(self):
		# time in milliseconds to next task
		T = self._TopItem()
		if T is not None:
			return max(int(round((T[0] - time.time())*1000)), 1)  # always at least 1 millisec if list non-empty
		else:
			return 0

	def PopTask(self):
		epsilon = 0.01
		T = self._TopItem()
		if T is not None:
			DiffToSched = T[0] - time.time()
			if DiffToSched <= epsilon:  # task is due
				self.HB.Entry('PopTask: ' + repr(T))
				I = heappop(self.List)[1]
				I.onlist = False
				del self.finder[id(I)]
				nextdelay = self.TimeToNext()
				pygame.time.set_timer(self.TASKREADY.type, nextdelay)
				debug.debugPrint('EventList', self.RelNow(), ' Pop: ', I, ' Nextdelay: ', nextdelay)
				return I
			else:  # we are early for some reason so just repost a wakeup
				'''
				Note - early wakeups are likely when events happen close together in time.  set_timer actually sets
				a repeating timer so if 2 events are scheduled for essentially the same time, the time to next after the
				first of them will be very short and it is likely to tick a second time before the correct time to next
				is set by the second of the 2 close events.
				'''
				self.HB.Entry('PopTaskEarly: ' + repr(T) + ' Early: ' + str(DiffToSched))
				pygame.time.set_timer(self.TASKREADY.type, int(round(DiffToSched*1000 + .5)))
				debug.debugPrint('EventList', self.RelNow(), ' Early wake: ', DiffToSched, self.PrettyList(self.List))
				return None
		else:
			self.HB.Entry('PopTask Empty')
			pygame.time.set_timer(self.TASKREADY.type, 0)  # there is no next item
			debug.debugPrint('EventList', self.RelNow(), ' Clear timer on list empty')
			return None

	def RemoveAllGrp(self, gpid):
		# remove all events where screen is this screen
		self.HB.Entry('RemoveGp: ' + repr(gpid))
		for e in self.finder.values():
			if e.gpid == gpid:
				self.RemoveTask(e)


