import time
from threading import Thread, Event
import threading

import config
import historybuffer
import logsupport
import os
import signal
from controlevents import CEvent, PostEvent, ConsoleEvent

TimerList = {}
TimerHB = historybuffer.HistoryBuffer(100, 'Timers')
LongOpInProgress = False
LongOpStart = {'maintenance': 0}
timersshut = False


def StartLongOp(nm):
	global LongOpInProgress, LongOpStart
	if nm not in LongOpStart: LongOpStart[nm] = 0
	if LongOpStart[nm] != 0:
		logsupport.Logs.Log('Long op start within existing long op for {} {}'.format(nm, LongOpStart),
							severity=logsupport.ConsoleWarning)
	LongOpStart[nm] = time.time()
	LongOpInProgress = any(LongOpStart.values())
	TimerHB.Entry('Start long op: {} {} {}'.format(nm, LongOpInProgress, LongOpStart))


def EndLongOp(nm):
	global LongOpInProgress, LongOpStart
	if LongOpStart[nm] == 0: logsupport.Logs.Log('End non-existent long op: {} {}'.format(nm, LongOpStart),
												 severity=logsupport.ConsoleWarning)
	LongOpStart[nm] = 0
	LongOpInProgress = any(LongOpStart.values())
	TimerHB.Entry('End long op: {} lasted: {}'.format(nm, time.time() - LongOpStart[nm]))


def AddToTimerList(name, timer):
	global TimerList
	if name in TimerList:
		TimerList[name].cancel()
		logsupport.Logs.Log("Duplicate timer name seen: {}".format(name), severity=logsupport.ConsoleWarning, hb=True)
		while name in TimerList:
			TimerHB.Entry("Waiting timer cancel to complete: {}".format(name))
	TimerList[name] = timer
	for i in range(3):
		try:
			tmrs = tuple(t for t in TimerList.keys())
			# tempdel print('Timers: {}'.format(tmrs))
			printlist = {}
			for n in tmrs:
				if isinstance(TimerList[n], RepeatingPost):
					printlist[n] = "Repeater running: {}".format(TimerList[n].running.is_set())
				elif isinstance(TimerList[n], CountedRepeatingPost):
					printlist[n] = "Counter: {}".format(TimerList[n].count)
				elif isinstance(TimerList[n], OnceTimer):
					printlist[n] = "Once"
				elif isinstance(TimerList[n], ResettableTimer):
					printlist[n] = "Resettable"
				else:
					printlist[n] = "Error?"
			TimerHB.Entry("Timers : {}".format(printlist))
			break
		except Exception as E:
			TimerHB.Entry("Creation race: {} for {}".format(i, name))
			logsupport.Logs.Log("Timer list race ({}) for {}, {}".format(E, name, i),
								severity=logsupport.ConsoleWarning, hb=True)
			continue
		logsupport.Logs.Log('Unresolved timer list race for {}'.format(name), severity=logsupport.ConsoleWarning)



def KillMe():
	time.sleep(5)
	if not timersshut:
		TimerHB.Entry("Timer Shutdown Failsafe hit")
		logsupport.DevPrint("Timer Shutdown Failsafe hit")
		#time.sleep(30)
		logsupport.Logs.log("Timer Shutdown Failsafe hit")
		time.sleep(1)
		x=threading.enumerate()
		for t in x: logsupport.DevPrint(t.name)
		os.kill(config.sysStore.Console_pid, signal.SIGKILL)
	else:
		pass
		#logsupport.DevPrint('Timer shutdown failsafe unneeded')


def ShutTimers(loc):
	global timersshut
	failsafe = Thread(name='Failsafe-Shut', target=KillMe)
	failsafe.daemon = True
	failsafe.start()
	tList = dict(TimerList)
	for n, t in tList.items():
		if t.is_alive():
			logsupport.Logs.Log('Shutting down timer: {}'.format(n))
			t.cancel()
	logsupport.Logs.Log('All timers shut down ({})'.format(loc))
	timersshut = True


