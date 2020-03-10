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
				if ns['state'] in ('', 'unknown', 'None'):
					logsupport.Logs.Log('Sensor data missing for {} value: {}'.format(ns['entity_id'], ns['state']))
				else:
					try:
						stval = stringtonumeric(ns['state'])
					except ValueError:
						stval = tuple(map(int, ns['state'].split(
							'-')))  # this is never executed because str to num returns the string if can't convert todo
					self.Hub.sensorstore.SetVal(self.entity_id, stval)
		except Exception as E:
			logsupport.Logs.Log('Sensor update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))


# print('Sensor update {} {} {}'.format(self.entity_id, stval, self.Hub.sensorstore.GetVal(self.entity_id)))

RegisterDomain('sensor', Sensor)
