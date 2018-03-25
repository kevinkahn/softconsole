import alerttasks
import logsupport

class MakeLogEntry(object):
	def __init__(self):
		pass

	def Log(self, alert):
		logsupport.Logs.Log("Log Entry Requested ", alert.param)

alerttasks.alertprocs["MakeLogEntry"] = MakeLogEntry