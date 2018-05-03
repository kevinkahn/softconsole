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
	def CheckStatusCaches(alert):
		def DoCheck(hubnm, hub):
			logsupport.Logs.Log('Integrity check for hub: ', hubnm, ' starting')
			valuestore.ValueStores[hubnm].CheckValsUpToDate()
			hub.CheckStates()
			logsupport.Logs.Log('Integrity check thread for hub: ', hubnm, ' complete')

		hubname = alert.param
		thishub = config.Hubs[hubname]
		T = threading.Thread(name='IntegrityCheck', target=DoCheck,args=(hubname,thishub))
		T.start()




alerttasks.alertprocs["CheckIntegrity"] = CheckIntegrity