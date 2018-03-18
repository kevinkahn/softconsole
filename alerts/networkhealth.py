import config
import subprocess
import isy
import logsupport
from stores import valuestore

class NetworkHealth(object):
	def __init__(self):
		self.LastState = {}

	def RobustPing(self, dest):
		# print dest
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

	# @staticmethod
	def Do_Ping(self, alert):
		# expects parameter = ipaddr,variable name (local)
		# set variable name to 0 if ipaddr was accessible and now is not
		var = valuestore.InternalizeVarName(alert.param[1])
		if alert.param[0] not in self.LastState:
			self.LastState[alert.param[0]] = True  # assume up to start
		config.DS.Tasks.StartLongOp()  # todo perhaps a cleaner way to deal with long ops
		if self.RobustPing(alert.param[0]):
			if not self.LastState[alert.param[0]]:
				self.LastState[alert.param[0]] = True
				isy.SetVar((3, config.ISY.varsLocal[var[1]]), 1)
				valuestore.SetVal(var,1)
				logsupport.Logs.Log("Network up to: " + alert.param[0])
		else:
			if self.LastState[alert.param[0]]:
				# was up now down
				self.LastState[alert.param[0]] = False
				valuestore.SetVal(var, 0)
				isy.SetVar((3, config.ISY.varsLocal[var[1]]), 0)  # Set down seen
				logsupport.Logs.Log("Network down to: " + alert.param[0])
		config.DS.Tasks.EndLongOp()


config.alertprocs["NetworkHealth"] = NetworkHealth
