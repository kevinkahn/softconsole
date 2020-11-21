import threading

from alertsystem import alerttasks
import hubs.hubs
import logsupport
from stores import valuestore


class CheckIntegrity(object):
	def __init__(self):
		pass

	# noinspection PyUnusedLocal
	@staticmethod
	def CheckStatusCaches(alert):
		def DoCheck(hubnm, hub):
			logsupport.Logs.Log('Integrity check for hub: ', hubnm, ' starting')
			logsupport.DevPrint('Integrity check for hub {}'.format(hubnm))
			valuestore.ValueStores[hubnm].CheckValsUpToDate()
			hub.CheckStates()
			logsupport.Logs.Log('Integrity check thread for hub: ', hubnm, ' complete')

		hubname = alert.param
		thishub = hubs.hubs.Hubs[hubname]
		T = threading.Thread(name='IntegrityCheck', target=DoCheck, args=(hubname, thishub), daemon=True)
		T.start()


alerttasks.alertprocs["CheckIntegrity"] = CheckIntegrity
