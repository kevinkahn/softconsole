from hubs.ha import haremote as ha
from hubs.ha.hasshub import StatefulHAnode, _NormalizeState, RegisterDomain, stringtonumeric
from controlevents import CEvent, PostEvent, ConsoleEvent
import screens.__screens as screens
import debug
import time
import timers
import config
import functools


class Thermostat(StatefulHAnode):  # not stateful since has much state info
	# todo update since state now in pushed stream
	def __init__(self, HAitem, d):
		self.climateitem = 0
		super(Thermostat, self).__init__(HAitem, **d)
		self.Hub.RegisterEntity('climate', self.entity_id, self)
		self.timerseq = 0
		# noinspection PyBroadException
		try:  # todo sort out new climate stuff
			self.temperature = self.attributes['temperature']
			self.curtemp = self.attributes['current_temperature']
			self.target_low = self.attributes['target_temp_low']
			self.target_high = self.attributes['target_temp_high']
			self.hvac_action = self.attributes['hvac_action']
			self.mode = self.internalstate #self.attributes['hvac_action']
			self.fan = self.attributes['fan_mode']
			self.fanstates = self.attributes['fan_modes']
			self.modelist = self.attributes['hvac_modes']
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
		self.hvac_action = self.attributes['hvac_action']
		self.mode = self.internalstate #self.attributes['hvac_action']
		self.fan = self.attributes['fan_mode']
		if screens.DS.AS is not None:
			if self.Hub.name in screens.DS.AS.HubInterestList:
				if self.entity_id in screens.DS.AS.HubInterestList[self.Hub.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.sysStore.ConsoleStartTime,
									 "HA reports node change(screen): ",
									 "Key: ", self.Hub.Entities[self.entity_id].name)

					# noinspection PyArgumentList
					PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
										   value=self.internalstate))

	def PushSetpoints(self, t_low, t_high):
		ha.call_service_async(self.Hub.api, 'climate', 'set_temperature',
							  {'entity_id': '{}'.format(self.entity_id), 'target_temp_high': str(t_high),
							   'target_temp_low': str(t_low)})
		self.timerseq += 1
		_ = timers.OnceTimer(5, start=True, name='fakepushsetpoint-{}'.format(self.timerseq),
							 proc=self.ErrorFakeChange)

	def GetThermInfo(self):
		if self.target_low is not None:
			#return self.curtemp, self.target_low, self.target_high, self.HVAC_state, self.mode, self.fan
			return self.curtemp, self.target_low, self.target_high, self.hvac_action, self.internalstate, self.fan
		else:
			#return self.curtemp, self.temperature, self.temperature, self.HVAC_state, self.mode, self.fan
			return self.curtemp, self.temperature, self.temperature, self.hvac_action, self.internalstate, self.fan

	# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
	def _HVACstatechange(self, storeitem, old, new, param, chgsource):
		self.HVAC_state = new
		if screens.DS.AS is not None:
			if self.Hub.name in screens.DS.AS.HubInterestList:
				if self.entity_id in screens.DS.AS.HubInterestList[self.Hub.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.sysStore.ConsoleStartTime,
									 "HA Tstat reports node change(screen): ",
									 "Key: ", self.Hub.Entities[self.entity_id].name)

					# noinspection PyArgumentList
					PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id, value=new))

	def _connectsensors(self, HVACsensor):
		self.HVAC_state = HVACsensor.state
		# noinspection PyProtectedMember
		HVACsensor._SetSensorAlert(functools.partial(self._HVACstatechange))

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
