from hubs.ha.hasshub import HAnode, RegisterDomain, stringtonumeric
from hubs.ha import haremote as ha
import logsupport
from logsupport import ConsoleWarning


class Input_Boolean(HAnode):  # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Input_Boolean, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('input_boolean', self.entity_id, self)
		self.inputtype = 'boolean'
		self.DisplayStuff('init')
		logsupport.Logs.Log(
			'Initialize attr store for input_boolean {} as {}'.format(self.entity_id, stringtonumeric(self.state)))  # ,

	# severity=logsupport.ConsoleDetail)

	def SetValue(self, val):
		# validate val as 'on/off', 0/1, true/false, or toggle
		if val == 'toggle':
			ha.call_service(self.Hub.api, 'input_boolean', 'toggle', {'entity_id': '{}'.format(self.entity_id)})
		elif val.lower in ('on', '1', 'true'):
			ha.call_service(self.Hub.api, 'input_boolean', 'turn_on', {'entity_id': '{}'.format(self.entity_id)})
		elif val.lower in ('off', '0', 'false'):
			ha.call_service(self.Hub.api, 'input_boolean', 'turn_off', {'entity_id': '{}'.format(self.entity_id)})
		else:
			logsupport.Logs.Log('{}: Illegal value ({}) for input_boolean {}'.format(self.Hub.name, val, self.name),
								severity=ConsoleWarning)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		#		self.DisplayStuff('update')
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
					stval = ns['state']
				self.state = stval
		except Exception as E:
			logsupport.Logs.Log('Input_boolean update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.state = 'unknown'


RegisterDomain('input_boolean', Input_Boolean)
