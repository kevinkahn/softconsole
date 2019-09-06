import multiprocessing
import os
import signal
import time
import atexit
import threading

import config
import logsupport as L
from controlevents import CEvent, PostEvent, ConsoleEvent

KeepAlive = multiprocessing.Event()
FailsafeInterval = 60


def DevPrint(msg):
	with open('/home/pi/Console/.HistoryBuffer/hlog', 'a') as f:
		f.write('{}: {}\n'.format(time.time(), msg))
		f.flush()

def TempThreadList():
	'''
	This routine is just for working cleanly with PyCharm IDE.  If you leave a system running that was launched from
	PyCharm, if the PC controlling it goes to sleep it kills the console.  Unfortunately it only partially kills it and
	so leaves zombies and threads running.  This code makes sure everything gets killed so as to not leave connections
	to the ISY which will eventually force it to its limit without manual intervention.
	'''
	time.sleep(10)
	while True:
		L = multiprocessing.active_children()  # clean any zombie failsafe
		# for x in L:
		#	DevPrint('Process {}: alive: {} pid: {} daemon: {}'.format(x.name, x.is_alive(), x.pid, x.daemon))
		threadlist = threading.enumerate()
		for thd in threadlist:
			#DevPrint('Threadlist: {} alive: {} ident: {} daemon: {} \n'.format(thd.name, thd.is_alive(), thd.ident, thd.daemon))
			if thd.name == 'MainThread' and not thd.is_alive():
				DevPrint('Main Thread died')
				os.kill(os.getpid(),signal.SIGINT)  # kill myself

		#DevPrint('=================End')
		time.sleep(30)

def NoEventInjector():
	L.Logs.Log('Starting watchdog activity injector')
	while config.Running:
		# noinspection PyBroadException
		try:
			now = time.time()
			L.Logs.Log('Inject: {}'.format(now), severity=L.ConsoleDetail)
			PostEvent(ConsoleEvent(CEvent.FailSafePing, inject=now))
			time.sleep(FailsafeInterval / 2)
		except Exception as E:
			time.sleep(FailsafeInterval / 2)
			DevPrint('Inject Exception {}'.format(repr(E)))
			# spurious exceptions during shutdown
	DevPrint('Injector exiting')

def EndWatchDog(signum, frame):
	DevPrint('Watchdog ending on shutdown {}'.format(signum))
	os._exit(0)


def WatchdogDying(signum, frame):
	try:
		if signum == signal.SIGTERM:
			DevPrint('Watchdog saw SIGTERM - must be from systemd')
			# console should have also seen this - give it time to shut down
			time.sleep(30)  # we should see a USR1 from console
			os._exit(0)
		else:
			DevPrint('Watchdog dying signum: {} frame: {}'.format(signum, frame))
			try:
				os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
			except:
				pass  # probably main console already gone
			time.sleep(3)
			try:
				os.kill(config.sysStore.Console_pid, signal.SIGKILL)  # with predjudice
			except:
				pass  # probably already gone
			os._exit(0)
	except Exception as E:
		DevPrint('Exception in WatchdogDying: {}'.format(E))
		time.sleep(1)
		os._exit(0)

def failsafedeath():
	DevPrint('Failsafe exit hook')
	DevPrint('failsafedeath {} watching {} at {}'.format(os.getpid(), config.sysStore.Console_pid, time.time()))
	os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
	time.sleep(3)
	os.kill(config.sysStore.Console_pid, signal.SIGKILL) # with predjudice

def IgnoreHUP(signum, frame):
	DevPrint('Watchdog got HUP - ignoring')

def MasterWatchDog():
	signal.signal(signal.SIGTERM, WatchdogDying)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, EndWatchDog)
	signal.signal(signal.SIGUSR1, EndWatchDog)
	signal.signal(signal.SIGHUP, IgnoreHUP)

	#failsafehooks.hook()
	atexit.register(failsafedeath)

	DevPrint('Master Watchdog Started {} for console pid: {}'.format(os.getpid(), config.sysStore.Console_pid))
	runningok = True
	while runningok:
		while KeepAlive.wait(FailsafeInterval):
			KeepAlive.clear()
			time.sleep(FailsafeInterval)
		runningok = False  # no keepalive seen for failsafe interval - try to restart
		DevPrint('No keepalive in failsafe interval')

	DevPrint('Watchdog loop exit: {}'.format(time.time()))
	# noinspection PyBroadException
	try:
		os.kill(config.sysStore.Console_pid, 0)
	except:
		DevPrint('Normal watchdog exit')
		return
	DevPrint('Failsafe interrupt {}'.format(config.sysStore.Console_pid))
	os.kill(config.sysStore.Console_pid, signal.SIGUSR1)
	time.sleep(3)  # wait for exit to complete
	try:
		os.kill(config.sysStore.Console_pid, 0)  # check if console exited - raises exception if it is gone
		DevPrint("Failsafe watchdog interrupt didn't reset - killing {}".format(config.sysStore.Console_pid))
		os.kill(config.sysStore.Console_pid, signal.SIGKILL)
		DevPrint("Failsafe exiting after kill attempt")
	except Exception as E:
		print('Failsafe exiting')
		DevPrint("Failsafe successfully ended console (pid: {}), failsafe (pid: {}) exiting (Exc: {})".format(
			config.sysStore.Console_pid,
																							   os.getpid(),repr(E)))
	DevPrint('Watchdog exiting')
