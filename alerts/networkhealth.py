import subprocess

import alerttasks
import logsupport
from stores import valuestore
import time
import functools
import controlevents
import threading


class NetworkHealth(object):
	def __init__(self):
		self.LastState = {}

	@staticmethod
	def RobustPing(dest, runproc):
		# logsupport.Logs.Log('Start ping {} in {}'.format(dest, threading.current_thread().name))
		ok = False
		cmd = 'ping -c 1 -W 2 ' + dest
		for i in range(7):
			# logsupport.LoggerQueue.put((logsupport.Command.FileWrite, '/home/pi/Console/.HistoryBuffer/hlog', 'a', 'Ping:\n'))
			try:
				pingresult = subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=subprocess.STDOUT).splitlines()
				ok = True
				#for l in pingresult:
				#	logsupport.LoggerQueue.put((logsupport.Command.FileWrite,'/home/pi/Console/.HistoryBuffer/hlog', 'a', 'Good ping: {}\n'.format(l)))
				#wlanq = subprocess.check_output('iwconfig wlan0', shell=True, universal_newlines=True,
				#								stderr=subprocess.STDOUT).splitlines()
				#for l in wlanq:
				#	logsupport.LoggerQueue.put((logsupport.Command.FileWrite,'/home/pi/Console/.HistoryBuffer/hlog', 'a', 'WLAN     : {}\n'.format(l)))
				break
			except subprocess.CalledProcessError as Res:
				logsupport.LoggerQueue.put(
					(
						logsupport.Command.FileWrite, '/home/pi/Console/.HistoryBuffer/hlog', 'a',
						'Bad ping: {}\n'.format(Res.returncode)))
				pingresult = Res.output.splitlines()
				for l in pingresult:
					logsupport.LoggerQueue.put(
						(logsupport.Command.FileWrite, '/home/pi/Console/.HistoryBuffer/hlog', 'a',
						 'Bad ping: {}\n'.format(l)))
				wlanq = subprocess.check_output('iwconfig wlan0', shell=True, universal_newlines=True, stderr=subprocess.STDOUT).splitlines()
				for l in wlanq:
					logsupport.LoggerQueue.put(
						(logsupport.Command.FileWrite, '/home/pi/Console/.HistoryBuffer/hlog', 'a',
						 'WLAN    : {}\n'.format(l)))
				time.sleep(.25)
		# logsupport.Logs.Log('Finished ping thread {} in {}'.format(ok, threading.current_thread().name))
		controlevents.PostEvent(
			controlevents.ConsoleEvent(controlevents.CEvent.RunProc, proc=functools.partial(runproc, ok),
									   name='FinishPing'))

	def Do_Ping(self, alert):
		# expects parameter = ipaddr,variable name (local)
		# set variable name to 0 if ipaddr was accessible and now is not
		var = valuestore.InternalizeVarName(alert.param[1])
		if alert.param[0] not in self.LastState:
			self.LastState[alert.param[0]] = True  # assume up to start
		FinishPing = functools.partial(self.Set_Ping_Result, alert.param[0], alert.param[1])
		Pinger = threading.Thread(target=self.RobustPing, args=(alert.param[0], FinishPing),
								  name='Pinger-{}'.format(alert.param[0]), daemon=True)
		Pinger.start()

	def Set_Ping_Result(self, addr, var, result):
		# logsupport.Logs.Log('Finish ping: {} {} {} in {}'.format(addr,var,result, threading.current_thread().name))
		if result:
			if not self.LastState[addr]:
				self.LastState[addr] = True
				valuestore.SetVal(var, 1)
				logsupport.Logs.Log("Network up to: " + addr)
		else:
			if self.LastState[addr]:
				# was up now down
				self.LastState[addr] = False
				valuestore.SetVal(var, 0)  # Set down seen
				logsupport.Logs.Log("Network down to: " + addr)


alerttasks.alertprocs["NetworkHealth"] = NetworkHealth
