from datetime import datetime
from dateutil.parser import parse

import logsupport
import timers
import utilities
import alertsystem.alertutils as alertutils
import alertsystem.alerttasks as alerttasks

triggername = 'Periodic'
AlertUnique = 0


class Periodictrigger(object):
	def __init__(self, periodic, interval, timeslist):
		self.periodic = periodic
		self.interval = interval
		self.timeslist = timeslist

	def NextInterval(self):
		if self.periodic:
			return self.interval
		else:
			now = datetime.now()
			seconds_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
			for schedtime in self.timeslist:
				if seconds_since_midnight < schedtime - 2:  # 2 seconds of slop to avoid rescheduling for immediate execution
					return schedtime - seconds_since_midnight
			# no times left for today
			return 24 * 3600 - seconds_since_midnight + self.timeslist[0]

	@staticmethod
	def ReArm(alert):
		SchedulePeriodicEvent(alert)

	@staticmethod
	def IsTrue():  # If trigger comes to execute it is because timer went off so always return condition True
		return True

	def __repr__(self):
		if self.periodic:
			return 'Every ' + str(self.interval) + ' seconds'
		else:
			return 'At ' + str(self.timeslist) + ' seconds past midnight'


def Parse(nm, spec, action, actionname, param):
	# parse time specs
	interval = utilities.get_timedelta(spec.get('Interval', None))
	secfrommid = []
	at = spec.get('At', '*unspec*')
	periodic = False
	if interval == 0 and at == '*unspec*':
		logsupport.Logs.Log("Periodic trigger must specify interval or time(s): ", nm,
							severity=logsupport.ConsoleWarning)
		return None
	if interval != 0:
		periodic = True
	if at != '*unspec*':
		if periodic:
			logsupport.Logs.Log("Periodic trigger cannot specify both interval and time(s): ", nm,
								severity=logsupport.ConsoleWarning)
			return None
		if isinstance(at, str): at = [at]
		for t in at:
			tm = parse(t, ignoretz=True)
			secfrommid.append(tm.hour * 3600 + tm.minute * 60 + tm.second)
		secfrommid.sort()
	return alerttasks.Alert(nm, triggername, Periodictrigger(periodic, interval, secfrommid), action, actionname, param)


def SchedulePeriodicEvent(alert):
	global AlertUnique
	AlertUnique += 1
	t = timers.OnceTimer(alert.trigger.NextInterval(), name=alert.name + '-Periodic-' + str(AlertUnique), alert=alert,
						 type='Periodic', proc=alert.Invoke)
	t.start()


alertutils.TriggerTypes[triggername] = alertutils.TriggerRecord(Parse, SchedulePeriodicEvent, Periodictrigger)
