
import pygame
import time
from stores import valuestore
from collections import OrderedDict
import logsupport
from logsupport import ConsoleWarning


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
		self.failedfetch = False
		self.location = location
		self.name = location
		self.ws.ConnectStore(self)

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

		try:
			for n, fcst in self.vars['Fcst'].items():
				fcst.Value = valuestore.StoreList(fcst)
			successcode = self.ws.FetchWeather()  # code for success(0), failure/redo(1) failure delay(2) fail perm(3)
			if successcode != 0: self.failedfetch = True
		except Exception as e:
			logsupport.Logs.Log('Error processing forecast for: ', self.name, ' ', repr(e), severity=ConsoleWarning)
			self.failedfetch = True

	def GetVal(self, name, failok=False):
		# if config.BadWunderKey:
		#	return None
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
