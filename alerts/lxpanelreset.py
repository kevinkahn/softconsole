from alertsystem import alerttasks
import logsupport
import subprocess
from logsupport import ConsoleWarning


# noinspection PyUnusedLocal
class LXPanelRestart(object):
	def __init__(self):
		pass

	# @staticmethod
	@staticmethod
	def LXPanelRestart(alert):
		try:
			cmd = 'XAUTHORITY=/home/pi/.Xauthority DISPLAY=":{}.0" lxpanelctl restart'
			with open('/dev/null') as null:
				p0 = subprocess.call(cmd.format(0), shell=True)
				p1 = subprocess.call(cmd.format(1), shell=True)
			if (p0 != 0) or (p1 != 0):
				logsupport.Logs.Log('LXPanel restart error {} {}'.format(p0, p1), severity=ConsoleWarning)
			else:
				logsupport.Logs.Log('LXPanels were restarted')
		except Exception as E:
			logsupport.Logs.Log('Exception in lxpanelrestart: {}'.format(repr(E)))


alerttasks.alertprocs["LXPanelRestart"] = LXPanelRestart
