from hubs.ha.hasshub import HAnode, _NormalizeState, RegisterDomain
from functools import partial

IgnoreThese = ('sun', 'person', 'notifications', 'persistent_notification', 'zwave', 'zone', 'history_graph', 'updater',
			   'configurator', 'weather')
IngoredEntities = {}


class IgnoredDomain(HAnode):
	def __init__(self, dom, HAitem, d):
		self.domname = dom
		super(IgnoredDomain, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity(self.domname, self.entity_id, self)
		IngoredEntities[dom][self.name] = self


for d in IgnoreThese:
	reg = partial(IgnoredDomain, d)
	IngoredEntities[d] = {}
	RegisterDomain(d, reg)
