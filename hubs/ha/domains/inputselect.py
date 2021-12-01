from hubs.ha.hasshub import HAnode, RegisterDomain
from hubs.ha import haremote as ha
import logsupport
from logsupport import ConsoleWarning


class Input_Select(HAnode):  # not stateful since it updates directly to store value
	def SetOptions(self):
		if 'options' in self.attributes:
			self.options = self.attributes['options']

	def __init__(self, HAitem, d):
		super(Input_Select, self).__init__(HAitem, **d)
		self.options = None
		self.Hub.RegisterEntity('input_select', self.entity_id, self)
		self.SetOptions()

	# self.DisplayStuff('init',True)

	def SetValue(self, val):
		# validate to optionval, first, last, next, nextcycle, prev, prevcycle
		if val.lower() == 'first':
			ha.call_service(self.Hub.api, 'input_select', 'select_first', {'entity_id': '{}'.format(self.entity_id)})
		elif val.lower() == 'last':
			ha.call_service(self.Hub.api, 'input_select', 'select_last', {'entity_id': '{}'.format(self.entity_id)})
		elif val.lower() in ('next', 'nextcycle'):
			cycle = val.lower() == 'nextcycle'
			ha.call_service(self.Hub.api, 'input_select', 'select_next',
							{'entity_id': '{}'.format(self.entity_id), 'cycle': cycle})
		elif val.lower() in ('prev', 'prevcycle'):
			cycle = val.lower() == 'prevcycle'
			ha.call_service(self.Hub.api, 'input_select', 'select_previous',
							{'entity_id': '{}'.format(self.entity_id), 'cycle': cycle})
		elif val in self.options:
			ha.call_service(self.Hub.api, 'input_select', 'select_option',
							{'entity_id': '{}'.format(self.entity_id), 'option': '{}'.format(val)})
		else:
			logsupport.Logs.Log('{}: Illegal value ({}) for Input_Select {}'.format(self.Hub.name, val, self.name),
								severity=ConsoleWarning)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		# self.DisplayStuff('update', True)
		if 'attributes' in ns:
			self.attributes = ns['attributes']
			self.SetOptions()
		try:
			if 'state' in ns:
				if ns['state'] in ('', 'unknown', 'None', 'unavailable'):
					logsupport.Logs.Log(
						'Input select data missing for {} value: {}'.format(ns['entity_id'], ns['state']))
					stval = None
				else:
					stval = ns['state']
				self.state = stval
		except Exception as E:
			logsupport.Logs.Log('Input_Select update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.state = 'unknown'
# self.DisplayStuff('update2', True)


RegisterDomain('input_select', Input_Select)
