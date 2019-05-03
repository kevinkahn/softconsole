import functools
import time
from datetime import datetime

import pygame
import requests

import config
import logsupport
from stores.weathprov.providerutils import TryShorten, WeathProvs
from utilfuncs import interval_str, TreeDict

EmptyIcon = pygame.Surface((64, 64))
EmptyIcon.fill((255, 255, 255))
EmptyIcon.set_colorkey((255, 255, 255))
WeatherIconCache = {'n/a': EmptyIcon}


def geticon(url):
	iconnm = url.split('/')[-2:]
	iconpath = icondir + '/'.join(iconnm)
	if iconpath in WeatherIconCache:
		return WeatherIconCache[iconpath]
	else:
		icon_gif = pygame.image.load(iconpath)
		icon_scr = pygame.Surface.convert_alpha(icon_gif)
		icon_scr.set_colorkey(icon_gif.get_colorkey())
		WeatherIconCache[iconpath] = icon_scr
	return icon_scr


def getdayname(param):
	return datetime.utcfromtimestamp(param).strftime('%a')


def doage(basetime):
	return interval_str(time.time() - basetime)


def setAge(param):
	return functools.partial(doage, param)


def fcstlength(param):
	return len(param)


CondFieldMap = {'Time': (str, ('current', 'last_updated')),
				'Location': (str, ('location', 'name')),
				'Temp': (float, ('current', 'temp_f')),
				'Sky': (TryShorten, ('current', 'condition', 'text')),
				'Feels': (float, ('current', 'feelslike_f')),
				'WindDir': (str, ('current', 'wind_dir')),
				'WindMPH': (float, ('current', 'wind_mph')),
				'Humidity': (str, ('current', 'humidity')),
				'Icon': (geticon, ('current', 'condition', 'icon')),  # get the surface
				'Sunrise': (str, ('forecast', 'forecastday', 0, 'astro', 'sunrise')),
				'Sunset': (str, ('forecast', 'forecastday', 0, 'astro', 'sunset')),
				'Moonrise': (str, ('forecast', 'forecastday', 0, 'astro', 'moonrise')),
				'Moonset': (str, ('forecast', 'forecastday', 0, 'astro', 'moonset')),
				'TimeEpoch': (int, ('current', 'last_updated_epoch')),
				'Age': (setAge, ('current', 'last_updated_epoch'))
				}

FcstFieldMap = {'Day': (getdayname, ('date_epoch',)),  # convert to day name
				'High': (float, ('day', 'maxtemp_f')),
				'Low': (float, ('day', 'mintemp_f')),
				'Sky': (TryShorten, ('day', 'condition', 'text')),
				'WindSpd': (str, ('day', 'maxwind_mph')),
				'WindDir': '',
				'Icon': (geticon, ('day', 'condition', 'icon'))  # get the surface
				}

CommonFieldMap = {'FcstDays': (fcstlength, ('forecast', 'forecastday')),
				  'FcstEpoch': (int, ('forecast', 'forecastday', 0, 'date_epoch')),
				  'FcstDate': (str, ('forecast', 'forecastday', 0, 'date'))}

icondir = config.sysStore.ExecDir + '/auxinfo/apixuicons/'


class APIXUWeatherSource(object):
	def __init__(self, storename, location, api):
		self.baseurl = 'https://api.apixu.com/v1/forecast.json'
		self.args = {'key': api, 'q': location, 'days': 7}
		self.apikey = api
		self.thisStoreName = storename
		self.thisStore = None
		self.location = location
		self.json = {}
		logsupport.Logs.Log('APIXU: Created weather for ', location, ' as ', storename)

	def ConnectStore(self, store):
		self.thisStore = store

	# noinspection PyMethodMayBeStatic
	def MapItem(self, src, item):
		if isinstance(item, tuple):
			return item[0](TreeDict(src, item[1]))
		else:
			return item

	def FetchWeather(self):
		temp = {}
		config.HBNet.Entry('Weather fetch: {}'.format(self.baseurl))
		r = requests.get(self.baseurl, params=self.args)
		config.HBNet.Entry('Weather fetch done')
		try:
			self.json = r.json()
			for fn, entry in CondFieldMap.items():
				val = self.MapItem(self.json, entry)
				self.thisStore.SetVal(('Cond', fn), val)
				temp[fn] = val
			fcstdays = len(self.json['forecast']['forecastday'])
			for i in range(fcstdays):
				try:
					temp = {}
					fcst = self.json['forecast']['forecastday'][i]
					for fn, entry in FcstFieldMap.items():
						val = self.MapItem(fcst, entry)
						self.thisStore.GetVal(('Fcst', fn)).append(val)

						temp[fn] = val
				except Exception as E:
					logsupport.Logs.Log('Exception in apixu forecast processing day {}: '.format(i), repr(E),
										severity=logsupport.ConsoleWarning)
					raise

			for fn, entry in CommonFieldMap.items():
				val = self.MapItem(self.json, entry)
				self.thisStore.SetVal(fn, val)

			return 0  # success
		except Exception as E:
			logsupport.Logs.Log('Exception in apixu report processing: ', repr(E), self.json,
								severity=logsupport.ConsoleWarning)
			logsupport.Logs.Log('Returned text: ', r.text)
			raise


WeathProvs['APIXU'] = [APIXUWeatherSource, '']  # api key gets filled in from config file
