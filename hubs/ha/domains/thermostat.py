from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain
from controlevents import CEvent, PostEvent, ConsoleEvent, PostIfInterested
from utils import timers
import functools
import logsupport

featureset = ('TargTemp', 'TargRange', 'TargHum', 'FanModes', 'Presets')


def GetFeatures(n):
	actfeats = []
	for i in range(len(featureset)):
		if n % 2 == 1:
			actfeats.append(featureset[i])
		n = n // 2
	return actfeats


# noinspection PyTypeChecker
class Thermostat(HAnode):  # not stateful since has much state info

	def GetRange(self):
		pass

	def GetTarget(self):
		pass

	def GetPresets(self):
		pass

	def GetFanModes(self):
		pass

	def __init__(self, HAitem, d):
		self.target_high = 100
		self.target_low = 0
		self.temperature = 0
		self.fanstates = []
		self.fan = None
		super().__init__(HAitem, **d)
		self.Hub.RegisterEntity('climate', self.entity_id, self)
		self.timerseq = 0
		# noinspection PyBroadException
		self.features = GetFeatures(self.attributes['supported_features'])
		if 'TargRange' in self.features:
			def GetRange():
				if 'target_temp_low' in self.attributes:
					self.target_low = self.attributes['target_temp_low']
				else:
					logsupport.Logs.Log("Missing target_low update in {} ({})".format(self.name, self.attributes))
				if 'target_temp_high' in self.attributes:
					self.target_high = self.attributes['target_temp_high']
				else:
					logsupport.Logs.Log("Missing target_high update in {} ({})".format(self.name, self.attributes))

			self.GetRange = GetRange

		if 'TargTemp' in self.features:
			def GetTarget():
				if 'temperature' in self.attributes:
					self.temperature = self.attributes['temperature']
				else:
					logsupport.Logs.Log("Missing temperature update in {} ({})".format(self.name, self.attributes))

			self.GetTarget = GetTarget

		if 'Presets' in self.features:
			def GetPresets():
				self.preset_modes = self.attributes['preset_modes']
				self.preset_mode = self.attributes['preset_mode']

			self.GetPresets = GetPresets

		if 'FanModes' in self.features:
			def GetFanModes():
				self.fan = self.attributes['fan_mode']
				self.fanstates = self.attributes['fan_modes']

			self.GetFanModes = GetFanModes

		try:
			self.curtemp = self.attributes['current_temperature']
			if 'hvac_action' in self.attributes:
				self.hvac_action = self.attributes['hvac_action']
			else:
				self.hvac_action = None

			self.mode = self.internalstate  # in new climate domain hvac operation mode is the state
			self.GetFanModes()
			self.GetTarget()
			self.GetRange()
			self.GetPresets()
			self.modelist = self.attributes['hvac_modes']
			self.internalstate = self._NormalizeState(self.state)
		# self.DisplayStuff('init')
		except Exception as E:
			# if attributes are missing then don't do updates later - probably a pool
			logsupport.Logs.Log(
				'{}: Climate device {} missing attributes ({}) - Exc:({})'.format(self.Hub.name, self.name,
																				  self.attributes, E))

	def _NormalizeState(self, state, brightness=None):  # state is just the operation mode
		return state

	# noinspection PyUnusedLocal
	def ErrorFakeChange(self, param=None):
		PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id, value=self.internalstate))

	def Update(self, **ns):
		self.__dict__.update(ns)
		self.internalstate = self._NormalizeState(self.state)
		if 'attributes' in ns: self.attributes = ns['attributes']
		self.GetTarget()
		self.curtemp = self.attributes['current_temperature']
		self.GetRange()
		if 'hvac_action' in self.attributes:  # some tstats don't say what they are currently doing
			self.hvac_action = self.attributes['hvac_action']
		self.mode = self.internalstate  # self.attributes['hvac_action']
		self.GetFanModes()
		self.GetPresets()
		# self.DisplayStuff('update')
		PostIfInterested(self.Hub, self.entity_id, self.internalstate)

	# noinspection DuplicatedCode
	def PushSetpoints(self, t_low, t_high):
		ha.call_service_async(self.Hub.api, 'climate', 'set_temperature',
							  {'entity_id': '{}'.format(self.entity_id), 'target_temp_high': str(t_high),
							   'target_temp_low': str(t_low)})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushsetpoint-{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)

	def PushSingleTarget(self, target):
		ha.call_service_async(self.Hub.api, 'climate', 'set_temperature',
							  {'entity_id': '{}'.format(self.entity_id), 'temperature': str(target)})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushsetpoint-{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)

	def GetThermInfo(self):  # only here to support old screen that didn't get range returned
		if 'TargRange' in self.features:
			self.DisplayStuff('getR')
			# return self.curtemp, self.target_low, self.target_high, self.HVAC_state, self.mode, self.fan
			return self.curtemp, self.target_low, self.target_high, self.hvac_action, self.internalstate, self.fan
		else:
			self.DisplayStuff('getNR')
			# return self.curtemp, self.temperature, self.temperature, self.HVAC_state, self.mode, self.fan
			return self.curtemp, self.temperature, self.temperature, self.hvac_action, self.internalstate, self.fan

	def GetFullThermInfo(self):
		if 'TargRange' in self.features:
			# self.DisplayStuff('FgetR')
			# return self.curtemp, self.target_low, self.target_high, self.HVAC_state, self.mode, self.fan
			return self.curtemp, self.target_low, self.target_high, self.hvac_action, self.internalstate, self.fan, True
		else:
			# self.DisplayStuff('FgetNR')
			# return self.curtemp, self.temperature, self.temperature, self.HVAC_state, self.mode, self.fan
			return self.curtemp, self.temperature, 0, self.hvac_action, self.internalstate, self.fan, False  # todo fix 0 to None

	# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
	def _HVACstatechange(self, storeitem, old, new, param, chgsource):
		self.HVAC_state = new
		PostIfInterested(self.Hub, self.entity_id, new)

	def _connectsensors(self, HVACsensor):
		self.HVAC_state = HVACsensor.state
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
		ha.call_service_async(self.Hub.api, 'climate', 'set_hvac_mode',
							  {'entity_id': '{}'.format(self.entity_id), 'hvac_mode': mode})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushmode -{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)


RegisterDomain('climate', Thermostat)
