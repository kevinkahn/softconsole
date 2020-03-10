import debug
from hubs.ha import haremote as ha
from hubs.ha.hasshub import StatefulHAnode, RegisterDomain


class Switch(StatefulHAnode):
	def __init__(self, HAitem, d):
		super(Switch, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('switch', self.entity_id, self)

	# noinspection PyUnusedLocal
	def SendOnOffCommand(self, settoon):
		selcmd = ('turn_off', 'turn_on')
		ha.call_service(self.Hub.api, 'switch', selcmd[settoon], {'entity_id': '{}'.format(self.entity_id)})
		debug.debugPrint('HASSgeneral', "Switch OnOff sent: ", selcmd[settoon], ' to ', self.entity_id)


RegisterDomain('switch', Switch)
