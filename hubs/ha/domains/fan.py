import debug
from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain
import logsupport

class Fan(HAnode):
	def __init__(self, HAitem, d):
		super().__init__(HAitem, **d)
		self.Hub.RegisterEntity('fan', self.entity_id, self)

	def Update(self, **ns):
		super().Update(**ns)

	# noinspection PyUnusedLocal
	def SendOnOffCommand(self, settoon):
		try:
			selcmd = ('turn_off', 'turn_on')
			# logsupport.DevPrint("Light on/off: {} {} {}".format(selcmd[settoon],self.entity_id, time.time()))
			ha.call_service(self.Hub.api, 'fan', selcmd[settoon], {'entity_id': '{}'.format(self.entity_id)})
			debug.debugPrint('HASSgeneral', "Fan OnOff sent: ", selcmd[settoon], ' to ', self.entity_id)
		# PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
		#					   value=(0, 255)[
		#						   settoon]))  # hack to provide immediate faked feedback on zwave lights that take a while to report back todo fix
		except ha.HomeAssistantError:
			logsupport.Logs.Log(
				"{} didn't respond to fan on/off for {} - probably restarting".format(self.Hub.name, self.name),
				severity=logsupport.ConsoleWarning)


RegisterDomain('fan', Fan)
