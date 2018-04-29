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
import functools

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
		elif state == 'unavailable':
			return -1
		else:
			try:
				val = literal_eval(state)
			except ValueError:
				logsupport.Logs.Log('HA Hub reports unknown state: ',state,severity=ConsoleError, tb=False)
				return -1
	else:
		val = state
	if isinstance(val, float):
		if val.is_integer():
			return int(val)
	return val

class HAnode(object):
	def __init__(self, HAitem, **entries):
		self.entity_id = ''
		self.name = ''
		self.attributes = {}
		self.state = 0
		self.internalstate = -1 # 0 = off, non-zero = on, 1 - 255 = intensity
		self.__dict__.update(entries)
		if 'friendly_name' in self.attributes: self.FriendlyName = self.attributes['friendly_name']
		self.address = self.entity_id
		self.Hub = HAitem

	def Update(self,**ns):
		logsupport.Logs.Log("Internal error - update call on " + self.entity_id, severity=ConsoleError, tb=False)
		debug.debugPrint('HASSgeneral', 'Bad call to update: ' + repr(self))

class StatefulHAnode(HAnode):
	def __init__(self, HAitem, **entries):
		super(StatefulHAnode, self).__init__(HAitem, **entries)
		self.internalstate = _NormalizeState(self.state)

	def Update(self,**ns):
		self.__dict__.update(ns)
		self.internalstate = _NormalizeState(self.state)
		if self.internalstate == -1:
			logsupport.Logs.Log("Node "+self.name+" set unavailable")
		if config.DS.AS is not None:
			if self.Hub.name in config.DS.AS.HubInterestList:
				if self.entity_id in config.DS.AS.HubInterestList[self.Hub.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.starttime, "HA reports node change(screen): ",
									 "Key: ", self.Hub.Entities[self.entity_id].name)

					# noinspection PyArgumentList
					notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.Hub.name, node=self.entity_id, value=self.internalstate)
					pygame.fastevent.post(notice)

	def __str__(self):
		return str(self.name)+'::'+str(self.state)

class Automation(HAnode):
	def __init__(self, HAitem, d):
		super(Automation, self).__init__(HAitem, **d)
		self.Hub.Automations[self.entity_id] = self

	def RunProgram(self):
		ha.call_service(self.Hub.api, 'automation', 'trigger', {'entity_id': '{}'.format(self.entity_id)})
		debug.debugPrint('HASSgeneral', "Automation trigger sent to: ", self.entity_id)

class Group(StatefulHAnode):
	def __init__(self, HAitem, d):
		super(Group, self).__init__(HAitem, **d)
		self.members = self.attributes['entity_id']
		self.Hub.Groups[self.entity_id] = self

class Light(StatefulHAnode):
	def __init__(self, HAitem, d):
		super(Light, self).__init__(HAitem, **d)
		self.Hub.Lights[self.entity_id] = self
		if 'brightness' in self.attributes:
			self.internalstate = _NormalizeState(self.state, int(self.attributes['brightness']))

	def Update(self,**ns):
		super(Light, self).Update(**ns)
		if 'brightness' in self.attributes:
			self.internalstate = _NormalizeState(self.state, int(self.attributes['brightness']))

	def SendOnOffCommand(self, settoon, presstype):
		selcmd = ('turn_off', 'turn_on')
		ha.call_service(self.Hub.api, 'light', selcmd[settoon], {'entity_id': '{}'.format(self.entity_id)})
		debug.debugPrint('HASSgeneral', "Light OnOff sent: ", selcmd[settoon], ' to ', self.entity_id)

class Switch(StatefulHAnode):
	def __init__(self, HAitem, d):
		super(Switch, self).__init__(HAitem, **d)
		self.Hub.Switches[self.entity_id] = self

	def SendOnOffCommand(self, settoon, presstype):
		selcmd = ('turn_off', 'turn_on')
		ha.call_service(self.Hub.api, 'switch', selcmd[settoon], {'entity_id': '{}'.format(self.entity_id)})
		debug.debugPrint('HASSgeneral', "Switch OnOff sent: ", selcmd[settoon], ' to ', self.entity_id)

