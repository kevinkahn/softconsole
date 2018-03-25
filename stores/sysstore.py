from stores import valuestore
import logsupport

class SystemStore(valuestore.ValueStore):
	def __init__(self, name):
		super(SystemStore, self).__init__(name)

	def SetVal(self, name, val, modifier = None):
		logsupport.Logs.Log("SysParam: ",valuestore.ExternalizeVarName(name),": ", val)
		super(SystemStore, self).SetVal(name,val,modifier=None)