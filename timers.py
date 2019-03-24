from threading import Thread, Event
import pygame
from controlevents import SchedEvent

TimerList = {}


def AddToTimerList(name, timer):
	global TimerList
	if name not in TimerList:
		TimerList[name] = timer
	else:
		print("Dup Timer Name") # todo make log entry


class RepeatingPost(Thread):
	"""Call a function after a specified number of seconds:

			t = Timer(30.0, f, args=None, kwargs=None)
			t.start()
			t.cancel()     # stop the timer's action if it's still waiting

	"""

	def __init__(self, interval, paused=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		self.interval = interval
		#self.args = args if args is not None else []
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.finished = Event()
		self.running = Event()
		if not paused: self.running.set()
		AddToTimerList(self.name, self)

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		self.running.set()

	def resume(self):
		self.running.set()

	def pause(self):
		self.running.clear()

	def run(self):
		while not self.finished.wait(self.interval):
			if self.running.is_set():
				pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
				#self.function()
			else:
				self.running.wait()
		del TimerList[self.name]


class CountedRepeatingPost(Thread):
	def __init__(self, interval, count, paused=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		self.interval = interval
		#self.args = args if args is not None else []
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.kwargs['initcount'] = count
		self.finished = Event()
		self.count = count
		AddToTimerList(self.name, self)

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()

	def run(self):
		while not self.finished.wait(self.interval) and self.count > 0:
			self.kwargs['count'] = self.count
			self.count -= 1
			pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
		del TimerList[self.name]


class OnceTimer(Thread):
	def __init__(self, interval, paused=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		self.interval = interval
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.finished = Event()
		AddToTimerList(self.name, self)

	def cancel(self):
		self.finished.set()

	def run(self):
		self.finished.wait(self.interval)
		if not self.finished.is_set():
			pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
		self.finished.set()
		del TimerList[self.name]
