import functools
import pygame
import io
import os
import sys
import json
import time
import datetime
import requests
import utilities
import config
from stores import valuestore
from collections import OrderedDict
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError

from stores import apixustore  # todo temp

'''
At the generic level defining the available fields seems reasonable; issue with the specific sources holding their mappings 
should they do it entirely inside their instance or use the mapinfo idea of the store; leaning toward the former since
no real reason to store the map in the store and it is only used to populate the store on a refresh

icon/icon cache - should different sources have different caches?  Different icons if multiple sources happen to get used?
'''


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
	if url in WeatherIconCache:
		return WeatherIconCache[url]
	else:
		r = requests.get(url)
		icon_str = r.content
		icon_file = io.BytesIO(icon_str)
		icon_gif = pygame.image.load(icon_file, 'icon.gif')
		icon_scr = pygame.Surface.convert_alpha(icon_gif)
		icon_scr.set_colorkey(icon_gif.get_colorkey())
		WeatherIconCache[url] = icon_scr
		return icon_scr


class WeatherItem(valuestore.StoreItem):
	def __init__(self, name, mapinfo, Store, vt=None):
		# self.MapInfo = mapinfo
		super(WeatherItem, self).__init__(name, None, store=Store, vt=vt)


class WeatherVals(valuestore.ValueStore):
	global WUcount

	def __init__(self, location, weathersource):
		self.fetchtime = 0
		CondFields = (
		('Time', str), ('Location', str), ('Temp', float), ('Sky', str), ('Feels', float), ('WindDir', str),
		('WindMPH', float), ('WindGust', int), ('Sunrise', str), ('Sunset', str), ('Moonrise', str),
		('Moonset', str), ('Humidity', int), ('Icon', pygame.Surface), ('TimeEpoch', int))
		FcstFields = (('Day', str), ('High', float), ('Low', float), ('Sky', str), ('WindSpd', float),
					  ('Icon', pygame.Surface))
		CommonFields = (('FcstDays', int), ('FcstEpoch', int), ('FcstDate', str))

		super(WeatherVals, self).__init__(location, refreshinterval=60 * 30)
		self.ws = weathersource
		self.fetchcount = 0
		self.vars = {'Cond': OrderedDict(), 'Fcst': OrderedDict()}
		self.failedfetch = False
		self.location = location
		self.name = location

		for fld, fldtype in CondFields:
			nm = ('Cond', fld)
			self.vars['Cond'][fld] = WeatherItem(nm, self.ws.CondFieldMap(fld), self,
												 vt=fldtype)  # This doesn't really work yet because ws may need to compute field rather than map (old synthetic)
		for fld, fldtype in FcstFields:
			nm = ('Fcst', fld)
			self.vars['Fcst'][fld] = WeatherItem(nm, self.ws.FcstFieldMap(fld), self, vt=fldtype)
		for fld, fldtype in CommonFields:
			self.vars[fld] = WeatherItem(fld, self.ws.CommFieldMap(fld), self, vt=fldtype)

	def BlockRefresh(self):

		if self.fetchtime + self.refreshinterval > time.time():
			# have recent data
			return

		self.fetchtime = time.time()
		self.failedfetch = False
		self.fetchcount += 1

		'''
		This is where we call the actual fetch weather
		That is provider specific and should update all the items in the store or set failedfetch
		'''

		self.ws.FetchWeather()

	# fcsts = TreeDict(parsed_json, 'forecast', 'simpleforecast', 'forecastday')
	# fcstepoch = int(fcsts[0]['date']['epoch'])
	# forecastjunk = False


	def geticon(self, n, day=-1):
		if day == -1:
			return get_icon(self.vars[n]['Iconurl'].Value)
		else:
			return get_icon(self.vars[n]['Iconurl'].Value[day])

	# noinspection PyUnusedLocal
	def setAge(self, junk):
		# noinspection PyBroadException
		try:
			return utilities.interval_str(time.time() - self.vars['Cond']['Time'].Value)
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

	#	def SetVal(self,name,val,modifier=None):
	#		logsupport.Logs.Log("Setting weather item via SetVal unsupported: "+str(name),severity=ConsoleError)

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
