import threading
import time

import logsupport
from utils.exitutils import FatalError
from logsupport import ConsoleWarning

HelperThreads = {}
Watcher = None
ThreadStarted = False


class ThreadStartException(Exception):
	pass


class ThreadItem(object):
	def __init__(self, name, proc, prestart, poststart, prerestart, postrestart, checkok, rpterr=True):
		self.name = name
		self.seq = 0
		self.Proc = proc  # base procedure of thread
		self.PreStartThread = prestart
		self.PostStartThread = poststart
		self.PreRestartThread = prerestart
		self.PostRestartThread = postrestart
		self.Thread = None
		self.CheckOk = checkok
		self.ReportError = rpterr


#	def StopThread(self):
#		self.Thread.stop()

def SetUpHelperThread(name, proc, prestart=None, poststart=None, prerestart=None, postrestart=None, checkok=None,
					  rpterr=True):
	global HelperThreads, ThreadStarted
	HelperThreads[name] = ThreadItem(name, proc, prestart, poststart, prerestart, postrestart, checkok, rpterr)
	if ThreadStarted: StartThread(HelperThreads[name])


def DeleteHelperThread(name):
	global HelperThreads
	del HelperThreads[name]


def DoRestart(T):
	T.seq += 1
	logsupport.Logs.Log("Restarting helper thread (", T.seq, ") for: ", T.name)
	for i in range(10):
		try:
			if T.PreRestartThread is not None: T.PreRestartThread()
			T.Thread = threading.Thread(name=T.name, target=T.Proc, daemon=True)
			T.Thread.start()
			if T.PostRestartThread is not None: T.PostRestartThread()
			return True
		except ThreadStartException:
			logsupport.Logs.Log("Problem restarting helper thread (", T.seq, ") for: ", T.name)
	return False


def CheckThreads():
	try:
		for T in HelperThreads.values():
			if not T.Thread.is_alive():  # or T.ServiceNotOK this would be an optional procedure to do semantic checking a la heartbeat
				rpt = T.ReportError if not callable(T.ReportError) else T.ReportError()
				logsupport.Logs.Log("Thread for: " + T.name + " is dead",
									severity=ConsoleWarning if rpt else logsupport.ConsoleInfo)
				if not DoRestart(T):
					# Fatal Error
					FatalError("Unrecoverable helper thread error(is_alive): " + T.name)
			if T.CheckOk is not None:
				if not T.CheckOk():
					# T.StopThread()
					logsupport.Logs.Log("Thread for: " + T.name + " reports not ok; stopping/restarting",
										severity=ConsoleWarning)
					if not DoRestart(T):
						# Fatal Error
						FatalError("Unrecoverable helper thread error(CheckOK): " + T.name)
	except Exception as E:
		logsupport.Logs.Log("Check threads fatal error: {}".format(repr(E)))


def StartThread(T):
	T.seq += 1
	logsupport.Logs.Log("Starting helper thread (", T.seq, ") for: ", T.name)
	if T.PreStartThread is not None: T.PreStartThread()
	T.Thread = threading.Thread(name=T.name, target=T.Proc, daemon=True)
	T.Thread.start()
	if T.PostStartThread is not None: T.PostStartThread()


def StartThreads():
	global ThreadStarted
	global Watcher

	for T in HelperThreads.values():
		StartThread(T)
	Watcher = threading.Thread(name='Watcher', target=Watch, daemon=True)
	Watcher.start()
	ThreadStarted = True


def Watch():
	while True:
		CheckThreads()
		time.sleep(2)
