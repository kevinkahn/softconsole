import debug
from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain
import logsupport


class Switch(HAnode):
	def __init__(self, HAitem, d):
		super().__init__(HAitem, **d)
		self.Hub.RegisterEntity('switch', self.entity_id, self)

	# noinspection PyUnusedLocal
	def SendOnOffCommand(self, settoon):
		try:
			selcmd = ('turn_off', 'turn_on')
			ha.call_service(self.Hub.api, 'switch', selcmd[settoon], {'entity_id': '{}'.format(self.entity_id)})
			debug.debugPrint('HASSgeneral', "Switch OnOff sent: ", selcmd[settoon], ' to ', self.entity_id)
		except ha.HomeAssistantError:
			# HA probably restarting
			logsupport.Logs.Log("{} didn't respond to switch on/off for {} - probably restarting".format(self.Hub.name, self.name), severity = logsupport.ConsoleWarning)


RegisterDomain('switch', Switch)
