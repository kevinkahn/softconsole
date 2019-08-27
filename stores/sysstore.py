import config
from stores import valuestore
import time, hw


class SystemStore(valuestore.ValueStore):
	def __init__(self, name):
		super(SystemStore, self).__init__(name)

	def SetVal(self, name, val, modifier=None):
		# logsupport.Logs.Log("SysParam: ", valuestore.ExternalizeVarName(name),": ", val)
		super(SystemStore, self).SetVal(name, val, modifier=None)

	def __setattr__(self, key, value):
		if key in config.sysvals:
			self.SetVal(key, value)
		else:
			object.__setattr__(self, key, value)

	def __getattr__(self, key):
		if key == 'Time': return time.time()
		if key == 'UpTime': return time.time() - self.GetVal('ConsoleStartTime')
		return self.GetVal(key)