class Sensor(HAnode): # not stateful since it updates directly to store value
	def __init__(self, HAitem, d):
		super(Sensor, self).__init__(HAitem, **d)
		self.Hub.Sensors[self.entity_id] = self
		self.Hub.sensorstore.SetVal(self.entity_id, self.state)

	def _SetSensorAlert(self, p):
		self.Hub.sensorstore.AddAlert(self.entity_id,p)

	def Update(self,**ns):
		#super(Sensor,self).Update(**ns)
		self.attributes = ns['attributes']
		if 'state' in ns:
			self.Hub.sensorstore.SetVal(self.entity_id, ns['state'])

class Thermostat(HAnode): # not stateful since has much state info
	def __init__(self, HAitem, d):
		super(Thermostat, self).__init__(HAitem, **d)
		self.Hub.Thermostats[self.entity_id] = self
		try:
			self.curtemp = self.attributes['current_temperature']
			self.target_low = self.attributes['target_temp_low']
			self.target_high = self.attributes['target_temp_high']
			self.mode = self.attributes['operation_mode']
			self.fan = self.attributes['fan_mode']
			self.fanstates = self.attributes['fan_list']
			self.modelist = self.attributes['operation_list']
		except:
			pass
	'''
	The code for the Nest limits sensor updates to 270 seconds which makes the "current hvac state" pretty useless.
	Edit /srv/homeassistant/lib/python3.5/site-packages/homeassistant/components/nest.py line 132 (0.67):
	access_token_cache_file=access_token_cache_file,cache_ttl=30, to add the cache_ttl=30; also put a scan_interval:30 in the
	config file for sensor platform nest
	'''

	def Update(self,**ns):
		self.attributes = ns['attributes']
		self.curtemp = self.attributes['current_temperature']
		self.target_low = self.attributes['target_temp_low']
		self.target_high = self.attributes['target_temp_high']
		self.mode = self.attributes['operation_mode']
		self.fan = self.attributes['fan_mode']
		if config.DS.AS is not None:
			if self.Hub.name in config.DS.AS.HubInterestList:
				if self.entity_id in config.DS.AS.HubInterestList[self.Hub.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.starttime, "HA reports node change(screen): ",
									 "Key: ", self.Hub.Entities[self.entity_id].name)

					# noinspection PyArgumentList
					notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.Hub.name, node=self.entity_id, value=self.internalstate)
					pygame.fastevent.post(notice)

	def PushSetpoints(self,t_low,t_high):
		ha.call_service(self.Hub.api, 'climate', 'set_temperature', {'entity_id': '{}'.format(self.entity_id),'target_temp_high':str(t_high),'target_temp_low':str(t_low)})

	def GetThermInfo(self):
		return self.curtemp, self.target_low, self.target_high, self.HVAC_state.capitalize(), self.mode.capitalize(), self.fan.capitalize()

	def _HVACstatechange(self, storeitem, old, new, param, chgsource):
		self.HVAC_state = new
		if config.DS.AS is not None:
			if self.Hub.name in config.DS.AS.HubInterestList:
				if self.entity_id in config.DS.AS.HubInterestList[self.Hub.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.starttime, "HA Tstat reports node change(screen): ",
									 "Key: ", self.Hub.Entities[self.entity_id].name)

					# noinspection PyArgumentList
					notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.Hub.name, node=self.entity_id, value=new)
					pygame.fastevent.post(notice)

	def _connectsensors(self, HVACsensor):
		self.HVAC_state = HVACsensor.state
		HVACsensor._SetSensorAlert(functools.partial(self._HVACstatechange))

class ZWave(HAnode):
	def __init__(self, HAitem, d):
		super(ZWave, self).__init__(HAitem, **d)
		self.Hub.ZWaves[self.entity_id] = self

