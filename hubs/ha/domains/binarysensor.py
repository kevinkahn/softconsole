from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, _NormalizeState, RegisterDomain
import logsupport
from logsupport import ConsoleWarning


class BinarySensor(HAnode):
	def __init__(self, HAitem, d):
		super(BinarySensor, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('binary_sensor', self.entity_id, self)
		if self.state not in ('on', 'off', 'unavailable'):
			logsupport.Logs.Log("Odd Binary sensor initial value: ", self.entity_id, ':', self.state,
								severity=ConsoleWarning)
		self.Hub.sensorstore.SetVal(self.entity_id, self.state == 'on')

	def _SetSensorAlert(self, p):
		self.Hub.sensorstore.AddAlert(self.entity_id, p)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		if 'attributes' in ns: self.attributes = ns['attributes']
		if 'state' in ns:
			if ns['state'] == 'on':
				st = True
			elif ns['state'] == 'off':
				st = False
			elif ns['state'] == 'unavailable':
				st = False
			else:
				st = False
				logsupport.Logs.Log("Bad Binary sensor value: ", self.entity_id, ':', ns['state'],
									severity=ConsoleWarning)
			self.Hub.sensorstore.SetVal(self.entity_id, st)

	def Source(self, roomname, sourcename):  # todo why ius this here?
		ha.call_service(self.Hub.api, 'media_player', 'select_source', {'entity_id': '{}'.format(roomname),
																		'source': '{}'.format(sourcename)})


RegisterDomain('binary_sensor', BinarySensor)
