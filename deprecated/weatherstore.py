import datetime
import functools
import io
import json
import os
import sys
import time
from collections import OrderedDict

import config
import logsupport
import pygame
import requests
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError
from stores import valuestore
from utilfuncs import *


def TreeDict(d, *args):
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
		return TreeDict(d[args[0]], *args[1:])


def TryShorten(term):
	if term in config.TermShortener:
		return config.TermShortener[term]
	elif len(term) > 12 and term[0:4] != 'http':
		logsupport.Logs.Log("Long term: " + term, severity=ConsoleWarning)
		config.TermShortener[term] = term  # only report once
		with open(config.exdir + '/termshortenlist.new', 'w') as f:
			json.dump(config.TermShortener, f, indent=4, separators=(',', ": "))
	return term


EmptyIcon = pygame.Surface((50, 50))
EmptyIcon.fill((255, 255, 255))
EmptyIcon.set_colorkey((255, 255, 255))
WeatherIconCache = {}
WUcount = 0


def get_icon(url):
	global EmptyIcon
	if url in WeatherIconCache:
		return WeatherIconCache[url]
	else:
		try:
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
		except Exception:
			logsupport.Logs.Log('Bad icon url fetch - using empty icon for: ', repr(url))
			return EmptyIcon


class WeatherItem(valuestore.StoreItem):
	def __init__(self, name, mapinfo, Store):
		self.MapInfo = mapinfo
		super(WeatherItem, self).__init__(name, None, store=Store)


