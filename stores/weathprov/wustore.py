import requests
import os, sys
import time
import pygame
from utilfuncs import interval_str, TreeDict
import functools
import config
import logsupport
from logsupport import ConsoleDetail, ConsoleWarning, ConsoleError
import io
from stores.weathprov.providerutils import TryShorten

EmptyIcon = pygame.Surface((64, 64))
EmptyIcon.fill((255, 255, 255))  # todo replace with a ? icon?
EmptyIcon.set_colorkey((255, 255, 255))
WeatherIconCache = {'n/a': EmptyIcon}

WUcount = 0


def geticon(url):
	if url in WeatherIconCache:
		return WeatherIconCache[url]
	if url.split('/')[-1] in ['.git', 'nt_.gif']:
		WeatherIconCache[url] = EmptyIcon
		return EmptyIcon
	r = requests.get(url)
	icon_str = r.content
	icon_file = io.BytesIO(icon_str)
	icon_gif = pygame.image.load(icon_file, 'icon.gif')
	icon_scr = pygame.Surface.convert_alpha(icon_gif)
	icon_scr.set_colorkey(icon_gif.get_colorkey())
	WeatherIconCache[url] = icon_scr
	return icon_scr


def doage(basetime, loc):
	rdingage = time.time() - basetime
	if rdingage > (60 * 60 * 24) * 5:  # over 5 days old
		logsupport.Logs.Log("Weather station likely gone: ", loc, " age is ", rdingage / (60 * 60 * 24),
							" days old", severity=ConsoleWarning)
	return interval_str(rdingage)


def fixsky(param):
	if param == '':
		return 'No Sky Rpt'
	else:
		TryShorten(param)


def setAge(param, loc):
	return functools.partial(doage, param, loc)

def makeTime(h, m):
	return "{0:02d}:{1:02d}".format(h, m)


def makewindir(param):
	return str(param) + '@'


def strtime(epochtime):
	return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epochtime))


CondFieldMap = {'Time': (strtime, ('current_observation', 'observation_epoch')),
				'Location': (str, ('current_observation', 'display_location', 'city')),
				'Temp': (float, ('current_observation', 'temp_f')),
				'Sky': (fixsky, ('current_observation', 'weather')),
				'Feels': (float, ('current_observation', 'feelslike_f')),
				'WindDir': (str, ('current_observation', 'wind_dir')),
				'WindMPH': (float, ('current_observation', 'wind_mph')),
				'WindGust': (float, ('current_observation', 'wind_gust_mph')),
				'Sunrise': (makeTime, ('sun_phase', 'sunrise', 'hour'), ('sun_phase', 'sunrise', 'minute')),
				'Sunset': (makeTime, ('sun_phase', 'sunset', 'hour'), ('sun_phase', 'sunset', 'minute')),
				'Moonrise': (makeTime, ('moon_phase', 'moonrise', 'hour'), ('moon_phase', 'moonrise', 'minute')),
				'Moonset': (makeTime, ('moon_phase', 'moonset', 'hour'), ('moon_phase', 'moonset', 'minute')),
				'TimeEpoch': (int, ('current_observation', 'observation_epoch')),
				'Age': (setAge, ('current_observation', 'observation_epoch'), 'location'),
				'Humidity': (str, ('current_observation', 'relative_humidity')),
				'Icon': (geticon, ('current_observation', 'icon_url'))
				}

FcstFieldMap = {'Day': (str, ('date', 'weekday_short')),  # convert to day name
				'High': (float, ('high', 'fahrenheit')),
				'Low': (float, ('low', 'fahrenheit')),
				'Sky': (fixsky, ('conditions',)),
				'WindSpd': (float, ('avewind', 'mph')),
				'WindDir': (makewindir, ('avewind', 'dir')),
				'Icon': (geticon, ('icon_url',))  # get the surface
				}

CommonFieldMap = {'FcstDays': 10, 'FcstEpoch': (int, ('forecast', 'simpleforecast', 'forecastday', 0, 'date', 'epoch')),
				  'FcstDate': (strtime, ('forecast', 'simpleforecast', 'forecastday', 0, 'date',
										 'epoch'))}  # todo constant 7 should be dynamic

