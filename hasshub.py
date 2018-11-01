import config
import haremote as ha
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
import eventlist

def stringtonumeric(v):
	if not isinstance(v,str):
		return v
	try:
		f = float(v)
		return f
	except:
		pass
	try:
		i = int(v)
		return i
	except:
		pass
	return v

from ast import literal_eval
def _NormalizeState(state, brightness=None):
	if isinstance(state, str):
		if state == 'on':
			if brightness is not None:
				return brightness
			else:
				return 255
		elif state == 'off':
			return 0
		elif state in ['unavailable', 'unknown']:
			return -1
		elif state in ['paused', 'playing']:
			return 255
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
		# just updates last triggered etc.
		self.__dict__.update(ns)

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

class Script(HAnode):
	def __init__(self, HAitem, d):
		super(Script, self).__init__(HAitem, **d)
		self.Hub.Scripts[self.entity_id] = self

	def RunProgram(self):
		ha.call_service(self.Hub.api, 'script', self.object_id)
		debug.debugPrint('HASSgeneral', "Script execute sent to: script.", self.object_id)

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
		self.Hub.sensorstore.SetVal(self.entity_id, stringtonumeric(self.state))

	def _SetSensorAlert(self, p):
		self.Hub.sensorstore.AddAlert(self.entity_id,p)

	def Update(self,**ns):
		#super(Sensor,self).Update(**ns)
		if 'attributes' in ns: self.attributes = ns['attributes']
		if 'state' in ns and ns['state'] != 'unknown':
			self.Hub.sensorstore.SetVal(self.entity_id, stringtonumeric(ns['state']))

class BinarySensor(HAnode):
	def __init__(self, HAitem, d):
		super(BinarySensor,self).__init__(HAitem, **d)
		self.Hub.BinarySensors[self.entity_id] = self
		if self.state not in ('on','off'):
			logsupport.Logs.Log("Odd Binary sensor initial value: ", self.entity_id, ':', self.state, severity=ConsoleWarning)
		self.Hub.sensorstore.SetVal(self.entity_id, self.state == 'on')

	def _SetSensorAlert(self, p):
		self.Hub.sensorstore.AddAlert(self.entity_id,p)

	def Update(self,**ns):
		#super(Sensor,self).Update(**ns)
		if 'attributes' in ns: self.attributes = ns['attributes']
		if 'state' in ns:
			if ns['state'] == 'on':
				st = True
			elif ns['state'] == 'off':
				st = False
			else:
				st = False
				logsupport.Logs.Log("Bad Binary sensor value: ", self.entity_id, ':', ns['state'], severity=ConsoleWarning)
			self.Hub.sensorstore.SetVal(self.entity_id, st)


