import time
from collections import OrderedDict
from dataclasses import dataclass
from random import random

import pygame
import json
import queue
from utils import threadmanager
import config
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail

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

CacheUser = {}  # index by provider to dict that indexes by location that points to instance
Provs = {}
WeatherFetcherNotInit = True  # thread that does the fetching
MQTTqueue = queue.Queue()
MINWAITBETWEENTRIES = 1800  # 30 minutes
NetMinimalFetchGap = 600


@dataclass
class CacheEntry:
	location: str
	fetchingnode: str
	fetchtime: float
	fetchcount: int
	weatherinfo: dict


WeatherCache = {}


def RegisterFetcher(provider, locname, instance, provmod):
	if provider not in CacheUser: CacheUser[provider] = {}
	CacheUser[provider][locname] = instance
	Provs[provider] = provmod

def LocationOnNode(prov, locname):
	return prov in CacheUser and locname in CacheUser[prov]


def MQTTWeatherUpdate(provider, locname, wpayload):
	if locname == 'fetched':
		age = time.time() - wpayload['time']
		if age > 5:
			config.ptf('Old fetched message {}'.format(age))
			return
		Provs[provider].lastfetch = wpayload['time']
		# MQTTqueue.put((provider, locname, wpayload))
		config.ptf('Fetched at: {}: {}'.format(time.strftime('%H:%M', time.localtime(wpayload['time'])), wpayload))
		if wpayload['success'] == 'both':
			config.ptf2('Fetch by {} of {} at {}'.format(wpayload['fetchingnode'], wpayload['location'],
														 time.strftime('%H:%M', time.localtime(wpayload['time']))))
		else:
			config.ptf2('Fail by {} of {} at {} because {}'.format(wpayload['fetchingnode'], wpayload['location'],
																   time.strftime('%H:%M',
																				 time.localtime(wpayload['time'])),
																   wpayload['success']))
			Provs[provider].RLHit()
		return
	elif locname == 'readytofetch':
		age = time.time() - wpayload['time']
		if age > 5:
			config.ptf('Old readytofetch message {}'.format(age))
			return
		config.ptf('Ready msg from {} for {} {}'.format(wpayload['fetchingnode'], wpayload['location'],
														Provs[provider].readytofetch))
		Provs[provider].readytofetch.add(wpayload['fetchingnode'])
		return
	elif locname == 'fetching':
		age = time.time() - wpayload['time']
		if age > 5:
			config.ptf('Old fetching message {}'.format(age))
			return
		config.ptf('Fetching msg from {} for {} {}'.format(wpayload['fetchingnode'], wpayload['location'],
														   Provs[provider].readytofetch))
		Provs[provider].readytofetch = set()  # someone beat me too it
		return

	if not LocationOnNode(provider, locname):
		# print('Unused location {} {}'.format(provider, locname))
		return  # broadcast for location this node doesn't use

	if not provider in WeatherCache: WeatherCache[provider] = {}

	winfo = wpayload['weatherinfo']
	# print('MQTTcall {} {}'.format(provider, locname))
	if isinstance(winfo, str):
		if winfo == 'CACHEPURGE':
			logsupport.Logs.Log(
				'Purge weatherbit cache for {}:{} issued by {}'.format(provider, locname, wpayload['fetchingnode']))
			if locname in WeatherCache[provider]:
				del WeatherCache[provider][locname]
				logsupport.Logs.Log('Removed entry for {}'.format(locname))
	elif (locname not in WeatherCache[provider]) or (
			WeatherCache[provider][locname].fetchtime != wpayload['fetchtime']):
		# curtime = WeatherCache[provider][locname].fetchtime if locname in WeatherCache[provider] else 0
		# print('Actual MQTT update for {} current {} incoming {}'.format(locname, curtime, wpayload['fetchtime']))
		WeatherCache[provider][locname] = CacheEntry(wpayload['location'], wpayload['fetchingnode'],
													 wpayload['fetchtime'], wpayload['fetchcount'], winfo)
		MQTTqueue.put((provider, locname))
	else:
		pass
	#print('Dupe MQTT update for {} times {}'.format(locname, WeatherCache[provider][locname].fetchtime))

def HandleMQTTItem(item):
	if len(item) == 2:  # normal cache update
		prov, locname = item
		CacheUser[prov][locname].LoadWeather(WeatherCache[prov][locname].weatherinfo,
											 WeatherCache[prov][locname].fetchtime,
											 fn=WeatherCache[prov][locname].fetchingnode)
	else:
		config.ptf('Should not get this!!! {}'.format(item))

def HandleMQTTinputs(timeout):
	if timeout <= 0:
		# print('Weather loop neg timeout {}'.format(timeout))
		timeout = .1
	elif timeout > 10800:
		# print('Weather loop timeout too long {}'.format(timeout))
		timeout = 10800
	try:
		mqttitem = MQTTqueue.get(timeout=timeout)
		HandleMQTTItem(mqttitem)
		while True:
			mqttitem = MQTTqueue.get(block=False)
			HandleMQTTItem(mqttitem)

	except queue.Empty:
		return


