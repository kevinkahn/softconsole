import debug
import historybuffer
import logsupport
import screens.__screens as screens
from utils import utilities
from configobjects import Section
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError
from screens.specificscreens import alertscreen
import guicore.switcher as switcher
import alertsystem.alertutils as alertutils
import os
import importlib

alertprocs = {}  # set by modules from alerts directory
monitoredvars = []

for trigtype in os.listdir(os.getcwd() + '/alertsystem/triggers'):
	if '__' not in trigtype:
		splitname = os.path.splitext(trigtype)
		if splitname[1] == '.py':
			importlib.import_module('alertsystem.triggers.' + splitname[0])

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
		self.timer = None  # holds timer when delayed

	@property
	def state(self):
		return self._state

	@state.setter
	def state(self, value):
		debug.debugPrint('AlertsTrace', 'Alert: ' + self.name + ' changed from ' + self._state + ' to ' + value)
		self._state = value

	# noinspection PyUnusedLocal
	def Invoke(self, param=None):
		if self.actiontarget is None:
			# alert causes no action (e.g., filewatch may just update vars)
			pass
		elif isinstance(self.actiontarget, screens.screentypes["Alert"]):
			self.state = 'Active'
			# if system is in a stack empty it.  End of alert will go back to home and not the stack
			switcher.SwitchScreen(self.actiontarget, 'Bright', 'Go to alert screen', newstate='Alert', clear=True)
		else:
			self.state = 'Active'
			self.actiontarget(self)  # target is the proc
			# noinspection PyAttributeOutsideInit
			self.state = "Armed"
		if hasattr(self.trigger, 'ReArm'):
			self.trigger.ReArm(self)

	def __repr__(self):
		if self.actiontarget is None:
			targtype = 'No Action'
		elif isinstance(self.actiontarget, tuple(
				screens.screentypes.values())):  # really should check for screen.ScreenDescriptor but that loops
			targtype = 'Screen'
		else:
			targtype = 'Proc'
		tname = '*no timer*'
		if self.timer is not None: tname = self.timer.name
		return '{}:{} Alert({}) Trigger: {} \n  Invoke: {}:{} Target:{}\n  Params: {}\n  Timer: {}'.format(self.name,
																										   self.type,
																										   self.state,
																										   repr(
																											   self.trigger),
																										   targtype,
																										   self.actionname,
																										   str(
																											   self.actiontarget),
																										   self.param,
																										   tname)


def ArmAlerts():
	for a in AlertsList.values():
		a.state = 'Armed'
		logsupport.Logs.Log("Arming " + a.type + " alert " + a.name)
		logsupport.Logs.Log("->" + str(a), severity=ConsoleDetail)

		if a.type in alertutils.TriggerTypes:
			alertutils.TriggerTypes[a.type].Arm(a)
		else:
			logsupport.Logs.Log("Internal error - unknown alert type: ", a.type, ' for ', a.name,
								severity=ConsoleError, tb=False)

def ParseAlertParams(nm, spec):
	global alertprocs, monitoredvars

	t = spec.get('Invoke', None)
	param = spec.get('Parameter', None)
	if t is None:
		logsupport.Logs.Log('Alert {} has no action'.format(nm), severity=ConsoleWarning)
		action = None
		actionname = '*none*'
		fixscreen = False
	else:
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
			utilities.MarkErr(spec)
			return None

	triggertype = alertutils.getvalid(spec, 'Type', alertutils.TriggerTypes.keys())
	if triggertype in alertutils.TriggerTypes:
		A = alertutils.TriggerTypes[triggertype].Parse(nm, spec, action, actionname, param)

	else:
		logsupport.Logs.Log("No such triggertype: {}".format(triggertype), severity=ConsoleError)
		A = None

	logsupport.Logs.Log("Created alert: " + nm)
	logsupport.Logs.Log("->" + str(A), severity=ConsoleDetail)
	if fixscreen:
		action.Alert = A

	return A


# class Alerts(object):
#	def __init__(self, alertsspec):
#		self.AlertsList = {}  # hash:AlertItem
#		if alertsspec is not None:
#			for nm, spec in alertsspec.items():
#				if isinstance(spec, Section):
#					alert = ParseAlertParams(nm, spec)
#					if alert is not None:
#						self.AlertsList[id(alert)] = alert

def ParseAlerts(alertspec):
	if alertspec is not None:
		for nm, spec in alertspec.items():
			if isinstance(spec, Section):
				alert = ParseAlertParams(nm, spec)
				if alert is not None:
					AlertsList[id(alert)] = alert


AlertsList = {}


# AlertItems: Alerts

def DumpAlerts():
	with open('/home/pi/Console/AlertsDump.txt', mode='w') as f:
		for _, a in AlertsList.items():
			f.write(repr(a) + '\n')


def HandleDeferredAlert(param):
	alert = param.param
	AlertsHB.Entry('Deferred Alert' + repr(alert))
	debug.debugPrint('Dispatch', 'Deferred alert fired: ', repr(alert))
	logsupport.Logs.Log("Deferred alert event fired" + repr(alert), severity=ConsoleDetail)
	alert.state = 'Fired'
	if alert.trigger.IsTrue():
		alert.Invoke()  # defered or delayed or scheduled alert firing or any periodic
	else:
		alert.state = 'Armed'
