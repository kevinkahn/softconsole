import config, utilities, logsupport
import exitutils
from configobjects import Section
import screen
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError
import isy
from stores import valuestore
import pygame
import debug
from screens import alertscreen
from datetime import datetime
from dateutil.parser import parse

alertprocs = {}  # set by modules from alerts directory
monitoredvars = []

Tests = ('EQ', 'NE')
AlertType = ('NodeChange', 'VarChange', 'StateVarChange', 'IntVarChange', 'LocalVarChange', 'Periodic', 'TOD', 'External', 'Init')

class Alert(object):
	def __init__(self, nm, type, trigger, action, actionname, param):
		self.name = nm
		self.state = 'Idle'
		self.type = type
		self.trigger = trigger
		self.actiontarget = action
		self.actionname = actionname
		self.param = param

	def Invoke(self):
		if isinstance(self.actiontarget, config.screentypes["Alert"]):
			self.state = 'Active'
			config.DS.SwitchScreen(self.actiontarget, 'Bright', 'Alert', 'Go to alert screen', NavKeys=False)
		else:
			self.actiontarget(self)  # target is the proc
			self.state = "Armed"

	def __repr__(self):
		if isinstance(self.actiontarget, screen.ScreenDesc):
			targtype = 'Screen'
		else:
			targtype = 'Proc'
		return self.name + ': ' + self.type + ' Alert (' + self.state + ') Trigger: ' + repr(
			self.trigger) + ' Invoke: ' + targtype + ':' + self.actionname


class NodeChgtrigger(object):
	def __init__(self, addr, test, value, delay):
		self.nodeaddress = addr
		self.test = test
		self.value = value
		self.delay = delay

	def IsTrue(self):
		val = isy.get_real_time_node_status(self.nodeaddress)
		if self.test == 'EQ':
			return int(val) == int(self.value)
		elif self.test == 'NE':
			return int(val) <> int(self.value)
		else:
			exitutils.FatalError('VarChgtriggerIsTrue')

	def __repr__(self):
		return 'Node ' + self.nodeaddress + ' status ' + self.test + ' ' + str(self.value) + ' delayed ' + str(
			self.delay) + ' seconds'

def VarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl','Var changed ',storeitem.name,' from ',old,' to ',new)
	notice = pygame.event.Event(config.DS.ISYVar, alert=param)
	pygame.fastevent.post(notice)

class VarChangeTrigger(object):
	def __init__(self, var, params):
		self.var = var
		self.test = params[0]
		self.value = params[1]
		self.delay = params[2]

	def IsTrue(self):
		val = valuestore.GetVal(self.var)
		if self.test == 'EQ':
			return int(val) == int(self.value)
		elif self.test == 'NE':
			return int(val) <> int(self.value)
		else:
			logsupport.Logs.Log('Bad test in IsTrue',self.test,severity=ConsoleError)
			return False # shouldn't happen

	def __repr__(self):
		return ' Variable ' + valuestore.ExternalizeVarName(self.var) + ' ' + self.test + ' ' + str(self.value) + ' delayed ' + str(self.delay) + ' seconds'

class InitTrigger(object):
	def __init__(self):
		pass

class Periodictrigger(object):
	def __init__(self, periodic, interval,timeslist):
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
				#print 'Check ', seconds_since_midnight, schedtime
				if seconds_since_midnight < schedtime - 2: # 2 seconds of slop to avoid rescheduling for immediate execution
					#print "Next ", schedtime - seconds_since_midnight
					return schedtime - seconds_since_midnight
			# no times left for today
			#print 'Tomorrow ', 24*3600 - seconds_since_midnight + self.timeslist[0]
			return 24*3600 - seconds_since_midnight + self.timeslist[0]

	def __repr__(self):
		if self.periodic:
			return 'Every ' + str(self.interval) + ' seconds'
		else:
			return 'At ' + str(self.timeslist) + ' seconds past midnight'

def getvalid(spec, item, choices, default=None):
	i = spec.get(item, default)
	if i is not None:
		if i in choices:
			return i
		else:
			logsupport.Logs.Log('Choice error: ' + item + " not in " + str(choices), severity=logsupport.ConsoleWarning)
			exitutils.errorexit(exitutils.ERRORDIE)
	else:
		logsupport.Logs.Log('Missing required alert parameter: ' + item, severity=ConsoleWarning)
		exitutils.errorexit(exitutils.ERRORDIE)


