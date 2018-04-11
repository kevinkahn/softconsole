import config
import homeassistant.remote as ha
import json
import time
import errno
import debug
import pygame
import websocket
import threadmanager
import logsupport
from stores import valuestore
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
import pprint

from ast import literal_eval
def _NormalizeState(state, brightness=None):
	if isinstance(state, str):
		if state == 'on':
			if brightness != None:
				return brightness
			else:
				return 255
		elif state == 'off':
			return 0
		else:
			try:
				val = literal_eval(state)
			except:
				return state
	else:
		val = state
	if isinstance(val, float):
		if val.is_integer():
			return int(val)
	return val

class HAnode(object):
	def __init__(self, HAitem, **entries):
		self.entity_id = ''
		self.state = 0
		self.name = ''
		self.attributes = {}
		self.internalstate = 0 # 0 = off, non-zero = on, 1 - 255 = intensity
		self.__dict__.update(entries)
		self.internalstate = _NormalizeState(self.state)
		self.address = self.entity_id
		self.HA = HAitem

	def Update(self,**ns):
		self.__dict__.update(ns)
		self.internalstate = _NormalizeState(self.state)
		if config.DS.AS is not None:
			if self.HA.name in config.DS.AS.HubInterestList:
				if self.entity_id in config.DS.AS.HubInterestList[self.HA.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.starttime, "HA reports node change(screen): ",
									 "Key: ", self.HA.Entities[self.entity_id].name)

					# noinspection PyArgumentList
					notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.HA.name, node=self.entity_id, value=self.internalstate)
					pygame.fastevent.post(notice)

	def __str__(self):
		return str(self.name)+'::'+str(self.state)

class Group(HAnode):
	def __init__(self, HAitem, d):
		super(Group, self).__init__(HAitem, **d)
		self.members = self.attributes['entity_id']
		self.HA.Groups[self.entity_id] = self
		self.HA.Entities[self.entity_id] = self

class Light(HAnode):
	def __init__(self, HAitem, d):
		super(Light, self).__init__(HAitem, **d)
		self.HA.Lights[self.entity_id] = self
		self.HA.Entities[self.entity_id] = self
		if 'brightness' in self.attributes:
			self.internalstate = _NormalizeState(self.state, int(self.attributes['brightness']))

	def Update(self,**ns):
		super(Light, self).Update(**ns)
		if 'brightness' in self.attributes:
			self.internalstate = _NormalizeState(self.state, int(self.attributes['brightness']))

	def SendCommand(self): # todo
		pass

class Switch(HAnode):
	def __init__(self, HAitem, d):
		super(Switch, self).__init__(HAitem, **d)
		self.HA.Switches[self.entity_id] = self
		self.HA.Entities[self.entity_id] = self

	def SendCommand(self):
		pass

class Sensor(HAnode):
	def __init__(self, HAitem, d):
		super(Sensor, self).__init__(HAitem, **d)
		self.HA.Sensors[self.entity_id] = self
		self.HA.Entities[self.entity_id] = self
		self.HA.sensorstore.SetVal(self.entity_id, self.state)

	def Update(self,**ns):
		super(Sensor,self).Update(**ns)
		self.HA.sensorstore.SetVal(self.entity_id, self.state)

class ZWave(HAnode):
	def __init__(self, HAitem, d):
		super(ZWave, self).__init__(HAitem, **d)
		self.HA.ZWaves[self.entity_id] = self

