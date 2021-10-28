from hubs.ha.hasshub import HAnode, RegisterDomain
from functools import partial
import hubs.ha.hasshub as hasshub
import logsupport

IgnoreThese = ('sun', 'person', 'notifications', 'persistent_notification', 'zone', 'history_graph', 'updater',
			   'configurator', 'weather', 'counter', 'camera', 'lock', 'alarm_control_panel',
			   'device_tracker', 'vacuum', 'input_number', 'input_text', 'input_select', 'timer', 'alert', 'zwave_js',
			   'select')
IngoredEntities = {}


class IgnoredDomain(HAnode):
	def __init__(self, dom, HAitem, args):
		super(IgnoredDomain, self).__init__(HAitem, **args)
		self.domname = dom
		self.Hub.RegisterEntity(self.domname, self.entity_id, self)
		IngoredEntities[dom][self.name] = self

	def Update(self, **ns):
		# print("ignore")
		return

	def LogNewEntity(self, newstate):
		logsupport.Logs.Log(
			"New entity in ignored domain since startup seen from {}: {} (Domain: {}) New: {}".format(
				self.Hub.name, self.entity_id, self.domname, repr(newstate)), severity=logsupport.ConsoleDetail)

	def _NormalizeState(self, state, brightness=None):
		# for ignored domains don't validate state info
		return state

def IgnoreDomainSpecificEvent(e, message):
	logsupport.Logs.Log("Event {} to ignored domain {}".format(e, message), severity=logsupport.ConsoleDetail)

def AddIgnoredDomain(dom):
	global IngoredEntities
	register = partial(IgnoredDomain, dom)
	IngoredEntities[dom] = {}
	RegisterDomain(dom, register, IgnoreDomainSpecificEvent)
	logsupport.Logs.Log('Adding ignored HA domain: {}'.format(dom))


hasshub.AddIgnoredDomain = AddIgnoredDomain

# logsupport.Logs.Log('Note: following HA domains are ignored by the console:')
for d in IgnoreThese:
	#	logsupport.Logs.Log('     {}'.format(d))
	reg = partial(IgnoredDomain, d)
	IngoredEntities[d] = {}
	RegisterDomain(d, reg, IgnoreDomainSpecificEvent)