class MediaPlayer(HAnode):
	def __init__(self, HAitem, d):
		super(MediaPlayer, self).__init__(HAitem, **d)
		self.Hub.MediaPlayers[self.entity_id] = self
		self.Sonos = False
		if 'sonos_group' in self.attributes:
			self.Sonos = True
			self.internalstate = 255
			self.sonos_group = self.attributes['sonos_group']
			self.source_list = self.attributes['source_list']
			self.muted = self.attributes['is_volume_muted']
			self.volume = self.attributes['volume_level']
			self.song = self.attributes['media_title'] if 'media_title' in self.attributes else ''
			self.artist = self.attributes['media_artist'] if 'media_artist' in self.attributes else ''
			self.album = self.attributes['media_album_name'] if 'media_album_name' in self.attributes else ''

	def Update(self, **ns):
		oldst = self.state
		if 'attributes' in ns: self.attributes = ns['attributes']
		self.state = ns['state']
		newst = _NormalizeState(self.state)
		if newst != self.internalstate:
			logsupport.Logs.Log("Mediaplayer state change: ", self.Hub.Entities[self.entity_id].name, ' was ',
								self.internalstate, ' now ', newst, '(', self.state, ')', severity=ConsoleDetail)
			self.internalstate = newst

		if self.Sonos:
			if self.internalstate == -1:  # unavailable
				logsupport.Logs.Log("Sonos room went unavailable: ", self.Hub.Entities[self.entity_id].name)
				return
			else:
				if oldst == -1:
					logsupport.Logs.Log("Sonos room became available: ", self.Hub.Entities[self.entity_id].name)
				self.sonos_group = self.attributes['sonos_group']
				if 'source_list' in self.attributes: self.source_list = self.attributes['source_list']
				self.muted = self.attributes['is_volume_muted'] if 'is_volume_muted' in self.attributes else 'True'
				self.volume = self.attributes['volume_level'] if 'volume_level' in self.attributes else 0
				self.song = self.attributes['media_title'] if 'media_title' in self.attributes else ''
				self.artist = self.attributes['media_artist'] if 'media_artist' in self.attributes else ''
				self.album = self.attributes['media_album_name'] if 'media_album_name' in self.attributes else ''

			if config.DS.AS is not None:
				if self.Hub.name in config.DS.AS.HubInterestList:
					if self.entity_id in config.DS.AS.HubInterestList[self.Hub.name]:
						debug.debugPrint('DaemonCtl', time.time() - config.starttime,
										 "HA reports node change(screen): ",
										 "Key: ", self.Hub.Entities[self.entity_id].name)

						# noinspection PyArgumentList
						notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
													value=self.internalstate)
						pygame.fastevent.post(notice)

	def Join(self, master, roomname):
		ha.call_service(self.Hub.api, 'media_player', 'sonos_join', {'master': '{}'.format(master),
																	 'entity_id': '{}'.format(roomname)})

	def UnJoin(self, roomname):
		ha.call_service(self.Hub.api, 'media_player', 'sonos_unjoin', {'entity_id': '{}'.format(roomname)})

	def VolumeUpDown(self, roomname, up):
		updown = 'volume_up' if up >= 1 else 'volume_down'
		ha.call_service(self.Hub.api, 'media_player', updown, {'entity_id': '{}'.format(roomname)})
		ha.call_service(self.Hub.api, 'media_player', 'media_play', {'entity_id': '{}'.format(roomname)})

	def Mute(self, roomname, domute):
		# todo - do I pass the boolean or translate it to string true/false
		ha.call_service(self.Hub.api, 'media_player', 'volume_mute', {'entity_id': '{}'.format(roomname),
																	  'is_volume_muted': domute})
		if not domute:  # implicitly start playing if unmuting in case source was stopped
			ha.call_service(self.Hub.api, 'media_player', 'media_play', {'entity_id': '{}'.format(roomname)})

	def Source(self, roomname, sourcename):
		ha.call_service(self.Hub.api, 'media_player', 'select_source', {'entity_id': '{}'.format(roomname),
																		'source': '{}'.format(sourcename)})

