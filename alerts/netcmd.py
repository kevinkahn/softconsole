import config
import alerttasks
import debug
import subprocess
import maintscreen
import exitutils
import isy
from logsupport import ConsoleWarning


class NetCmd(object):
	"""
	Variable values:
	1: Restart Console
	2: Reboot Console
	3: Download Stable
	4: Download Beta
	5: Set Stable
	6: Set Beta
	1xx: Set xxth debug flag
	2xx: Clear xxth debug flag
	30x: Set LogLevel to x (defaults 3, debug set 0)
	"""

	def __init__(self):
		pass

	#	@staticmethod
	def Command(self, alert):
		if not isinstance(alert.trigger, alerttasks.VarChgtrigger):
			config.Logs.Log('Net Command not triggered by variable', severity=ConsoleWarning)
		vartype = alert.trigger.vartype
		varid = alert.trigger.varid
		varval = config.DS.WatchVarVals[(vartype, varid)]
		isy.SetVar((vartype, varid), 0)
		if varval == 1:
			config.Logs.Log('Remote restart')
			exitutils.Exit_Screen_Message('Remote restart requested', 'Remote Restart')
			exitutils.Exit(exitutils.REMOTERESTART)
		elif varval == 2:
			config.Logs.Log('Remote reboot')
			exitutils.Exit_Screen_Message('Remote reboot requested', 'Remote Reboot')
			exitutils.Exit(exitutils.REMOTEREBOOT)
		elif varval == 3:
			config.Logs.Log('Remote download stable')
			maintscreen.fetch_stable()
		elif varval == 4:
			config.Logs.Log('Remote download beta')
			maintscreen.fetch_beta()
		elif varval == 5:
			config.Logs.Log('Remote set stable')
			subprocess.Popen('sudo rm /home/pi/usebeta', shell=True)
		elif varval == 6:
			config.Logs.Log('Remote set beta')
			subprocess.Popen('sudo touch /home/pi/usebeta', shell=True)
		elif varval in range(100, 100 + len(debug.DbgFlags)):
			flg = debug.DbgFlags[varval - 100]
			debug.Flags[flg] = True
			debug.DebugFlagKeys[flg].State = True
			config.Logs.Log('Remote set debug ', flg)
		elif varval in range(200, 200 + len(debug.DbgFlags)):
			flg = debug.DbgFlags[varval - 200]
			debug.Flags[flg] = False
			debug.DebugFlagKeys[flg].State = False
			config.Logs.Log('Remote clear debug ', flg)
		elif varval in range(300, 310):
			config.LogLevel = varval - 300
			config.Logs.Log('Remove set LogLevel to ', varval - 300)

		else:
			config.Logs.Log('Unknown remote command: ', varval)




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
