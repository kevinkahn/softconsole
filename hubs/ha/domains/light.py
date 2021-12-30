import time

import debug
from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain
from controlevents import CEvent, PostEvent, ConsoleEvent
import logsupport
from utils.utilfuncs import safeprint


class Light(HAnode):
	def __init__(self, HAitem, d):
		super().__init__(HAitem, **d)
		self.Hub.RegisterEntity('light', self.entity_id, self)
		if 'brightness' in self.attributes:
			self.internalstate = self._NormalizeState(self.state, int(self.attributes['brightness']))
		self.pctatidle = -1
		self.lastsendtime = 0

	def Update(self, **ns):
		if self.entity_id == 'light.bar_lights' and 'brightness' in self.attributes:
			oldbright = self.attributes['brightness']
		else:
			oldbright = -1
		super().Update(**ns)
		if self.entity_id == 'light.bar_lights' and 'brightness' in self.attributes:
			safeprint('{} Update {}->{}'.format(time.strftime('%m-%d-%y %H:%M:%S', time.localtime()), oldbright,
												self.attributes['brightness']))
			if self.attributes['brightness'] < 25: print(
				'{} Update {} {} {}->{}'.format(time.strftime('%m-%d-%y %H:%M:%S', time.localtime()), self.name,
												self.state, oldbright, self.attributes['brightness']))
		if 'brightness' in self.attributes:
			self.internalstate = self._NormalizeState(self.state, int(self.attributes['brightness']))

	# noinspection PyUnusedLocal
	def SendOnOffCommand(self, settoon):
		try:
			selcmd = ('turn_off', 'turn_on')
			# logsupport.DevPrint("Light on/off: {} {} {}".format(selcmd[settoon],self.entity_id, time.time()))
			ha.call_service(self.Hub.api, 'light', selcmd[settoon], {'entity_id': '{}'.format(self.entity_id)})
			debug.debugPrint('HASSgeneral', "Light OnOff sent: ", selcmd[settoon], ' to ', self.entity_id)
			PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
								   value=(0, 255)[
									   settoon]))  # hack to provide immediate faked feedback on zwave lights that take a while to report back todo fix
		except ha.HomeAssistantError:
			logsupport.Logs.Log(
				"{} didn't respond to light on/off for {} - probably restarting".format(self.Hub.name, self.name),
				severity=logsupport.ConsoleWarning)

	def GetBrightness(self):
		if 'brightness' in self.attributes:
			t = 100 * (self.attributes['brightness'] / 255) if self.pctatidle == -1 else self.pctatidle
			if t < 5: print('GetBright: {} {} {}'.format(self.name, t, self.pctatidle))
			return 100 * (self.attributes['brightness'] / 255) if self.pctatidle == -1 else self.pctatidle
		else:
			return 0

	def SendOnPct(self, brightpct, final=False):
		self.pctatidle = brightpct
		now = time.time()
		if now - self.lastsendtime > 1 or final:
			self.lastsendtime = now
			try:
				if brightpct < 5: print('SendOnPct {} {}'.format(self.name, brightpct))
				if brightpct == 0:
					print('Send -> Turn Off')
					ha.call_service(self.Hub.api, 'light', 'turn_off', {'entity_id': '{}'.format(self.entity_id)})
				else:
					ha.call_service(self.Hub.api, 'light', 'turn_on',
									{'entity_id': '{}'.format(self.entity_id), 'brightness_pct': brightpct})
			except ha.HomeAssistantError:
				logsupport.Logs.Log(
					"{} didn't respond to on percent change for {}".format(self.Hub.name, self.name),
					severity=logsupport.ConsoleWarning)

	def IdleSend(self):
		try:
			if self.pctatidle < 5: print('IdleSend {} {}'.format(self.name, self.pctatidle))
			if self.pctatidle == 0:
				print('Send -> Turn Off ({})'.format(self.name))
				ha.call_service(self.Hub.api, 'light', 'turn_off', {'entity_id': '{}'.format(self.entity_id)})
			else:
				ha.call_service(self.Hub.api, 'light', 'turn_on',
								{'entity_id': '{}'.format(self.entity_id), 'brightness_pct': self.pctatidle})
		except ha.HomeAssistantError:
			logsupport.Logs.Log(
				"{} didn't respond to on percent change for {}".format(self.Hub.name, self.name),
				severity=logsupport.ConsoleWarning)
		self.pctatidle = -1


RegisterDomain('light', Light)
