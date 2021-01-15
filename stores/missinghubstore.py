from stores import valuestore
import logsupport
from logsupport import ConsoleError


class MissingHubStore(valuestore.ValueStore):
	def __init__(self, hubnm, hub):
		super().__init__(hubnm)
		self.hub = hub
		logsupport.Logs.Log('Created dummy store {}'.format(hubnm))

	def GetVal(self, name, failok=False):
		return None

	def SetVal(self, name, val, modifier=None):
		logsupport.Logs.Log('Attempt to set a value {} in dummy store {} item {}'.format(val, self.name, name))
		pass
