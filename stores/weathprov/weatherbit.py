import functools
import time
from datetime import datetime

import pygame
import controlevents
import json

import config
import historybuffer
import logsupport

from ._weatherbit.api import Api
from ._weatherbit.utils import LocalizeDateTime
from ._weatherbit.models import Current, Forecast

from stores.weathprov.providerutils import TryShorten, WeathProvs, MissingIcon
from utilfuncs import interval_str

WeatherIconCache = {'n/a': MissingIcon}

WeatherCache = {}  # entries are location:(time, current, forecast)



def TreeDict(d, args):
	# Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
	if len(args) == 1:
		if isinstance(d, dict):
			temp = d[args[0]]
		else:
			temp = getattr(d, args[0])
		if isinstance(temp, str) and temp.isdigit():
			temp = int(temp)
		else:
			try:
				temp = float(temp)
			except (ValueError, TypeError):
				pass
		return temp
	else:
		if isinstance(d, dict):
			return TreeDict(d[args[0]], args[1:])
		else:
			return TreeDict(getattr(d,args[0]),args[1:])

def geticon(nm):
	try:  #todo fix for n/d suffix
		code = IconMap[nm[0:3]]
		daynight = 'day' if nm[3] == 'd' else 'night'
		iconnm = daynight + '/' + str(code) + '.png'
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
		logsupport.Logs.Log('No Weatherbit icon for {}'.format(nm))
		return WeatherIconCache['n/a']


def getdayname(param):
	return datetime.utcfromtimestamp(param).strftime('%a')


def getdatetime(param):  #make string from Localized date time  todo - move localization of sunrise here?
	return LocalizeDateTime(param).strftime('%H:%M')

def strFromDateTime(param):
	return param.strftime('%H:%M')

def makeEpoch(param):
	return param.timestamp()

def doage(param):
	return interval_str(time.time() - param)


def degToCompass(num):
	val = int((num / 22.5) + .5)
	arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
	return arr[(val % 16)]

def setAge(param):
	readingepoch = param.timestamp()
	return functools.partial(doage, readingepoch)


def fcstlength(param):
	return len(param)

# for icons see https://www.weatherbit.io/api/codes

'''
Code	Description	Icons
-200	Thunderstorm with light rain	Weather API Day Thunderstorm with light raint01d, Weather API Night Thunderstorm with light raint01n
-201	Thunderstorm with rain	Weather API Day Thunderstorm with raint02d, Weather API Night Thunderstorm with raint02n
-202	Thunderstorm with heavy rain	Weather API Day Thunderstorm with raint03d, Weather API Night Thunderstorm with raint03n
-230	Thunderstorm with light drizzle	Weather API Day Thunderstorm with drizzlet04d, Weather API Night Thunderstorm with drizzlet04n
-231	Thunderstorm with drizzle	Weather API Day Thunderstorm with drizzlet04d, Weather API Night Thunderstorm with drizzlet04n
-232	Thunderstorm with heavy drizzle	Weather API Day Thunderstorm with drizzlet04d, Weather API Night Thunderstorm with drizzlet04n
-233	Thunderstorm with Hail	Weather API Day Thunderstorm with hailt05d, Weather API Night Thunderstorm with hailt05n
-300	Light Drizzle	Weather API Day Drizzled01d, Weather API Night Drizzled01n
-301	Drizzle	Weather API Day Drizzled02d, Weather API Night Drizzled02n
-302	Heavy Drizzle	Weather API Day Drizzled03d, Weather API Night Drizzled03n
-500	Light Rain	Weather API Day Rainr01d, Weather API Night Rainr01n
-501	Moderate Rain	Weather API Day Rainr02d, Weather API Night Rainr02n
-502	Heavy Rain	Weather API Day Heavy Rainr03d, Weather API Night Heavy Rainr03n
-511	Freezing rain	Weather API Day Freezing Rainf01d, Weather API Night Freezing Rainf01n
-520	Light shower rain	Weather API Day Shower Rainr04d, Weather API Night Shower Rainr04n
-521	Shower rain	Weather API Day Shower Rainr05d, Weather API Night Shower Rainr05n
-522	Heavy shower rain	Weather API Day Shower Rainr06d, Weather API Night Shower Rainr06n
-600	Light snow	Weather API Day Snows01d, Weather API Night Snows01n
-601	Snow	Weather API Day Snows02d, Weather API Night Snows02n
-602	Heavy Snow	Weather API Day Snows03d, Weather API Night Snows03n
-610	Mix snow/rain	Weather API Day Snows04d, Weather API Night Snows04n
-611	Sleet	Weather API Day Sleets05d, Weather API Night Sleets05n
-612	Heavy sleet	Weather API Day Sleets05d, Weather API Night Sleets05n
-621	Snow shower	Weather API Day Snows01d, Weather API Night Snows01n
-622	Heavy snow shower	Weather API Day Snows02d, Weather API Night Snows02n
-623	Flurries	Weather API Day Flurriess06d, Weather API Night Flurriess06n
-700	Mist	Weather API Day Mista01d, Weather API Night Mista01n
-711	Smoke	Weather API Day Smokea02d, Weather API Night Smokea02n
-721	Haze	Weather API Day Hazea03d, Weather API Night Hazea03n
-731	Sand/dust	Weather API Day Sand/Dusta04d, Weather API Night Sand/Dusta04n
-741	Fog	Weather API Day foga05d, Weather API Night foga05n
-751	Freezing Fog	Weather API Day Freezing foga06d, Weather API Night freezing foga06n
-800	Clear sky	Weather API Day clear skyc01d, Weather API Night clear skyc01n
-801	Few clouds	Weather API Day few cloudsc02d, Weather API Night few cloudsc02n
-802	Scattered clouds	Weather API Day few cloudsc02d, Weather API Night few cloudsc02n
-803	Broken clouds	Weather API Day Broken cloudsc03d, Weather API Night Broken cloudsc03n
-804	Overcast clouds	Weather API Day Overcast cloudsc04d, Weather API Night Overcast cloudsc04n
900	Unknown Precipitation	Weather API Day Unknown Precipitationu00d, Weather API Night Unknown Precipitationu00n
'''

