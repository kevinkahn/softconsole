import multiprocessing, threading
import time
import logsupport
import config
import os, signal
import pygame
import controlevents

KeepAlive = multiprocessing.Event()
FailsafeInterval = 30 # todo need an injection of a no-op periodically to ensure not just long idle

def NoEventInjector():
	logsupport.Logs.Log('Starting watchdog activity injector')
	while True:
		try:
			now = time.time()
			#print('Inject: {}'.format(now))
			pygame.fastevent.post(pygame.event.Event(controlevents.NOEVENT, {'inject': now}))
			time.sleep(FailsafeInterval/2)
		except Exception as E:
			time.sleep(FailsafeInterval/2)
			pass # spurious exceptions during shutdown
			#logsupport.Logs.Log("NoEvent Injector Exception {}".format(E), severity=logsupport.ConsoleWarning)

def MasterWatchDog():
	while KeepAlive.wait(FailsafeInterval):
		time.sleep(FailsafeInterval)
		KeepAlive.clear()
	try:
		os.kill(config.Console_pid, 0)
	except:
		print('Normal watchdog exit')
		logsupport.Logs.Log("Failsafe watchdog exiting normally")
		return
	logsupport.Logs.Log("Failsafe watchdog saw console go autistic - interrupting {}".format(config.Console_pid))
	os.kill(config.Console_pid, signal.SIGINT)
	time.sleep(3) # wait for exit to complete
	try:
		os.kill(config.Console_pid, 0) # check if console exited - raises exception if it is gone
		logsupport.Logs.Log("Failsafe watchdog interrupt didn't reset - killing {}".format(config.Console_pid))
		os.kill(config.Console_pid, signal.SIGKILL)
		logsupport.Logs.Log("Failsafe exiting after kill attempt")
	except Exception as E:
		logsupport.Logs.Log("Failsafe successfully ended console (pid: {}), failsafe (pid: {}) exiting".format(config.Console_pid, os.getpid()))

Failsafe = multiprocessing.Process(target=MasterWatchDog)
Failsafe.daemon = True
Injector = threading.Thread(target=NoEventInjector)
Injector.daemon = True