import functools
import time
from datetime import datetime, timezone
import dateutil

import pygame
import controlevents

import config
import historybuffer
import logsupport

from darksky.types import languages, units, weather
from darksky.request_manager import RequestManger

from stores.weathprov.providerutils import TryShorten, WeathProvs, MissingIcon
from utilfuncs import interval_str, TreeDict

WeatherIconCache = {'n/a': MissingIcon}


def geticon(nm):
	try:
		code = IconMap[nm]
		daynight = 'day' if code < 1000 else 'night'
		iconnm = daynight + '/' + str(code if code < 1000 else code - 1000) + '.png'
		iconpath = icondir + '/' + iconnm
		if iconpath in WeatherIconCache:
			return WeatherIconCache[iconpath]
		else:
			icon_gif = pygame.image.load(iconpath)
			icon_scr = pygame.Surface.convert_alpha(icon_gif)
			icon_scr.set_colorkey(icon_gif.get_colorkey())
			WeatherIconCache[iconpath] = icon_scr
		return icon_scr
	except Exception as E:
		logsupport.Logs.Log('No DarkSky icon for {}'.format(nm))
		return WeatherIconCache['n/a']


def getdayname(param):
	return datetime.utcfromtimestamp(param).strftime('%a')


def getdatetime(param):
	return datetime.utcfromtimestamp(param).strftime('%Y-%m-%d %H:%M:%S')


def getTOD(param):
	lt = time.localtime(param)
	return time.strftime('%H:%M', lt)

def doage(basetime):
	return interval_str(time.time() - basetime)


def degToCompass(num):
	val = int((num / 22.5) + .5)
	arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
	return arr[(val % 16)]

def setAge(param):
	return functools.partial(doage, param)


def fcstlength(param):
	return len(param)


IconMap = {'clear-day': 113, 'clear-night': 1113, 'rain': 308, 'snow': 338, 'sleet': 284, 'wind': 0, 'fog': 248,
		   'cloudy': 119, 'partly-cloudy-day': 116, 'partly-cloudy-night': 1116}

CondFieldMap = {'Time': (getdatetime, ('currently', 'time')),
				'Temp': (float, ('currently', 'temperature')),
				'Sky': (TryShorten, ('currently', 'summary')),
				'Feels': (float, ('currently', 'apparentTemperature')),
				'WindDir': (degToCompass, ('currently', 'windBearing')),
				'WindMPH': (float, ('currently', 'windSpeed')),
				'Humidity': (str, ('currently', 'humidity')),
				'Icon': (geticon, ('currently', 'icon')),  # get the surface
				'Sunrise': (getTOD, ('daily', 'data', 0, 'sunriseTime')),
				'Sunset': (getTOD, ('daily', 'data', 0, 'sunsetTime')),
				# 'Moonrise': (str, ('forecast', 'forecastday', 0, 'astro', 'moonrise')),
				# 'Moonset': (str, ('forecast', 'forecastday', 0, 'astro', 'moonset')),
				'TimeEpoch': (int, ('currently', 'time')),
				'Age': (setAge, ('currently', 'time'))
				}

FcstFieldMap = {'Day': (getdayname, ('time',)),  # convert to day name
				'High': (float, ('temperatureHigh',)),
				'Low': (float, ('temperatureLow',)),
				'Sky': (TryShorten, ('summary',)),
				'WindSpd': (float, ('windSpeed',)),
				'WindDir': (degToCompass, ('windBearing',)),
				'Icon': (geticon, ('icon',))  # get the surface
				}

CommonFieldMap = {'FcstDays': (fcstlength, ('daily', 'data')),
				  'FcstEpoch': (int, ('daily', 'data', 0, 'time')),
				  'FcstDate': (getdatetime, ('daily', 'data', 0, 'time'))}

icondir = config.sysStore.ExecDir + '/auxinfo/apixuicons/'


