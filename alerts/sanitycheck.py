import alerttasks
from stores import valuestore

class CheckIntegrity(object):
	def __init__(self):
		pass

	# noinspection PyUnusedLocal
	@staticmethod
	def CheckISYVars(alert):
		valuestore.ValueStores['ISY'].CheckValsUpToDate()





alerttasks.alertprocs["CheckIntegrity"] = CheckIntegrity