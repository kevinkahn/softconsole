import alerttasks
import config
from stores import valuestore
import threading
import logsupport

class CheckIntegrity(object):
	def __init__(self):
		pass

	# noinspection PyUnusedLocal
	@staticmethod
	def CheckISYVars(alert):
		def DoCheck(hubnm, hub):
			logsupport.Logs.Log('Integrity check for hub: ', hubnm)
			valuestore.ValueStores[hubnm].CheckValsUpToDate()
			hub.CheckStates()
			logsupport.Logs.Log('Integrity check thread for hub: ', hubnm, ' complete')

		hubnm = alert.param
		hub = config.Hubs[hubnm]
		T = threading.Thread(name='IntegrityCheck', target=DoCheck,args=(hubnm,hub))
		T.start()




alerttasks.alertprocs["CheckIntegrity"] = CheckIntegrity