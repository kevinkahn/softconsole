from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, _NormalizeState, RegisterDomain
import debug


class Automation(HAnode):
	def __init__(self, HAitem, d):
		super(Automation, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('automation', self.entity_id, self)

	def RunProgram(self):
		ha.call_service(self.Hub.api, 'automation', 'trigger', {'entity_id': '{}'.format(self.entity_id)})
		debug.debugPrint('HASSgeneral', "Automation trigger sent to: ", self.entity_id)


RegisterDomain('automation', Automation)