class WeatherVals(valuestore.ValueStore):
	global WUcount

	def __init__(self, location, WunderKey):
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
						'MoonriseH': (int, ('moon_phase', 'moonrise', 'hour')),
						'MoonriseM': (int, ('moon_phase', 'moonrise', 'minute')),
						'MoonsetH': (int, ('moon_phase', 'moonset', 'hour')),
						'MoonsetM': (int, ('moon_phase', 'moonset', 'minute')),
						'MoonPct': (int, ('moon_phase', 'percentIlluminated')),
						'Humidity': (str, ('current_observation', 'relative_humidity')),
						'Iconurl': (str, ('current_observation', 'icon_url'))
						}
		ForecastDay = {'Day': (str, ('date', 'weekday_short')),
					   'High': (int, ('high', 'fahrenheit')),
					   'Low': (int, ('low', 'fahrenheit')),
					   'Sky': (str, ('conditions',)),
					   'WindDir': (str, ('avewind', 'dir')),
					   'WindSpd': (float, ('avewind', 'mph')),
					   'Iconurl': (str, ('icon_url',))}

		super(WeatherVals, self).__init__(location)
		self.refreshinterval = 60 * 30
		self.fetchcount = 0
		self.vars = {'Cond': OrderedDict(), 'Fcst': OrderedDict()}
		csynthmap = {'Icon': ('synthetic', self.geticon, 'Cond'),
					 'Moonrise': ('synthetic', self.fixMoon, 'rise'),
					 'Moonset': ('synthetic', self.fixMoon, 'set'),
					 'Age': ('synthetic', self.setAge, '')}
		fsynthmap = {'Icon': (
		'synthetic', self.geticon, 'Fcst')}  # if other forecast synthetics defined then code below won't work
		# because it doesn't factor in the day of the forecast any place. Probably need to pass as parameter to the procedure
		# defined here in the map.  Don't need to for the icon only because it is handled as a special case below
		self.failedfetch = False
		self.location = location
		self.name = location
		self.url = 'http://api.wunderground.com/api/' + WunderKey + '/conditions/forecast10day/astronomy/q/' \
				   + location + '.json'
		for fld, fldinfo in ConditionMap.items():
			self.vars['Cond'][fld] = WeatherItem(('Cond', fld), fldinfo, self)
		for fld, fldinfo in csynthmap.items():
			self.vars['Cond'][fld] = WeatherItem(('Cond', fld), fldinfo, self)
		for fld, fldinfo in ForecastDay.items():
			self.vars['Fcst'][fld] = WeatherItem(('Fcst', fld), fldinfo, self)
		for fld, fldinfo in fsynthmap.items():
			self.vars['Fcst'][fld] = WeatherItem(('Fcst', fld), fldinfo, self)
		self.vars['FcstDays'] = valuestore.StoreItem('FcstDays', 0, store=self)
		self.vars['LastGoodFcst'] = valuestore.StoreItem('LastGoodFcst', 0, store=self)

	def _FetchWeather(self):
		global WUcount
		if config.BadWunderKey:
			# if key was bad don't bother banging on WU
			self.failedfetch = True
			return None
		# noinspection PyBroadException
		try:
			r = requests.get(self.url, timeout=15)
			val = r.text
			WUcount += 1
			logsupport.Logs.Log(
				"Actual weather fetch for " + self.location + "(" + str(self.fetchcount) + ')' + " WU count: " + str(
					WUcount),
				severity=ConsoleDetail)
		except:
			logsupport.Logs.Log("Error fetching weather: " + self.url + str(sys.exc_info()[0]),
								severity=ConsoleWarning)
			self.failedfetch = True
			return None

		if val.find("keynotfound") != -1:
			config.BadWunderKey = True
			# only report once in log
			logsupport.Logs.Log("Bad weatherunderground key:" + self.location, severity=ConsoleError, tb=False)
			self.failedfetch = True
			return None

		if val.find("you must supply a key") != -1:
			logsupport.Logs.Log("WeatherUnderground missed the key:" + self.location, severity=ConsoleWarning)
			self.fetchtime = 0  # force retry next time since this didn't register with WU
			self.failedfetch = True
			return None

		if val.find('been an error') != -1:
			# odd error case that's been seen where html rather than json is returned
			logsupport.Logs.Log("WeatherUnderground returned nonsense for station: ", self.location,
								severity=ConsoleWarning)
			with open(os.path.dirname(config.configfile) + '/' + self.location + '-WUjunk.log', 'w') as f:
				f.write(val)
				f.flush()
			self.failedfetch = True
			return None

		if val.find('backend failure') != -1:
			logsupport.Logs.Log("WeatherUnderground backend failure on station: ", self.location,
								severity=ConsoleWarning)
			self.failedfetch = True
			return None

		try:
			parsed_json = json.loads(val)
		except ValueError as e:  # in Python3 this could be a JSONDecodeError which is a subclass of ValueError
			logsupport.Logs.Log("Bad weather json: ", repr(e), severity=ConsoleWarning)
			with open(os.path.dirname(config.configfile) + '/' + self.location + '-WUjunk.log', 'w') as f:
				f.write(val)
				f.flush()

			self.failedfetch = True
			return None
		return parsed_json

	def BlockRefresh(self):

		if self.fetchtime + self.refreshinterval > time.time():
			# have recent data
			return

		self.failedfetch = False
		self.fetchcount += 1

		parsed_json = self._FetchWeather()

		if parsed_json is None:
			logsupport.Logs.Log("FetchWeather failed - not updating information for: ", self.location,
								severity=ConsoleWarning)
			# but don't retry too quickly
			self.fetchtime = time.time() - self.refreshinterval + 120  # should fake a 2 minute delay before a retry
			return
		# good fetch so don't repeat for interval
		self.fetchtime = time.time()
		if parsed_json['current_observation']['weather'] == '':
			parsed_json['current_observation']['weather'] = 'No-Sky-Cond'
			logsupport.Logs.Log("Missing sky condition: ", self.location, severity=ConsoleWarning)

		fcsts = TreeDict(parsed_json, 'forecast', 'simpleforecast', 'forecastday')
		fcstepoch = int(fcsts[0]['date']['epoch'])
		forecastjunk = False
		if int(time.time()) - fcstepoch > 60 * 60 * 24:  # 1 day
			forecastjunk = True
			logsupport.Logs.Log("WU returned nonsense forecast for ", self.location, " from: ",
								datetime.datetime.fromtimestamp(fcstepoch).strftime('%c'), severity=ConsoleWarning)
			# retry once
			parsed_json = self._FetchWeather()
			fcsts = TreeDict(parsed_json, 'forecast', 'simpleforecast', 'forecastday')
			fcstepoch = int(fcsts[0]['date']['epoch'])
			if int(time.time()) - fcstepoch > 60 * 60 * 24:  # 1 day
				logsupport.Logs.Log("Retry didn't resolve WU issue")
			else:
				logsupport.Logs.Log("Retry resolved WU issue")
				forecastjunk = False

		js = functools.partial(TreeDict, parsed_json)

		for n, cond in self.vars['Cond'].items():
			# noinspection PyBroadException
			try:
				if cond.MapInfo[0] != 'synthetic':
					cond.Value = cond.MapInfo[0](js(*cond.MapInfo[1]))
					if cond.MapInfo[0] == str:
						cond.Value = TryShorten(cond.Value)
				else:
					cond.Value = cond.MapInfo[1](cond.MapInfo[2])
			except:
				cond.Value = None  # set error equiv to Conderr?

		if self.vars['Cond']['Icon'] is None:
			logsupport.Logs.Log('Internal icon error', severity=ConsoleError, tb=False)

		if not forecastjunk:
			self.vars['LastGoodFcst'].Value = time.time()
			self.vars['FcstDays'].Value = len(fcsts)
			for n, fcst in self.vars['Fcst'].items():
				fcst.Value = valuestore.StoreList(fcst)
				for i, fcstitem in enumerate(fcsts):
					fs = functools.partial(TreeDict, fcstitem)
					# noinspection PyBroadException
					try:
						if fcst.MapInfo[0] != 'synthetic':
							itemval = fcst.MapInfo[0](fs(*fcst.MapInfo[1]))
							fcst.Value.append(itemval if fcst.MapInfo[0] != str else TryShorten(itemval))
						else:
							fcst.Value.append(fcst.MapInfo[1](fcst.MapInfo[2], day=i))
					except:
						fcst.Value.append(None)
		else:
			logsupport.Logs.Log("Continuing to use forecast retrieved at: ",
								datetime.datetime.fromtimestamp(self.vars['LastGoodFcst'].Value).strftime('%c'),
								severity=ConsoleWarning)

	def geticon(self, n, day=-1):
		if day == -1:
			return get_icon(self.vars[n]['Iconurl'].Value)
		else:
			return get_icon(self.vars[n]['Iconurl'].Value[day])

	# noinspection PyUnusedLocal
	def setAge(self, junk):
		# noinspection PyBroadException
		try:
			rdingage = time.time() - self.vars['Cond']['Time'].Value
			if rdingage > (60 * 60 * 24) * 5:
				logsupport.Logs.Log("Weather station likely gone: ", self.name, " age is ", rdingage / (60 * 60 * 24),
									" days old", severity=ConsoleWarning)
			return interval_str(rdingage)
		except:
			return "No readings ever retrieved"

	def fixMoon(self, evnt):
		MoonH = 'Moon' + evnt + 'H'
		MoonM = 'Moon' + evnt + 'M'
		if (self.vars['Cond'][MoonH].Value is None) or (self.vars['Cond'][MoonM].Value is None):
			return 'n/a'
		else:
			return "{d[0]:02d}:{d[1]:02d}".format(
				d=[self.vars['Cond'][x].Value for x in (MoonH, MoonM)])

	def GetVal(self, name):
		if config.BadWunderKey:
			return None
		self.BlockRefresh()
		if self.failedfetch:
			return None
		else:
			return super(WeatherVals, self).GetVal(name)

	def SetVal(self, name, val, modifier=None):
		logsupport.Logs.Log("Setting weather item via SetVal unsupported: " + str(name), severity=ConsoleError)

	"""
	def dumpweatherresp(self, val, djson, tag, param):
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(val) + '\n=================')
			self.weathjsonfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(djson) + '\n=================')
			self.weathvalfile.flush()
			self.weathjsonfile.flush()
	"""