class RepeatingPost(Thread):
	"""
	Repeatedly post every specified number of seconds:
	"""

	def __init__(self, interval, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry(
			"Created RepeatingPost: {} int: {}  start: {} paused: {} args: {}".format(name, interval, start, paused,
																					  kwargs))
		self.interval = interval
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.kwargs['timer'] = self
		self.finished = Event()
		self.running = Event()
		if not paused: self.running.set()
		AddToTimerList(self.name, self)
		if start: self.start()
		self.cumulativeslip = 0  # for analysis purposes

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		self.running.set()

		temp = 10
		while self.is_alive():
			TimerHB.Entry("Cancelling repeater: {}".format(self.name))
			time.sleep(.1)  # wait for thread to finish to avoid any late activations causing races
			temp -= 1
			if temp < 0:
				logsupport.Logs.Log(
					"RepeatingPost {} won't cancel finished: {} running: {}".format(self.name, self.finished.is_set(),
																					self.running.is_set()),
					severity=logsupport.ConsoleError, hb=True, tb=False)
				return
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
		loopend = time.time()  # tempdel
		while not self.finished.wait(self.interval):
			TimerHB.Entry('Interval expired: {} {} {} {} {}'.format(self.name, targettime, time.time(), self.interval,
																	time.time() - loopend))  # tempdel
			if not self.finished.is_set():
				if self.running.is_set():
					self.kwargs['TargetTime'] = targettime
					diff = time.time() - targettime
					self.cumulativeslip += diff
					TimerHB.Entry(
						'Post repeater: {} diff: {} cumm: {} args: {}'.format(self.name, diff, self.cumulativeslip,
																			  self.kwargs))
					tt = ConsoleEvent(CEvent.SchedEvent, **self.kwargs)
					PostEvent(tt)
				else:
					self.running.wait()
				targettime = time.time() + self.interval  # don't accumulate errors
				loopend = time.time()  # tempdel
				TimerHB.Entry(
					'Next target: {} {} {} {}'.format(self.name, loopend, targettime, self.interval))  # tempdel
		del TimerList[self.name]
		TimerHB.Entry('Exit repeater: {}'.format(self.name))


class ResettableTimer(Thread):
	"""
	Timer that can be reset to a new event and time; note that due to race conditions the old event my fire even if the
	new event seems to be set before the firing time so the validity  must be checked before actually processing if executing early is an issue
	"""

	def __init__(self, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry("Created ResettableTimer: {} start: {} args: {}".format(name, start, kwargs))
		self.interval = 0
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.kwargs['timer'] = self
		self.finished = Event()
		self.newevent = None # these are used to communicate from set to actual timer loop
		self.newdelta = 999
		AddToTimerList(self.name, self)
		self.eventtopost = None
		self.changingevent = Event()
		self.changedone = Event()
		if start: self.start()

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.newdelta = .01 # force out of loop in run in case waiting an event to appear
		# todo - should it also set self.newevent?
		self.finished.set()
		self.changingevent.set()

		temp = 10
		while self.is_alive():
			TimerHB.Entry("Cancelling resettable: {}".format(self.name))
			time.sleep(.2)  # wait for thread to finish to avoid any late activations causing races
			temp -= 1
			self.changingevent.set()
			if temp < 0:
				logsupport.Logs.Log(
					"Resettable {} won't cancel finished: {} changing: {} changedone: {}".format(self.name,
																								 self.finished.is_set(),
																								 self.changingevent.is_set(),
																								 self.changedone.is_set()),
					severity=logsupport.ConsoleError, hb=True, tb=False)
				return
		TimerHB.Entry("Canceled resettable: {}".format(self.name))

	def set(self, event, delta):
		if self.finished.is_set(): return
		self.newevent = event
		self.newdelta = delta
		self.changingevent.set()
		self.changedone.wait()
		self.changedone.clear()

	def run(self):
		TimerHB.Entry('Start resettable: {}'.format(self.name))
		while True:
			while self.interval == 0:
				self.changingevent.wait()  # there is not event time set
				self.eventtopost = self.newevent
				self.interval = self.newdelta
				self.changingevent.clear()  # new values copied up so assuming non-zero interval should proceed to wait in next statement
				self.changedone.set()
			while not self.changingevent.wait(self.interval):  # enter while loop if interval ends
				TimerHB.Entry('Post resettable: {}'.format(self.eventtopost))
				PostEvent(self.eventtopost)
			#print('loop exit changing event')
			# get here if changingevent got set - either new values ready or canceling timer
			if self.finished.is_set():
				#print('finishing')
				break  # shutting down requires cancel to set first finished then changing to insure this is set here
			self.eventtopost = self.newevent
			#print('Newdelta: {}'.format(self.newdelta))
			self.interval = self.newdelta
			self.changingevent.clear()
			self.changedone.set()
		# otherwise back to waiting for a non-zero interval to set

		del TimerList[self.name]
		TimerHB.Entry('Exit resettable: {}'.format(self.name))


class CountedRepeatingPost(Thread):
	def __init__(self, interval, count, paused=False, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry(
			"Created CountedRepeatingPost: {} int: {}  count: {} start: {} paused: {} args: {}".format(name, interval,
																									   count, start,
																									   paused, kwargs))
		self.interval = interval
		# self.args = args if args is not None else []
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.kwargs['initcount'] = count
		self.kwargs['timer'] = self
		self.finished = Event()
		self.count = count
		AddToTimerList(self.name, self)
		if start: self.start()

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		while self.is_alive():
			time.sleep(0.1)
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
			PostEvent(ConsoleEvent(CEvent.SchedEvent, **self.kwargs))
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
		self.kwargs['timer'] = self
		self.finished = Event()
		AddToTimerList(self.name, self)
		if start: self.start()

	def cancel(self):
		self.finished.set()
		while self.is_alive():
			time.sleep(0.1)
		TimerHB.Entry("Canceled once: {}".format(self.name))

	def run(self):
		TimerHB.Entry('Start once: {}'.format(self.name))
		self.kwargs['TargetTime'] = time.time() + self.interval
		self.finished.wait(self.interval)
		if not self.finished.is_set():
			TimerHB.Entry(
				'Post once: {} diff: {} args: {}'.format(self.name, time.time() - self.kwargs['TargetTime'],
														 self.kwargs))
			PostEvent(ConsoleEvent(CEvent.SchedEvent, **self.kwargs))
		self.finished.set()
		del TimerList[self.name]
		TimerHB.Entry('Exit once: {}'.format(self.name))
