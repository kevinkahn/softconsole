from threading import Thread, Event
import pygame, time
from controlevents import SchedEvent
import historybuffer
import logsupport

TimerList = {}
TimerHB = historybuffer.HistoryBuffer(100, 'Timers')
LongOpInProgress = False
LongOpStart = {}

def StartLongOp(nm):
	global LongOpInProgress, LongOpStart
	if LongOpInProgress: logsupport.Logs.Log('Overlapped long ops: {} {}'.format(nm, LongOpStart),severity=logsupport.ConsoleWarning)
	LongOpStart[nm] = time.time()
	TimerHB.Entry('Start long op: {}'.format(nm))
	LongOpInProgress = True

def EndLongOp(nm):
	global LongOpInProgress, LongOpStart
	if not LongOpInProgress: logsupport.Logs.Log('End non-existent long op: {} {}'.format(nm, LongOpStart),severity=logsupport.ConsoleWarning)
	TimerHB.Entry('End long op: {} lasted: {}'.format(nm, time.time()-LongOpStart[nm]))
	LongOpStart[nm]= 0
	LongOpInProgress = False

def AddToTimerList(name, timer):
	global TimerList
	if name in TimerList:
		TimerList[name].cancel()
		logsupport.Logs.Log("Duplicate timer name seen: {}".format(name),severity=logsupport.ConsoleWarning,hb=True)
		#print("Dup Timer Name {}".format(name)) # todo make log entry
		while name in TimerList:
			TimerHB.Entry("Waiting timer cancel to complete: {}".format(name))
	TimerList[name] = timer
	printlist = {}
	for n, t in TimerList.items():
		if isinstance(t, RepeatingPost):
			printlist[n] = "Repeater running: {}".format(t.running.is_set())
		elif isinstance(t, CountedRepeatingPost):
			printlist[n] = "Counter: {}".format(t.count)
		elif isinstance(t, OnceTimer):
			printlist[n] = "Once"
		else:
			printlist[n] = "Error?"
	TimerHB.Entry("Timers : {}".format(printlist))
	#print("Timers : {}".format(printlist))

def ShutTimers():
	tList = dict(TimerList)
	for n, t in tList.items():
		if t.is_alive():
			print('Cancel {}'.format(n))
			logsupport.Logs.Log('Shutting down timer: {}:'.format(n))
			t.cancel()
	time.sleep(1)

class RepeatingPost(Thread):
	"""
	Repeatedly post every specified number of seconds:
	"""

	def __init__(self, interval, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry("Created RepeatingPost: {} int: {}  start: {} paused: {} args: {}".format(name, interval, start, paused, kwargs))
		self.interval = interval
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
		TimerHB.Entry("Canceled repeater: {}".format(self.name))

	def resume(self):
		TimerHB.Entry('Resume repeater: {}'.format(self.name))
		self.running.set()

	def pause(self):
		TimerHB.Entry('Pause repeater: {}'.format(self.name))
		self.running.clear()

	def run(self):
		TimerHB.Entry('Start repeater: {}'.format(self.name))
		targettime = time.time() + self.interval
		while not self.finished.wait(self.interval):
			if not self.finished.is_set():
				if self.running.is_set():
					self.kwargs['TargetTime'] = targettime
					TimerHB.Entry('Post repeater: {} diff: {} args: {}'.format(self.name, time.time()- targettime, self.kwargs))
					pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
					targettime += self.interval
					#self.function()
				else:
					self.running.wait()
					targettime = time.time() + self.interval
		del TimerList[self.name]
		TimerHB.Entry('Exit repeater: {}'.format(self.name))


class CountedRepeatingPost(Thread):
	def __init__(self, interval, count, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry(
			"Created CountedRepeatingPost: {} int: {}  count: {} start: {} paused: {} args: {}".format(name, interval,
						count, start, paused, kwargs))
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
		TimerHB.Entry("Canceled counter: {}".format(self.name))

	def run(self):
		TimerHB.Entry('Start counter: {}'.format(self.name))
		targettime = time.time() + self.interval
		while not self.finished.wait(self.interval) and self.count > 0:
			self.kwargs['TargetTime'] = targettime
			self.kwargs['count'] = self.count
			self.count -= 1
			TimerHB.Entry(
				'Post counter: {} diff: {} args: {}'.format(self.name, time.time() - targettime, self.kwargs))
			pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
			targettime += self.interval
		del TimerList[self.name]
		TimerHB.Entry('Exit counter: {}'.format(self.name))


class OnceTimer(Thread):
	def __init__(self, interval, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry(
			"Created OnceTimer: {} int: {}  start: {} paused: {} args: {}".format(name, interval, start, paused,
																					  kwargs))
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
		TimerHB.Entry("Canceled once: {}".format(self.name))

	def run(self):
		TimerHB.Entry('Start once: {}'.format(self.name))
		self.kwargs['TargetTime'] = time.time() + self.interval
		self.finished.wait(self.interval)
		if not self.finished.is_set():
			TimerHB.Entry(
				'Post once: {} diff: {} args: {}'.format(self.name, time.time() - self.kwargs['TargetTime'], self.kwargs))
			pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
		self.finished.set()
		del TimerList[self.name]
		TimerHB.Entry('Exit once: {}'.format(self.name))

