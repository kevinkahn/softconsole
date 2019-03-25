from threading import Thread, Event
import pygame, time
from controlevents import SchedEvent

TimerList = {}


def AddToTimerList(name, timer):
	global TimerList
	if name in TimerList:
		TimerList[name].cancel()
		print("Dup Timer Name {}".format(name)) # todo make log entry
		while name in TimerList:
			print('Wait cancel')
	TimerList[name] = timer
	print("Timers : {}".format(list(TimerList.keys())))



class RepeatingPost(Thread):
	"""Call a function after a specified number of seconds:

			t = Timer(30.0, f, args=None, kwargs=None)
			t.start()
			t.cancel()     # stop the timer's action if it's still waiting

	"""

	def __init__(self, interval, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		self.interval = interval
		#self.args = args if args is not None else []
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.finished = Event()
		self.running = Event()
		if not paused: self.running.set()
		AddToTimerList(self.name, self)
		if start: self.start()

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		self.running.set()
		while self.is_alive():
			time.sleep(0) # wait for thread to finish to avoid any late activations causing races

	def resume(self):
		self.running.set()

	def pause(self):
		self.running.clear()

	def run(self):
		targettime = time.time() + self.interval
		while not self.finished.wait(self.interval):
			if not self.finished.is_set():
				if self.running.is_set():
					self.kwargs['TargetTime'] = targettime
					pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
					targettime += self.interval
					#self.function()
				else:
					self.running.wait()
					targettime = time.time() + self.interval
		del TimerList[self.name]


class CountedRepeatingPost(Thread):
	def __init__(self, interval, count, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		self.interval = interval
		#self.args = args if args is not None else []
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.kwargs['initcount'] = count
		self.finished = Event()
		self.count = count
		AddToTimerList(self.name, self)
		if start: self.start()

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		while self.is_alive():
			time.sleep(0)

	def run(self):
		targettime = time.time() + self.interval
		while not self.finished.wait(self.interval) and self.count > 0:
			self.kwargs['TargetTime'] = targettime
			self.kwargs['count'] = self.count
			self.count -= 1
			pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
			targettime += self.interval
		del TimerList[self.name]


class OnceTimer(Thread):
	def __init__(self, interval, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		self.interval = interval
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.finished = Event()
		AddToTimerList(self.name, self)
		if start: self.start()

	def cancel(self):
		self.finished.set()
		while self.is_alive():
			time.sleep(0)

	def run(self):

		self.kwargs['TargetTime'] = time.time() + self.interval
		self.finished.wait(self.interval)
		if not self.finished.is_set():
			pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
		self.finished.set()
		del TimerList[self.name]
