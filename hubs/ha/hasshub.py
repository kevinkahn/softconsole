import errno
import json
import time
import os
import importlib

import websocket

import config
import debug
import screens.__screens as screens
from . import haremote as ha
import historybuffer
import hw
import logsupport
import threadmanager
from controlevents import CEvent, PostEvent, ConsoleEvent
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from stores import valuestore

AddIgnoredDomain = None  # gets filled in by ignore to avoid import loop

ignoredeventtypes = ('system_log_event', 'call_service', 'service_executed', 'logbook_entry', 'timer_out_of_sync',
					 'persistent_notifications_updated', 'zwave.network_complete', 'zwave.scene_activated',
					 'zwave.network_ready', 'automation_triggered', 'script_started')

def stringtonumeric(v):
	if not isinstance(v, str):
		return v
	# noinspection PyBroadException
	try:
		f = float(v)
		return f
	except:
		pass
	# noinspection PyBroadException
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
				logsupport.Logs.Log('HA Hub reports unknown state: ', state, severity=ConsoleError, tb=False)
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
		self.internalstate = -1  # 0 = off, non-zero = on, 1 - 255 = intensity
		self.__dict__.update(entries)
		if 'friendly_name' in self.attributes: self.FriendlyName = self.attributes['friendly_name']
		self.address = self.entity_id
		self.Hub = HAitem
		self.domname = 'unset'

	def LogNewEntity(self, newstate):
		logsupport.Logs.Log(
			"New entity since startup seen from {}: {} (Domain: {}) New: {}".format(
				self.Hub.name, self.entity_id, self.domname, repr(newstate)))

	def Update(self, **ns):
		# just updates last triggered etc.
		self.__dict__.update(ns)


class StatefulHAnode(HAnode):
	def __init__(self, HAitem, **entries):
		super(StatefulHAnode, self).__init__(HAitem, **entries)
		self.internalstate = _NormalizeState(self.state)

	def Update(self, **ns):
		self.__dict__.update(ns)
		oldstate = self.internalstate
		self.internalstate = _NormalizeState(self.state)
		if self.internalstate == -1:
			logsupport.Logs.Log("Node " + self.name + " set unavailable", severity=ConsoleDetail)
		if oldstate == -1 and self.internalstate != -1:
			logsupport.Logs.Log("Node " + self.name + " became available (" + str(self.internalstate) + ")",
								severity=ConsoleDetail)
		if screens.DS.AS is not None:
			if self.Hub.name in screens.DS.AS.HubInterestList:
				if self.entity_id in screens.DS.AS.HubInterestList[self.Hub.name]:
					debug.debugPrint('DaemonCtl', time.time() - config.sysStore.ConsoleStartTime, "HA reports node change(screen): ",
									 "Key: ", self.Hub.Entities[self.entity_id].name)
					PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub=self.Hub.name, node=self.entity_id,
										   value=self.internalstate))

	def __str__(self):
		return str(self.name) + '::' + str(self.state)



class Indirector(object):
	# used as a placeholder if config names a node that isn't in HA - allows for late discovery of HA nodes
	# in GetNode if name doesn't exist create one of these and return it
	# in the stream handling if new entity is seen create the node and plug it in here
	# Indirector has a field Undefined that gets set False once a node is linked.
	def __init__(self, Hub, name):
		self.Undefined = True
		self.realnode = None
		self.Hub = Hub
		self.impliedname = name
		Hub.Indirectors[name] = self
		logsupport.Logs.Log('Creating indirector for missing {} node {}'.format(Hub.name,name),severity=ConsoleWarning)

	def SetRealNode(self, node):
		self.realnode = node
		self.Undefined = False
		logsupport.Logs.Log('Real node appeared for hub {} node {}'.format(self.Hub.name,self.impliedname))

	def __getattr__(self, name):
		# noinspection PyBroadException
		try:
			return getattr(self.realnode, name)
		except:
			if name == 'name': return self.impliedname
			if name == 'address': return self.impliedname
			logsupport.Logs.Log('Attempt to access uncompleted indirector for hub {} node {}'.format(self.Hub.name,self.impliedname),severity=ConsoleWarning)