IconMap = {'c01':113, 'c02':116, 'c03':119, 'c04':122, 'a05':143, 'r05':176, 's01':179, 's04':182, 's02':185, 's03':185,
		   's05':284, 'f01':227, 'r04':293, 'r06':305, 'r03':308, 'r01':302, 'r02':302, 'd03':308, 'd02':302, 'd01':302,
		   's06':323, 't01':386, 't02':386, 't03':386, 't04':389, 't05':395, 'a01':248, 'a02':248, 'a03':248, 'a04':248,
		   'a06':248}

CondFieldMap = {'Time': (getdatetime, ('datetime',)),
				'Temp': (float, ('temp',)),
				'Sky': (TryShorten, ('weather', 'description')),
				'Feels': (float, ('app_temp',)),
				'WindDir': (degToCompass, ('wind_dir',)),
				'WindMPH': (float, ('wind_spd',)),
				'Humidity': (str, ('rh',)),
				'Icon': (geticon, ('weather', 'icon')),  # get the surface
				'Sunrise': (strFromDateTime, ('sunrise',)),
				'Sunset': (strFromDateTime, ('sunset',)),
				# 'Moonrise': (str, ('forecast', 'forecastday', 0, 'astro', 'moonrise')),
				# 'Moonset': (str, ('forecast', 'forecastday', 0, 'astro', 'moonset')),
				'TimeEpoch': (makeEpoch, ('datetime',)),
				'Age': (setAge, ('datetime',))
				}

FcstFieldMap = {'Day': (getdayname, ('ts',)),  # convert to day name
				'High': (float, ('max_temp',)),
				'Low': (float, ('min_temp',)),
				'Sky': (TryShorten, ('weather','description')),
				'WindSpd': (float, ('wind_spd',)),
				'WindDir': (degToCompass, ('wind_dir',)),
				'Icon': (geticon, ('weather','icon'))  # get the surface
				}

icondir = config.sysStore.ExecDir + '/auxinfo/apixuicons/'


