from hubs.ha import haremote as ha
from hubs.ha.hasshub import StatefulHAnode, _NormalizeState, RegisterDomain


class Group(StatefulHAnode):
	def __init__(self, HAitem, d):
		super(Group, self).__init__(HAitem, **d)
		self.members = self.attributes['entity_id']
		self.Hub.RegisterEntity('group', self.entity_id, self)


RegisterDomain('group', Group)
