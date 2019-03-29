import config, utilities, logsupport
import exitutils
from screens import alertscreen
import screens.__screens as screens
from configobjects import Section
import screen
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError
from stores import valuestore
from controlevents import *
import debug
import timers
import historybuffer

from datetime import datetime
from dateutil.parser import parse

alertprocs = {}  # set by modules from alerts directory
monitoredvars = []

AlertItems = []

Tests = ('EQ', 'NE')
AlertType = ('NodeChange', 'VarChange', 'StateVarChange', 'IntVarChange', 'LocalVarChange', 'Periodic', 'TOD', 'External', 'Init')

AlertsHB = historybuffer.HistoryBuffer(100, 'Alerts')

class Alert(object):
	def __init__(self, nm, atype, trigger, action, actionname, param):
		self.name = nm
		self._state = 'Idle'
		self.type = atype
		self.trigger = trigger
		self.actiontarget = action
		self.actionname = actionname
		self.param = param

	@property
	def state(self):
		return self._state

	@state.setter
	def state(self, value):
		debug.debugPrint('AlertsTrace','Alert: '+self.name+' changed from ' + self._state + ' to '+ value)
		self._state = value

	def Invoke(self, param=None):
		if isinstance(self.actiontarget, screens.screentypes["Alert"]):
			self.state = 'Active'
			config.DS.SwitchScreen(self.actiontarget, 'Bright', 'Alert', 'Go to alert screen', NavKeys=False)
		else:
			self.state = 'Active'
			self.actiontarget(self)  # target is the proc
			# noinspection PyAttributeOutsideInit
			self.state = "Armed"
		if isinstance(self.trigger, Periodictrigger):  # todo move inside the "proc"? perhaps have a reset proc for all triggers and blindly call that here
			SchedulePeriodicEvent(self)

	def __repr__(self):
		if isinstance(self.actiontarget, screen.ScreenDesc):
			targtype = 'Screen'
		else:
			targtype = 'Proc'
		return self.name + ': ' + self.type + ' Alert (' + self.state + ') Trigger: ' + repr(
			self.trigger) + ' Invoke: ' + targtype + ':' + self.actionname + str(self.actiontarget)


class NodeChgtrigger(object):
	def __init__(self, node, test, value, delay):
		self.node = node
		self.test = test
		self.value = value
		self.delay = delay

	def IsTrue(self):
		val = self.node.Hub.GetCurrentStatus(self.node)
		if val is None:
			logsupport.Logs.Log("No state available in alert for: " + self.node.name)
			val = -1
		if self.test == 'EQ':
			return int(val) == int(self.value)
		elif self.test == 'NE':
			return int(val) != int(self.value)
		else:
			exitutils.FatalError('VarChgtriggerIsTrue')

	def __repr__(self):
		naddr = "*NONE*" if self.node is None else self.node.address
		return 'Node ' + naddr + ' status ' + self.test + ' ' + str(self.value) + ' delayed ' + str(
			self.delay) + ' seconds' + ' IsTrue: ' + str(self.IsTrue())


# noinspection PyUnusedLocal
def VarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl','Var changed ',storeitem.name,' from ',old,' to ',new)
	# noinspection PyArgumentList
	if old != new:
		#PostControl(ISYVar, hub='AlertTasksVarChange', alert=param)
		tt = ConsoleEvent(CEvent.ISYVar, hub='AlertTasksVarChange', alert=param)
		print('post: {}'.format(repr(tt)))
		PostEvent(tt)
		#PostEvent(ConsoleEvent(CEvent.ISYVar, hub='AlertTasksVarChange', alert=param))

class VarChangeTrigger(object):
	def __init__(self, var, params):
		self.var = var
		self.test = params[0]
		self.value = params[1]
		self.delay = params[2]

	def IsTrue(self):
		val = -99999
		try:
			val = valuestore.GetVal(self.var)
			if self.test == 'EQ':
				return int(val) == int(self.value)
			elif self.test == 'NE':
				return int(val) != int(self.value)
			else:
				logsupport.Logs.Log('Bad test in IsTrue',self.test,severity=ConsoleError)
				return False # shouldn't happen
		except Exception as E:
			print(E)
			logsupport.Logs.Log('Exception in IsTrue: {} Test: {} Val: {} Compare Val: {}'.format(repr(E),self.test,val,self.value), severity=ConsoleError)
			return False

	def __repr__(self):
		return ' Variable ' + valuestore.ExternalizeVarName(self.var) + ' ' + self.test + ' ' + str(
			self.value) + ' delayed ' + str(self.delay) + ' seconds' + ' IsTrue: ' + str(self.IsTrue())

class InitTrigger(object):
	def __init__(self):
		pass
