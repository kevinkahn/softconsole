from threading import Thread, Event
import time
from controlevents import *
import historybuffer
import logsupport
import config, os, signal

TimerList = {}
TimerHB = historybuffer.HistoryBuffer(100, 'Timers')
LongOpInProgress = False
LongOpStart = {}

def StartLongOp(nm):
	global LongOpInProgress, LongOpStart
	print('StartLO {}'.format(nm))
	if nm not in LongOpStart: LongOpStart[nm] = 0
	if LongOpStart[nm] != 0:
		logsupport.Logs.Log('Long op start within existing long op for {} {}'.format(nm, LongOpStart), severity=logsupport.ConsoleWarning)
	LongOpStart[nm] = time.time()
	LongOpInProgress = any(LongOpStart.values())
	TimerHB.Entry('Start long op: {} {} {}'.format(nm, LongOpInProgress, LongOpStart))
	print('Start long op: {} {} {}'.format(nm, LongOpInProgress, LongOpStart))


def EndLongOp(nm):
	global LongOpInProgress, LongOpStart
	print('EndLO {}'.format(nm))
	if LongOpStart[nm] == 0: logsupport.Logs.Log('End non-existent long op: {} {}'.format(nm, LongOpStart),severity=logsupport.ConsoleWarning)
	LongOpStart[nm] = 0
	LongOpInProgress = any(LongOpStart.values())
	TimerHB.Entry('End long op: {} lasted: {}'.format(nm, time.time()-LongOpStart[nm]))
	print('End long op: {} {} {}'.format(nm, LongOpInProgress, LongOpStart))

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
	#print("Timers : {}".format(printlist)) todo delete all printlist stuff

def KillMe():
	print("Failsafe hit")
	logsupport.Logs.log("Failsafe hit")
	time.sleep(1)
	os.kill(config.Console_pid,signal.SIGKILL)


def ShutTimers(loc):
	failsafe = OnceTimer(10.0,start=False,name='Failsafe',proc=KillMe)
	del TimerList['Failsafe']
	failsafe.daemon = True
	failsafe.start()
	tList = dict(TimerList)
	for n, t in tList.items():
		if t.is_alive():
			logsupport.Logs.Log('Shutting down timer: {}'.format(n))
			t.cancel()
	logsupport.Logs.Log('All timers shut down {}'.format(loc))

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
		self.cumulativeslip = 0 # for analysis purposes

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		self.running.set()

		temp = 5
		while self.is_alive():
			TimerHB.Entry("Cancelling repeater: {}".format(self.name))
			time.sleep(.1) # wait for thread to finish to avoid any late activations causing races
			temp -= 1
			if temp < 0:
				logsupport.Logs.Log("RepeatingPost {} won't cancel finished: {} running: {}".format(self.name,self.finished.is_set(),self.running.is_set()),severity=logsupport.ConsoleError,hb=True,tb=False)
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
		while not self.finished.wait(self.interval):
			if not self.finished.is_set():
				if self.running.is_set():
					self.kwargs['TargetTime'] = targettime
					diff = time.time()- targettime
					self.cumulativeslip += diff
					TimerHB.Entry('Post repeater: {} diff: {} cumm: {} args: {}'.format(self.name, diff, self.cumulativeslip, self.kwargs))
					pygame.fastevent.post(pygame.event.Event(SchedEvent, **self.kwargs))
					tt = ConsoleEvent(CEvent.SchedEvent,**self.kwargs)
					#print('RR: {}'.format(repr(tt)))
					PostEvent(tt)
					targettime = time.time() + self.interval # don't accumulate errors
				else:
					self.running.wait()
					targettime = time.time() + self.interval
		del TimerList[self.name]
		TimerHB.Entry('Exit repeater: {}'.format(self.name))

class ResettableTimer(Thread):
	'''
	Timer that can be reset to a new event and time; note that due to race conditions the old event my fire even if the
	new event seems to be set before the firing time so the validity  must be checked before actually processing if executing early is an issue
	'''
	def __init__(self, start=False, name='', **kwargs):
		Thread.__init__(self, name=name)
		TimerHB.Entry("Created ResettableTimer: {} start: {} args: {}".format(name, start, kwargs))
		self.interval = 0
		self.kwargs = kwargs if kwargs is not None else {}
		self.kwargs['name'] = name
		self.finished = Event()
		AddToTimerList(self.name, self)
		self.eventtopost = None
		self.changingevent = Event()
		self.changedone = Event()
		if start: self.start()

	def cancel(self):
		"""Stop the timer if it hasn't finished yet."""
		self.finished.set()
		self.changingevent.set()

		temp = 5
		while self.is_alive():
			TimerHB.Entry("Cancelling resettable: {}".format(self.name))
			time.sleep(.1) # wait for thread to finish to avoid any late activations causing races
			temp -= 1
			if temp < 0:
				logsupport.Logs.Log("Resettable {} won't cancel finished: {} running: {}".format(self.name,self.finished.is_set(),self.running.is_set()),severity=logsupport.ConsoleError,hb=True,tb=False)
				return
		TimerHB.Entry("Canceled resettable: {}".format(self.name))

	def set(self,event,delta):
		self.newevent = event
		self.newdelta = delta
		self.changingevent.set()
		#print('Wait till done {} {}'.format(delta, event))
		self.changedone.wait()
		#print('Change Done')
		self.changedone.clear()


	def run(self):
		TimerHB.Entry('Start resettable: {}'.format(self.name))
		while True:
			while self.interval == 0:
				self.changingevent.wait() # there is not event time set
				self.eventtopost = self.newevent
				self.interval = self.newdelta
				self.changingevent.clear() # new values copied up so assuming non-zero interval should proceed to wait in next statement
				self.changedone.set()
			while not self.changingevent.wait(self.interval):  #enter while loop if interval ends
				TimerHB.Entry('Post resettable: {}'.format(self.eventtopost))
				#print('Fired: {}'.format(self.eventtopost))
				PostEvent(self.eventtopost)
				#self.interval = 0
				#self.eventtopost = None
			# get here if changingevent got set - either new values ready or canceling timer
			if self.finished.is_set(): break # shutting down requires cancel to set first finished then changing to insure this is set here
			self.eventtopost = self.newevent
			self.interval = self.newdelta
			self.changingevent.clear()
			self.changedone.set()
			# otherwise back to waiting for a non-zero interval to set


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
			PostEvent(ConsoleEvent(CEvent.SchedEvent, **self.kwargs))
		self.finished.set()
		del TimerList[self.name]
		TimerHB.Entry('Exit once: {}'.format(self.name))

