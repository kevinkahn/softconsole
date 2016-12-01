import config, utilities, logsupport
from configobjects import Section
import screen
from logsupport import ConsoleWarning
from debug import debugPrint
import isy

Tests = ('EQ', 'NE')
AlertType = ('NodeChange', 'StateVarChange', 'IntVarChange', 'Periodic', 'TOD', 'External')

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
		return self.name + ': ' + self.type + ' Alert (' + self.state + ') Triggered: ' + repr(
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
			utilities.FatalError('VarChgtriggerIsTrue')

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


class InitTrigger(object):
	def __init__(self, spec):
		self.spec = spec

class Periodictrigger(object):
	def __init__(self, interval):
		self.interval = interval

	def __repr__(self):
		return 'Every ' + str(self.interval) + ' seconds'


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
	VarsTypes = {'StateVarChange': (2, config.ISY.varsState), 'IntVarChange': (1, config.ISY.varsInt)}
	t = spec.get('Invoke', None)
	if t is None:
		config.Logs.Log('Missing alert proc invoke spec in ' + nm, severity=ConsoleWarning)
		return None
	nmlist = t.split('.')

	if nmlist[0] in config.alertprocs:
		if len(nmlist) <> 2:
			config.Logs.Log('Bad alert proc spec ' + t + ' in ' + nm, severity=ConsoleWarning)
			return None
		action = getattr(config.alertprocs[nmlist[0]], nmlist[1])
		actionname = t
		fixscreen = False
	elif nmlist[0] in config.alertscreens:
		if len(nmlist) <> 1:
			config.Logs.Log('Alert screen name must be unqualified in ' + nm)
			return None
		action = config.alertscreens[nmlist[0]]
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
	elif triggertype == 'Init':  # Trigger once at start up passing in the configobj spec
		trig = InitTrigger(spec)
		A = Alert(nm, triggertype, trig, action, actionname)

	config.Logs.Log("Created alert: " + A)
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
