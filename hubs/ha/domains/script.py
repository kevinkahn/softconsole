from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain, stringtonumeric
import debug


class Script(HAnode):
	def __init__(self, HAitem, d):
		super(Script, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('script', self.entity_id, self)

	def RunProgram(self, param=None):
		ha.call_service_async(self.Hub.api, 'script', self.name)  # , service_data=param)
		debug.debugPrint('HASSgeneral', "Script execute sent to: script.", self.object_id)


RegisterDomain('script', Script)
