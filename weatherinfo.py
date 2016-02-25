import functools
import json
import time
import urllib2

import config
import logsupport


def TreeDict(d, *args):
	# Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
	if len(args) == 1:
		temp = d[args[0]]
		if isinstance(temp,
					  basestring) and temp.isdigit():  # todo now that I spec type above is this stuff still needed
			temp = int(temp)
		else:
			try:
				temp = float(temp)
			except (ValueError, TypeError):
				pass

		return temp
	else:
		return TreeDict(d[args[0]], *args[1:])


class WeatherInfo:
	ConditionMap = {'Time': (int, ('current_observation', 'observation_epoch')),
					'Location': (str, ('location', 'city')),
					'Temp': (float, ('current_observation', 'temp_f')),
					'Sky': (str, ('current_observation', 'weather')),
					'Feels': (float, ('current_observation', 'feelslike_f')),
					'WindDir': (str, ('current_observation', 'wind_dir')),
					'WindMPH': (float, ('current_observation', 'wind_mph')),
					'WindGust': (float, ('current_observation', 'wind_gust_mph')),
					'SunriseH': (int, ('sun_phase', 'sunrise', 'hour')),
					'SunriseM': (int, ('sun_phase', 'sunrise', 'minute')),
					'SunsetH': (int, ('sun_phase', 'sunset', 'hour')),
					'SunsetM': (int, ('sun_phase', 'sunset', 'minute')),
					'MoonriseH': (int, ('moon_phase', 'moonrise', 'hour')),  # intstr
					'MoonriseM': (int, ('moon_phase', 'moonrise', 'minute')),
					'MoonsetH': (int, ('moon_phase', 'moonset', 'hour')),
					'MoonsetM': (int, ('moon_phase', 'moonset', 'minute')),
					'MoonPct': (int, ('moon_phase', 'percentIlluminated')),
					}
	ForecastDay = {'Day': (str, ('date', 'weekday_short')),
				   'High': (int, ('high', 'fahrenheit')),
				   'Low': (int, ('low', 'fahrenheit')),
				   'Sky': (str, ('conditions',)),
				   'WindDir': (str, ('avewind', 'dir')),
				   'WindSpd': (float, ('avewind', 'mph'))}

	def __init__(self, WunderKey, location):
		self.lastwebreq = 0  # time of last call out to wunderground
		self.url = 'http://api.wunderground.com/api/' + WunderKey + '/geolookup/conditions/forecast/astronomy/q/' \
				   + location + '.json'
		self.ConditionVals = {}
		self.ForecastVals = []

	def FetchWeather(self):
		if time.time() > self.lastwebreq + 5*60:
			try:
				# refresh the conditions - don't do more than once per 5 minutes
				f = urllib2.urlopen(self.url)
				val = f.read()
				if val.find("keynotfound") <> -1:
					config.Logs.Log("Bad weatherunderground key:" + self.name, severity=logsupport.Error)
					return config.HomeScreen  # todo fix this
				self.lastwebreq = time.time()
				parsed_json = json.loads(val)
				js = functools.partial(TreeDict, parsed_json)
				fcsts = TreeDict(parsed_json, 'forecast', 'simpleforecast', 'forecastday')
				f.close()
				self.ConditionVals = {}
				self.ForecastVals = []
				for cond, desc in WeatherInfo.ConditionMap.iteritems():
					self.ConditionVals[cond] = desc[0](js(*desc[1]))
				for i, fcst in enumerate(fcsts):
					self.ForecastVals.append({})
					fs = functools.partial(TreeDict, fcst)
					for fc, desc in WeatherInfo.ForecastDay.iteritems():
						self.ForecastVals[i][fc] = desc[0](fs(*desc[1]))
			except:
				config.Logs.Log("Error retrieving weather", logsupport.Error)
				print "Get fresh weather failed ", time.time()
				print self.url
		return self.lastwebreq
