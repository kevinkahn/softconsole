import subprocess
import time

import alerttasks
import config
import debug
import exitutils
import historybuffer
import issuecommands
import logsupport
import maintscreen
from logsupport import ConsoleWarning
from stores import valuestore


class NetCmd(object):
	"""
	Variable values:
	1: Restart Console
	2: Reboot Console
	3: Download Stable
	4: Download Beta
	5: Set Stable
	6: Set Beta
	7: Dump HistoryBuffer
	8: Clear error indicator
	1xx: Set xxth debug flag
	2xx: Clear xxth debug flag
	30x: Set LogLevel to x (defaults 3, debug set 0)
	"""

	def __init__(self):
		pass
	#todo make the download etc async
	@staticmethod
	def Command(alert):
		if not isinstance(alert.trigger, alerttasks.VarChangeTrigger):
			logsupport.Logs.Log('Net Command not triggered by variable', severity=ConsoleWarning)
		varval = valuestore.GetVal(alert.trigger.var)
		valuestore.SetVal(alert.trigger.var, 0)
		if varval == 1:
			logsupport.Logs.Log('Remote restart')
			exitutils.Exit_Screen_Message('Remote restart requested', 'Remote Restart')
			config.terminationreason = 'remote restart'
			exitutils.Exit(exitutils.REMOTERESTART)
		elif varval == 2:
			logsupport.Logs.Log('Remote reboot')
			exitutils.Exit_Screen_Message('Remote reboot requested', 'Remote Reboot')
			config.terminationreason = 'remote reboot'
			exitutils.Exit(exitutils.REMOTEPIREBOOT)
		elif varval == 3:
			logsupport.Logs.Log('Remote download stable')
			issuecommands.fetch_stable()
		elif varval == 4:
			logsupport.Logs.Log('Remote download beta')
			issuecommands.fetch_beta()
		elif varval == 5:
			logsupport.Logs.Log('Remote set stable')
			subprocess.Popen('sudo rm /home/pi/usebeta', shell=True)
		elif varval == 6:
			logsupport.Logs.Log('Remote set beta')
			subprocess.Popen('sudo touch /home/pi/usebeta', shell=True)
		elif varval == 7:
			logsupport.Logs.Log('Remote history buffer dump')
			entrytime = time.strftime('%m-%d-%y %H:%M:%S')
			historybuffer.DumpAll('Command Dump', entrytime)
		elif varval == 8:
			logsupport.Logs.Log('Remote error indicator cleared')
			config.sysStore.ErrorNotice = -1
		elif varval in range(100, 100 + len(debug.DbgFlags)):
			flg = debug.DbgFlags[varval - 100]
			valuestore.SetVal(('Debug', flg), True)
			logsupport.Logs.Log('Remote set debug ', flg)
		elif varval in range(200, 200 + len(debug.DbgFlags)):
			flg = debug.DbgFlags[varval - 200]
			valuestore.SetVal(('Debug', flg), False)
			logsupport.Logs.Log('Remote clear debug ', flg)
		elif varval in range(300, 310):
			valuestore.SetVal(('Debug', 'LogLevel'), varval - 300)
			logsupport.Logs.Log('Remote set LogLevel to ', varval - 300)

		else:
			logsupport.Logs.Log('Unknown remote command: ', varval)


alerttasks.alertprocs["NetCmd"] = NetCmd