class Thermostat(HAnode): # not stateful since has much state info
	# todo update since state now in pushed stream
	def __init__(self, HAitem, d):
		super(Thermostat, self).__init__(HAitem, **d)
		self.Hub.Thermostats[self.entity_id] = self
		# noinspection PyBroadException
		try:
			self.temperature = self.attributes['temperature']
			self.curtemp = self.attributes['current_temperature']
			self.target_low = self.attributes['target_temp_low']
			self.target_high = self.attributes['target_temp_high']
			self.mode = self.attributes['operation_mode']
			self.fan = self.attributes['fan_mode']
			self.fanstates = self.attributes['fan_list']
			self.modelist = self.attributes['operation_list']
		except:
			pass

	def ErrorFakeChange(self):
		# noinspection PyArgumentList
		notice = pygame.event.Event(config.DS.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
									value=self.internalstate)
		pygame.fastevent.post(notice)

	def Update(self,**ns):
		if 'attributes' in ns: self.attributes = ns['attributes']
		self.temperature = self.attributes['temperature']
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
		# todo with nest pushing setpoint while not in auto seems to be a no-op and so doesn't cause an event
		ha.call_service(self.Hub.api, 'climate', 'set_temperature', {'entity_id': '{}'.format(self.entity_id),'target_temp_high':str(t_high),'target_temp_low':str(t_low)})
		# should push a fake event a few seconds into the future to handle error cases todo
		E = eventlist.ProcEventItem(id(self), 'setpointnoresp', self.ErrorFakeChange)
		config.DS.Tasks.AddTask(E, 5) # if HA doesn't respond clear the tentative values after short wait

	def GetThermInfo(self):
		if self.target_low is not None:
			return self.curtemp, self.target_low, self.target_high, self.HVAC_state, self.mode, self.fan
		else:
			return self.curtemp, self.temperature, self.temperature, self.HVAC_state, self.mode, self.fan

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
		# noinspection PyProtectedMember
		HVACsensor._SetSensorAlert(functools.partial(self._HVACstatechange))

	def GetModeInfo(self):
		return self.modelist, self.fanstates

	def PushFanState(self,mode):
		ha.call_service(self.Hub.api, 'climate', 'set_fan_mode',
						{'entity_id': '{}'.format(self.entity_id), 'fan_mode': mode})

	def PushMode(self,mode):
		# noinspection PyBroadException
		try:
			ha.call_service(self.Hub.api, 'climate', 'set_operation_mode',
						{'entity_id': '{}'.format(self.entity_id), 'operation_mode': mode})
		except:
			pass

class ZWave(HAnode):
	def __init__(self, HAitem, d):
		super(ZWave, self).__init__(HAitem, **d)
		self.Hub.ZWaves[self.entity_id] = self

