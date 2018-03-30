import time


class AutoAway(object):
	def __init__(self):
		self.lastactivity = time.time()  # last time some human activity noticed, initialized to startup
		self.awaytimeout = 60  # temp seconds before setting away

	def NodeChanged(self, alert):
		pass

	def VarChanged(self, alert):
		pass

	def PeriodicCheck(self, alert):
		pass
