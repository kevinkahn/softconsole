import multiprocessing
import os
import signal
import time
import timers

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


def MasterWatchDog():
	signal.signal(signal.SIGTERM, signal.SIG_DFL)  # don't want the sig handlers from the main console
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	logsupport.DevPrint('Master Watchdog Started {}'.format(os.getpid()))
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
		os.kill(config.Console_pid, 0)
	except:
		logsupport.DevPrint('Normal watchdog exit')
		# logsupport.Logs.Log("Failsafe watchdog exiting normally")
		return
	logsupport.DevPrint('Failsafe interrupt {}'.format(config.Console_pid))
	# logsupport.Logs.Log("Failsafe watchdog saw console go autistic - interrupting {}".format(config.Console_pid))
	os.kill(config.Console_pid, signal.SIGINT)
	time.sleep(3)  # wait for exit to complete
	try:
		os.kill(config.Console_pid, 0)  # check if console exited - raises exception if it is gone
		logsupport.DevPrint("Failsafe watchdog interrupt didn't reset - killing {}".format(config.Console_pid))
		# logsupport.Logs.Log("Failsafe watchdog interrupt didn't reset - killing {}".format(config.Console_pid))
		os.kill(config.Console_pid, signal.SIGKILL)
		logsupport.DevPrint("Failsafe exiting after kill attempt")
	# logsupport.Logs.Log("Failsafe exiting after kill attempt")
	except Exception as E:
		print('Failsafe exiting')
		logsupport.DevPrint(
			"Failsafe successfully ended console (pid: {}), failsafe (pid: {}) exiting (Exc: {})".format(config.Console_pid,
																							   os.getpid(),repr(E)))
	# logsupport.Logs.Log("Failsafe successfully ended console (pid: {}), failsafe (pid: {}) exiting".format(config.Console_pid, os.getpid()))
	logsupport.DevPrint('Watchdog exiting')
