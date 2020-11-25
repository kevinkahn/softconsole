import debug
import logsupport
from controlevents import PostEvent, ConsoleEvent, CEvent
from stores import valuestore
import alertsystem.alertutils as alertutils
import alertsystem.alerttasks as alerttasks
from functools import partial

triggername = 'VarChange'


class VarChangeTrigger(object):
	def __init__(self, var, params):
		self.var = var
		self.test = params[0]
		self.value = params[1]
		self.delay = params[2]

	def IsTrue(self):
		return alertutils.TestCondition(valuestore.GetVal(self.var), self.value, self.test)

	def __repr__(self):
		return ' Variable ' + valuestore.ExternalizeVarName(self.var) + ' ' + self.test + ' ' + str(
			self.value) + ' delayed ' + str(self.delay) + ' seconds' + ' IsTrue: ' + str(self.IsTrue())


def Arm(a):
	a.state = 'Init'
	if a.trigger.IsTrue():
		PostEvent(ConsoleEvent(CEvent.ISYVar, hub='AlertTasksVarChange', alert=a))


# Note: VarChange alerts don't need setup because the store has an alert proc

def VarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl', 'Var changed ', storeitem.name, ' from ', old, ' to ', new)
	# noinspection PyArgumentList
	if old != new:
		PostEvent(ConsoleEvent(CEvent.ISYVar, hub='AlertTasksVarChange', alert=param))


def FinishParse(n, nm, spec, action, actionname, param):
	alerttasks.monitoredvars.append(n)
	trig = VarChangeTrigger(n, alertutils.comparams(spec))
	A = alerttasks.Alert(nm, triggername, trig, action, actionname, param)
	valuestore.AddAlert(n, (VarChanged, A))
	return A


def Parse(nm, spec, action, actionname, param):
	tmp = spec.get('Var', None)
	if tmp is None:
		logsupport.Logs.Log("Alert: ", nm, " var name doesn't exist", severity=logsupport.ConsoleWarning)
		return None
	n = tmp.split(':')
	return FinishParse(n, nm, spec, action, actionname, param)


def ParseOld(nm, spec, action, actionname, param, oldnm):
	VarsTypes = {'StateVarChange': ('ISY', 'State'), 'IntVarChange': ('ISY', 'Int'), 'LocalVarChange': ('LocalVars',)}
	n = VarsTypes[oldnm] + (spec.get('Var', ''),)
	if n is None:
		logsupport.Logs.Log("Alert: ", nm, " var name doesn't exist", severity=logsupport.ConsoleWarning)
		return None
	logsupport.Logs.Log("Deprecated alert trigger ", oldnm, ' used - change to use VarChange ',
						valuestore.ExternalizeVarName(n),
						severity=logsupport.ConsoleWarning)
	return FinishParse(n, nm, spec, action, actionname, param)


alertutils.TriggerTypes[triggername] = alertutils.TriggerRecord(Parse, Arm, VarChangeTrigger)
alertutils.TriggerTypes['StateVarChange'] = alertutils.TriggerRecord(partial(ParseOld, 'StateVarChange'), Arm,
																	 VarChangeTrigger)
alertutils.TriggerTypes['IntVarChange'] = alertutils.TriggerRecord(partial(ParseOld, 'IntVarChange'), Arm,
																   VarChangeTrigger)
alertutils.TriggerTypes['LocalVarChange'] = alertutils.TriggerRecord(partial(ParseOld, 'LocalVarChange'), Arm,
																	 VarChangeTrigger)