def DoWeatherFetches():
	time.sleep(1)
	HandleMQTTinputs(1)  # delay at startup to allow MQTT cache fills to happen
	MinimalFetchGap = NetMinimalFetchGap if config.mqttavailable else 0
	fetchcnt = sum(len(v) for v in CacheUser.values())
	while True:
		for provnm, prov in CacheUser.items():
			for instnm, inst in prov.items():
				store = inst.thisStore
				now = time.time()
				if time.time() - Provs[provnm].lastfetch < MinimalFetchGap:  # minimal interval between fetches
					config.ptf('Too recent fetch {}'.format(time.time() - Provs[provnm].lastfetch))
					break
				if (now - store.ValidWeatherTime < store.refreshinterval) or (now - store.failedfetchtime < 120):
					# have recent data or a recent failure
					tmp = store.ValidWeatherTime + store.refreshinterval
					config.ptf(
						'Not yet time for {} ({})'.format(instnm, time.strftime('%H:%M', time.localtime(tmp))))
					continue
				config.ptf('Prep local fetch for {}'.format(instnm))
				Provs[provnm].readytofetch.add(config.sysStore.hostname)
				pld = {'fetchingnode': config.sysStore.hostname, 'time': time.time(),
					   'location': instnm}
				if config.mqttavailable:
					config.MQTTBroker.Publish('Weatherbit/readytofetch', node='all/weather2',
											  payload=json.dumps(pld))
				logsupport.Logs.Log(
					'Try weather refresh: {} age: {} {} {} {} {}'.format(store.name, (now - store.ValidWeatherTime),
																		 store.ValidWeatherTime, store.refreshinterval,
																		 store.failedfetchtime, now),
					severity=ConsoleDetail)
				config.ptf('Presleep set for {}: {}'.format(store.name, Provs[provnm].readytofetch))
				if config.mqttavailable: time.sleep(10)  # if net fetching in use wait to see if others doing work
				config.ptf('Fetch set for {}: {}'.format(store.name, Provs[provnm].readytofetch))
				if config.sysStore.hostname not in Provs[provnm].readytofetch:
					# some other node already started a fetch
					config.ptf('Another node started fetch {} ({})'.format(store.name, Provs[provnm].readytofetch))
					break
				else:
					selectee = sorted(Provs[provnm].readytofetch)[0]
					Provs[provnm].readytofetch = set()
					config.ptf('Selected {} to fetch {}'.format(selectee, store.name))
					if selectee != config.sysStore.hostname:
						Provs[
							provnm].lastfetch = time.time()  # wait at least this ammount expect actual fetch message to reset
						break
					elif Provs[provnm].lastfetch + MinimalFetchGap > time.time():
						config.ptf("Race to fetch {} lastfetch: {} Stand down".format(store.name,
																					  time.strftime('%H:%M',
																									time.localtime(
																										Provs[
																											provnm].lastfetch))))
						break

				pld = {'fetchingnode': config.sysStore.hostname, 'time': time.time(),
					   'location': instnm}
				if config.mqttavailable:
					config.MQTTBroker.Publish('Weatherbit/fetching', node='all/weather2',
											  payload=json.dumps(pld))
				else:
					fetchcnt -= 1
					if fetchcnt <= 0: MinimalFetchGap = NetMinimalFetchGap

				config.ptf('Do local fetch for {}'.format(instnm))

				store.CurFetchGood = False
				store.Status = ("Fetching",)
				store.startedfetch = time.time()
				winfo = inst.FetchWeather()
				weathertime = time.time()

				if store.CurFetchGood:
					store.failedfetchcount = 0
					store.fetchcount += 1
					store.Status = ("Weather available",)
				else:
					store.failedfetchcount += 1
					if time.time() > store.ValidWeatherTime + 3 * store.refreshinterval:  # use old weather for up to 3 intervals
						# really have stale data
						store.ValidWeather = False
						if store.StatusDetail is None:
							store.Status = ("Weather not available", "(failed fetch)")
							logsupport.Logs.Log(
								'{} weather fetch failures for: {} No weather for {} seconds'.format(
									store.failedfetchcount,
									store.name, time.time() - store.ValidWeatherTime), severity=ConsoleWarning)
						else:
							store.Status = ("Weather not available", store.StatusDetail)
						store.failedfetchtime = time.time()
					else:
						logsupport.Logs.Log(
							'Failed fetch for {} number {} using old weather'.format(store.name,
																					 store.failedfetchcount))
					break  # don't try to load bad weather

				if not inst.LoadWeather(winfo, weathertime, fn='self'):
					# print('Load for {} time {}'.format(store.name, weathertime))
					if config.mqttavailable:  # force bad fetch out of the cache
						config.MQTTBroker.Publish('{}/{}'.format(provnm, inst.thisStoreName), node='all/weather2',
												  payload=json.dumps(
													  {'weatherinfo': 'CACHEPURGE', 'location': inst.location,
													   'fetchingnode': config.sysStore.hostname}))
						config.MQTTBroker.Publish('{}/{}'.format(provnm, inst.thisStoreName), node='all/weather2',
												  payload=None, retain=True)
						logsupport.Logs.Log('Force cache clear for {}({})'.format(inst.location, inst.thisStoreName))
				else:
					if not provnm in WeatherCache: WeatherCache[provnm] = {}
					WeatherCache[provnm][inst.thisStoreName] = CacheEntry(inst.location, 'self',
																		  weathertime, inst.actualfetch.Values()[0],
																		  winfo)
					if winfo is not None:
						bcst = {'weatherinfo': winfo, 'location': inst.thisStoreName,
								'fetchtime': weathertime,
								'fetchcount': inst.actualfetch.Values()[0],
								'fetchingnode': config.sysStore.hostname}
						if config.mqttavailable:
							config.MQTTBroker.Publish('{}/{}'.format(provnm, inst.thisStoreName), node='all/weather2',
													  payload=json.dumps(bcst), retain=True)
				break

		now = time.time()
		nextfetch = now + 60 * 60 * 24  # 1 day - just need a big starting value to compute next fetch time
		config.ptf(
			'Compute next fetch at {} ({})'.format(time.strftime('%H:%M', time.localtime(nextfetch)),
												   Provs['Weatherbit'].readytofetch))

		for provnm, prov in CacheUser.items():
			mindelay = time.time() - Provs[provnm].lastfetch if time.time() - Provs[
				provnm].lastfetch < MinimalFetchGap else 0
			for instnm, inst in prov.items():
				store = inst.thisStore
				now = time.time()
				nextfetchforloc = max(store.ValidWeatherTime + store.refreshinterval,
									  store.failedfetchtime + MINWAITBETWEENTRIES)
				nextfetch = min(nextfetchforloc, nextfetch)
				config.ptf('Next {} in {} Val {} Intrvl {} Next {}'.format(instnm, int(nextfetchforloc - now),
																		   time.strftime('%H:%M', time.localtime(
																			   store.ValidWeatherTime)),
																		   store.refreshinterval,
																		   time.strftime('%H:%M', time.localtime(
																			   nextfetchforloc))))
			now = time.time()
			if mindelay + now > nextfetch:
				config.ptf('Override next fetch timing for gapping was: {} now: {}'.format(
					time.strftime('%c', time.localtime(nextfetch)),
					time.strftime('%c', time.localtime(mindelay + now))))
				nextfetch = mindelay + now
		config.ptf('Next fetch at {}'.format(time.strftime('%c', time.localtime(nextfetch))))
		HandleMQTTinputs(nextfetch - now)
		config.ptf('Back from HandleInput at {}'.format(time.strftime('%c', time.localtime(time.time()))))


