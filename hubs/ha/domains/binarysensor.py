from hubs.ha.hasshub import HAnode, RegisterDomain
import logsupport
from logsupport import ConsoleWarning


class BinarySensor(HAnode):
	def __init__(self, HAitem, d):
		super(BinarySensor, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('binary_sensor', self.entity_id, self)
		if self.state not in ('on', 'off', 'unavailable', 'unknown'):
			logsupport.Logs.Log("Odd Binary sensor initial value: ", self.entity_id, ':', self.state,
								severity=ConsoleWarning)
		self.Hub.attrstore.SetVal(self.entity_id, self.state == 'on')
		self.missinglast = 'Explicit' if self.state in (
			'Xunknown', 'Xunavailable') else 'No'  # if unknown assume really not there (like pool stuff) options:
		if self.missinglast == 'Explicit':
			print('Unavailable: {}'.format(self.entity_id))

	def SetSensorAlert(self, p):
		self.Hub.attrstore.AddAlert(self.entity_id, p)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		if 'attributes' in ns:
			self.attributes = ns['attributes']
		if 'state' in ns:
			if ns['state'] == 'on':
				st = True
			elif ns['state'] == 'off':
				st = False
			elif ns['state'] in ('unavailable', 'unknown'):
				st = None
			else:
				st = None
				logsupport.Logs.Log("Bad Binary sensor value: ", self.entity_id, ':', ns['state'],
									severity=ConsoleWarning)
			self.Hub.attrstore.SetVal(self.entity_id, st)


RegisterDomain('binary_sensor', BinarySensor)
