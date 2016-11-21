import config, utilities, logsupport
from configobjects import Section
import screen
from logsupport import ConsoleWarning

Tests = ('EQ', 'NE')
AlertType = ('NodeChange', 'StateVarChange', 'IntVarChange', 'Periodic', 'TOD', 'External')
VarsTypes = {'StateVarChange': (2, config.ISY.varsState), 'IntVarChange': (1, config.ISY.varsInt)}
AlertState = ('Armed', 'Delayed', 'Active', 'Deferred', 'Idle')


class Alert(object):
	def __init__(self, nm, type, trigger, action, actionname):
		self.name = nm
		self.state = 'Idle'
		self.type = type
		self.trigger = trigger
		self.actiontarget = action
		self.actionname = actionname

	def Invoke(self):
		if isinstance(self.actiontarget, config.alertscreentype):
			self.State = 'Active'
			config.DS.SwitchScreen(self.actiontarget, 'Bright', 'Alert', 'Go to alert screen', NavKeys=False)
			#			config.DS.SwitchScreenOld(self.actiontarget, NavKeys=False)
			pass  # switch to screen and set active
		else:
			self.actiontarget.Invoke(self)
			self.State = "Armed"

	def __repr__(self):
		if isinstance(self.actiontarget, screen.ScreenDesc):
			targtype = 'Screen'
		else:
			targtype = 'Proc'
		return self.name + ': ' + self.type + ' Alert (' + self.state + ') Triggered: ' + repr(
			self.trigger) + ' Call ' + targtype + ':' + self.actionname


class NodeChgtrigger(object):
	def __init__(self, addr, test, value, delay):
		self.nodeaddress = addr
		self.test = test
		self.value = value
		self.delay = delay

	def __repr__(self):
		return 'Node ' + self.nodeaddress + ' status ' + self.test + ' ' + str(self.value) + ' delayed ' + str(
			self.delay) + ' seconds'


class VarChgtrigger(object):
	def __init__(self, var, test, value, delay):
		self.vartype = var[0]
		self.varid = var[1]
		self.test = test
		self.value = value
		self.delay = delay
		self.VT = ('UNKN', 'Integer', 'State')
		if self.vartype == 1:
			self.name = config.ISY.varsIntInv[int(self.varid)]
		elif self.vartype == 2:
			self.name = config.ISY.varsStateInv[int(self.varid)]

	def __repr__(self):
		return str(self.VT[self.vartype]) + ' variable ' + self.name + '(' + str(
			self.varid) + '} ' + self.test + ' ' + str(self.value) + ' delayed ' + str(self.delay) + ' seconds'

	def IsTrue(self):
		val = config.DS.WatchVarVals[(self.vartype, self.varid)]
		if self.test == 'EQ':
			return int(val) == int(self.value)
		elif self.test == 'NE':
			return int(val) <> int(self.value)
		else:
			utilities.FatalError('VarChgtriggerIsTrue')


class Periodictrigger(object):
	def __init__(self, interval):
		self.interval = interval

	def __repr__(self):
		return 'Every ' + str(self.interval.days) + ' days + ' + str(self.interval) + ' seconds'


def getvalid(spec, item, choices, default=None):
	i = spec.get(item, default)
	if i is not None:
		if i in choices:
			return i
		else:
			config.Logs.Log('Choice error: ' + item + " not in " + choices, severity=logsupport.ConsoleWarning)
			return None
	else:
		config.Logs.Log('Missing required alert parameter: ' + item)


def ParseAlertParams(nm, spec):
	t = spec.get('Invoke', None)
	# todo check none
	if t in config.alertprocs:
		action = config.alertprocs[t]
		actionname = t
		fixscreen = False
	elif t in config.alertscreens:
		action = config.alertscreens[t]
		actionname = t
		fixscreen = True
	else:
		config.Logs.Log('No such action name for alert: ' + nm, severity=ConsoleWarning)
		return None
	triggertype = getvalid(spec, 'Type', AlertType)
	if triggertype == 'Periodic':
		# parse time specs
		interval = utilities.get_timedelta(spec.get('Interval', None))
		A = Alert(nm, triggertype, Periodictrigger(interval), action, actionname)
	elif triggertype == 'TOD':
		pass
		return None
	# todo parse times
	elif triggertype == 'NodeChange':  # needs node, test, status, delay
		n = spec.get('Node', None)
		if n is not None:
			Node = config.ISY.NodesByName[n].address
		else:
			Node = ''
		test = getvalid(spec, 'Test', Tests)
		value = spec.get('Status', None)
		delay = utilities.get_timedelta(spec.get('Delay', None))
		trig = NodeChgtrigger(Node, test, value, delay)
		# todo check nones
		A = Alert(nm, triggertype, trig, action, actionname)

	elif triggertype in ('StateVarChange', 'IntVarChange'):  # needs var, test, value, delay
		n = spec.get('Var', None)
		if n is not None:
			varspec = (VarsTypes[triggertype][0], VarsTypes[triggertype][1][n])  # todo nonecheck
		test = getvalid(spec, 'Test', Tests)
		value = spec.get('Value', None)
		delay = utilities.get_timedelta(spec.get('Delay', None))
		trig = VarChgtrigger(varspec, test, value, delay)
		A = Alert(nm, triggertype, trig, action, actionname)
	elif triggertype == 'External':
		pass  # todo external?
		return None

	if fixscreen:
		action.Alert = A

	return A


class Alerts(object):
	def __init__(self, alertsspec):
		if alertsspec is not None:
			self.AlertsList = {}  # hash:AlertItem
			for nm, spec in alertsspec.items():
				if isinstance(spec, Section):
					alert = ParseAlertParams(nm, spec)
					if alert is not None:
						self.AlertsList[id(alert)] = alert
