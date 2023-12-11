import logsupport
import alertsystem.alerttasks as alerttasks
import alertsystem.alertutils as alertutils
import hubs.hubs
from controlevents import PostEvent, ConsoleEvent, CEvent

triggername = 'NodeChange'


class NodeChgtrigger(object):
	def __init__(self, node, test, value, delay):
		self.node = node
		self.test = test
		self.value = value
		self.delay = delay

	def IsTrue(self):
		return alertutils.TestCondition(self.node.Hub.GetCurrentStatus(self.node), self.value, self.test)

	def __repr__(self):
		naddr = "*NONE*" if self.node is None else self.node.address
		return 'Node ' + naddr + ' status ' + self.test + ' ' + str(self.value) + ' delayed ' + str(
			self.delay) + ' seconds' + ' IsTrue: ' + str(self.IsTrue())


def Parse(nm, spec, action, actionname, param):
	n = spec.get('Node', '').split(':')
	if len(n) == 1:
		nd = n[0]  # unqualified node - use default hub
		hub = hubs.hubs.defaulthub
	else:
		nd = n[1]
		hub = hubs.hubs.Hubs[n[0]]
	Node = hub.GetNode(nd, nd)[1]  # use MonitorObj (1)
	test, value, delay = alertutils.comparams(spec)
	if Node is None:
		logsupport.Logs.Log("Bad Node Spec on NodeChange alert in " + nm, severity=logsupport.ConsoleWarning)
		return None
	trig = NodeChgtrigger(Node, test, value, delay)
	return alerttasks.Alert(nm, triggername, trig, action, actionname, param)


def Arm(a):
	a.trigger.node.Hub.SetAlertWatch(a.trigger.node, a)
	if a.trigger.IsTrue():
		# noinspection PyArgumentList
		PostEvent(ConsoleEvent(CEvent.ISYAlert, hub='DS-NodeChange', alert=a))


alertutils.TriggerTypes[triggername] = alertutils.TriggerRecord(Parse, Arm, NodeChgtrigger)
