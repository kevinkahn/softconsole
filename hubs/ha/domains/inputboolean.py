from hubs.ha.hasshub import HAnode, RegisterDomain
from hubs.ha import haremote as ha
import logsupport
from logsupport import ConsoleWarning


class Input_Boolean(HAnode):  # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Input_Boolean, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('input_boolean', self.entity_id, self)
		# self.DisplayStuff('init')

	def SetValue(self, inputop):
		# validate val as 'on/off', 0/1, true/false, or toggle
		if inputop.lower() == 'toggle':
			ha.call_service(self.Hub.api, 'input_boolean', 'toggle', {'entity_id': '{}'.format(self.entity_id)})
		elif inputop.lower() in ('on', '1', 'true'):
			ha.call_service(self.Hub.api, 'input_boolean', 'turn_on', {'entity_id': '{}'.format(self.entity_id)})
		elif inputop.lower() in ('off', '0', 'false'):
			ha.call_service(self.Hub.api, 'input_boolean', 'turn_off', {'entity_id': '{}'.format(self.entity_id)})
		else:
			logsupport.Logs.Log('{}: Illegal value ({}) for input_boolean {}'.format(self.Hub.name, inputop, self.name),
								severity=ConsoleWarning)

	def Update(self, **ns):
		if 'attributes' in ns:
			self.attributes = ns['attributes']
		try:
			if 'state' in ns:
				if ns['state'] in ('', 'unknown', 'None', 'unavailable'):
					logsupport.Logs.Log(
						'Input boolean data missing for {} value: {}'.format(ns['entity_id'], ns['state']))
					stval = None
				else:
					stval = ns['state']
				self.state = stval
			super().Update(**ns)
		except Exception as E:
			logsupport.Logs.Log('Input_boolean update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.state = 'unknown'


RegisterDomain('input_boolean', Input_Boolean)
