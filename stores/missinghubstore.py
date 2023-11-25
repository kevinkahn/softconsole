from stores import valuestore
import logsupport


class MissingHubStore(valuestore.ValueStore):
	def __init__(self, hubnm, hub):
		super().__init__(hubnm)
		self.hub = hub
		self.name = 'DummyHub'
		logsupport.Logs.Log('Created dummy store {}'.format(hubnm))
		self.reportedlist = []

	def GetVal(self, name, failok=False):
		return None

	def SetVal(self, name, val, modifier=None):
		if not name in self.reportedlist:
			logsupport.Logs.Log('Attempt to set a value {} in dummy store {} item {}'.format(val, self.name, name))
			self.reportedlist.append(name)
