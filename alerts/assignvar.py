import alerttasks
import logsupport
from logsupport import ConsoleDetail
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
		for p in params:
			item = p.split('=')
			# noinspection PyBroadException
			try:
				val = float(item[1].strip())
			except:
				val = valuestore.GetVal(item[1].strip())
			valuestore.SetVal(item[0].strip(),val)
			logsupport.Logs.Log("Var ", item[0], ' set to value of ', item[1], ' (', val, ')', severity=ConsoleDetail)

alerttasks.alertprocs["AssignVar"] = AssignVar