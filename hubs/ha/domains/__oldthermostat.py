from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain
from controlevents import CEvent, PostEvent, ConsoleEvent, PostIfInterested
from utils import timers
import functools


# noinspection PyTypeChecker
class Thermostat(HAnode):  # deprecated version
	def __init__(self, HAitem, d):
		super(Thermostat, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('climate', self.entity_id, self)
		self.timerseq = 0
		# noinspection PyBroadException
		try:
			self.temperature = self.attributes['temperature']
			self.curtemp = self.attributes['current_temperature']
			self.target_low = self.attributes['target_temp_low']
			self.target_high = self.attributes['target_temp_high']
			self.mode = self.attributes['operation_mode']
			self.fan = self.attributes['fan_mode']
			self.fanstates = self.attributes['fan_list']
			self.modelist = self.attributes['operation_list']
		except:
			pass

	# noinspection PyUnusedLocal
	def ErrorFakeChange(self, param=None):
		PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id, value=self.internalstate))

	def Update(self, **ns):
		if 'attributes' in ns: self.attributes = ns['attributes']
		self.temperature = self.attributes['temperature']
		self.curtemp = self.attributes['current_temperature']
		self.target_low = self.attributes['target_temp_low']
		self.target_high = self.attributes['target_temp_high']
		self.mode = self.attributes['operation_mode']
		self.fan = self.attributes['fan_mode']
		PostIfInterested(self.Hub, self.entity_id, self.internalstate)

	# noinspection DuplicatedCode
	def PushSetpoints(self, t_low, t_high):
		ha.call_service_async(self.Hub.api, 'climate', 'set_temperature',
							  {'entity_id': '{}'.format(self.entity_id), 'target_temp_high': str(t_high),
							   'target_temp_low': str(t_low)})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushsetpoint-{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)

	def GetThermInfo(self):
		if self.target_low is not None:
			return self.curtemp, self.target_low, self.target_high, self.HVAC_state, self.mode, self.fan
		else:
			return self.curtemp, self.temperature, self.temperature, self.HVAC_state, self.mode, self.fan

	# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
	def _HVACstatechange(self, storeitem, old, new, param, chgsource):
		self.HVAC_state = new
		PostIfInterested(self.Hub, self.entity_id, new)

	def _connectsensors(self, HVACsensor):
		self.HVAC_state = HVACsensor.state
		# noinspection PyProtectedMember
		HVACsensor.SetSensorAlert(functools.partial(self._HVACstatechange))

	def GetModeInfo(self):
		return self.modelist, self.fanstates

	def PushFanState(self, mode):
		ha.call_service_async(self.Hub.api, 'climate', 'set_fan_mode',
							  {'entity_id': '{}'.format(self.entity_id), 'fan_mode': mode})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushfanstate-{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)

	def PushMode(self, mode):
		# noinspection PyBroadException
		ha.call_service_async(self.Hub.api, 'climate', 'set_operation_mode',
							  {'entity_id': '{}'.format(self.entity_id), 'operation_mode': mode})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushmode -{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)


RegisterDomain('climate', Thermostat)