class WeatherItem(valuestore.StoreItem):
	def __init__(self, name, Store, vt=None):
		# self.MapInfo = mapinfo
		super(WeatherItem, self).__init__(name, None, store=Store, vt=vt)


class WeatherVals(valuestore.ValueStore):

	def __init__(self, location, weathersource, refresh):
		global WeatherFetcherNotInit
		if WeatherFetcherNotInit:
			# create the fetcher thread
			threadmanager.SetUpHelperThread('WeatherFetcher', DoWeatherFetches)
			WeatherFetcherNotInit = False

		self.sourcespecset = []
		self.failedfetchcount = 0
		self.failedfetchtime = 0
		self.refreshinterval = 60 * refresh
		if config.mqttavailable:  # randomize refresh intervals
			self.refreshinterval += int((random() * .05) * self.refreshinterval)
		super().__init__(location)
		self.ws = weathersource
		self.fetchcount = 0
		self.vars = {'Cond': OrderedDict(), 'Fcst': OrderedDict(), 'FcstDays': 0, 'FcstEpoch': 0, 'FcstDate': ''}
		self.location = location
		self.name = location
		self.ws.ConnectStore(self)
		self.DoingFetch = None  # thread that is handling a fetch or none
		self.ValidWeather = False  # status result
		self.StatusDetail = None
		self.ValidWeatherTime = 0
		self.CurFetchGood = False
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

	def InitSourceSpecificFields(self, fcst):
		if self.sourcespecset: return self.sourcespecset  # only do once
		for fld, val in fcst.items():
			if not isinstance(val, dict):
				nm = ('Fcst', fld)
				self.vars['Fcst'][fld] = WeatherItem(nm, self, vt=type(val))
				self.vars['Fcst'][fld].Value = valuestore.StoreList(self.vars['Fcst'][fld])
				self.sourcespecset.append(fld)
		return self.sourcespecset
