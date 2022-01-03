from hubs.ha.hasshub import HAnode, RegisterDomain
import logsupport


class Cover(HAnode):
	def __init__(self, HAitem, d):
		super().__init__(HAitem, **d)
		self.Hub.RegisterEntity('cover', self.entity_id, self)

	def Update(self, **ns):
		super().Update(**ns)

	def _NormalizeState(self, state, brightness=None):  # may be overridden for domains with special state settings
		if isinstance(state, str):
			if state == 'open':
				return 1
			elif state == 'closed':
				return 0
			else:
				logsupport.Logs.Log('Cover {} reports odd state {}'.format(self.name, state),
									severity=logsupport.ConsoleDetail)
				return -1
		else:
			logsupport.Logs.Log('Cover {} reports non-string state {}'.format(self.name, state),
								severity=logsupport.ConsoleDetail)
			return -1

RegisterDomain('cover', Cover)
