import subprocess

import alerttasks
import logsupport
import timers
from stores import valuestore
import time


class NetworkHealth(object):
	def __init__(self):
		self.LastState = {}

	@staticmethod
	def RobustPing(dest):
		ok = False
		cmd = 'ping -c 1 -W 2 ' + dest
		for i in range(7):
			logsupport.LoggerQueue.put((2, '/home/pi/Console/hlog', 'a', 'Ping:\n'))
			try:
				pingresult = subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=subprocess.STDOUT).splitlines()
				ok = True
				#for l in pingresult:
				#	logsupport.LoggerQueue.put((2,'/home/pi/Console/hlog', 'a', 'Good ping: {}\n'.format(l)))
				#wlanq = subprocess.check_output('iwconfig wlan0', shell=True, universal_newlines=True,
				#								stderr=subprocess.STDOUT).splitlines()
				#for l in wlanq:
				#	logsupport.LoggerQueue.put((2,'/home/pi/Console/hlog', 'a', 'WLAN     : {}\n'.format(l)))
				break
			except subprocess.CalledProcessError as Res:
				logsupport.LoggerQueue.put(
					(2, '/home/pi/Console/hlog', 'a', 'Bad ping: {}\n'.format(Res.returncode)))
				pingresult = Res.output.splitlines()
				for l in pingresult:
					logsupport.LoggerQueue.put((2,'/home/pi/Console/hlog', 'a', 'Bad ping: {}\n'.format(l)))
				wlanq = subprocess.check_output('iwconfig wlan0', shell=True, universal_newlines=True, stderr=subprocess.STDOUT).splitlines()
				for l in wlanq:
					logsupport.LoggerQueue.put((2,'/home/pi/Console/hlog', 'a', 'WLAN    : {}\n'.format(l)))
				time.sleep(.25)
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
				valuestore.SetVal(var, 1)
				logsupport.Logs.Log("Network up to: " + alert.param[0])
		else:
			if self.LastState[alert.param[0]]:
				# was up now down
				self.LastState[alert.param[0]] = False
				valuestore.SetVal(var, 0)  # Set down seen
				logsupport.Logs.Log("Network down to: " + alert.param[0])
		timers.EndLongOp('NetworkHealth')


alerttasks.alertprocs["NetworkHealth"] = NetworkHealth
