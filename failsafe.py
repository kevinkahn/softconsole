import multiprocessing
import os, sys
import signal
import time
import timers
import atexit

import config
import logsupport
from controlevents import CEvent, PostEvent, ConsoleEvent

KeepAlive = multiprocessing.Event()
FailsafeInterval = 60


def NoEventInjector():
	logsupport.Logs.Log('Starting watchdog activity injector')
	while True:
		# noinspection PyBroadException
		try:
			now = time.time()
			logsupport.Logs.Log('Inject: {}'.format(now), severity = logsupport.ConsoleDetail)
			logsupport.DevPrint('Inject: {}'.format(now))
			PostEvent(ConsoleEvent(CEvent.FailSafePing, inject=now))
			time.sleep(FailsafeInterval / 2)
		except Exception:
			time.sleep(FailsafeInterval / 2)
			pass  # spurious exceptions during shutdown
	# logsupport.Logs.Log("NoEvent Injector Exception {}".format(E), severity=logsupport.ConsoleWarning)


def WatchdogDying(signum, frame):
	logsupport.DevPrint('Watchdog dying signum: {} frame: {}'.format(signum, frame))
	os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
	time.sleep(3)
	os.kill(config.sysStore.Console_pid, signal.SIGKILL) # with predjudice

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
		print('exithook {}'.format(code))
		with open("/home/pi/Console/fsmsg.txt", "a") as f:
			f.writelines('failsafe exithook exit {} watching {} at {} code {}\n'.format(os.getpid(), config.sysStore.Console_pid, time.time(),code))
		self.exit_code = code
		self._orig_exit(code)

	def exc_handler(self, exc_type, exc, *args):
		print('exc hdlr {}'.format(exc))
		with open("/home/pi/Console/fsmsg.txt", "a") as f:
			f.writelines('failsafe exithook hdlr {} watching {} at {}\n Exception {}'.format(os.getpid(), config.sysStore.Console_pid, time.time(),repr(exc)))
		self.exception = exc
		sys.__excepthook__(exc_type, exc, args)

failsafehooks = ExitHooks()

def MasterWatchDog():
	signal.signal(signal.SIGTERM, WatchdogDying)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	failsafehooks.hook()
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
