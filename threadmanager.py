import logsupport
from logsupport import ConsoleWarning

HelperThreads = {}

class ThreadItem(object):
	def __init__(self, name, start, restart):
		self.name = name
		self.StartThread = start
		self.RestartThread = restart
		self.Thread = None

	def StopThread(self):
		self.Thread.stop()

def CheckThreads():
	for T in HelperThreads.values():
		if not T.Thread.is_alive():
			logsupport.Logs.Log("Thread for: "+T.name+" died; restarting",severity=ConsoleWarning)
			T.Thread = T.RestartThread(T)

def StartThreads():
	for T in HelperThreads.values():
		logsupport.Logs.Log("Starting helper thread for: ", T.name)
		T.Thread = T.StartThread()




