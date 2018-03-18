import functools
import debug
import pygame
import io
import os
import sys
import json
import time
import urllib2
import utilities
import config
from stores import valuestore
from collections import OrderedDict
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError

def TreeDict(d, *args):
	# Allow a nest of dictionaries to be accessed by a tuple of keys for easier code
	if len(args) == 1:
		temp = d[args[0]]
		if isinstance(temp, basestring) and temp.isdigit():
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

WeatherIconCache = {}
WUcount = 0

def get_icon(url):
	if 	WeatherIconCache.has_key(url):
		return WeatherIconCache[url]
	else:
		icon_str = urllib2.urlopen(url).read()
		icon_file = io.BytesIO(icon_str)
		icon_gif = pygame.image.load(icon_file,'icon.gif')
		icon_scr = pygame.Surface.convert_alpha(icon_gif)
		icon_scr.set_colorkey(icon_gif.get_colorkey())
		WeatherIconCache[url] = icon_scr
		return icon_scr

class WeatherItem(valuestore.StoreItem):
	def __init__(self,name, mapinfo, Store):
		self.MapInfo = mapinfo
		super(WeatherItem,self).__init__(name,None,store=Store)

class FcstItem(valuestore.StoreItem):
	def __init__(self,name,mapinfo):
		self.MapInfo = mapinfo
		super(FcstItem, self).__init__([])


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
						'MoonriseH': (int, ('moon_phase', 'moonrise', 'hour')),  # todo intstr
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

		super(WeatherVals,self).__init__(location, refreshinterval = 60*30)
		self.fetchcount = 0
		self.vars = {'Cond':OrderedDict(),'Fcst':OrderedDict()}
		csynthmap = {'Icon':('synthetic', self.geticon, 'Cond'),
					'Moonrise':('synthetic',self.fixMoon,'rise'),
					'Moonset':('synthetic',self.fixMoon,'set'),
					'Age':('synthetic',self.setAge,'')}
		fsynthmap = {'Icon':('synthetic', self.geticon, 'Fcst')}  # if other forecast synthetics defined then code below won't work
		# because it doesn't factor in the day of the forecast any place. Probably need to pass as parameter to the procedure
		# defined here in the map.  Don't need to for the icon only because it is handled as a special case below
		self.failedfetch = False
		self.location = location
		self.name = location
		self.url = 'http://api.wunderground.com/api/' + WunderKey + '/conditions/forecast10day/astronomy/q/' \
				   + location + '.json'
		for fld, fldinfo in ConditionMap.iteritems():
			self.vars['Cond'][fld] = WeatherItem(('Cond',fld),fldinfo,self)
		for fld, fldinfo in csynthmap.iteritems():
			self.vars['Cond'][fld] = WeatherItem(('Cond',fld),fldinfo,self)
		for fld, fldinfo in ForecastDay.iteritems():
			self.vars['Fcst'][fld] = WeatherItem(('Fcst',fld),fldinfo,self)
		for fld, fldinfo in fsynthmap.iteritems():
			self.vars['Fcst'][fld] = WeatherItem(('Fcst',fld),fldinfo,self)

	def BlockRefresh(self):
		global WUcount
		if self.fetchtime + self.refreshinterval > time.time():
			# have recent data
			return

		self.fetchtime = time.time()
		self.failedfetch = False
		self.fetchcount += 1
		try:
			f = urllib2.urlopen(self.url, None, 15)  # wait at most 15 seconds for weather response then timeout
			val = f.read()
			f.close
			WUcount += 1
			logsupport.Logs.Log("Actual weather fetch for " + self.location + "(" + str(self.fetchcount) + ')' + " WU count: " + str(WUcount),
							severity=ConsoleDetail)
		except:
			logsupport.Logs.Log("Error fetching weather: " + self.url + str(sys.exc_info()[0]),
							severity=ConsoleWarning)
			#self.dumpweatherresp(val, 'none', 'fetch', '--')
			self.failedfetch = True
			return None

		if val.find("keynotfound") != -1:
			config.BadWunderKey = True
			# only report once in log
			logsupport.Logs.Log("Bad weatherunderground key:" + self.location, severity=ConsoleError, tb=False)
			return None

		if val.find("you must supply a key") != -1:
			logsupport.Logs.Log("WeatherUnderground missed the key:" + self.location, severity=ConsoleWarning)
			self.fetchtime = 0  # force retry next time since this didn't register with WU
			return None

		"""
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile = open(os.path.dirname(config.configfile) + '/' + self.location + 'wv.log', 'w')
			self.weathvalfile.write(self.location + ' \n==================\n')
			self.weathvalfile.flush()
			self.weathjsonfile = open(os.path.dirname(config.configfile) + '/' + self.location + 'wj.log', 'w')
			self.weathjsonfile.write(self.location + '\n==================\n')
			self.weathjsonfile.flush()
			# dump
		"""

		parsed_json = json.loads(val)
		js = functools.partial(TreeDict, parsed_json)
		fcsts = TreeDict(parsed_json, 'forecast', 'simpleforecast', 'forecastday')
		for n, cond in self.vars['Cond'].iteritems():
			try:
				if cond.MapInfo[0] != 'synthetic':
					cond.Value = cond.MapInfo[0](js(*cond.MapInfo[1]))
					if cond.MapInfo[0] == str:
						cond.Value = TryShorten(cond.Value)
				else:
					cond.Value = cond.MapInfo[1](cond.MapInfo[2])
			except:
				cond.Value = None  # set error equiv to Conderr?

		for n, fcst in self.vars['Fcst'].iteritems():
			fcst.Value = valuestore.StoreList(fcst)
			for i, fcstitem in enumerate(fcsts):
				fs = functools.partial(TreeDict,fcstitem)
				try:
					if fcst.MapInfo[0] != 'synthetic':
						itemval = fcst.MapInfo[0](fs(*fcst.MapInfo[1]))
						fcst.Value.append(itemval if fcst.MapInfo[0] != str else TryShorten(itemval))
					else:
						fcst.Value.append(fcst.MapInfo[1](fcst.MapInfo[2], day=i))
				except:
					fcst.Value.append(None)

	def geticon(self,n, day=-1):
		if day == -1:
			return get_icon(self.vars[n]['Iconurl'].Value)
		else:
			return get_icon(self.vars[n]['Iconurl'].Value[day])

	def setAge(self,junk):
		try:
			return utilities.interval_str(time.time() - self.vars['Cond']['Time'].Value)
		except:
			return "No readings ever retrieved"

	def fixMoon(self,evnt):
			MoonH = 'Moon'+evnt+'H'
			MoonM = 'Moon'+evnt+'M'
			if (self.vars['Cond'][MoonH].Value is None) or (self.vars['Cond'][MoonM].Value is None):
				return 'n/a'
			else:
				return "{d[0]:02d}:{d[1]:02d}".format(
					d=[self.vars['Cond'][x].Value for x in (MoonH, MoonM)])

	def GetVal(self,name):
		if config.BadWunderKey:
			return None
		self.BlockRefresh()
		if self.failedfetch:
			return None
		else:
			return super(WeatherVals,self).GetVal(name)

	def SetVal(self,name,val):
		logsupport.Logs.Log("Setting weather item via SetVal unsupported: "+name,severity=ConsoleError)




	def dumpweatherresp(self, val, json, tag, param):
		if config.versionname in ('development', 'homerelease'):
			self.weathvalfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(val) + '\n=================')
			self.weathjsonfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(json) + '\n=================')
			self.weathvalfile.flush()
			self.weathjsonfile.flush()