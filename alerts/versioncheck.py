import config


class VersionCheck(object):
	def __init__(self):
		self.name = "VersionCheck"
		pass

	def Invoke(self, alert):
		print "---------------------VC invocation", alert

	# Invoked when the specified event or time occurs
	# reason is one of Interval, Time, Device, Variable
	# param is the object that caused the alert if one exists (device or var)


config.alertprocs["VersionCheck"] = VersionCheck()
