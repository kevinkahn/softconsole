import config


class VersionCheck(object):
	def __init__(self):
		self.name = "VersionCheck"
		self.ct1 = 0
		self.ct2 = 0
		pass

	def AlertProc1(self, alert):
		print "---------------------VC invocation", self.ct1, alert, id(alert)
		self.ct1 += 1

	def AlertProc2(self, alert):
		print "=====================VC alt incovation", self.ct2, alert, id(alert)
		self.ct2 += 1

	# Invoked when the specified event or time occurs
	# reason is one of Interval, Time, Device, Variable
	# param is the object that caused the alert if one exists (device or var)


config.alertprocs["VersionCheck"] = VersionCheck
