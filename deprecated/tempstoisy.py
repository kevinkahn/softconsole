import alerttasks
import config
import exitutils
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail
from stores import valuestore, weatherstore


class GetTempsToISY(object):
	def __init__(self):
		pass

	@staticmethod
	def SendTemps(alert):
		"""
		params: Station, (Fieldspec Var)+  where Fieldspec = C|F:fieldname Var = S|I|L:name)
		"""
		station = alert.param[0]
		WI = valuestore.NewValueStore(weatherstore.WeatherVals(station, config.WunderKey))

		assigns = alert.param[1].split(' ')
		for i in range(0, len(assigns), 2):
			weathcode = (assigns[i].split(':'))

			if weathcode[0] == 'C':
				weathval = WI.GetVal(('Cond', weathcode[1]))
			elif weathcode[0] == 'F':
				weathval = WI.GetVal(('Fcst', weathcode[1], 0))
			else:
				weathval = ''  # to supress warning on log msg below
				exitutils.FatalError('Weather field error in SendTemps')

			if not (isinstance(weathval, int) or isinstance(weathval, float)):
				logsupport.Logs.Log(
					"No valid weather value to send (" + station + '):' + weathcode[0] + ':' + weathcode[1] + str(
						weathval), severity=ConsoleWarning)
				return
			isyv = list(assigns[i + 1].split(':'))
			if isyv[0] == 'S': isyv[0] = 'State'
			if isyv[0] == 'I': isyv[0] = 'Int'
			valuestore.SetVal([config.defaultISYname] + isyv, int(weathval))
			logsupport.Logs.Log(
				"Temps sent to ISY(" + station + '):' + weathcode[0] + ':' + weathcode[1] + ' -> ' + str(weathval),
				severity=ConsoleDetail)


alerttasks.alertprocs["GetTempsToISY"] = GetTempsToISY
