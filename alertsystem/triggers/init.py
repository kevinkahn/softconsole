import alertsystem.alertutils as alertutils
import alertsystem.alerttasks as alerttasks

triggername = 'Init'


class InitTrigger(object):
	def __init__(self):
		pass


def Arm(a):
	a.Invoke()


# noinspection PyUnusedLocal
def Parse(nm, spec, action, actionname, param):
	trig = InitTrigger()
	return alerttasks.Alert(nm, triggername, trig, action, actionname, param)


alertutils.TriggerTypes[triggername] = alertutils.TriggerRecord(Parse, Arm, InitTrigger)