class HA(object):

	class HAClose(Exception):
		pass

	def GetNode(self, name, proxy = ''):
		# noinspection PyBroadException
		try:
			return self.Entities[name], self.Entities[name]
		except:
			logsupport.Logs.Log("Attempting to access unknown object: "+ name + " in HA Hub: " + self.name, severity=ConsoleWarning)
			return None, None

	def GetProgram(self, name):
		try:
			return self.Automations['automation.' + name]
		except:
			pass

		try:
			return self.Scripts['script.' + name]
		except KeyError:
			logsupport.Logs.Log("Attempt to access unknown program: " + name + " in HA Hub " + self.name, severity = ConsoleWarning)
			return None

	def GetCurrentStatus(self, MonitorNode):
		# noinspection PyBroadException
		try:
			return MonitorNode.internalstate
		except:
			logsupport.Logs.Log("Error accessing current state in HA Hub: " + self.name + ' ' + repr(MonitorNode), severity=ConsoleWarning)
			return None

	def CheckStates(self):
		try:
			for n, s in self.Sensors.items():
				cacheval = self.sensorstore.GetVal(s.entity_id)
				e = ha.get_state(self.api, s.entity_id)
				if e is None:
					actualval = '*unknown*'
				else:
					actualval = e.state
				if cacheval != actualval:
					logsupport.Logs.Log('Sensor value anomoly('+self.name+'): Cached: '+str(cacheval)+ ' Actual: '+str(actualval),severity=ConsoleWarning)
					self.sensorstore.SetVal(s.entity_id, actualval)
		except:
			logsupport.Logs.Log('Sensor value check did not complete',severity=ConsoleWarning)

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
			self.delaystart = 152  # HA probably restarting so give it a chance to get set up
		self.watchstarttime = time.time()
		self.HAnum += 1

	def PostStartHAEvents(self):
		try:
			ha.call_service(self.api, 'logbook', 'log',
							{'name': 'Softconsole', 'message': config.hostname + ' connected'})
		except ha.HomeAssistantError:
			logsupport.Logs.Log(self.name + " not responding to service call after restart", severity=ConsoleWarning)

	def HAevents(self):

		def findDiff(d1, d2):
			chg = {}
			dels = {}
			adds = {}
			old = {} if d1 is None else d1
			new = {} if d2 is None else d2
			for k in new.keys():
				if not k in old:
					adds[k] = new[k]
			for k in old.keys():
				if k in new:
					if isinstance(old[k], dict):
						c, d, a = findDiff(old[k], new[k])
						if c != {}: chg[k] = c
						if d != {}: dels[k] = d
						if a != {}: adds[k] = a
						#chg[k], dels[k], adds[k] = findDiff(d1[k], d2[k])
					else:
						if old[k] != new[k]:
							chg[k] = new[k]
				else:
					dels[k] = old[k]
			return chg, dels, adds

		def on_message(qws, message):
			try:
				self.msgcount += 1
				# if self.msgcount <4: logsupport.Logs.Log(self.name + " Message "+str(self.msgcount)+':'+ repr(message))
				try:
					mdecode = json.loads(message)
				except:
					logsupport.Logs.Log("HA event with bad message: ", message, severity=ConsoleError)
					return
				if mdecode['type'] == 'auth_ok':
					debug.debugPrint('HASSgeneral', 'WS Authorization OK, subscribing')
					self.ws.send(
						json.dumps(
							{'id': self.HAnum, 'type': 'subscribe_events'}))  # , 'event_type': 'state_changed'}))
					return
				if mdecode['type'] == 'auth_required':
					debug.debugPrint('HASSgeneral', 'WS Authorization requested, sending')
					self.ws.send(json.dumps({"type": "auth", "access_token": self.password}))
					return
				if mdecode['type'] == 'auth_invalid':
					logsupport.Logs.Log("Invalid password for hub: " + self.name + '(' + str(self.msgcount) + ')',
										repr(message),
										severity=ConsoleError,
										tb=False)  # since already validate with API shouldn't get here
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
						debug.debugPrint('HASSgeneral', self.name,
										 ' WS Stream item for unhandled entity type: ' + ent + ' Added: ' + str(
											 adds) + ' Deleted: ' + str(dels) + ' Changed: ' + str(chgs))
						logsupport.Logs.Log("New entity since startup seen from ", self.name, ": ", ent)
						self.IgnoredEntities[ent] = None
						return
					if ent in self.IgnoredEntities:
						return
					debug.debugPrint('HASSchg', 'WS change: ' + ent + ' Added: ' + str(adds) + ' Deleted: ' + str(
						dels) + ' Changed: ' + str(chgs))
					# debug.debugPrint('HASSchg', 'New: ' + str(new))
					# debug.debugPrint('HASSchg', 'Old: ' + str(old))
					if ent in self.Entities and new is not None:
						self.Entities[ent].Update(**new)

					if m['origin'] == 'LOCAL': del m['origin']
					if m['data'] == {}: del m['data']
					timefired = m['time_fired']
					del m['time_fired']
					if m != {}: debug.debugPrint('HASSchg', "Extras @ " + timefired + ' : ' + repr(m))
					if ent in self.AlertNodes:
						# alert node changed
						debug.debugPrint('DaemonCtl', 'HASS reports change(alert):', ent)
						for a in self.AlertNodes[ent]:
							logsupport.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
							# noinspection PyArgumentList
							notice = pygame.event.Event(config.DS.ISYAlert, node=ent,  hub=self.name,
														value=self.Entities[ent].internalstate,
														alert=a)
							pygame.fastevent.post(notice)
				elif m['event_type'] == 'system_log_event':
					logsupport.Logs.Log('Hub: ' + self.name + ' logged at level: ' + d['level'] + ' Msg: ' + d[
						'message'])  # todo fake an event for Nest error?
				elif m['event_type'] in (
				'call_service', 'service_executed', 'zwave.scene_activated', 'logbook_entry', 'service_registered',
				'service_removed',
				'config_entry_discovered', 'persistent_notifications_updated'):
					# debug.debugPrint('HASSchg', "Other expected event" + str(m))
					pass
				else:
					debug.debugPrint('HASSgeneral', "Unknown event: " + str(m))
					logsupport.Logs.Log("Previously unknown event seen: " + str(m))
			except Exception as e:
				logsupport.Logs.Log("Exception handling HA message: ", repr(e), repr(message), severity=ConsoleWarning)

		def on_error(qws, error):
			self.lasterror = error
			# noinspection PyBroadException
			try:
				if error.args[0] == "'NoneType' object has no attribute 'connected'":
					# library bug workaround - get this error after close happens just ignore
					logsupport.Logs.Log("WS lib workaround hit (1)")  # todo remove
					return
			except:
				pass
				logsupport.Logs.Log("WS lib workaround hit (2)")  # todo remove
			if isinstance(error, websocket.WebSocketConnectionClosedException):
				self.delaystart = 20  # server or network business?
				logsupport.Logs.Log(self.name + " closed WS stream " + str(self.HAnum) + "; attempt to reopen",
									severity=ConsoleWarning)
			elif isinstance(error, ConnectionRefusedError):
				self.delaystart = 149  # likely initial message after attempt to reconnect - server still down
				logsupport.Logs.Log(self.name + " WS socket refused connection", severity=ConsoleWarning)
			elif isinstance(error, TimeoutError):
				self.delaystart = 150  # likely router reboot delay
				logsupport.Logs.Log(self.name + " WS socket timed out", severity=ConsoleWarning)
			elif isinstance(error, OSError):
				if error[0] == errno.ENETUNREACH:
					self.delaystart = 151  # likely router reboot delay
					logsupport.Logs.Log(self.name + " WS network down", severity=ConsoleWarning)
				else:
					self.delaystart = 21  # likely router reboot delay
					logsupport.Logs.Log(self.hubname + ' WS OS error', repr(error), severity=ConsoleError, tb=False)
			else:
				self.delaystart = 15
				logsupport.Logs.Log(self.name + ": Unknown Error in WS stream " + str(self.HAnum) + ':' + repr(error),
									severity=ConsoleWarning)
			try:
				if isinstance(error, AttributeError):
					# error = (errno.ETIMEDOUT,"Websock bug catch")
					logsupport.Logs.Log("WS lib workaround hit (3)")  # todo remove
			except:
				pass
			qws.close()

		def on_close(qws, code, reason):
			"""
			:param reason:  str
			:param code: int
			:type qws: websocket.WebSocketApp
			"""
			if self.delaystart == 0:
				self.delaystart = 30  # if no other delay set just delay a bit
			logsupport.Logs.Log(
				self.name + " WS stream " + str(self.HAnum) + " closed: " + str(code) + ' : ' + str(reason),
				severity=ConsoleWarning, tb=False)
			raise self.HAClose

		def on_open(qws):
			logsupport.Logs.Log(self.name + " WS stream " + str(self.HAnum) + " opened for " + self.name)
			#if self.password != '':
			#	ws.send({"type": "auth","api_password": self.password})
			#ws.send(json.dumps({'id': self.HAnum, 'type': 'subscribe_events'})) #, 'event_type': 'state_changed'}))

		if self.delaystart > 0:
			logsupport.Logs.Log(
				self.name + ' thread delaying start for ' + str(self.delaystart) + ' seconds to allow HA to restart')
			time.sleep(self.delaystart)
		self.delaystart = 0
		websocket.setdefaulttimeout(30)
		while True:
			try:
				#websocket.enableTrace(True)
				self.ws = websocket.WebSocketApp(self.wsurl, on_message=on_message,
											on_error=on_error,
											on_close=on_close, on_open=on_open, header=self.api._headers)
				self.msgcount = 0
				break
			except AttributeError as e:
				logsupport.Logs.Log(self.name + ": Problem starting WS handler - retrying: ", repr(e),
									severity=ConsoleWarning)
		try:
			self.ws.run_forever(ping_timeout=999)
		except self.HAClose:
			logsupport.Logs.Log(self.name + " Event thread got close")
		logsupport.Logs.Log(self.name + " Event Thread " + str(self.HAnum) + " exiting", severity=ConsoleWarning,
							tb=False)

	def __init__(self, hubname, addr, user, password):
		logsupport.Logs.Log("Creating Structure for Home Assistant hub: ", hubname)

		hadomains = {'group': Group, 'light': Light, 'switch': Switch, 'sensor': Sensor, 'automation': Automation,
					 'climate': Thermostat, 'media_player': MediaPlayer, 'binary_sensor': BinarySensor, 'script': Script}
		haignoredomains = {'zwave': ZWave, 'sun': HAnode, 'notifications': HAnode, 'persistent_notification': HAnode}
		haignoreandskipdomains = ('history_graph','updater')

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
		self.ws = None  # websocket client instance
		self.msgcount = 0
		self.watchstarttime = time.time()
		self.Entities = {}
		self.IgnoredEntities = {} # things we expect and do nothing with
		self.Domains = {}
		self.Groups = {}
		self.Lights = {}
		self.Switches = {}
		self.Sensors = {}
		self.BinarySensors = {}
		self.ZWaves = {}
		self.Automations = {}
		self.Scripts = {}
		self.Thermostats = {}
		self.MediaPlayers = {}
		self.Others = {}
		self.alertspeclist = {}  # if ever want auto alerts like ISY command vars they get put here
		self.AlertNodes = {}
		self.lasterror = None
		self.delaystart = 0
		if password != '':
			self.api = ha.API(self.url,password)
		else:
			self.api = ha.API(self.url)
		for i in range(9):
			hassok = False
			if ha.validate_api(self.api).value != 'ok':  # todo check not connected response and give different message
				logsupport.Logs.Log(self.name + ' access failed validation - retrying', severity=ConsoleWarning)
				time.sleep(
					4 * i)  # if this is a system boot or whole house power hit it may take a while for HA to be ready so stretch the wait out
			else:
				hassok = True
				break
		if hassok:
			logsupport.Logs.Log('HA access accepted for: ' + self.name)
		else:
			logsupport.Logs.Log('HA access failed multiple trys for: ' + self.name, severity=ConsoleError, tb=False)
			raise ValueError

		# self.config = ha.get_config(self.api)
		entities = ha.get_states(self.api)
		for e in entities:
			if e.domain not in self.Domains:
				self.Domains[e.domain] = {}
			p2 = dict(e.as_dict(),**{'domain':e.domain, 'name':e.name, 'object_id':e.object_id})

			if e.domain in hadomains:
				N = hadomains[e.domain](self, p2)
				self.Entities[e.entity_id] = N
			elif e.domain in haignoredomains:
				N = HAnode(self, **p2)
				self.IgnoredEntities[e.entity_id] = N
			elif e.domain in haignoreandskipdomains:
				N = None
				pass # totally ignore these
			else:
				N = HAnode(self,**p2)
				self.Others[e.entity_id] = N
				logsupport.Logs.Log(self.name + ': Uncatagorized HA domain type: ', e.domain, ' for entity: ',
									e.entity_id)
				debug.debugPrint('HASSgeneral', "Unhandled node type: ", e.object_id)

			self.Domains[e.domain][e.object_id] = N

		for n, T in self.Thermostats.items():
			tname = n.split('.')[1]
			tsensor = self.Sensors['sensor.'+tname+'_thermostat_hvac_state']
			T._connectsensors(tsensor)

		services = ha.get_services(self.api)
		#listeners = ha.get_event_listeners(self.api)
		logsupport.Logs.Log(self.name + " Processed " + str(len(self.Entities)) + " total entities")
		logsupport.Logs.Log("    Lights: " + str(len(self.Lights)) + " Switches: " + str(len(self.Switches)) +
							" Sensors: " + str(len(self.Sensors)) + " BinarySensors: " + str(len(self.BinarySensors)) +
							" Automations: " + str(len(self.Automations)))
		threadmanager.SetUpHelperThread(self.name, self.HAevents, prerestart=self.PreRestartHAEvents, poststart=self.PostStartHAEvents, postrestart=self.PostStartHAEvents)
		logsupport.Logs.Log("Finished creating Structure for Home Assistant hub: ", self.name)




