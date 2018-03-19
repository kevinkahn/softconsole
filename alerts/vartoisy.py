import config
import logsupport
from logsupport import ConsoleDetail
from stores import valuestore


class SendVarToISY(object):
	def __init__(self):
		pass

	def SendVar(self, alert):
		"""
		params: Station, (Fieldspec Var)+  where Fieldspec = C|F:fieldname Var = S|I|L:name)
		"""
		params = (alert.param,) if isinstance(alert.param, str) else alert.param
		for p in params:
			assign = p.split(' ')
			val = int(valuestore.GetVal(assign[0]))
			valuestore.SetVal(assign[1],val)
			logsupport.Logs.Log("Var ", assign[1], ' set to value of ', assign[0], ' (', val, ')', severity=ConsoleDetail)

config.alertprocs["SendVarToISY"] = SendVarToISY