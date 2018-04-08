import alerttasks
import config
from stores import valuestore

class CheckIntegrity(object):
	def __init__(self):
		pass

	# noinspection PyUnusedLocal
	@staticmethod
	def CheckISYVars(alert):
		valuestore.ValueStores[config.defaultISYname].CheckValsUpToDate() #todo param for ISY to sanity check





alerttasks.alertprocs["CheckIntegrity"] = CheckIntegrity