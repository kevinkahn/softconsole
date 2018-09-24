
import pygame
import json
import time
import config
from stores import valuestore
from collections import OrderedDict
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail, ConsoleError

from stores.weathprov import apixustore  # todo temp

'''
At the generic level defining the available fields seems reasonable; issue with the specific sources holding their mappings 
should they do it entirely inside their instance or use the mapinfo idea of the store; leaning toward the former since
no real reason to store the map in the store and it is only used to populate the store on a refresh

icon/icon cache - should different sources have different caches?  Different icons if multiple sources happen to get used?
'''

CondFields = (
	('Time', str), ('Location', str), ('Temp', float), ('Sky', str), ('Feels', float), ('WindDir', str),
	('WindMPH', float), ('WindGust', int), ('Sunrise', str), ('Sunset', str), ('Moonrise', str),
	('Moonset', str), ('Humidity', float), ('Icon', pygame.Surface), ('TimeEpoch', int), ('Age', None))
FcstFields = (('Day', str), ('High', float), ('Low', float), ('Sky', str), ('WindSpd', float), ('WindDir', str),
			  ('Icon', pygame.Surface))
CommonFields = (('FcstDays', int), ('FcstEpoch', int), ('FcstDate', str))

def TryShorten(term):
	if term in config.TermShortener:
		return config.TermShortener[term]
	elif len(term) > 12 and term[0:4] != 'http':
		logsupport.Logs.Log("Long term: " + term, severity=ConsoleWarning)
		config.TermShortener[term] = term  # only report once
		with open(config.exdir + '/termshortenlist.new', 'w') as f:
			json.dump(config.TermShortener, f, indent=4, separators=(',', ": "))
	return term



class WeatherItem(valuestore.StoreItem):
	def __init__(self, name, Store, vt=None):
		# self.MapInfo = mapinfo
		super(WeatherItem, self).__init__(name, None, store=Store, vt=vt)


class WeatherVals(valuestore.ValueStore):
	global WUcount

	def __init__(self, location, weathersource):
		self.fetchtime = 0

		super(WeatherVals, self).__init__(location, refreshinterval=60 * 30)
		self.ws = apixustore.APIXUWeatherSource(self, location)  # weathersource
		self.fetchcount = 0
		self.vars = {'Cond': OrderedDict(), 'Fcst': OrderedDict(), 'FcstDays': 0, 'FcstEpoch': 0, 'FcstDate': ''}
		self.failedfetch = False
		self.location = location
		self.name = location

		for fld, fldtype in CondFields:
			nm = ('Cond', fld)
			self.vars['Cond'][fld] = WeatherItem(nm, self, vt=fldtype)
		for fld, fldtype in FcstFields:
			nm = ('Fcst', fld)
			self.vars['Fcst'][fld] = WeatherItem(nm, self, vt=fldtype)
			self.vars['Fcst'][fld].Value = valuestore.StoreList(self.vars['Fcst'][fld])
		for fld, fldtype in CommonFields:
			self.vars[fld] = WeatherItem(fld, self, vt=fldtype)

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
		try:
			for n, fcst in self.vars['Fcst'].items():
				fcst.Value = valuestore.StoreList(fcst)
			self.ws.FetchWeather()  # todo return failure indicator?
		except Exception as e:
			print(repr(e))

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
