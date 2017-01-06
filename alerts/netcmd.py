import config
import githubutil
import exitutils
import eventlist
from logsupport import ConsoleWarning


class NetCmd(object):
	def __init__(self):
		pass

	@staticmethod
	def Restart(self):
		pass

	def Reboot(self):
		pass

	def DownloadStable(self):
		pass

	def DownLoadBeta(self):
		pass

	def SetStable(self):
		pass

	def SetBeta(self):
		pass


config.alertprocs["NetCmd"] = NetCmd
