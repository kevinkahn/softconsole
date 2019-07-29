from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, _NormalizeState, RegisterDomain, stringtonumeric
import debug


class Script(HAnode):
	def __init__(self, HAitem, d):
		super(Script, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('script', self.entity_id, self)

	def RunProgram(self):
		ha.call_service(self.Hub.api, 'script', self.object_id)  # todo this looks wrong
		debug.debugPrint('HASSgeneral', "Script execute sent to: script.", self.entity_id)


RegisterDomain('script', Script)