AlertUnigue = 0
def SchedulePeriodicEvent(alert):
	global AlertUnigue
	AlertUnigue += 1
	t = timers.OnceTimer(alert.trigger.NextInterval(), name=alert.name+'-Periodic-'+str(AlertUnigue), alert=alert, type='Periodic', proc=alert.Invoke);
	t.start()

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

	@staticmethod
	def IsTrue(): # If trigger comes to execute it is because timer went off so always return condition True
		return True

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
	def comparams(cspec):
		ctest = getvalid(cspec, 'Test', Tests)
		cvalue = cspec.get('Value', None)
		cdelay = utilities.get_timedelta(cspec.get('Delay', None))
		return ctest, cvalue, cdelay

	VarsTypes = {'StateVarChange': ('ISY', 'State'), 'IntVarChange': ('ISY', 'Int'), 'LocalVarChange': ('LocalVars',)}
	t = spec.get('Invoke', None)
	param = spec.get('Parameter', None)
	if t is None:
		logsupport.Logs.Log('Missing alert proc invoke spec in ' + nm, severity=ConsoleWarning)
		return None
	nmlist = t.split('.')

	if nmlist[0] in alertprocs:
		if len(nmlist) != 2:
			logsupport.Logs.Log('Bad alert proc spec ' + t + ' in ' + nm, severity=ConsoleWarning)
			return None
		# noinspection PyBroadException
		try:
			action = getattr(alertprocs[nmlist[0]], nmlist[1])
		except:
			logsupport.Logs.Log('No proc ', nmlist[1], ' in ', nmlist[0], severity=ConsoleWarning)
			return None
		actionname = t
		fixscreen = False
	elif nmlist[0] in alertscreen.alertscreens:
		if len(nmlist) != 1:
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
		n = spec.get('Node', '').split(':')
		if len(n) == 1:
			nd = n[0] # unqualified node - use default hub
			hub = config.defaulthub  # todo rethink in terms of the store stuff for the default hub then config.defaulthub coule go away
		else:
			nd = n[1]
			hub = config.Hubs[n[0]]
		Node = hub.GetNode(nd, nd)[1]  # use MonitorObj (1)
		test, value, delay = comparams(spec)
		if Node is None:
			logsupport.Logs.Log("Bad Node Spec on NodeChange alert in " + nm, severity=ConsoleWarning)
			return None
		trig = NodeChgtrigger(Node, test, value, delay)
		A = Alert(nm, triggertype, trig, action, actionname, param)
	elif triggertype in ('StateVarChange','IntVarChange', 'LocalVarChange'):
		n = VarsTypes[triggertype] + (spec.get('Var', ''),)
		logsupport.Logs.Log("Deprecated alert trigger ", triggertype, ' used - change to use VarChange ',valuestore.ExternalizeVarName(n),
							severity=ConsoleWarning)
		if n is None:
			logsupport.Logs.Log("Alert: ", nm, " var name doesn't exist", severity=ConsoleWarning)
			return None
		monitoredvars.append(n)
		trig = VarChangeTrigger(n,comparams(spec))
		A = Alert(nm, 'VarChange', trig, action, actionname, param)
		valuestore.AddAlert(n, (VarChanged, A))

	elif triggertype == 'VarChange':
		tmp = spec.get('Var', None)
		if tmp is None:
			logsupport.Logs.Log("Alert: ", nm, " var name doesn't exist", severity=ConsoleWarning)
			return None
		n = tmp.split(':')
		monitoredvars.append(n)
		trig = VarChangeTrigger(n,comparams(spec))
		A = Alert(nm, triggertype, trig, action, actionname, param)
		valuestore.AddAlert(n,(VarChanged, A))

	elif triggertype == 'External':
		pass
		return None
	elif triggertype == 'Init':  # Trigger once at start up passing in the configobj spec
		trig = InitTrigger()
		A = Alert(nm, triggertype, trig, action, actionname, param)
	else:
		logsupport.Logs.Log("Internal triggertype error",severity=ConsoleError)
		A = None

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

def DumpAlerts():
	with open('/home/pi/Console/AlertsDump.txt', mode='w') as f:
		for _, a in Alerts.AlertsList.items():
			f.write(repr(a) + '\n')


def HandleDeferredAlert(param):
	print(param)
	print(param.param)
	alert = param.param
	AlertsHB.Entry('Deferred Alert' + repr(alert))
	debug.debugPrint('Dispatch', 'Deferred alert fired: ', repr(alert))
	logsupport.Logs.Log("Deferred alert event fired" + repr(alert), severity=ConsoleDetail)
	alert.state = 'Fired'
	if alert.trigger.IsTrue():
		alert.Invoke()  # defered or delayed or scheduled alert firing or any periodic
	else:
		if isinstance(alert.trigger, NodeChgtrigger):
			# why not cleared before getting here?
			logsupport.Logs.Log('NodeChgTrigger cleared while deferred: ', repr(alert),
								severity=ConsoleDetail, hb=True)
		elif isinstance(alert.trigger, VarChangeTrigger):
			logsupport.Logs.Log('VarChangeTrigger cleared while deferred: ', repr(alert),
								severity=ConsoleDetail, hb=True)
		alert.state = 'Armed'
