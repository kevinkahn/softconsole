from hubs.ha.hasshub import HAnode, RegisterDomain
from hubs.ha import haremote as ha
import logsupport
from logsupport import ConsoleWarning

class Input_Number(HAnode):  # not stateful since it updates directly to store value
	def SetMinMax(self):
		if 'min' in self.attributes:
			self.minval = float(self.attributes['min'])
			self.maxval = float(self.attributes['max'])

	def __init__(self, HAitem, d):
		super(Input_Number, self).__init__(HAitem, **d)
		self.minval = None
		self.maxval = None
		self.Hub.RegisterEntity('input_number', self.entity_id, self)
		self.SetMinMax()

	# self.DisplayStuff('init',True)

	def SetValue(self, inputop):
		# validate val between min and max, inc or dec
		if inputop.lower() == 'inc':
			ha.call_service(self.Hub.api, 'input_number', 'increment', {'entity_id': '{}'.format(self.entity_id)})
		elif inputop.lower() == 'dec':
			ha.call_service(self.Hub.api, 'input_number', 'decrement', {'entity_id': '{}'.format(self.entity_id)})
		else:
			try:
				inputop = float(inputop)
			except ValueError:
				logsupport.Logs.Log(
					'{}: Illegal value ({}) for input_number {}'.format(self.Hub.name, inputop, self.name),
					severity=ConsoleWarning)
				return
			if self.minval <= inputop <= self.maxval:
				ha.call_service(self.Hub.api, 'input_number', 'set_value',
								{'entity_id': '{}'.format(self.entity_id), 'value': '{}'.format(inputop)})
			else:
				logsupport.Logs.Log(
					'{}: Out of range value ({}) for input_number {}'.format(self.Hub.name, inputop, self.name),
					severity=ConsoleWarning)

	def Update(self, **ns):
		# super(Sensor,self).Update(**ns)
		# self.DisplayStuff('update', True)
		if 'attributes' in ns:
			self.attributes = ns['attributes']
			self.SetMinMax()
		try:
			if 'state' in ns:
				if ns['state'] in ('', 'unknown', 'None', 'unavailable'):
					logsupport.Logs.Log(
						'Input number data missing for {} value: {}'.format(ns['entity_id'], ns['state']))
					stval = None
				else:
					stval = ns['state']
				self.state = stval
		except Exception as E:
			logsupport.Logs.Log('Input_number update error: State: {}  Exc:{}'.format(repr(ns), repr(E)))
			self.state = 'unknown'
	#self.DisplayStuff('update2', True)


RegisterDomain('input_number', Input_Number)
