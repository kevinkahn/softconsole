from hubs.ha.hasshub import HAnode, RegisterDomain
from functools import partial
import hubs.ha.hasshub as hasshub
import logsupport

IgnoreThese = ('sun', 'person', 'notifications', 'persistent_notification', 'zwave', 'zone', 'history_graph', 'updater',
			   'configurator', 'weather', 'zwave_mqtt', 'scene')
IngoredEntities = {}


class IgnoredDomain(HAnode):
	def __init__(self, dom, HAitem, d):
		self.domname = dom
		super(IgnoredDomain, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity(self.domname, self.entity_id, self)
		IngoredEntities[dom][self.name] = self

	def LogNewEntity(self, newstate):
		logsupport.Logs.Log(  # tempdel
			"New entity in ignored domain since startup seen from {}: {} (Domain: {}) New: {}".format(
				self.Hub.name, self.entity_id, self.domname, repr(newstate)), severity = logsupport.ConsoleDetail)


def AddIgnoredDomain(dom):
	global IngoredEntities
	reg = partial(IgnoredDomain, dom)
	IngoredEntities[dom] = {}
	RegisterDomain(dom, reg)


hasshub.AddIgnoredDomain = AddIgnoredDomain


for d in IgnoreThese:
	reg = partial(IgnoredDomain, d)
	IngoredEntities[d] = {}
	RegisterDomain(d, reg)
