import config
import subprocess
import alerttasks
import logsupport
from stores import valuestore
import timers

class NetworkHealth(object):
	def __init__(self):
		self.LastState = {}

	@staticmethod
	def RobustPing(dest):
		ok = False
		with open('/dev/null', 'a') as null:
			cmd = 'ping -c 1 -W 2 ' + dest
			for i in range(4):
				p = subprocess.call(cmd, shell=True, stdout=null, stderr=null)
				if p == 0:
					ok = True  # one success in loop is success
					break
				else:
					pass
		return ok

	def Do_Ping(self, alert):
		# expects parameter = ipaddr,variable name (local)
		# set variable name to 0 if ipaddr was accessible and now is not
		var = valuestore.InternalizeVarName(alert.param[1])
		if alert.param[0] not in self.LastState:
			self.LastState[alert.param[0]] = True  # assume up to start
		timers.StartLongOp('NetworkHealth')
		if self.RobustPing(alert.param[0]):
			if not self.LastState[alert.param[0]]:
				self.LastState[alert.param[0]] = True
				valuestore.SetVal(var,1)
				logsupport.Logs.Log("Network up to: " + alert.param[0])
		else:
			if self.LastState[alert.param[0]]:
				# was up now down
				self.LastState[alert.param[0]] = False
				valuestore.SetVal(var, 0) # Set down seen
				logsupport.Logs.Log("Network down to: " + alert.param[0])
		timers.EndLongOp('NetworkHealth')

alerttasks.alertprocs["NetworkHealth"] = NetworkHealth
