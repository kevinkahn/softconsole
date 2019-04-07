import alerttasks
import logsupport


class MakeLogEntry(object):
	def __init__(self):
		pass

	@staticmethod
	def Log(alert):
		logsupport.Logs.Log("Log Entry Requested ", alert.param)


alerttasks.alertprocs["MakeLogEntry"] = MakeLogEntry
