import requests
from datetime import datetime
import time
import pygame
from utilfuncs import interval_str
import functools


def TreeDict(d, args):
	# Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
	if len(args) == 1:
		temp = d[args[0]]
		if isinstance(temp, str) and temp.isdigit():
			temp = int(temp)
		else:
			try:
				temp = float(temp)
			except (ValueError, TypeError):
				pass
		return temp
	else:
		return TreeDict(d[args[0]], args[1:])


EmptyIcon = pygame.Surface((64, 64))
EmptyIcon.fill((255, 255, 255))  # todo replace with a ? icon?
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
	print(datetime.utcfromtimestamp(param).strftime('%c'))
	return datetime.utcfromtimestamp(param).strftime('%a')


def doage(basetime):
	return interval_str(time.time() - basetime)


def setAge(param):
	return functools.partial(doage, param)


CondFieldMap = {'Time': (str, ('current', 'last_updated')),
				'Location': (str, ('location', 'name')),
				'Temp': (float, ('current', 'temp_f')),
				'Sky': (str, ('current', 'condition', 'text')),
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
				'Sky': (str, ('day', 'condition', 'text')),
				'WindSpd': (str, ('day', 'maxwind_mph')),
				'WindDir': '',
				'Icon': (geticon, ('day', 'condition', 'icon'))  # get the surface
				}

CommonFieldMap = {'FcstDays': 7, 'FcstEpoch': (int, ('forecastday', 0, 'date_epoch')),
				  'FcstDate': (str, ('forecastday', 0, 'date'))}  # todo constant 7 should be dynamic

# icondir = config.exdir+'/auxinfo/apixuicons/'
icondir = '/home/pi/consolerem' + '/auxinfo/apixuicons/'


class APIXUWeatherSource(object):
	def __init__(self, store, location):
		api = '2e7efedc0e11436f9a3182807182105'  # todo api as param
		self.baseurl = 'https://api.apixu.com/v1/forecast.json'
		self.args = {'key': api, 'q': location, 'days': 7}
		self.apikey = api
		self.thisStore = store
		self.location = location
		self.json = {}

	def MapItem(self, src, item):
		if isinstance(item, tuple):
			if isinstance(item[0], type):
				return item[0](TreeDict(src, item[1]))
			else:
				return item[0](TreeDict(src, item[1]))  # todo redundant
		else:
			return item

	def FetchWeather(self):
		temp = {}
		r = requests.get(self.baseurl, params=self.args)
		self.json = r.json()
		for fn, entry in CondFieldMap.items():
			val = self.MapItem(self.json, entry)
			self.thisStore.SetVal(('Cond', fn), val)
			temp[fn] = val
		# self.thisStore.SetVal(('Cond', fn), entry[0](val))
		print(repr(temp))
		fcstdays = len(self.json['forecast']['forecastday'])
		for i in range(fcstdays):
			temp = {}
			fcst = self.json['forecast']['forecastday'][i]
			for fn, entry in FcstFieldMap.items():
				val = self.MapItem(fcst, entry)
				self.thisStore.GetVal(('Fcst', fn)).append(val)

				temp[fn] = val
			# self.thisStore.SetVal((('Fcst', fn), i), val)
			print(i)
			print(repr(temp))

		for fn, entry in CommonFieldMap.items():
			val = self.MapItem(self.json, entry)
			self.thisStore.SetVal(fn, val)

		'''
		Should also set common fields and possibly return fail indicator
		'''
