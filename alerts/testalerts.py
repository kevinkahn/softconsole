import alerttasks
import exitutils
import logsupport


class testalerts(object):
	def __init__(self):
		self.name = "testalerts"
		self.ct1 = 0
		self.ct2 = 0
		pass

	def AlertProc1(self, alert):
		logsupport.DevPrint("---------------------VC invocation" + str(self.ct1) + str(alert) + str(id(alert)))
		logsupport.Logs.Log('Alert proc test exiting')
		logsupport.Logs.Log('Restart for new version')
		exitutils.Exit(66)

	def AlertProc2(self, alert):
		logsupport.DevPrint("=====================VC alt incovation" + str(self.ct2) + str(alert) + str(id(alert)))
		self.ct2 += 1

# Invoked when the specified event or time occurs
# reason is one of Interval, Time, Device, Variable
# param is the object that caused the alert if one exists (device or var)


alerttasks.alertprocs["testalerts"] = testalerts