class HA(object):

	def GetNode(self, name, proxy):
		return self.Entities[name], self.Entities[name]  # todo needs not found logic

	def GetCurrentStatus(self, MonitorNode):
		return MonitorNode.internalstate

	def StatesDump(self):
		for n, nd in self.Entities.items():
			print('Node(', type(nd),'): ', n, ' -> ', nd.internalstate, nd.state, type(nd.state))

	def PreRestartHAEvents(self):
		self.watchstarttime = time.time()
		self.HAnum += 1
		'''
		try:
			if self.lasterror[0] == errno.ENETUNREACH:
				# likely home network down so wait a bit
				logsupport.Logs.Log('Wait for likely router reboot or down', severity=ConsoleError)
				# todo overlay a screen delay message so locked up console is understood
				time.sleep(120)
			elif self.lasterror[0] == errno.ETIMEDOUT:
				logsupport.Logs.Log('Timeout on WS - delay to allow possible ISY or router reboot',severity=ConsoleError, tb=False)
				logsupport.Logs.Log('Original error report: '+repr(self.lasterror))
				time.sleep(15)
				# todo - bug in websocket that results in attribute error for errno.WSEACONNECTIONREFUSED check
			else:
				logsupport.Logs.Log('Unexpected error on WS stream: ',repr(self.lasterror), severity=ConsoleError, tb=False)
		except Exception as e:
			logsupport.Logs.Log('PreRestartQH internal error ',e)
		'''

	def HAevents(self):

		def findDiff(d1, d2):
			chg = {}
			dels = {}
			adds = {}
			for k in d2.keys():
				if not k in d1:
					adds[k] = d2[k]
			for k in d1.keys():
				if k in d2:
					if isinstance(d1[k], dict):
						c, d, a = findDiff(d1[k], d2[k])
						if c != {}: chg[k] = c
						if d != {}: dels[k] = d
						if a != {}: adds[k] = a
						#chg[k], dels[k], adds[k] = findDiff(d1[k], d2[k])
					else:
						if d1[k] != d2[k]:
							chg[k] = d2[k]
				else:
					dels[k] = d1[k]
			return chg, dels, adds

		def on_message(qws, message):
			mdecode = json.loads(message)
			if mdecode['type'] == 'auth_ok':
				debug.debugPrint('HASSgeneral', 'WS Authorization OK')
				return
			if mdecode['type'] != 'event':
				debug.debugPrint('HASSgeneral', 'Non event seen on WS stream: ', str(mdecode))
				return
			m = mdecode['event']
			del mdecode['event']
			d = m['data']
			if m['event_type'] == 'state_changed':
				del m['event_type']
				ent = d['entity_id']
				if not ent in self.Entities: # not an entitity type that is currently handled
					debug.debugPrint('HASSgeneral', 'WS Steam item for unhandled entity type: ',ent)
					return
				new = d['new_state']
				old = d['old_state']
				del d['new_state']
				del d['old_state']
				del d['entity_id']
				chgs, dels, adds = findDiff(old, new)
				debug.debugPrint('HASSchg', 'WS change: ' + ent + ' Added: ' + str(adds) + ' Deleted: ' + str(dels) + ' Changed: ' + str(chgs))
				debug.debugPrint('HASSchg', 'New: ' + str(new))
				debug.debugPrint('HASSchg', 'Old: ' + str(old))
				if ent in self.Sensors:
					self.Entities[ent].Update(**new)
				else:
					self.Entities[ent].Update(**new)
				if m['origin'] == 'LOCAL': del m['origin']
				if m['data'] == {}: del m['data']
				timefired = m['time_fired']
				del m['time_fired']
				if m != {}: debug.debugPrint('HASSchg', "Extras @ " + timefired+ ' : ' + m)
			else:
				debug.debugPrint('HASSchg', "Not a state change: " + str(m))

		def on_error(qws, error):
			logsupport.Logs.Log("Error in HA WS stream " + str(self.HAnum) + ':' + repr(error), severity=ConsoleError, tb=False)
			try:
				if error == TimeoutError: # Py3
					error = (errno.ETIMEDOUT,"Converted Py3 Timeout")
			except:
				pass
			try:
				if error == AttributeError: # Py2 websocket debug todo
					error = (errno.ETIMEDOUT,"Websock bug catch")
			except:
				pass
			self.lasterror = error
			qws.close()

		def on_close(qws, code, reason):
			logsupport.Logs.Log("HA ws stream " + str(self.HAnum) + " closed: " + str(code) + ' : ' + str(reason),
							severity=ConsoleError, tb=False)

		def on_open(qws):
			logsupport.Logs.Log("HA WS stream " + str(self.HAnum) + " opened")
			ws.send(json.dumps({'id': self.HAnum, 'type': 'subscribe_events', 'event_type': 'state_changed'}))

		websocket.setdefaulttimeout(30)
		while True:
			try:
				#websocket.enableTrace(True)
				ws = websocket.WebSocketApp(self.wsurl, on_message=on_message,
											on_error=on_error,
											on_close=on_close, on_open=on_open)
				break
			except AttributeError as e:
				logsupport.Logs.Log("Problem starting HA WS handler - retrying: ", repr(e), severity = ConsoleWarning)
		ws.run_forever()
		logsupport.Logs.Log("HA Event Thread " + str(self.HAnum) + " exiting", severity=ConsoleError)

	def __init__(self, hubname, addr, user, password):
		logsupport.Logs.Log("Creating Structure for Home Assistant hub: ", hubname)

		hadomains = {'group':Group, 'light':Light, 'switch':Switch, 'sensor':Sensor, 'zwave':ZWave}
		self.sensorstore = valuestore.NewValueStore(valuestore.ValueStore(hubname,itemtyp=valuestore.StoreItem))
		self.name = hubname
		self.addr = addr
		self.url = addr #+ '/api/states'
		if self.addr.startswith('http://'):
			self.wsurl = 'ws://' + self.addr[7:] + ':8123/api/websocket'
		elif self.addr.startswith('https://'):
			self.wsurl = 'wss://' + self.addr[8:] + ':8123/api/websocket'
		else:
			self.wsurl = 'ws://' +self.addr + ':8123/api/websocket'
		self.HAnum = 1
		self.watchstarttime = time.time()
		self.Entities = {}
		self.Domains = {}
		self.Groups = {}
		self.Lights = {}
		self.Switches = {}
		self.Sensors = {}
		self.ZWaves = {}
		self.Others = {}
		self.alertspeclist = {}  # todo - test
		if password != '':
			self.api = ha.API(self.url,password)
		else:
			self.api = ha.API(self.url)
		if ha.validate_api(self.api).value != 'ok':
			logsupport.Logs.Log('HA access failed validation', severity = ConsoleError)
			return

		self.config = ha.get_config(self.api)
		entities = ha.get_states(self.api)
		for e in entities:
			if e.domain not in self.Domains:
				self.Domains[e.domain] = {}
			p2 = dict(e.as_dict())
			p2['domain'] = e.domain
			p2['name'] = e.name
			if e.domain in hadomains:
				N = hadomains[e.domain](self, p2)
			else:
				N = HAnode(self,**p2)
				self.Others[e.entity_id] = N

			self.Domains[e.domain][e.object_id] = N
		threadmanager.SetUpHelperThread(self.name, self.HAevents, prerestart=self.PreRestartHAEvents)
		logsupport.Logs.Log("Finished creating Structure for Home Assistant hub: ", self.name)

		self.services = ha.get_services(self.api)
		for i in self.services:
			print(i['domain']+':')
			for sn, s in i['services'].items():
				print('   '+sn+': '+str(s['description']))
				for fn,f in s['fields'].items():
					print('           '+fn+': '+str(f))




