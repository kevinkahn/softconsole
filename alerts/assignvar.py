import alerttasks
import logsupport
from logsupport import ConsoleDetail, ConsoleWarning
from stores import valuestore


class AssignVar(object):
	def __init__(self):
		pass

	@staticmethod
	def Assign(alert):
		"""
		params: Var Var, . . .
		"""
		params = (alert.param,) if isinstance(alert.param, str) else alert.param
		val = -99999
		for p in params:
			item = p.split('=')
			# noinspection PyBroadException
			try:
				val = float(item[1].strip())
			except:
				try:
					val = valuestore.GetVal(item[1].strip())
				except BaseException as e:
					logsupport.Logs.Log("Error setting var in AssignVar alert: ", str(item[1]), ' to ', repr(val),
										severity=ConsoleWarning)
					logsupport.Logs.Log("Exception was: ", repr(e), severity=ConsoleWarning)
			valuestore.SetVal(item[0].strip(),val)
			logsupport.Logs.Log("Var ", item[0], ' set to value of ', item[1], ' (', val, ')', severity=ConsoleDetail)

alerttasks.alertprocs["AssignVar"] = AssignVar