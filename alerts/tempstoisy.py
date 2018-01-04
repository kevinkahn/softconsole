import weatherinfo
import config
import exitutils
from logsupport import ConsoleError, ConsoleInfo, ConsoleWarning
import isy


class GetTempsToISY(object):
	def __init__(self):
		pass

	def SendTemps(self, alert):
		"""
		params: Station, (Fieldspec Var)+  where Fieldspec = C|F:fieldname Var = S|I|L:name)
		"""
		station = alert.param[0]
		WI = weatherinfo.WeatherInfo(config.WunderKey, station)
		if WI.FetchWeather() == -1:
			config.Logs.Log("Weather not available in SendTemps(" + station + ')', severity=ConsoleError)
			return
		assigns = alert.param[1].split(' ')
		for i in range(0, len(assigns), 2):
			weathcode = (assigns[i].split(':'))
			if weathcode[0] == 'C':
				weathval = WI.ConditionVals[weathcode[1]]
			elif weathcode[0] == 'F':
				weathval = WI.ForecastVals[0][weathcode[1]]
			else:
				exitutils.FatalError('Weather field error in SendTemps', restartopt='shut')

			if not isinstance(weathval,int):
				config.Logs.Log("No valid weather value to send (" + station +'):'+weathcode[0]+':'+weathcode[1]+ +str(weathval),severity=ConsoleWarning)
				return
			isyvar = config.ISY.GetVarCode(tuple(assigns[i + 1].split(':')))
			config.Logs.Log(
				"Temps sent to ISY(" + station + '):' + weathcode[0] + ':' + weathcode[1] + ' -> ' + str(weathval),
				severity=ConsoleInfo)
			if isyvar != (0, 0):
				isy.SetVar(isyvar, int(weathval))
			else:
				exitutils.FatalError('Variable name error in SendTemps', restartopt='shut')


config.alertprocs["GetTempsToISY"] = GetTempsToISY
