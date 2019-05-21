import time
from collections import OrderedDict

import pygame

import threading
import logsupport
from logsupport import ConsoleWarning
from stores import valuestore

'''
At the generic level defining the available fields seems reasonable; issue with the specific sources holding their mappings 
should they do it entirely inside their instance or use the mapinfo idea of the store; leaning toward the former since
no real reason to store the map in the store and it is only used to populate the store on a refresh

icon/icon cache - should different sources have different caches?  Different icons if multiple sources happen to get used?
'''

CondFields = (
	('Time', str), ('Location', str), ('Temp', float), ('Sky', str), ('Feels', float), ('WindDir', str),
	('WindMPH', float), ('WindGust', int), ('Sunrise', str), ('Sunset', str), ('Moonrise', str),
	('Moonset', str), ('Humidity', str), ('Icon', pygame.Surface), ('TimeEpoch', int), ('Age', None))
FcstFields = (('Day', str), ('High', float), ('Low', float), ('Sky', str), ('WindSpd', float), ('WindDir', str),
			  ('Icon', pygame.Surface))
CommonFields = (('FcstDays', int), ('FcstEpoch', int), ('FcstDate', str))


class WeatherItem(valuestore.StoreItem):
	def __init__(self, name, Store, vt=None):
		# self.MapInfo = mapinfo
		super(WeatherItem, self).__init__(name, None, store=Store, vt=vt)


class WeatherVals(valuestore.ValueStore):

	def __init__(self, location, weathersource, refresh):
		self.fetchtime = 0
		self.refreshinterval = 60 * refresh
		super(WeatherVals, self).__init__(location)
		self.ws = weathersource  # apixustore.APIXUWeatherSource(self, location)  #
		self.fetchcount = 0
		self.vars = {'Cond': OrderedDict(), 'Fcst': OrderedDict(), 'FcstDays': 0, 'FcstEpoch': 0, 'FcstDate': ''}
		self.location = location
		self.name = location
		self.ws.ConnectStore(self)
		self.DoingFetch = None  # thread that is handling a fetch or none
		self.ValidWeather = False  # status result
		self.ValidWeatherTime = 0
		self.startedfetch = 0
		self.Status = ('Weather not available', '(Initial fetch)')

		for fld, fldtype in CondFields:
			nm = ('Cond', fld)
			self.vars['Cond'][fld] = WeatherItem(nm, self, vt=fldtype)
		for fld, fldtype in FcstFields:
			nm = ('Fcst', fld)
			self.vars['Fcst'][fld] = WeatherItem(nm, self, vt=fldtype)
			self.vars['Fcst'][fld].Value = valuestore.StoreList(self.vars['Fcst'][fld])
		for fld, fldtype in CommonFields:
			self.vars[fld] = WeatherItem(fld, self, vt=fldtype)
		for n, fcst in self.vars['Fcst'].items():
			fcst.Value = valuestore.StoreList(fcst)

	def BlockRefresh(self):

		if self.fetchtime + self.refreshinterval > time.time():
			# have recent data
			return

		if self.DoingFetch is None:
			self.DoingFetch = threading.Thread(target=self.ws.FetchWeather, name='WFetch-{}'.format(self.name),
											   daemon=True)
			self.DoingFetch.start()
			logsupport.Logs.Log('Starting weather refresh for {}'.format(self.name))
			# self.Status = ("Fetching",)
			self.startedfetch = time.time()
		# no thread doing a fetch at this point - start one

		elif self.DoingFetch.is_alive():
			# fetch in progress
			if self.startedfetch + self.refreshinterval < time.time():
				# fetch ongoing too long - don't use stale data any longer
				self.Status = ('Weather not available', '(trying to fetch)')
				logsupport.Logs.Log('Weather fetch taking long time for: {}'.format(self.name),
									severity=logsupport.ConsoleWarning)
		# else just wait for next time
		else:
			# fetch completed
			logsupport.Logs.Log(
				'Weather fetch complete for {} at {} fetchedtime {}'.format(self.name, self.ValidWeatherTime,
																			self.vars['Cond']['Time'].Value))
			self.DoingFetch = None
			self.fetchtime = time.time()
			if self.ValidWeather:
				self.fetchcount += 1
				self.Status = ("Weather available",)
			else:
				self.Status = ("Weather not available", "(failed fetch)")
				logsupport.Logs.Log('Weather fetch failed for: {}'.format(self.name),
									severity=logsupport.ConsoleWarning)


	def GetVal(self, name, failok=False):
		# if config.BadWunderKey:
		#	return None
		self.BlockRefresh()
		return super(WeatherVals, self).GetVal(name)

	#	def SetVal(self,name,val,modifier=None):
	#		logsupport.Logs.Log("Setting weather item via SetVal unsupported: "+str(name),severity=ConsoleError)

	"""
	def dumpweatherresp(self, val, djson, tag, param):
		if config.sysStore.versionname in ('development', 'homerelease'):
			self.weathvalfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(val) + '\n=================')
			self.weathjsonfile.write(
				time.strftime('%H:%M:%S') + ' ' + tag + repr(param) + '\n' + repr(djson) + '\n=================')
			self.weathvalfile.flush()
			self.weathjsonfile.flush()
	"""
