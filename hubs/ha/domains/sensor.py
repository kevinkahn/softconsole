from hubs.ha.hasshub import HAnode, RegisterDomain, stringtonumeric
import logsupport


class Sensor(HAnode):  # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Sensor, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('sensor', self.entity_id, self)
		self.Hub.sensorstore.SetVal(self.entity_id, stringtonumeric(self.state))

	def _SetSensorAlert(self, p):
		self.Hub.sensorstore.AddAlert(self.entity_id, p)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		if 'attributes' in ns: self.attributes = ns['attributes']
		try:
			if 'state' in ns:
				if ns['state'] in ('', 'unknown', 'None', 'unavailable'):
					logsupport.Logs.Log('Sensor data missing for {} value: {}'.format(ns['entity_id'], ns['state']))
					stval = None
				else:
					stval = stringtonumeric(ns['state'])
				self.Hub.sensorstore.SetVal(self.entity_id, stval)
		except Exception as E:
			logsupport.Logs.Log('Sensor update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.Hub.sensorstore.SetVal(self.entity_id, None)


RegisterDomain('sensor', Sensor)