hadomains = {}


def RegisterDomain(domainname, domainmodule):
	hadomains[domainname] = domainmodule

class HA(object):
	class HAClose(Exception):
		pass

	# noinspection PyUnusedLocal
	def GetNode(self, name, proxy=''):
		# noinspection PyBroadException
		try:
			return self.Entities[name], self.Entities[name]
		except:
			logsupport.Logs.Log("Attempting to access unknown object: " + name + " in HA Hub: " + self.name,
								severity=ConsoleWarning)
			I = Indirector(self, name)
			return I, I

	def GetProgram(self, name):
		try:
			return self.DomainEntityReg['automation']['automation.' + name]
		except KeyError:
			pass

		try:
			return self.DomainEntityReg['script']['script.' + name]
		except KeyError:
			logsupport.Logs.Log("Attempt to access unknown program: " + name + " in HA Hub " + self.name,
								severity=ConsoleWarning)
			return None

	def GetCurrentStatus(self, MonitorNode):
		# noinspection PyBroadException
		try:
			return MonitorNode.internalstate
		except:
			#todo part of handling late discovered nodes
			logsupport.Logs.Log("Error accessing current state in HA Hub: " + self.name + ' ' + repr(MonitorNode),
								severity=ConsoleWarning)
			return None

	def CheckStates(self):
		# noinspection PyBroadException
		try:
			for n, s in self.DomainEntityReg['sensor'].items():
				cacheval = self.sensorstore.GetVal(s.entity_id)
				e = ha.get_state(self.api, s.entity_id)
				if e is None:
					actualval = '*unknown*'
				else:
					actualval = e.state
				if cacheval != type(cacheval)(actualval):
					logsupport.Logs.Log(
						'Sensor value anomoly(' + self.name + '): Cached: ' + str(cacheval) + ' Actual: ' + str(
							actualval), severity=ConsoleWarning, hb=True)
					logsupport.DevPrint('Check anomoly for {}: cache: {} actual: {}'.format(self.name,cacheval,actualval))
					self.sensorstore.SetVal(s.entity_id, actualval)
		except Exception as E:
			logsupport.Logs.Log('Sensor value check did not complete: {}'.format(repr(E)), severity=ConsoleWarning)

	def SetAlertWatch(self, node, alert):
		if node.address in self.AlertNodes:
			self.AlertNodes[node.address].append(alert)
		else:
			self.AlertNodes[node.address] = [alert]

	def StatesDump(self):
		with open('/home/pi/Console/{}Dump.txt'.format(self.name), mode='w') as f:
			for n, nd in self.Entities.items():
				f.write('Node({}) {}: -> {} {} {}\n'.format(type(nd), n, nd.internalstate, nd.state, type(nd.state)))

	def HACheckThread(self):
		if self.haconnectstate != "Running":
			logsupport.Logs.Log("{} failed thread check; state: {}".format(self.name, self.haconnectstate),
								severity=ConsoleWarning)
			return False
		return True

	def PreRestartHAEvents(self):
		self.haconnectstate = "Prestart"
		self.config = ha.get_config(self.api)
		if self.config == {}:
			# HA not responding yet - long delay
			self.delaystart = 180
		if isinstance(self.lasterror, ConnectionRefusedError):
			self.delaystart = 152  # HA probably restarting so give it a chance to get set up
		self.watchstarttime = time.time()
		self.HAnum += 1

	def PostStartHAEvents(self):
		while self.haconnectstate == "Delaying":
			time.sleep(1)
		i = 0
		while self.haconnectstate != "Running":
			i += 1
			if i > 60:
				logsupport.Logs.Log("{} not running after thread start ({})".format(self.name, self.haconnectstate),
									severity=ConsoleError)
			time.sleep(1)
			i = 0
		try:
			ha.call_service(self.api, 'logbook', 'log',
							{'name': 'Softconsole', 'message': hw.hostname + ' connected'})
		except ha.HomeAssistantError:
			logsupport.Logs.Log(self.name + " not responding to service call after restart", severity=ConsoleWarning)

	def RegisterEntity(self, domain, entity, item):
		if domain in self.DomainEntityReg:
			if entity in self.DomainEntityReg[domain]:
				logsupport.Logs.Log('Duplicate entity reported in {} hub {}: {}'.format(self.name, domain, entity))
			else:
				self.DomainEntityReg[domain][entity] = item
		else:
			self.DomainEntityReg[domain] = {entity: item}


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
					# chg[k], dels[k], adds[k] = findDiff(d1[k], d2[k])
					else:
						if old[k] != new[k]:
							chg[k] = new[k]
				else:
					dels[k] = old[k]
			return chg, dels, adds

		# noinspection PyUnusedLocal
		def on_message(qws, message):
			loopstart = time.time()
			self.HB.Entry(repr(message))
			try:
				self.msgcount += 1
				# if self.msgcount <4: logsupport.Logs.Log(self.name + " Message "+str(self.msgcount)+':'+ repr(message))
				# noinspection PyBroadException
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
				if mdecode['type'] == 'platform_discovered':  # todo temp
					logsupport.Logs.Log('{} discovered platform: {}'.format(self.name, message))
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
					dom, nm = ent.split('.')
					new = d['new_state']
					old = d['old_state']
					del d['new_state']
					del d['old_state']
					del d['entity_id']
					chgs, dels, adds = findDiff(old, new)

					if not ent in self.Entities:
						# not an entitity type that is currently known
						debug.debugPrint('HASSgeneral', self.name,
										 ' WS Stream item for unhandled entity: ' + ent + ' Added: ' + str(
											 adds) + ' Deleted: ' + str(dels) + ' Changed: ' + str(chgs))
						if dom in self.addibledomains:
							p2 = dict(new, **{'domain': dom, 'name': nm, 'object_id': ent})
							N = hadomains[dom](self, p2)
							self.Entities[ent] = N
							N.AddPlayer()  # todo specific to media player?
						if ent in self.Indirectors: # expected node finally showed up
							p2 = dict(new, **{'domain': dom,
											  'name': new['attributes']['friendly_name'] if 'friendly_name' in new[
												  'attributes'] else nm.replace('_', ' '), 'object_id': ent})
							if dom in hadomains:
								N = hadomains[dom](self, p2)
								self.Indirectors[ent].SetRealNode(N)
								del self.Indirectors[ent]
								self.Entities[ent] = N
								logsupport.Logs.Log('Indirector from {} for {} resolved'.format(self.name, ent))
							else:
								del self.Indirectors[ent]
								logsupport.Logs.Log('Indirector in {} for {} not for a supported domain {}'.format(self.name,ent,dom))
						else:
							if old != None:
								logsupport.Logs.Log(
									"New entity seen with 'old' state from {}: {} (Domain: {}) (Old: {}  New: {})".format(
									self.name, ent, dom, repr(old), repr(new)))
							p2 = dict(new, **{'domain': dom, 'name': nm, 'object_id': ent})
							if dom not in hadomains:
								AddIgnoredDomain(dom)
								logsupport.Logs.Log('New domain seen from {}: {}'.format(self.name, dom))

							if config.sysStore.versionname in ('development', 'homerelease'):
								with open('{}/Console/{}-entities'.format(config.sysStore.HomeDir, self.name),
										  'a') as f:
									print('New ignored entity in {}: {} {}'.format(self.name, dom, ent), file=f)

							N = hadomains[dom](self, p2)
							N.LogNewEntity(repr(new))
							self.Entities[ent] = N  # only report once
						return
					elif new is not None:
						self.Entities[ent].Update(**new)

					self.HB.Entry(
						'Change to {} Added: {} Deleted: {} Changed: {}'.format(ent, str(adds), str(dels), str(chgs)))

					if m['origin'] == 'LOCAL': del m['origin']
					if m['data'] == {}: del m['data']
					timefired = m['time_fired']
					del m['time_fired']
					if m != {}: self.HB.Entry('Extras @ {}: {}'.format(timefired, repr(m)))
					if ent in self.AlertNodes:
						# alert node changed
						self.HB.Entry('Report change to: {}'.format(ent))
						for a in self.AlertNodes[ent]:
							logsupport.Logs.Log("Node alert fired: " + str(a), severity=ConsoleDetail)
							# noinspection PyArgumentList
							PostEvent(ConsoleEvent(CEvent.ISYAlert, node=ent, hub=self.name,
												   value=self.Entities[ent].internalstate, alert=a))
				elif m['event_type'] == 'system_log_event':
					logsupport.Logs.Log('Hub: ' + self.name + ' logged at level: ' + d['level'] + ' Msg: ' + d[
						'message'])
				elif m['event_type'] == 'config_entry_discovered':
					logsupport.Logs.Log("{} config entry discovered: {}".format(self.name, message))
				elif m['event_type'] == 'service_registered':  # fix plus add service removed
					d = m['data']
					if d['domain'] not in self.knownservices:
						self.knownservices[d['domain']] = {}
					if d['service'] not in self.knownservices[d['domain']]:
						self.knownservices[d['domain']][d['service']] = d['service']
					logsupport.Logs.Log(
						"{} has new service: {}".format(self.name, message),
						severity=ConsoleDetail)  # all the zwave services todo
				elif m['event_type'] not in ignoredeventtypes:
					# debug.debugPrint('HASSchg', "Other expected event" + str(m))
					logsupport.Logs.Log('{} Event: {}'.format(self.name, message))
					debug.debugPrint('HASSgeneral', "Unknown event: " + str(m))
			except Exception as E:
				logsupport.Logs.Log("Exception handling HA message: ", repr(E), repr(message), severity=ConsoleWarning,
									tb=True)
			loopend = time.time()
			self.HB.Entry('Processing time: {} Done: {}'.format(loopend - loopstart, repr(message)))
			time.sleep(.1)  # force thread to give up processor to allow response to time events

		# self.HB.Entry('Gave up control for: {}'.format(time.time() - loopend))

		def on_error(qws, error):
			self.HB.Entry('ERROR: ' + repr(error))
			self.lasterror = error
			# noinspection PyBroadException
			try:
				if error.args[0] == "'NoneType' object has no attribute 'connected'":
					# library bug workaround - get this error after close happens just ignore
					logsupport.Logs.Log("WS lib workaround hit (1)")  # tempdel
					return
			except:
				pass
				logsupport.Logs.Log("WS lib workaround hit (2)")  # tempdel
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
				if error.errno == errno.ENETUNREACH:
					self.delaystart = 151  # likely router reboot delay
					logsupport.Logs.Log(self.name + " WS network down", severity=ConsoleWarning)
				else:
					self.delaystart = 21  # likely router reboot delay
					logsupport.Logs.Log(self.name + ' WS OS error', repr(error), severity=ConsoleError, tb=False)
			else:
				self.delaystart = 15
				logsupport.Logs.Log(self.name + ": Unknown Error in WS stream " + str(self.HAnum) + ':' + repr(error),
									severity=ConsoleWarning)
			# noinspection PyBroadException
			try:
				if isinstance(error, AttributeError):
					# error = (errno.ETIMEDOUT,"Websock bug catch")
					logsupport.Logs.Log("WS lib workaround hit (3)")  # tempdel
			except:
				pass
			self.haconnectstate = "Failed"
			qws.close()

		# noinspection PyUnusedLocal
		def on_close(qws, code, reason):
			"""
			:param reason:  str
			:param code: int
			:type qws: websocket.WebSocketApp
			"""
			self.HB.Entry('Close')
			if self.delaystart == 0:
				self.delaystart = 30  # if no other delay set just delay a bit
			logsupport.Logs.Log(
				self.name + " WS stream " + str(self.HAnum) + " closed: " + str(code) + ' : ' + str(reason),
				severity=ConsoleWarning, tb=False, hb=True)
			if self.haconnectstate != "Failed": self.haconnectstate = "Closed"

		# raise self.HAClose

		# noinspection PyUnusedLocal
		def on_open(qws):
			self.HB.Entry('Open')
			logsupport.Logs.Log(self.name + ": WS stream " + str(self.HAnum) + " opened")
			self.haconnectstate = "Running"

		# if self.password != '':
		#	ws.send({"type": "auth","api_password": self.password})
		# ws.send(json.dumps({'id': self.HAnum, 'type': 'subscribe_events'})) #, 'event_type': 'state_changed'}))

		if self.delaystart > 0:
			logsupport.Logs.Log(
				self.name + ' thread delaying start for ' + str(self.delaystart) + ' seconds to allow HA to restart')
			self.haconnectstate = "Delaying"
			time.sleep(self.delaystart)
		self.delaystart = 0
		self.haconnectstate = "Starting"
		websocket.setdefaulttimeout(30)
		while True:
			try:
				# websocket.enableTrace(True)
				self.ws = websocket.WebSocketApp(self.wsurl, on_message=on_message,
												 on_error=on_error,
												 on_close=on_close, on_open=on_open, header=self.api._headers)
				self.msgcount = 0
				break
			except AttributeError as e:
				logsupport.Logs.Log(self.name + ": Problem starting WS handler - retrying: ", repr(e),
									severity=ConsoleWarning)
		try:
			self.haconnectstate = "Running"
			self.ws.run_forever(ping_timeout=999)
		except self.HAClose:  # todo this can't happen
			logsupport.Logs.Log(self.name + " Event thread got close")
		logsupport.Logs.Log(self.name + " Event Thread " + str(self.HAnum) + " exiting", severity=ConsoleWarning,
							tb=False)
		if self.haconnectstate not in ("Failed", "Closed"): self.haconnectstate = "Exited"

	# noinspection PyUnusedLocal
	def __init__(self, hubname, addr, user, password):
		self.DomainEntityReg = {}
		self.knownservices = []
		self.HB = historybuffer.HistoryBuffer(40, hubname)
		logsupport.Logs.Log("{}: Creating structure for Home Assistant hub at {}".format(hubname, addr))

		self.dyndomains = {}
		for domainimpl in os.listdir(os.getcwd() + '/hubs/ha/domains'):
			if '__' not in domainimpl:
				splitname = os.path.splitext(domainimpl)
				if splitname[1] == '.py':
					self.dyndomains[splitname[0]] = importlib.import_module('hubs.ha.domains.' + splitname[0])

		for dom in hadomains:
			self.DomainEntityReg[dom] = {}

		self.addibledomains = {}  # {'media_player': MediaPlayer} todo resolve how to add things

		self.sensorstore = valuestore.NewValueStore(valuestore.ValueStore(hubname, itemtyp=valuestore.StoreItem))
		self.name = hubname
		self.addr = addr
		self.url = addr
		self.config = None
		self.password = password
		if self.addr.startswith('http://'):
			self.wsurl = 'ws://' + self.addr[7:] + ':8123/api/websocket'
		elif self.addr.startswith('https://'):
			self.wsurl = 'wss://' + self.addr[8:] + ':8123/api/websocket'
		else:
			self.wsurl = 'ws://' + self.addr + ':8123/api/websocket'
		self.HAnum = 0
		self.ws = None  # websocket client instance
		self.msgcount = 0
		self.watchstarttime = time.time()
		self.Entities = {}
		self.Domains = {}
		self.Indirectors = {} # these hold nodes that the console config thinks exist but HA doesn't have yet - happens at startup of joint HA/Console node
		self.Others = {}
		self.alertspeclist = {}  # if ever want auto alerts like ISY command vars they get put here
		self.AlertNodes = {}
		self.lasterror = None
		self.delaystart = 0
		if password != '':
			self.api = ha.API(self.url, password)
		else:
			self.api = ha.API(self.url)
		for i in range(9):
			hassok = False
			apistat = ha.validate_api(self.api)
			if apistat == ha.APIStatus.OK:
				hassok = True
				break
			elif apistat == ha.APIStatus.CANNOT_CONNECT:
				logsupport.Logs.Log('{}: Not yet responding (starting up?)'.format(self.name))
				time.sleep(10 * i)
			elif apistat == ha.APIStatus.INVALID_PASSWORD:
				logsupport.Logs.Log('{}: Bad access key'.format(self.name), severity=ConsoleError)
				raise ValueError
			else:
				logsupport.Logs.Log(
					'{}: Failed access validation for unknown reasons ({})'.format(self.name, repr(apistat)),
					severity=ConsoleWarning)
				time.sleep(5)

		# noinspection PyUnboundLocalVariable
		if hassok:
			logsupport.Logs.Log('{}: Access accepted'.format(self.name))
		else:
			logsupport.Logs.Log('HA access failed multiple trys for: ' + self.name, severity=ConsoleError, tb=False)
			raise ValueError

		entities = ha.get_states(self.api)
		for e in entities:
			if e.domain not in self.Domains:
				self.Domains[e.domain] = {}
			p2 = dict(e.as_dict(), **{'domain': e.domain, 'name': e.name, 'object_id': e.object_id})

			if e.domain in hadomains:
				N = hadomains[e.domain](self, p2)
				self.Entities[e.entity_id] = N
			else:
				N = HAnode(self, **p2)
				self.Others[e.entity_id] = N
				logsupport.Logs.Log(self.name + ': Uncatagorized HA domain type: ', e.domain, ' for entity: ',
									e.entity_id)
				debug.debugPrint('HASSgeneral', "Unhandled node type: ", e.object_id)

			self.Domains[e.domain][e.object_id] = N

		for n, T in self.DomainEntityReg['climate'].items():  # todo why not in Tstat processing
			tname = n.split('.')[1]
			tsensor = self.DomainEntityReg['sensor']['sensor.' + tname + '_thermostat_hvac_state']
			# noinspection PyProtectedMember
			T._connectsensors(tsensor)
		self.haconnectstate = "Init"
		services = {}
		for i in range(3):
			services = ha.get_services(self.api)
			if services != {}: break
			logsupport.Logs.Log('Retry getting services from {}'.format(self.name))
			time.sleep(1)
		if services == {}:
			logsupport.Logs.Log('{} reports no services'.format(self.name), severity=ConsoleWarning)
		self.knownservices = {}
		for d in services:
			if not d['domain'] in self.knownservices:
				self.knownservices[d['domain']] = {}
			for s,c in d['services'].items():
				if s in self.knownservices[d['domain']]:
					logsupport.DevPrint('Duplicate service noted for domain {}: service: {} existing: {} new: {}'.format(d['domain'], s, self.knownservices[d['domain'][s]],c))
				self.knownservices[d['domain']][s] = c

		if config.sysStore.versionname in ('development', 'homerelease'):
			with open('{}/Console/{}-services'.format(config.sysStore.HomeDir, self.name), 'w') as f:
				for d, svc in self.knownservices.items():
					print(d, file=f)
					for s, c in svc.items():
						print('    {}'.format(s), file=f)
						print('         {}'.format(c), file=f)
					print('==================', file=f)
			with open('{}/Console/{}-entities'.format(config.sysStore.HomeDir, self.name), 'w') as f:
				print('===== Ignored =====', file=f)
				for d, de in self.DomainEntityReg.items():
					for e, t in de.items():
						if isinstance(t, self.dyndomains['ignore'].IgnoredDomain):
							print('Ignored entity in {}: {} {}'.format(self.name, d, e), file=f)
				print('===== Active  =====', file=f)
				for d, de in self.DomainEntityReg.items():
					for e, t in de.items():
						if not isinstance(t, self.dyndomains['ignore'].IgnoredDomain):
							print('Watched entity in {}: {} {}'.format(self.name, d, e), file=f)
				print('=====   New   =====', file=f)
		# listeners = ha.get_event_listeners(self.api)
		logsupport.Logs.Log(self.name + ": Processed " + str(len(self.Entities)) + " total entities")
		for d, e in self.DomainEntityReg.items():
			if e != {}: logsupport.Logs.Log("    {}: {}".format(d, len(e)))

		threadmanager.SetUpHelperThread(self.name, self.HAevents, prerestart=self.PreRestartHAEvents,
										poststart=self.PostStartHAEvents, postrestart=self.PostStartHAEvents,
										prestart=self.PreRestartHAEvents, checkok=self.HACheckThread)
		logsupport.Logs.Log("{}: Finished creating structure for hub".format(self.name))
