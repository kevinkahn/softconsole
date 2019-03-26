import multiprocessing
import time
import logsupport
import config
import os, signal

KeepAlive = multiprocessing.Event()
FailsafeInterval = 15


def MasterWatchDog():
	logsupport.Logs.Log('Starting master watchdog {} for {}'.format(os.getpid(), config.Console_pid))
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