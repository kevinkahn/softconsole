from hubs.ha.hasshub import HAnode, RegisterDomain, stringtonumeric
from hubs.ha import haremote as ha
import logsupport
from logsupport import ConsoleWarning


# todo = actually code this

class Input_Number(HAnode):  # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Input_Number, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('input_number', self.entity_id, self)
		self.DisplayStuff('init')

	def SetValue(self, val):
		# validate val between min and max, inc or dec
		if val.lower == 'inc':
			ha.call_service(self.Hub.api, 'input_number', 'increment', {'entity_id': '{}'.format(self.entity_id)})
		elif val.lower == 'dec':
			ha.call_service(self.Hub.api, 'input_number', 'decrement', {'entity_id': '{}'.format(self.entity_id)})
		elif val.lower in ('off', '0', 'false'):  # todo check in range convert to number call set value
			ha.call_service(self.Hub.api, 'input_number', 'turn_off',
							{'entity_id': '{}'.format(self.entity_id), 'value': '{}'.format(val)})
		else:
			logsupport.Logs.Log('{}: Illegal value ({}) for input_number {}'.format(self.Hub.name, val, self.name),
								severity=ConsoleWarning)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		self.DisplayStuff('update')
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
					print(ns['state'])
					stval = ns['state']
				self.state = stval
		except Exception as E:
			logsupport.Logs.Log('Input_number update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.state = 'unknown'
		self.DisplayStuff('update2')


RegisterDomain('input_number', Input_Number)