# icondir = config.exdir+'/auxinfo/apixuicons/'
icondir = '/home/pi/consolerem' + '/auxinfo/apixuicons/'


class WUWeatherSource(object):
	global WUcount

	def __init__(self, storename, location, api):
		self.baseurl = 'https://api.apixu.com/v1/forecast.json'
		self.args = {'key': api, 'q': location, 'days': 7}
		self.apikey = api
		self.thisStoreName = storename
		self.thisStore = None
		self.location = location
		self.fetchcount = 0
		self.json = {}
		self.url = 'http://api.wunderground.com/api/' + self.apikey + '/conditions/forecast10day/astronomy/q/' \
				   + location + '.json'
		logsupport.Logs.Log('Created WU weather for: ', location, ' as ', storename)

	def ConnectStore(self, store):
		self.thisStore = store

	def MapItem(self, src, item):
		if isinstance(item, tuple):
			if len(item) == 2:
				return item[0](TreeDict(src, item[1]))
			else:
				if isinstance(item[2], str):
					if item[2] == 'location':  # can add other internal variables here if needed
						return item[0](TreeDict(src, item[1]), self.location)
				else:
					return item[0](TreeDict(src, item[1]), TreeDict(src, item[2]))
		else:
			return item

	def FetchWeather(self):
		global WUcount
		if self.apikey == '*':  # marker for bad key
			# if key was bad don't bother banging on WU
			self.failedfetch = True
			return 3  # permanent failure

		try:
			r = requests.get(self.url, timeout=15)
			WUcount += 1
			logsupport.Logs.Log(
				"Actual weather fetch for " + self.location + "(" + str(self.fetchcount) + ')' + " WU count: " + str(
					WUcount),
				severity=ConsoleDetail)
		except:
			logsupport.Logs.Log("Error fetching weather: " + self.url + str(sys.exc_info()[0]),
								severity=ConsoleWarning)
			self.failedfetch = True
			return 1

		if r.text.find("keynotfound") != -1:
			self.apikey = '*'
			# only report once in log
			logsupport.Logs.Log("Bad weatherunderground key:" + self.location, severity=ConsoleError, tb=False)
			self.failedfetch = True
			return 3

		if r.text.find("you must supply a key") != -1:
			logsupport.Logs.Log("WeatherUnderground missed the key:" + self.location, severity=ConsoleWarning)
			self.fetchtime = 0  # force retry next time since this didn't register with WU todo
			self.failedfetch = True
			return 1

		if r.text.find('been an error') != -1:
			# odd error case that's been seen where html rather than json is returned
			logsupport.Logs.Log("WeatherUnderground returned nonsense for station: ", self.location,
								severity=ConsoleWarning)
			with open(os.path.dirname(config.configfile) + '/' + self.location + '-WUjunk.log', 'w') as f:
				f.write(r.text)
				f.flush()
			self.failedfetch = True
			return 2

		if r.text.find('backend failure') != -1:
			logsupport.Logs.Log("WeatherUnderground backend failure on station: ", self.location,
								severity=ConsoleWarning)
			self.failedfetch = True
			return 1

		self.json = r.json()
		for fn, entry in CondFieldMap.items():
			val = self.MapItem(self.json, entry)
			self.thisStore.SetVal(('Cond', fn), val)
		fcstdays = len(self.json['forecast']['simpleforecast']['forecastday'])
		for i in range(fcstdays):
			try:
				fcst = self.json['forecast']['simpleforecast']['forecastday'][i]
				for fn, entry in FcstFieldMap.items():
					val = self.MapItem(fcst, entry)
					self.thisStore.GetVal(('Fcst', fn)).append(val)
			except Exception as e:
				logsupport.Logs.Log('Exception in wu forecast processing: ', fn, repr(e),
									severity=logsupport.ConsoleWarning)

		for fn, entry in CommonFieldMap.items():
			val = self.MapItem(self.json, entry)
			self.thisStore.SetVal(fn, val)


config.WeathProvs['WU'] = [WUWeatherSource, '']  # api key gets filled in from config file