class HA(object):

	class HAClose(Exception):
		pass

	def GetNode(self, name, proxy = ''):
		try:
			return self.Entities[name], self.Entities[name]
		except:
			logsupport.Logs.Log("Attempting to access unknown object: "+ name + " in HA Hub: " + self.name, severity=ConsoleWarning)
			return None, None

	def GetProgram(self, name):
		try:
			return self.Automations[name]
		except KeyError:
			logsupport.Logs.Log("Attempt to access unknown program: " + name + " in HA Hub " + self.name, severity = ConsoleWarning)
			return None

	def GetCurrentStatus(self, MonitorNode):
		try:
			return MonitorNode.internalstate
		except:
			logsupport.Logs.Log("Error accessing current state in HA Hub: " + self.name + ' ' + repr(MonitorNode), severity=ConsoleWarning)
			return None

	def CheckStates(self):
		pass # todo add integrity check code

	def SetAlertWatch(self, node, alert):
		if node.address in self.AlertNodes:
			self.AlertNodes[node.address].append(alert)
		else:
			self.AlertNodes[node.address] = [alert]

	def StatesDump(self):
		for n, nd in self.Entities.items():
			print('Node(', type(nd),'): ', n, ' -> ', nd.internalstate, nd.state, type(nd.state))

	def PreRestartHAEvents(self):
		if isinstance(self.lasterror, ConnectionRefusedError):
			self.delaystart = 8 # HA probably restarting so give it a chance to get set up
		self.watchstarttime = time.time()
		self.HAnum += 1

	def PostRestartHAEvents(self):
		ha.call_service(self.api, 'logbook', 'log', {'message': 'Softconsole connected'})

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
				debug.debugPrint('HASSgeneral', 'WS Authorization OK, subscribing')
				ws.send(
					json.dumps({'id': self.HAnum, 'type': 'subscribe_events'}))  # , 'event_type': 'state_changed'}))
				return
			if mdecode['type'] == 'auth_required':
				debug.debugPrint('HASSgeneral', 'WS Authorization requested, sending')
				ws.send(json.dumps({"type": "auth", "api_password": self.password}))
				return
			if mdecode['type'] == 'auth_invalid':
				logsupport.Logs.Log("Invalid password for hub: "+self.name, severity=ConsoleError) # since already validate with API shouldn't get here
				return
			if mdecode['type'] in ('result', 'service_registered', 'zwave.network_complete', 'platform_discovered'):
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
				new = d['new_state']
				old = d['old_state']
				del d['new_state']
				del d['old_state']
				del d['entity_id']
				chgs, dels, adds = findDiff(old, new)
				if not ent in self.Entities and not ent in self.IgnoredEntities:
					# not an entitity type that is currently known
					debug.debugPrint('HASSgeneral', 'WS Stream item for unhandled entity type: ' + ent + ' Added: ' + str(adds) + ' Deleted: ' + str(dels) + ' Changed: ' + str(chgs))
					return
				if ent in self.IgnoredEntities:
					return
				debug.debugPrint('HASSchg', 'WS change: ' + ent + ' Added: ' + str(adds) + ' Deleted: ' + str(dels) + ' Changed: ' + str(chgs))
				#debug.debugPrint('HASSchg', 'New: ' + str(new))
				#debug.debugPrint('HASSchg', 'Old: ' + str(old))
				if ent in self.Entities:
					self.Entities[ent].Update(**new)

				if m['origin'] == 'LOCAL': del m['origin']
				if m['data'] == {}: del m['data']
				timefired = m['time_fired']
				del m['time_fired']
				if m != {}: debug.debugPrint('HASSchg', "Extras @ " + timefired+ ' : ' + m)
				if ent in self.AlertNodes:
					# alert node changed
					debug.debugPrint('DaemonCtl', 'HASS reports change(alert):', ent)
					for a in self.AlertNodes[ent]:
						logsupport.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
						# noinspection PyArgumentList
						notice = pygame.event.Event(config.DS.ISYAlert, node=ent, value=self.Entities[ent].internalstate,
													alert=a)
						pygame.fastevent.post(notice)
			elif m['event_type'] == 'system_log_event':
				logsupport.Logs.Log('Hub: '+self.name+' logged at level: '+d['level']+' Msg: '+d['message'])
			elif m['event_type'] in ('call_service', 'service_executed'):
				#debug.debugPrint('HASSchg', "Other expected event" + str(m))
				pass
			else:
				debug.debugPrint('HASSchg', "Unknown event: " + str(m))

		def on_error(qws, error):
			self.lasterror = error
			try:
				if error.args[0] == "'NoneType' object has no attribute 'connected'":
					# library bug workaround - get this error after close happens just ignore
					return
			except:
				pass
			logsupport.Logs.Log("Error in HA WS stream " + str(self.HAnum) + ':' + repr(error), severity=ConsoleError, tb=False)
			try:
				if error == TimeoutError: # Py3
					error = (errno.ETIMEDOUT,"Converted Py3 Timeout")
			except:
				pass
			try:
				if error == AttributeError:
					error = (errno.ETIMEDOUT,"Websock bug catch")
			except:
				pass
			qws.close()

		def on_close(qws, code, reason):
			"""

			:type qws: object
			"""
			self.delaystart = 20 # probably a HA server restart so give it some time
			logsupport.Logs.Log("HA ws stream " + str(self.HAnum) + " closed: " + str(code) + ' : ' + str(reason),
							severity=ConsoleError, tb=False)

		def on_open(qws):
			logsupport.Logs.Log("HA WS stream " + str(self.HAnum) + " opened")
			#if self.password != '':
			#	ws.send({"type": "auth","api_password": self.password})
			#ws.send(json.dumps({'id': self.HAnum, 'type': 'subscribe_events'})) #, 'event_type': 'state_changed'}))

		if self.delaystart > 0:
			logsupport.Logs.Log('HA thread delaying start for '+str(self.delaystart)+' seconds to allow HA to restart')
			time.sleep(self.delaystart)
		self.delaystart = 0
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
		try:
			ws.run_forever()
		except self.HAClose:
			self.delaystart = 20
			logsupport.Logs.Log("HA Event thread got close")
		logsupport.Logs.Log("HA Event Thread " + str(self.HAnum) + " exiting", severity=ConsoleError, tb=False)

	def __init__(self, hubname, addr, user, password):
		logsupport.Logs.Log("Creating Structure for Home Assistant hub: ", hubname)

		hadomains = {'group':Group, 'light':Light, 'switch':Switch, 'sensor':Sensor, 'automation':Automation, 'climate':Thermostat}
		haignoredomains = {'zwave':ZWave, 'sun':HAnode, 'notifications':HAnode}

		self.sensorstore = valuestore.NewValueStore(valuestore.ValueStore(hubname,itemtyp=valuestore.StoreItem))
		self.name = hubname
		self.addr = addr
		self.url = addr
		self.password = password
		if self.addr.startswith('http://'):
			self.wsurl = 'ws://' + self.addr[7:] + ':8123/api/websocket'
		elif self.addr.startswith('https://'):
			self.wsurl = 'wss://' + self.addr[8:] + ':8123/api/websocket'
		else:
			self.wsurl = 'ws://' +self.addr + ':8123/api/websocket'
		self.HAnum = 1
		self.watchstarttime = time.time()
		self.Entities = {}
		self.IgnoredEntities = {} # things we expect and do nothing with
		self.Domains = {}
		self.Groups = {}
		self.Lights = {}
		self.Switches = {}
		self.Sensors = {}
		self.ZWaves = {}
		self.Automations = {}
		self.Thermostats = {}
		self.Others = {}
		self.alertspeclist = {}  # if ever want auto alerts like ISY command vars they get put here
		self.AlertNodes = {}
		self.lasterror = None
		self.delaystart = 0
		if password != '':
			self.api = ha.API(self.url,password)
		else:
			self.api = ha.API(self.url)
		if ha.validate_api(self.api).value != 'ok':
			logsupport.Logs.Log('HA access failed validation', severity = ConsoleError, tb=False)
			raise ValueError
		logsupport.Logs.Log('HA access accepted for: '+self.name)

		self.config = ha.get_config(self.api)
		entities = ha.get_states(self.api)
		for e in entities:
			if e.domain not in self.Domains:
				self.Domains[e.domain] = {}
			p2 = dict(e.as_dict(),**{'domain':e.domain, 'name':e.name})

			if e.domain in hadomains:
				N = hadomains[e.domain](self, p2)
				self.Entities[e.entity_id] = N
			elif e.domain in haignoredomains:
				N = HAnode(self, **p2)
				self.IgnoredEntities[e.entity_id] = N
			else:
				N = HAnode(self,**p2)
				self.Others[e.entity_id] = N

			self.Domains[e.domain][e.object_id] = N

		for n, T in self.Thermostats.items():
			tname = n.split('.')[1]
			tsensor = self.Sensors['sensor.'+tname+'_thermostat_hvac_state']
			T._connectsensors(tsensor)

		services = ha.get_services(self.api)
		#listeners = ha.get_event_listeners(self.api)
		logsupport.Logs.Log("Processed "+str(len(self.Entities))+" total entities")
		logsupport.Logs.Log("    Lights: " + str(len(self.Lights)) + " Switches: " + str(len(self.Switches)) + " Sensors: " + str(len(self.Sensors)) +
							" Automations: " + str(len(self.Automations)))
		threadmanager.SetUpHelperThread(self.name, self.HAevents, prerestart=self.PreRestartHAEvents, postrestart=self.PostRestartHAEvents)
		logsupport.Logs.Log("Finished creating Structure for Home Assistant hub: ", self.name)