class WeatherbitWeatherSource(object):
	def __init__(self, storename, location, apiky, units='I'):
		self.apikey = apiky
		self.api = Api(self.apikey)
		self.thisStoreName = storename
		self.thisStore = None
		self.location = location
		self.units = units
		self.dailyreset = 0
		self.resettime = '(unset)'
		logsupport.WeatherMsgCount[location] = 0
		logsupport.WeatherMsgStoreName[location] = storename
		try:  # t try to convert to lat/lon
			locationstr = location.split(',')
			if len(locationstr) != 2:
				raise ValueError
			self.lat, self.lon = (float(locationstr[0]), float(locationstr[1]))
			self.get_forecast = functools.partial(self.api.get_forecast, lat=self.lat, lon=self.lon, units=self.units)
			self.get_current = functools.partial(self.api.get_current, lat=self.lat, lon=self.lon, units=self.units)
			logsupport.Logs.Log(
				'Powered by Weatherbit: Created weather for ({},{}) as {}'.format(self.lat, self.lon, storename))
		except Exception as E:  # assume city, state form
			self.get_forecast = functools.partial(self.api.get_forecast, city=self.location, units=self.units)
			self.get_current = functools.partial(self.api.get_current, city=self.location, units=self.units)
			logsupport.Logs.Log(
				'Powered by Weatherbit: Created weather for {} as {}'.format(self.location, storename))

	@staticmethod
	def MQTTWeatherUpdate(payload):
		weatherinfo = json.loads(payload)
		logsupport.Logs.Log(
			'Cache update: {} {} {} {}'.format(weatherinfo['location'], weatherinfo['fetchtime'], time.time(),
											   weatherinfo['fetchingnode']))
		c = Current(weatherinfo['current'], 'viaMQTT', weatherinfo['fetchingnode'])
		f = Forecast(weatherinfo['forecast'], 'viaMQTT', weatherinfo['fetchingnode'])
		WeatherCache[weatherinfo['location']] = (weatherinfo['fetchtime'], c, f, weatherinfo['fetchingnode'])
		if weatherinfo['fetchingnode'] in logsupport.WeatherFetches:
			logsupport.WeatherFetches[weatherinfo['fetchingnode']] += 2
		else:
			logsupport.WeatherFetches[weatherinfo['fetchingnode']] = 2
		logsupport.WeatherFetchNodeInfo[weatherinfo['fetchingnode']] = weatherinfo['fetchcount']
		if weatherinfo['location'] in logsupport.WeatherMsgCount:
			logsupport.WeatherMsgCount[weatherinfo['location']] += 2
		else:
			logsupport.WeatherMsgCount[weatherinfo['location']] = 2
			logsupport.WeatherMsgStoreName[weatherinfo['location']] = '(Not on Node)'

	def ConnectStore(self, store):
		self.thisStore = store

	# noinspection PyMethodMayBeStatic
	# access item by name
	def MapItem(self, src, item):
		if isinstance(item, tuple):
			return item[0](TreeDict(src, item[1]))
		else:
			return item

	def FetchWeather(self):
		try:
			# check for a cached set of readings newer that CurrentFetchTime
			if self.location in WeatherCache and \
					WeatherCache[self.location][0] > self.thisStore.ValidWeatherTime:
				# Newer weather has been broadcast so use that for now
				current = WeatherCache[self.location][1].points[0]
				forecast = WeatherCache[self.location][2].points
				fetcher = WeatherCache[self.location][3]
				weathertime = WeatherCache[self.location][0]
				logsupport.Logs.Log(
					'Using cache weather: {} {} {} {}'.format(self.location, weathertime, time.time(), fetcher))
			elif time.time() < self.dailyreset:
				logsupport.Logs.Log(
					"Skip Weatherbit fetch for {}, over limit until {}".format(self.thisStoreName, self.resettime))
				self.thisStore.ValidWeather = False
				return
			else:
				r = None
				fetchworked = False
				try:
					historybuffer.HBNet.Entry('Weatherbit weather fetch{}'.format(self.thisStoreName))
					c = self.get_current()
					current = c.points[0]  # single point for current reading
					f = self.get_forecast()
					forecast = f.points  # list of 16 points for forecast point 0 is today
					logsupport.Weatherbitfetches += 2
					logsupport.Weatherbitfetches24 += 2
					bcst = {'current': c.json, 'forecast': f.json, 'location': self.location,
							'fetchtime': time.time(),
							'fetchcount': logsupport.Weatherbitfetches24, 'fetchingnode': config.sysStore.hostname}
					if config.mqttavailable:
						config.MQTTBroker.Publish('Weatherbit/{}'.format(self.thisStoreName), node='all/weather',
												  payload=json.dumps(bcst), retain=True)
					historybuffer.HBNet.Entry('Weather fetch done')
					fetchworked = True
					fetcher = 'local'
				except Exception as E:
					if E.response.status_code == 429:
						try:
							resetin = float(
								json.loads(E.response.text)['status_message'].split("after ", 1)[1].split(' ')[0])
							self.resettime = time.strftime('%H:%M', time.localtime(time.time() + 60 * resetin))
						except:
							resetin = 0
							self.resettime = '(unknown)'
						logsupport.Logs.Log(
							'Weatherbit over daily limit, reset at {} for {}'.format(self.resettime,
																					 self.thisStoreName),
							severity=logsupport.ConsoleWarning)
						self.dailyreset = time.time() + 60 * resetin
						self.thisStore.StatusDetail = "(Over Limit until {})".format(self.resettime)
					else:
						logsupport.Logs.Log(
							"Weatherbit failed to get weather for {} last Exc: {}".format(self.thisStoreName, E),
							severity=logsupport.ConsoleWarning, hb=True)
						self.thisStore.StatusDetail = None
					historybuffer.HBNet.Entry('Weather fetch exception: {}'.format(repr(E)))
				if not fetchworked:
					self.thisStore.ValidWeather = False
					return
				else:
					weathertime = time.time()
			# noinspection PyUnboundLocalVariable
			logsupport.Logs.Log(
				'Fetched weather for {} ({}) via {} (age: {} min.)'.format(self.thisStoreName, self.location, fetcher,
																		   (time.time() - weathertime) // 60))
		except Exception as E:
			logsupport.Logs.Log('Unhandled exception in Weatherbit fetch: {}'.format(E),
								severity=logsupport.ConsoleWarning)
		try:
			self.thisStore.ValidWeather = False  # show as invalid for the short duration of the update - still possible to race but very unlikely.
			tempfcstinfo = {}
			for fn, entry in FcstFieldMap.items():
				tempfcstinfo[fn] = []

			self.thisStore.SetVal(('Cond', 'Location'), self.thisStoreName)
			for fn, entry in CondFieldMap.items():
				val = self.MapItem(current, entry)
				self.thisStore.SetVal(('Cond', fn), val)

			fcstdays = len(forecast)
			for i in range(fcstdays):
				try:
					dbgtmp = {}
					fcst = forecast[i]

					for fn, entry in FcstFieldMap.items():
						val = self.MapItem(fcst, entry)
						tempfcstinfo[fn].append(val)
						dbgtmp[fn] = val
				except Exception as E:
					logsupport.Logs.Log(
						'Exception in Weatherbit forecast processing for {} day {}: {}'.format(self.thisStoreName, i,
																							   repr(E)))
					logsupport.Logs.Log('Forecast: {}'.format(forecast))
					raise
			for fn, entry in FcstFieldMap.items():
				self.thisStore.GetVal(('Fcst', fn)).replacelist(tempfcstinfo[fn])
			self.thisStore.SetVal('FcstDays', fcstdays)
			self.thisStore.SetVal('FcstEpoch', int(forecast[0].ts))
			self.thisStore.SetVal('FcstDate', forecast[0].valid_date)

			self.thisStore.CurFetchGood = True
			self.thisStore.ValidWeather = True
			self.thisStore.StatusDetail = None
			self.thisStore.ValidWeatherTime = weathertime
			controlevents.PostEvent(controlevents.ConsoleEvent(controlevents.CEvent.GeneralRepaint))
			return  # success
		except Exception as E:
			logsupport.DevPrint(
				'Exception {} in Weatherrbit report processing: {} (via: {})'.format(E, forecast, fetcher))
			self.thisStore.CurFetchGood = False
		logsupport.Logs.Log(
			'Decode failure on return data from weather fetch of {} via {}'.format(self.thisStoreName, fetcher))


WeathProvs['Weatherbit'] = [WeatherbitWeatherSource, '']  # api key gets filled in from config file
