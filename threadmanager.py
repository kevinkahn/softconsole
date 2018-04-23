import logsupport
from logsupport import ConsoleWarning
import threading

HelperThreads = {}

class ThreadItem(object):
	def __init__(self, name, proc, prestart, poststart, prerestart, postrestart, checkok):
		self.name = name
		self.seq = 0
		self.Proc = proc # base procedure of thread
		self.PreStartThread = prestart
		self.PostStartThread = poststart
		self.PreRestartThread = prerestart
		self.PostRestartThread = postrestart
		self.Thread = None
		self.CheckOk = checkok

	def StopThread(self):
		self.Thread.stop()

def SetUpHelperThread(name, proc, prestart=None, poststart=None, prerestart=None, postrestart=None, checkok=None):
	HelperThreads[name] = ThreadItem(name,proc,prestart,poststart,prerestart,postrestart,checkok)

def DoRestart(T):
	T.seq += 1
	logsupport.Logs.Log("Restarting helper thread (", T.seq, ") for: ", T.name)
	if T.PreRestartThread is not None: T.PreRestartThread()
	T.Thread = threading.Thread(name=T.name, target=T.Proc)
	T.Thread.setDaemon(True)
	T.Thread.start()
	if T.PostRestartThread is not None: T.PostRestartThread()

def CheckThreads():
	for T in HelperThreads.values():
		if not T.Thread.is_alive(): # or T.ServiceNotOK this would be an optional procedure to do semantic checking a la heartbeat
			logsupport.Logs.Log("Thread for: "+T.name+" is dead",severity=ConsoleWarning)
			DoRestart(T)
		if T.CheckOk is not None:
			if not T.CheckOk():
				T.StopThread()
				logsupport.Logs.Log("Thread for: "+T.name+" reports not ok; stopping/restarting",severity=ConsoleWarning)
				DoRestart(T)

def StartThreads():
	for T in HelperThreads.values():
		T.seq += 1
		logsupport.Logs.Log("Starting helper thread (", T.seq,") for: ", T.name)
		if T.PreStartThread is not None: T.PreStartThread()
		T.Thread = threading.Thread(name=T.name, target=T.Proc)
		T.Thread.setDaemon(True)
		T.Thread.start()
		if T.PostStartThread is not None: T.PostStartThread()




