import config, utilities, logsupport
import exitutils
from configobjects import Section
import screen
from logsupport import ConsoleWarning, ConsoleDetail
import isy

Tests = ('EQ', 'NE')
AlertType = ('NodeChange', 'StateVarChange', 'IntVarChange', 'LocalVarChange', 'Periodic', 'TOD', 'External', 'Init')

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
			exitutils.FatalError('VarChgtriggerIsTrue')

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
		self.VT = ('UNKN', 'Integer', 'State', 'Local')
		if self.vartype == 1:
			self.name = config.ISY.varsIntInv[int(self.varid)]
		elif self.vartype == 2:
			self.name = config.ISY.varsStateInv[int(self.varid)]
		elif self.vartype == 3:
			self.name = config.ISY.varsLocalInv[int(self.varid)]

	def __repr__(self):
		return str(self.VT[self.vartype]) + ' variable ' + self.name + '(' + str(
			self.varid) + ') ' + self.test + ' ' + str(self.value) + ' delayed ' + str(self.delay) + ' seconds'

	def IsTrue(self):
		val = config.DS.WatchVarVals[(self.vartype, self.varid)]
		if self.test == 'EQ':
			return int(val) == int(self.value)
		elif self.test == 'NE':
			return int(val) <> int(self.value)
		else:
			exitutils.FatalError('VarChgtriggerIsTrue')


class InitTrigger(object):
	def __init__(self):
		pass

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
			config.Logs.Log('Choice error: ' + item + " not in " + str(choices), severity=logsupport.ConsoleWarning)
			return None
	else:
		config.Logs.Log('Missing required alert parameter: ' + item, severity=ConsoleWarning)
		return None


def ParseAlertParams(nm, spec):
	VarsTypes = {'StateVarChange': (2, config.ISY.varsState), 'IntVarChange': (1, config.ISY.varsInt),
				 'LocalVarChange': (3, config.ISY.varsLocal)}
	t = spec.get('Invoke', None)
	param = spec.get('Parameter', None)
	if t is None:
		config.Logs.Log('Missing alert proc invoke spec in ' + nm, severity=ConsoleWarning)
		return None
	nmlist = t.split('.')

	if nmlist[0] in config.alertprocs:
		if len(nmlist) <> 2:
			config.Logs.Log('Bad alert proc spec ' + t + ' in ' + nm, severity=ConsoleWarning)
			return None
		try:
			action = getattr(config.alertprocs[nmlist[0]], nmlist[1])
		except:
			config.Logs.Log('No proc ', nmlist[1], ' in ', nmlist[0], severity=ConsoleWarning)
			return None
		actionname = t
		fixscreen = False
	elif nmlist[0] in config.alertscreens:
		if len(nmlist) <> 1:
			config.Logs.Log('Alert screen name must be unqualified in ' + nm, severity=ConsoleWarning)
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
		A = Alert(nm, triggertype, Periodictrigger(interval), action, actionname, param)
	elif triggertype == 'TOD':
		pass
		return None
	# todo parse times
	elif triggertype == 'NodeChange':  # needs node, test, status, delay
		"""
		n = spec.get('Node', None)
		if n is not None:
			Node = config.ISY.NodesByName[n].address
		else:
			Node = ''
		"""
		n = spec.get('Node', None)
		try:
			Node = config.ISY.NodesByName[n].address
		except:
			Node = ''
			config.Logs.Log("Bad Node Spec on NodeChange alert in " + nm, severity=ConsoleWarning)
		test = getvalid(spec, 'Test', Tests)
		value = spec.get('Value', None)
		delay = utilities.get_timedelta(spec.get('Delay', None))
		trig = NodeChgtrigger(Node, test, value, delay)
		# todo check nones
		A = Alert(nm, triggertype, trig, action, actionname, param)

	elif triggertype in ('StateVarChange', 'IntVarChange', 'LocalVarChange'):  # needs var, test, value, delay
		n = spec.get('Var', None)
		if n is not None:
			if n in VarsTypes[triggertype][1]:
				varspec = (VarsTypes[triggertype][0], VarsTypes[triggertype][1][n])
			else:
				config.Logs.Log("Alert: ", nm, " var name " + n + " doesn't exist", severity=ConsoleWarning)
				return None
		else:
			config.Logs.Log("Alert: ", nm, " var name not specified", severity=ConsoleWarning)
			return None
		test = getvalid(spec, 'Test', Tests)
		value = spec.get('Value', None)
		if (test is None) or (value is None):
			return None
		delay = utilities.get_timedelta(spec.get('Delay', None))
		trig = VarChgtrigger(varspec, test, value, delay)
		A = Alert(nm, triggertype, trig, action, actionname, param)
	elif triggertype == 'External':
		pass  # todo external?
		return None
	elif triggertype == 'Init':  # Trigger once at start up passing in the configobj spec
		trig = InitTrigger()
		A = Alert(nm, triggertype, trig, action, actionname, param)

	config.Logs.Log("Created alert: " + nm)
	config.Logs.Log("->" + str(A), severity=ConsoleDetail)
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
