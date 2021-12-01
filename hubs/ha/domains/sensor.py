from hubs.ha.hasshub import HAnode, RegisterDomain, stringtonumeric
import logsupport


class Sensor(HAnode):  # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Sensor, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('sensor', self.entity_id, self)
		logsupport.Logs.Log(
			'Initialize attr store for sensor {} as {}'.format(self.entity_id, stringtonumeric(self.state)),
			severity=logsupport.ConsoleDetail)
		self.Hub.attrstore.SetVal(self.entity_id, stringtonumeric(self.state))
		self.missinglast = self.state == 'unknown'  # if unknown assume really not there (like pool stuff)

	def SetSensorAlert(self, p):
		self.Hub.attrstore.AddAlert(self.entity_id, p)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		if 'attributes' in ns: self.attributes = ns['attributes']
		try:
			if 'state' in ns:
				if ns['state'] in ('', 'unknown', 'None', 'unavailable'):
					if not self.missinglast:  # don't keep reporting same outage
						logsupport.Logs.Log('Sensor data missing for {} value: {}'.format(ns['entity_id'], ns['state']))
					else:
						logsupport.Logs.Log('Sensor data missing for {} value: {}'.format(ns['entity_id'], ns['state']),
											severity=logsupport.ConsoleDetail)
					self.missinglast = True
					stval = None
				else:
					# noinspection PyBroadException
					try:
						# convert to numeric if a number
						stval = stringtonumeric(ns['state'])
					except Exception:
						# otherwise, leave as string
						stval = ns['state']
				self.Hub.attrstore.SetVal(self.entity_id, stval)
		except Exception as E:
			logsupport.Logs.Log('Sensor update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.Hub.attrstore.SetVal(self.entity_id, None)


RegisterDomain('sensor', Sensor)