class DarkSkyWeatherSource(object):
	def __init__(self, storename, location, api):
		self.apikey = api
		self.thisStoreName = storename
		self.thisStore = None
		self.location = location
		try:
			locationstr = location.split(',')
			if len(locationstr) != 2:
				raise ValueError
			self.lat, self.lon = (float(locationstr[0]), float(locationstr[1]))
		except Exception as E:
			logsupport.Logs.Log('Improper location lat/lon: {} Exc: {}'.format(location, E))
			self.lat, self.lon = (0.0, 0.0)
		# self.DarkSky = DarkSky(self.apikey)
		self.request_manager = RequestManger(True)
		self.url = 'https://api.darksky.net/forecast/{}/{},{}'.format(self.apikey, self.lat, self.lon)
		logsupport.Logs.Log('Powered by DarkSky: Created weather for ({},{}) as {}'.format(self.lat, self.lon, storename))

	def ConnectStore(self, store):
		self.thisStore = store

	# noinspection PyMethodMayBeStatic
	def MapItem(self, src, item):
		if isinstance(item, tuple):
			return item[0](TreeDict(src, item[1]))
		else:
			return item

	def FetchWeather(self):
		for trydecode in range(2):  # if a decode fails try another actual fetch
			r = None
			fetchworked = False
			trycnt = 4
			lastE = None
			while not fetchworked and trycnt > 0:
				trycnt -= 1
				# logsupport.Logs.Log('Actual weather fetch attempt: {}'.format(self.location))
				try:
					historybuffer.HBNet.Entry('DarkSky weather fetch{}: {}'.format(trycnt, self.thisStoreName))
					forecast = self.request_manager.make_request(url=self.url, extend=None, lang=languages.ENGLISH,
																 units=units.AUTO, exclude='minutely,hourly,flags')
					historybuffer.HBNet.Entry('Weather fetch done')
					logsupport.DarkSkyfetches += 1
					logsupport.DarkSkyfetches24 += 1
					fetchworked = True
				except Exception as E:
					fetchworked = False
					lastE = E
					historybuffer.HBNet.Entry('Weather fetch exception: {}'.format(repr(E)))
					time.sleep(2)
			if not fetchworked:
				logsupport.Logs.Log(
					"Failed multiple tries to get weather for {} last Exc: {}".format(self.location, lastE),
					severity=logsupport.ConsoleWarning, hb=True)
				self.thisStore.ValidWeather = False
				return
			try:
				self.thisStore.ValidWeather = False  # show as invalid for the short duration of the update - still possible to race but very unlikely.
				tempfcstinfo = {}
				for fn, entry in FcstFieldMap.items():
					tempfcstinfo[fn] = []
				# self.thisStore.GetVal(('Fcst', fn)).emptylist()
				self.thisStore.SetVal(('Cond', 'Location'), self.thisStoreName)
				for fn, entry in CondFieldMap.items():
					val = self.MapItem(forecast, entry)
					self.thisStore.SetVal(('Cond', fn), val)
				fcstdays = len(forecast['daily']['data'])
				for i in range(fcstdays):
					try:
						dbgtmp = {}
						fcst = forecast['daily']['data'][i]
						for fn, entry in FcstFieldMap.items():
							val = self.MapItem(fcst, entry)
							tempfcstinfo[fn].append(val)
							# self.thisStore.GetVal(('Fcst', fn)).append(val)
							dbgtmp[fn] = val
					# logsupport.Logs.Log('Weatherfcst({}): {}'.format(self.location, dbgtmp))
					except Exception as E:
						logsupport.DevPrint(
							'Exception (try{}) in DarkSky forecast processing day {}: {}'.format(trydecode, i, repr(E)))
						raise
				for fn, entry in FcstFieldMap.items():
					self.thisStore.GetVal(('Fcst', fn)).replacelist(tempfcstinfo[fn])
				for fn, entry in CommonFieldMap.items():
					val = self.MapItem(forecast, entry)
					self.thisStore.SetVal(fn, val)

				self.thisStore.CurFetchGood = True
				self.thisStore.ValidWeather = True
				self.thisStore.ValidWeatherTime = time.time()
				controlevents.PostEvent(controlevents.ConsoleEvent(controlevents.CEvent.GeneralRepaint))
				return  # success
			except Exception as E:
				logsupport.DevPrint('Exception {} in apixu report processing: {}'.format(E, forecast))
				self.thisStore.CurFetchGood = False
		logsupport.Logs.Log('Multiple decode failures on return data from weather fetch of {}'.format(self.location))


WeathProvs['DarkSky'] = [DarkSkyWeatherSource, '']  # api key gets filled in from config file
