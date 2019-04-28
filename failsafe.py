import multiprocessing
import os, sys
import signal
import time
import timers
import atexit
import threading

import config
import logsupport
from controlevents import CEvent, PostEvent, ConsoleEvent

KeepAlive = multiprocessing.Event()
FailsafeInterval = 60

def TempThreadList():
	'''
	This routine is just for working cleanly with PyCharm IDE.  If you leave a system running that was launched from
	PyCharm, if the PC controlling it goes to sleep it kills the console.  Unfortunately it only partially kills it and
	so leaves zombies and threads running.  This code makes sure everything gets killed so as to not leave connections
	to the ISY which will eventually force it to its limit without manual intervention.
	'''
	time.sleep(10)
	while True:
		logsupport.AsyncFileWrite('/home/pi/Console/hlog', '=================Start\n')
		L = multiprocessing.active_children()  # clean any zombie failsafe
		for x in L:
			logsupport.AsyncFileWrite('/home/pi/Console/hlog',
									  '{} Process {}: alive: {} pid: {} daemon: {}\n'.format(time.time(), x.name,
											x.is_alive(), x.pid, x.daemon))
		threadlist = threading.enumerate()
		for thd in threadlist:
			logsupport.AsyncFileWrite('/home/pi/Console/hlog','{} Threadlist: {} alive: {} ident: {} daemon: {} \n'.format(time.time(), thd.name, thd.is_alive(), thd.ident, thd.daemon))
			if thd.name == 'MainThread' and not thd.is_alive():
				logsupport.AsyncFileWrite('/home/pi/Console/hlog','Main Thread died\n')
				os.kill(os.getpid(),signal.SIGINT)  # kill myself

		logsupport.AsyncFileWrite('/home/pi/Console/hlog','=================End\n')
		time.sleep(30)

def NoEventInjector():
	logsupport.Logs.Log('Starting watchdog activity injector')
	while config.Running:
		# noinspection PyBroadException
		try:
			now = time.time()
			logsupport.Logs.Log('Inject: {}'.format(now), severity = logsupport.ConsoleDetail)
			#logsupport.DevPrint('Inject: {}'.format(now))
			PostEvent(ConsoleEvent(CEvent.FailSafePing, inject=now))
			time.sleep(FailsafeInterval / 2)
		except Exception as E:
			time.sleep(FailsafeInterval / 2)
			logsupport.DevPrint('Inject Exception {}'.format(repr(E)))
			# spurious exceptions during shutdown
	logsupport.DevPrint('Injector exiting')

def EndWatchDog(signum, frame):
	logsupport.DevPrint('Watchdog ending on shutdown {}'.format(signum))
	os._exit(0)


def WatchdogDying(signum, frame):
	if signum == signal.SIGTERM:
		logsupport.DevPrint('Watchdog saw SIGTERM - must be from systemd')
		# console should have also seen this - give it time to shut down
		time.sleep(30) # we should see a USR1 from console
		os._exit(0)
	else:
		logsupport.DevPrint('Watchdog dying signum: {} frame: {}'.format(signum, frame))
		try:
			os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
		except:
			pass # probably main console already gone
		time.sleep(3)
		try:
			os.kill(config.sysStore.Console_pid, signal.SIGKILL) # with predjudice
		except:
			pass # probably already gone
		os._exit(0)

def failsafedeath():
	logsupport.DevPrint('Failsafe exit hook')
	with open("/home/pi/Console/fsmsg.txt", "a") as f:
		f.writelines('failsafedeath {} watching {} at {}\n'.format(os.getpid(), config.sysStore.Console_pid, time.time()))
	os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
	time.sleep(3)
	os.kill(config.sysStore.Console_pid, signal.SIGKILL) # with predjudice

class ExitHooks(object):
	def __init__(self):
		self.exit_code = None
		self.exception = None
		self._orig_exit = None

	def hook(self):
		self._orig_exit = sys.exit
		sys.exit = self.exit
		sys.excepthook = self.exc_handler

	def exit(self, code=0):
		print('exithookWatchdog {}'.format(code))
		#with open("/home/pi/Console/fsmsg.txt", "a") as f:
		#	f.writelines('failsafe exithook exit {} watching {} at {} code {}\n'.format(os.getpid(), config.sysStore.Console_pid, time.time(),code))
		self.exit_code = code
		self._orig_exit(code)

	def exc_handler(self, exc_type, exc, *args):
		print('exc hdlr {}'.format(exc))
		with open("/home/pi/Console/fsmsg.txt", "a") as f:
			f.writelines('failsafe exithook hdlr {} watching {} at {}\n Exception {}'.format(os.getpid(), config.sysStore.Console_pid, time.time(),repr(exc)))
		self.exception = exc
		sys.__excepthook__(exc_type, exc, args)

#failsafehooks = ExitHooks()

def MasterWatchDog():
	signal.signal(signal.SIGTERM, WatchdogDying)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, EndWatchDog)
	signal.signal(signal.SIGUSR1, EndWatchDog)
	signal.signal(signal.SIGHUP, signal.SIG_IGN)

	#failsafehooks.hook()
	atexit.register(failsafedeath)

	logsupport.DevPrint('Master Watchdog Started {} for console pid: {}'.format(os.getpid(),config.sysStore.Console_pid))
	runningok = True
	while runningok:
		while timers.LongOpStart['maintenance'] != 0:
			logsupport.DevPrint('Failsafe suspended while in maintenance mode')
			time.sleep(120)
		while KeepAlive.wait(FailsafeInterval):
			logsupport.DevPrint('Watchdog ok: {}'.format(time.time()))
			KeepAlive.clear()
			time.sleep(FailsafeInterval)

		if timers.LongOpStart['maintenance'] == 0:  runningok = False  # not in maintenance mode and not acting alive
	logsupport.DevPrint('Watchdog loop exit: {}'.format(time.time()))
	# noinspection PyBroadException
	try:
		os.kill(config.sysStore.Console_pid, 0)
	except:
		logsupport.DevPrint('Normal watchdog exit')
		# logsupport.Logs.Log("Failsafe watchdog exiting normally")
		return
	logsupport.DevPrint('Failsafe interrupt {}'.format(config.sysStore.Console_pid))
	# logsupport.Logs.Log("Failsafe watchdog saw console go autistic - interrupting {}".format(config.sysStore.Console_pid))
	os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
	time.sleep(3)  # wait for exit to complete
	try:
		os.kill(config.sysStore.Console_pid, 0)  # check if console exited - raises exception if it is gone
		logsupport.DevPrint("Failsafe watchdog interrupt didn't reset - killing {}".format(config.sysStore.Console_pid))
		# logsupport.Logs.Log("Failsafe watchdog interrupt didn't reset - killing {}".format(config.sysStore.Console_pid))
		os.kill(config.sysStore.Console_pid, signal.SIGKILL)
		logsupport.DevPrint("Failsafe exiting after kill attempt")
	# logsupport.Logs.Log("Failsafe exiting after kill attempt")
	except Exception as E:
		print('Failsafe exiting')
		logsupport.DevPrint(
			"Failsafe successfully ended console (pid: {}), failsafe (pid: {}) exiting (Exc: {})".format(config.sysStore.Console_pid,
																							   os.getpid(),repr(E)))
	# logsupport.Logs.Log("Failsafe successfully ended console (pid: {}), failsafe (pid: {}) exiting".format(config.sysStore.Console_pid, os.getpid()))
	logsupport.DevPrint('Watchdog exiting')