def ParseAlertParams(nm, spec):
	global alertprocs, monitoredvars
	def comparams(spec):
		test = getvalid(spec, 'Test', Tests)
		value = spec.get('Value', None)
		delay = utilities.get_timedelta(spec.get('Delay', None))
		return test, value, delay


	VarsTypes = {'StateVarChange': ('ISY','State'), 'IntVarChange': ('ISY','Int'), 'LocalVarChange': ('LocalVars',)}
	t = spec.get('Invoke', None)
	param = spec.get('Parameter', None)
	if t is None:
		logsupport.Logs.Log('Missing alert proc invoke spec in ' + nm, severity=ConsoleWarning)
		return None
	nmlist = t.split('.')

	if nmlist[0] in alertprocs:
		if len(nmlist) <> 2:
			logsupport.Logs.Log('Bad alert proc spec ' + t + ' in ' + nm, severity=ConsoleWarning)
			return None
		try:
			action = getattr(alertprocs[nmlist[0]], nmlist[1])
		except:
			logsupport.Logs.Log('No proc ', nmlist[1], ' in ', nmlist[0], severity=ConsoleWarning)
			return None
		actionname = t
		fixscreen = False
	elif nmlist[0] in alertscreen.alertscreens:
		if len(nmlist) <> 1:
			logsupport.Logs.Log('Alert screen name must be unqualified in ' + nm, severity=ConsoleWarning)
			return None
		action = alertscreen.alertscreens[nmlist[0]]
		actionname = t
		fixscreen = True
	else:
		logsupport.Logs.Log('No such action name for alert: ' + nm, severity=ConsoleWarning)
		return None
	triggertype = getvalid(spec, 'Type', AlertType)
	if triggertype == 'Periodic':
		# parse time specs
		interval = utilities.get_timedelta(spec.get('Interval', None))
		secfrommid = []
		at = spec.get('At', '*unspec*')
		periodic = False
		if interval == 0 and at == '*unspec*':
			logsupport.Logs.Log("Periodic trigger must specify interval or time(s): ", nm, severity=ConsoleWarning)
			return None
		if interval != 0:
			periodic = True
		if at != '*unspec*':
			if periodic:
				logsupport.Logs.Log("Periodic trigger cannot specify both interval and time(s): ", nm, severity=ConsoleWarning)
				return None
			if isinstance(at,str): at = [at]
			for t in at:
				tm = parse(t,ignoretz=True)
				secfrommid.append(tm.hour*3600 + tm.minute*60 + tm.second)
			secfrommid.sort()
		A = Alert(nm, triggertype, Periodictrigger(periodic, interval, secfrommid), action, actionname, param)

	elif triggertype == 'NodeChange':  # needs node, test, status, delay
		n = spec.get('Node', None)
		try:
			Node = config.ISY.GetNodeByName(n).address
		except:
			Node = ''
			logsupport.Logs.Log("Bad Node Spec on NodeChange alert in " + nm, severity=ConsoleWarning)
		test, value, delay = comparams(spec)
		trig = NodeChgtrigger(Node, test, value, delay)
		# todo check nones
		A = Alert(nm, triggertype, trig, action, actionname, param)
	elif triggertype in ('StateVarChange','IntVarChange', 'LocalVarChange'):
		n = VarsTypes[triggertype] + (spec.get('Var', ''),)
		logsupport.Logs.Log("Deprecated alert trigger ", triggertype, ' used - change to use VarChange ',n,
							severity=ConsoleWarning)
		if n is None:
			logsupport.Logs.Log("Alert: ", nm, " var name " + n + " doesn't exist", severity=ConsoleWarning)
			return None
		monitoredvars.append(n)
		trig = VarChangeTrigger(n,comparams(spec))
		A = Alert(nm, 'VarChange', trig, action, actionname, param)
		valuestore.AddAlert(n, (VarChanged, A))

	elif triggertype == 'VarChange':
		n = spec.get('Var', None).split(':')
		if n is None:
			logsupport.Logs.Log("Alert: ", nm, " var name " + n + " doesn't exist", severity=ConsoleWarning)
			return None
		monitoredvars.append(n)
		trig = VarChangeTrigger(n,comparams(spec))
		A = Alert(nm, triggertype, trig, action, actionname, param)
		valuestore.AddAlert(n,(VarChanged, A))

	elif triggertype == 'External':
		pass  # todo external?
		return None
	elif triggertype == 'Init':  # Trigger once at start up passing in the configobj spec
		trig = InitTrigger()
		A = Alert(nm, triggertype, trig, action, actionname, param)
	else:
		logsupport.Logs.Log("Internal triggertype error",severity=ConsoleError)

	logsupport.Logs.Log("Created alert: " + nm)
	logsupport.Logs.Log("->" + str(A), severity=ConsoleDetail)
	if fixscreen:
		action.Alert = A

	return A


class Alerts(object):
	def __init__(self, alertsspec):
		self.AlertsList = {}  # hash:AlertItem
		if alertsspec is not None:
			for nm, spec in alertsspec.items():
				if isinstance(spec, Section):
					alert = ParseAlertParams(nm, spec)
					if alert is not None:
						self.AlertsList[id(alert)] = alert
