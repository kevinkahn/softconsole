import subprocess

import alerttasks
import logsupport
import timers
from stores import valuestore


class NetworkHealth(object):
	def __init__(self):
		self.LastState = {}

	@staticmethod
	def RobustPing(dest):
		ok = False
		with open('/dev/null', 'a') as f:
		#with open('/home/pi/Console/hlog', 'a') as f: # todo - if want to save ping output need to figure out async for redirect
			cmd = 'ping -c 1 -W 2 ' + dest
			for i in range(7):
				logsupport.LoggerQueue.put((2,'/home/pi/Console/hlog','a','Ping:\n'))
				#f.write('Ping:\n')
				#f.flush()
				p = subprocess.call(cmd, shell=True, stdout=f, stderr=f)
				if p == 0:
					ok = True  # one success in loop is success
					break
				else:
					logsupport.LoggerQueue.put((2, '/home/pi/Console/hlog', 'a', 'Ping result: {}\n'.format(p)))
					#f.write('Ping result: {}'.format(p))
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
