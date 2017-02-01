import functools
import sys
import json
import time
import urllib2
import utilities
import os
import string

import config
from logsupport import ConsoleWarning, ConsoleError


class WFormatter(string.Formatter):
	def format_field(self, value, format_spec):
		if format_spec.endswith(('f', 'd')) and value is None:
			return 'n/a'
		elif value is None:
			return 'n/a'
		else:
			return super(WFormatter, self).format_field(value, format_spec)

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


def TryShorten(term):
	if term in config.TermShortener:
		return config.TermShortener[term]
	elif len(term) > 12:
		config.Logs.Log("Long term: " + term, severity=ConsoleWarning)
		config.TermShortener[term] = term  # only report once
		with open(config.exdir + '/termshortenlist.new', 'w') as f:
			json.dump(config.TermShortener, f, indent=4, separators=(',', ": "))
	return term


class WeatherInfo:
	ConditionMap = {'Time': (int, ('current_observation', 'observation_epoch')),
					'Location': (str, ('current_observation', 'display_location', 'city')),
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
					'MoonriseH': (int, ('moon_phase', 'moonrise', 'hour')),  #  todo intstr
					'MoonriseM': (int, ('moon_phase', 'moonrise', 'minute')),
					'MoonsetH': (int, ('moon_phase', 'moonset', 'hour')),
					'MoonsetM': (int, ('moon_phase', 'moonset', 'minute')),
					'MoonPct': (int, ('moon_phase', 'percentIlluminated')),
	                'Humidity': (str, ('current_observation', 'relative_humidity'))
					}
	ForecastDay = {'Day': (str, ('date', 'weekday_short')),
				   'High': (int, ('high', 'fahrenheit')),
				   'Low': (int, ('low', 'fahrenheit')),
				   'Sky': (str, ('conditions',)),
				   'WindDir': (str, ('avewind', 'dir')),
				   'WindSpd': (float, ('avewind', 'mph'))}

	def __init__(self, WunderKey, location):
		self.nextwebreq = 0  # time of next call out to wunderground
		self.webreqinterval = 60*30  # 30 minutes
		self.url = 'http://api.wunderground.com/api/' + WunderKey + '/conditions/forecast/astronomy/q/' \
				   + location + '.json'
		self.ConditionVals = {}
		self.ForecastVals = []
		self.location = location
		self.returnval = 0
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile = open(os.path.dirname(config.configfile) + '/' + location + 'wv.log', 'w')
			self.weathjsonfile = open(os.path.dirname(config.configfile) + '/' + location + 'wj.log', 'w')
			self.weathvalfile.write(location + ' \n==================\n')
			self.weathvalfile.flush()
			self.weathjsonfile.write(location + '\n==================\n')
			self.weathjsonfile.flush()

	def dumpweatherresp(self, val, json):
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile.write(time.strftime('%H:%M:%S') + '\n' + repr(val) + '\n=================')
			self.weathjsonfile.write(time.strftime('%H:%M:%S') + '\n' + repr(json) + '\n=================')
			self.weathvalfile.flush()
			self.weathjsonfile.flush()

	def FetchWeather(self):
		if time.time() > self.nextwebreq:
			self.returnval = time.time()
			try:
				# refresh the conditions - don't do more than once per webrequestinterval seconds
				self.nextwebreq = time.time() + self.webreqinterval  # do this first so that even in error cases we wait a while to try again
				try:
					f = urllib2.urlopen(self.url, None, 15)  # wait at most 15 seconds for weather response then timeout
					val = f.read()
				except:
					config.Logs.Log("Error fetching weather: " + self.url + str(sys.exc_info()[0]),
									severity=ConsoleWarning)
					self.dumpweatherresp(val, 'none')
					raise
				if val.find("keynotfound") <> -1:
					if self.location <> "":
						# only report once in log
						config.Logs.Log("Bad weatherunderground key:" + self.location, severity=ConsoleError, tb=False)
					self.location = ""
					self.nextwebreq = time.time() + 60*60*24*300  # next web request in 300 days - i.e., never
					raise
				if val.find("you must supply a key") <> -1:
					config.Logs.Log("WeatherUnderground missed the key:" + self.locations, severity=ConsoleWarning)
					self.returnval = -1
					self.nextwebreq = time.time()  # try this again since key didn't register or count
					return -1
				parsed_json = json.loads(val)
				js = functools.partial(TreeDict, parsed_json)
				fcsts = TreeDict(parsed_json, 'forecast', 'simpleforecast', 'forecastday')
				f.close()
				self.ConditionVals = {}
				self.ForecastVals = []
				self.ConditionErr = []
				self.ForecastErr = []
				for cond, desc in WeatherInfo.ConditionMap.iteritems():
					try:
						self.ConditionVals[cond] = desc[0](js(*desc[1]))
						if desc[0] == str:
							self.ConditionVals[cond] = TryShorten(self.ConditionVals[cond])
						progress = (4,cond)
					except:
						self.ConditionVals[cond] = None  # desc[0]('0')
						self.ConditionErr.append(cond)
				for i, fcst in enumerate(fcsts):
					self.ForecastVals.append({})
					self.ForecastErr.append([])
					fs = functools.partial(TreeDict, fcst)
					for fc, desc in WeatherInfo.ForecastDay.iteritems():
						try:
							self.ForecastVals[i][fc] = desc[0](fs(*desc[1]))
							if desc[0] == str:
								self.ForecastVals[i][fc] = TryShorten(self.ForecastVals[i][fc])
						except:
							config.Logs.Log("Forecast error: Day " + str(i) + ' field ' + str(fc) + ' returned *' + str(
								fs(*desc[1])) + '*', severity=ConsoleError, tb=False)
							self.ForecastVals[i][fc] = None  #desc[0]('0')
							self.ForecastErr[i].append(fc)
				"""
				Create synthetic fields and fix error cases
				"""
				# Moonrise/set
				if 'MoonriseH' not in self.ConditionErr and 'MoonriseM' not in self.ConditionErr:
					self.ConditionVals['Moonrise'] = "{d[0]:02d}:{d[1]:02d}".format(
						d=[self.ConditionVals[x] for x in ('MoonriseH', 'MoonriseM')])
				else:
					self.ConditionVals['Moonrise'] = 'n/a'
					if 'MoonriseH' in self.ConditionErr:
						self.ConditionErr.remove('MoonriseH')
					if 'MoonriseM' in self.ConditionErr:
						self.ConditionErr.remove('MoonriseM')
				if 'MoonsetH' not in self.ConditionErr and 'MoonsetM' not in self.ConditionErr:
					self.ConditionVals['Moonset'] = "{d[0]:02d}:{d[1]:02d}".format(
						d=[self.ConditionVals[x] for x in ('MoonsetH', 'MoonsetM')])
				else:
					self.ConditionVals['Moonset'] = 'n/a'
					if 'MoonsetH' in self.ConditionErr:
						self.ConditionErr.remove('MoonsetH')
					if 'MoonsetM' in self.ConditionErr:
						self.ConditionErr.remove('MoonsetM')

				# Wind not reported at station
				if self.ConditionVals['WindMPH'] < 0:
					self.ConditionVals['WindStr'] = 'n/a'
				else:
					self.ConditionVals['WindStr'] = "{d[0]}@{d[1]} gusts {d[2]}".format(
						d=[self.ConditionVals[x] for x in ('WindDir', 'WindMPH', 'WindGust')])

				if self.ForecastErr:
					self.dumpweatherresp(val, parsed_json)

				if self.ConditionErr:
					config.Logs.Log("Weather error: ", self.location, self.ConditionErr, severity=ConsoleWarning)
					self.dumpweatherresp(val, parsed_json)
				# self.returnval = -1
				#return -1

			except:
				config.Logs.Log(
					"Error retrieving weather" + str(sys.exc_info()[0]) + ':' + str(sys.exc_info()[1]) + ' ' + self.url,
					severity=ConsoleError)
				self.dumpweatherresp(val, parsed_json)
				self.returnval = -1
				return -1
		try:
			self.ConditionVals['Age'] = utilities.interval_str(time.time() - self.ConditionVals['Time'])
		except:
			self.ConditionVals['Age'] = "No readings ever retrieved"
		return self.returnval
