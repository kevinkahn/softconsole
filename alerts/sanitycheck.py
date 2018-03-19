import alerttasks
from stores import valuestore

class CheckIntegrity(object):
	def __init__(self):
		pass

	def CheckISYVars(self, alert):
		valuestore.ValueStores['ISY'].CheckValsUpToDate()





alerttasks.alertprocs["CheckIntegrity"] = CheckIntegrity