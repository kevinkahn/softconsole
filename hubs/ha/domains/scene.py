import time

import debug
from hubs.ha import haremote as ha
from hubs.ha.hasshub import HAnode, RegisterDomain
import logsupport
import threading


class Scene(HAnode):
	def __init__(self, HAitem, d):
		super().__init__(HAitem, **d)
		self.Hub.RegisterEntity('scene', self.entity_id, self)
		self.opthreadcnt = 0

	def SceneOn(self):
		self.opthreadcnt += 1
		logsupport.Logs.Log(f'Scene on thread {self.opthreadcnt} for {self.entity_id}')
		scnstart = time.time()
		try:
			ha.call_service(self.Hub.api, 'scene', 'turn_on', {'entity_id': '{}'.format(self.entity_id)}, timeout=10)
			debug.debugPrint('HASSgeneral', "Scene On sent to ", self.entity_id)
			logsupport.Logs.Log(
				'Scene on complete for {} took {} seconds'.format(self.entity_id, time.time() - scnstart))
			self.opthreadcnt -= 1
		except ha.HomeAssistantError:
			# HA probably restarting
			logsupport.Logs.Log(
				f"{self.Hub.name} didn't respond to scene on for {self.name} - probably restarting (threadcnt: {self.opthreadcnt})",
				severity=logsupport.ConsoleWarning)
			self.opthreadcnt -= 1

	# noinspection PyUnusedLocal
	def SendOnOffCommand(self, settoon):
		if settoon:
			t = threading.Thread(name='HAscene-' + self.name, target=self.SceneOn, daemon=True)

			t.start()
			return False  # scenes always show as off for display purposes
		else:
			logsupport.Logs.Log('{} attempt to set scene {} to off'.format(self.Hub.name, self.name),
								severity=logsupport.ConsoleWarning)
			return False

	def _NormalizeState(self, state, brightness=None):
		# print('Scene {} last set at {}'.format(self.name,state))
		return state


RegisterDomain('scene', Scene)
