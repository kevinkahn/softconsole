import errno
import json
import time
import os
import importlib

from utils.utilfuncs import safeprint
from ..hubs import HubInitError

import websocket
from typing import Callable, Union

import config
import debug
from . import haremote as ha
import historybuffer
import logsupport
from utils import threadmanager, hw
from controlevents import CEvent, PostEvent, ConsoleEvent, PostIfInterested
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail, ConsoleInfo
from stores import valuestore, haattraccess
from utils.utilities import CheckPayload

AddIgnoredDomain: Union[Callable, None] = None  # type Union[Callable, None]
# gets filled in by ignore to avoid import loop

ignoredeventtypes = [
	'system_log_event', 'service_executed', 'logbook_entry', 'timer_out_of_sync', 'result',
	'persistent_notifications_updated', 'automation_triggered', 'script_started', 'service_removed', 'hacs/status',
	'hacs/repository', 'hacs/config', 'entity_registry_updated', 'component_loaded', 'device_registry_updated',
	'entity_registry_updated', 'lovelace_updated', 'isy994_control', 'core_config_updated', 'homeassistant_start',
	'config_entry_discovered', 'automation_reloaded', 'hacs/stage', 'hacs/reload', 'zwave_js_value_notification',
	'event_template_reloaded', 'panels_updated', 'data_entry_flow_progressed']


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

class HAnode(object):
	def __init__(self, HAitem, **entries):
		self.entity_id = ''
		self.object_id = ''
		self.name = ''
		self.attributes = {}
		self.state = 0
		self.internalstate = self._NormalizeState(self.state)
		self.__dict__.update(entries)
		if 'friendly_name' in self.attributes: self.FriendlyName = self.attributes['friendly_name']
		self.address = self.entity_id
		self.Hub = HAitem
		self.domname = 'unset'

	def DisplayStuff(self, prefix, withattr=False):
		d = dict(vars(self))
		if not withattr: del d['attributes']
		print(prefix, d)

	def LogNewEntity(self, newstate):
		logsupport.Logs.Log(
			"New entity since startup seen from {}: {} (Domain: {}) New: {}".format(
				self.Hub.name, self.entity_id, self.domname, repr(newstate)))

	# def Update(self, **ns):
	#	# just updates last triggered etc.
	#	self.__dict__.update(ns)

	def Update(self, **ns):
		if self.entity_id in self.Hub.MonitoredAttributes:
			val = ns['attributes']
			try:
				for attr in self.Hub.MonitoredAttributes[self.entity_id]:
					val = val[attr]
			except KeyError:
				val = None
			self.Hub.attrstore.SetVal([self.entity_id] + self.Hub.MonitoredAttributes[self.entity_id], val)

		self.__dict__.update(ns)
		oldstate = self.internalstate
		self.internalstate = self._NormalizeState(self.state)
		if self.internalstate == -1:
			logsupport.Logs.Log(
				"Node {} ({}) set unavailable (was {})".format(self.name, self.entity_id, str(oldstate)),
				severity=ConsoleDetail)
		if oldstate == -1 and self.internalstate != -1:
			logsupport.Logs.Log(
				"Node {} ({}) became available ({})".format(self.name, self.entity_id, str(self.internalstate)),
				severity=ConsoleDetail)
		PostIfInterested(self.Hub, self.entity_id, self.internalstate)

	def _NormalizeState(self, state, brightness=None): # may be overridden for domains with special state settings
		if isinstance(state, str):
			if state == 'on':
				if brightness is not None:
					return brightness
				else:
					return 255
			elif state == 'off':
				return 0
			elif state == 'scening':  # scenes really have no state but using -1 would cause X display
				return 0
			elif state in ['unavailable', 'unknown']:
				return -1
			else:
				try:
					val = literal_eval(state)
				except ValueError:
					logsupport.Logs.Log('{} reports unknown state: {}'.format(self.Hub.name, state),
										severity=ConsoleError, tb=False)
					return -1
		else:
			val = state
		if isinstance(val, float):
			if val.is_integer():
				return int(val)
		return val

	def SendSpecialCmd(self, cmd, target, params):
		# This should get the target domain, check that the cmd applies, validate the params, and send the command to the hub
		spccmds = self.Hub.SpecialCmds
		targdom, targent = target.split('.')

		if cmd in spccmds[targdom] and spccmds[targdom][cmd]['target'] == targdom:
			thiscmd = spccmds[targdom][cmd]
			# Normal command targeting an entity in the domain
			for p, val in params.items():
				if p not in thiscmd:
					logsupport.Logs.Log('Invalid paramter {} for command {}'.format(p, cmd), severity=ConsoleWarning)
					raise KeyError(p)
			# send the command
			serviceparams = dict(params)
			serviceparams['entity_id'] = target
			ha.call_service_async(self.Hub.api, targdom, cmd, service_data=serviceparams)
		else:
			logsupport.Logs.Log('Invalid special command {}({}} set at {}'.format(cmd, params, target),
								severity=ConsoleWarning)
			raise ValueError

	def SendOnOffCommand(self, settoon):
		pass

	def SendOnOffFastCommand(self, settoon):
		pass

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
			if name == 'FriendlyName': return self.impliedname
			logsupport.Logs.Log(
				'Attempt to access uncompleted indirector for hub {} node {} (call {})'.format(self.Hub.name,
																							   self.impliedname, name))


hadomains = {}  # todo should these really be separate per hub.  As it is they get created twice for 2 hubs
domainspecificevents = {}
specialcommands = {}


def DomainSpecificEvent(e, message):
	logsupport.Logs.Log('Default event handler {} {}'.format(e, message))
	pass


def RegisterDomain(domainname, domainmodule, eventhdlr=DomainSpecificEvent, speccmd=None):
	if domainname in hadomains:
		logsupport.Logs.Log('Redundant registration of HA domain {}'.format())
	hadomains[domainname] = domainmodule
	domainspecificevents[domainname] = eventhdlr
	specialcommands[domainname] = speccmd


class HA(object):
	class HAClose(Exception):
		pass

	def GetNode(self, name, proxy=''):
		if proxy == '':
			pn = name
		elif ':' in proxy:
			t = proxy.split(':')
			if t[0] == self.name:
				pn = t[1]
			else:
				logsupport.Logs.Log("{}: Proxy must be in same hub as button {}".format(self.name, proxy))
				pn = name
		else:
			pn = proxy
		try:
			return self.Entities[name], self.Entities[pn]
		except KeyError:
			if pn not in self.Entities:
				logsupport.Logs.Log("{}: Attempting to use unknown Proxy {}".format(self.name, pn),
									severity=ConsoleWarning)
			if name not in self.Entities:
				logsupport.Logs.Log("{}: Attempting to access unknown object: {}".format(self.name, name),
									severity=ConsoleWarning)
			I = Indirector(self, name)
			return I, I
		except Exception as E:
			logsupport.Logs.Log("{}: Exception in GetNode: {}".format(self.name, E), severity=ConsoleWarning)
			return None, None

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
			# ** part of handling late discovered nodes
			logsupport.Logs.Log("Error accessing current state in HA Hub: " + self.name + ' ' + repr(MonitorNode),
								severity=ConsoleWarning)
			return None

	def _StatusChecker(self):
		worktodo = True
		while worktodo:
			templist = dict(self.UnknownList)
			for node in templist:
				# noinspection PyUnusedLocal
				e = self.GetActualState(node.name)
			# ** should post e as a node state change
			time.sleep(10)
			worktodo = bool(self.UnknownList)

	def StartStatusChecker(self):
		# logic here would be to start a thread that runs while List is non-empty - need to be careful regarding it changing length
		# while in the loop.  Also needs to be conservative about stopping and the starter needs to double-check the is alive in some way
		# so as not to get caught with an entry but not running.
		pass

	def AddToUnknowns(self, node):  # ** flesh out
		# need to start a thread that checks periodically the status of the node.  When it changes to known value that thread should exit (perhaps post?)
		# the "delete" would get triggered the next time the paint is called (or would it? - can the change to real value happen under the covers?)  Maybe don't need to do the delete
		# since the thread will be not alive - can just start the thread if not alive and let it die peacefully after doing its job?
		self.UnknownList[node.name] = node
		# need a single slot for the node status checker thread per hub instance check is_alive on each entry.  Worst case on the next key repaint this will get
		# called again and the status checking will start.
		logsupport.Logs.Log('{}: Adding {} to unknowns list {}'.format(self.name, node.name, self.UnknownList),
							severity=ConsoleWarning)
		if self.UnknownList:
			if self.StatusCheckerThread is None:
				self.StartStatusChecker()
			elif not self.StatusCheckerThread.is_alive():
				self.StartStatusChecker()

	# noinspection DuplicatedCode
	def DeleteFromUnknowns(self, node):
		try:
			del self.UnknownList[node.name]
			logsupport.Logs.Log('{}: Deleted {} from unknowns list {}'.format(self.name, node.name, self.UnknownList),
								severity=ConsoleWarning)
		except Exception as E:
			logsupport.Logs.Log(
				'{}: Failed attempt to delete {} from unknowns list {} ({})'.format(self.name, node.name,
																					self.UnknownList, E),
				severity=ConsoleWarning)

	def GetActualState(self, ent):
		try:
			e = ha.get_state(self.api, ent)
		except Exception as E:
			logsupport.Logs.Log('{}: State check did not complete for {} exc: {}'.format(self.name, ent, E),
								severity=ConsoleWarning)
			e = -1
		return e

	# end of WIP for checking actual status with hub

	def CheckStates(self):
		# noinspection PyBroadException
		try:
			for n, s in self.DomainEntityReg['sensor'].items():
				cacheval = self.attrstore.GetVal(s.entity_id)
				e = ha.get_state(self.api, s.entity_id)
				if e is None:
					actualval = '*unknown*'
				else:
					actualval = e.state
				if cacheval != type(cacheval)(actualval):
					logsupport.Logs.Log(
						'Sensor value anomoly(' + self.name + '): Cached: ' + str(cacheval) + ' Actual: ' + str(
							actualval), severity=ConsoleWarning, hb=True)
					logsupport.DevPrint(
						'Check anomoly for {}: cache: {} actual: {}'.format(self.name, cacheval, actualval))
					self.attrstore.SetVal(s.entity_id, actualval)
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
			logsupport.Logs.Log(
				"{}({}) failed thread check; state: {}".format(self.name, self.HAnum, self.haconnectstate),
				severity=ConsoleWarning)
			return False
		return True

	def PreRestartHAEvents(self):
		self.haconnectstate = "Prestart"
		trycnt = 60
		while True:
			self.config = ha.get_config(self.api)
			if self.config != {}:
				break  # HA is up
			trycnt -= 1
			if trycnt < 0:
				logsupport.Logs.Log("{}: Waiting for HA to come up - retrying: ".format(self.name),
									severity=ConsoleWarning)
				trycnt = 60
			time.sleep(1)  # don't flood network
		self.watchstarttime = time.time()
		self.HAnum += 1

	def PostStartHAEvents(self):
		# todo need to get all the current state since unlike ISY, HA doesn't just push it
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
		i = 3
		while i > 0:
			try:
				ha.call_service(self.api, 'logbook', 'log',
								{'name': 'Softconsole', 'message': hw.hostname + ' connected'})
				return
			except ha.HomeAssistantError:
				i -= 1
				if i == 0:
					logsupport.Logs.Log(self.name + " not responding to service call after restart",
										severity=ConsoleWarning)
					return
				else:
					time.sleep(1)

	def RegisterEntity(self, domain, entity, item):
		if domain in self.DomainEntityReg:
			if entity in self.DomainEntityReg[domain]:
				logsupport.Logs.Log('Duplicate entity reported in {} hub {}: {}'.format(self.name, domain, entity))
			else:
				self.DomainEntityReg[domain][entity] = item
		else:
			self.DomainEntityReg[domain] = {entity: item}

	def GetAllCurrentState(self):
		entities = ha.get_states(self.api)
		# with open('/home/pi/Console/msglog{}'.format(self.name), 'a') as f:
		#	f.write('----------REFRESH\n')
		for e in entities:
			try:
				p2 = dict(e.as_dict(), **{'domain': e.domain, 'name': e.name, 'object_id': e.object_id})
				if e.entity_id in self.Entities:
					self.Entities[e.entity_id].Update(**p2)
				else:
					logsupport.Logs.Log("{} restart found new entity {} state: {}".format(self.name, e, p2),
										severity=ConsoleWarning)
				# it's new
			except Exception as E:
				logsupport.Logs.Log(
					"{}: Exception in getting current states for {} Exception: {}".format(self.name, e.entity_id, E),
					severity=ConsoleWarning)

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
			prog = 0
			loopstart = time.time()
			self.HB.Entry(repr(message))
			# logsupport.Logs.Log("-->{}".format(repr(message)))
			# with open('/home/pi/Console/msglog{}'.format(self.name),'a') as f:
			#	f.write('{}\n'.format(repr(message)))
			adds = []
			chgs = []
			dels = []
			new = []
			old = []
			try:
				self.msgcount += 1
				# if self.msgcount <4: logsupport.Logs.Log(self.name + " Message "+str(self.msgcount)+':'+ repr(message))
				# noinspection PyBroadException
				try:
					mdecode = json.loads(CheckPayload(message, 'none', 'hasshubmsg'))
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
				if mdecode['type'] == 'platform_discovered':
					logsupport.Logs.Log('{} discovered platform: {}'.format(self.name, message))
				if mdecode['type'] != 'event':
					debug.debugPrint('HASSgeneral', 'Non event seen on WS stream: ', str(mdecode))
					return

				m = mdecode['event']
				del mdecode['event']
				d = m['data']

				if m['event_type'] == 'state_changed':
					prog = 1
					del m['event_type']
					ent = d['entity_id']
					dom, nm = ent.split('.')
					new = d['new_state']
					old = d['old_state']
					del d['new_state']
					del d['old_state']
					del d['entity_id']
					if ent == 'light.bar_lights': safeprint(
						'{} {} -> {}'.format(time.strftime('%m-%d-%y %H:%M:%S', time.localtime()), old, new))
					prog = 1.5
					chgs, dels, adds = findDiff(old, new)
					prog = 2

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
							if old is not None:
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
						prog = 3
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
				elif m['event_type'] == 'call_service':
					d = m['data']
					if d['domain'] == 'homeassistant' and d['service'] == 'restart':
						# only pay attention to restarts
						logsupport.Logs.Log('{}: Restarting, suppress errors until restarted'.format(self.name))
						self.restarting = True
						self.restartingtime = time.time()
				# else:
				#	logsupport.Logs.Log('Saw {}'.format(d))
				elif m['event_type'] == 'system_log_event':
					logsupport.Logs.Log('Hub: ' + self.name + ' logged at level: ' + d['level'] + ' Msg: ' + d[
						'message'])
				elif m['event_type'] == 'service_registered':  # fix plus add service removed
					d = m['data']
					if d['domain'] not in self.knownservices:
						self.knownservices[d['domain']] = {}
					if d['service'] not in self.knownservices[d['domain']]:
						self.knownservices[d['domain']][d['service']] = d['service']
					logsupport.Logs.Log(
						"{} has new service: {}".format(self.name, message), severity=ConsoleDetail)
				elif m['event_type'] in ignoredeventtypes:
					pass
				elif '.' in m['event_type']:
					# domain specific event
					d, ev = m['event_type'].split('.')
					if d in domainspecificevents:
						domainspecificevents[d](ev, message)
				elif m['event_type'] == 'homeassistant_started':
					# HA just finished initializing everything, so we may have been quicker - refresh all state
					# with open('/home/pi/Console/msglog{}'.format(self.name), 'a') as f:
					#	f.write('DO REFRESH FOR STARTED')
					self.GetAllCurrentState()
				else:
					logsupport.Logs.Log('{} Unknown event: {}'.format(self.name, message), severity=ConsoleWarning)
					ignoredeventtypes.append(m['event_type'])  # only log once
					debug.debugPrint('HASSgeneral', "Unknown event: " + str(m))
			except Exception as E:
				logsupport.Logs.Log("Exception handling HA message: ({}) {} {}".format(prog, repr(E), repr(message)),
									severity=ConsoleWarning,
									tb=True, hb=True)
				if prog == 1.5:
					logsupport.Logs.Log("Diff error {}:::{}".format(old, new))
				elif prog == 2:
					logsupport.Logs.Log("Post diff: {}:::{}:::{}".format(adds, dels, chgs))
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
					logsupport.Logs.Log("WS lib workaround hit (1)", severity=ConsoleWarning)  # tempdel
					return
			except:
				pass
				logsupport.Logs.Log("WS lib workaround hit (2)", severity=ConsoleWarning)  # tempdel
			if isinstance(error, websocket.WebSocketConnectionClosedException):
				logsupport.Logs.Log(self.name + " closed WS stream " + str(self.HAnum) + "; attempt to reopen",
									severity=ConsoleWarning if not self.restarting else ConsoleInfo)
			elif isinstance(error, ConnectionRefusedError):
				logsupport.Logs.Log(self.name + " WS socket refused connection", severity=ConsoleWarning)
			elif isinstance(error, TimeoutError):
				logsupport.Logs.Log(self.name + " WS socket timed out", severity=ConsoleWarning)
			elif isinstance(error, OSError):
				if error.errno == errno.ENETUNREACH:
					logsupport.Logs.Log(self.name + " WS network down", severity=ConsoleWarning)
				else:
					logsupport.Logs.Log(self.name + ' WS OS error', repr(error), severity=ConsoleError, tb=False)
			else:
				logsupport.Logs.Log(self.name + ": Unknown Error in WS stream " + str(self.HAnum) + ':' + repr(error),
									severity=ConsoleWarning)
			# noinspection PyBroadException
			try:
				if isinstance(error, AttributeError):
					# error = (errno.ETIMEDOUT,"Websock bug catch")
					logsupport.Logs.Log("WS lib workaround hit (3)", severity=ConsoleWarning)  # tempdel
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
			logsupport.Logs.Log(
				self.name + " WS stream " + str(self.HAnum) + " closed: " + str(code) + ' : ' + str(reason),
				severity=ConsoleWarning if not self.restarting else ConsoleInfo, tb=False, hb=True)
			if self.haconnectstate != "Failed": self.haconnectstate = "Closed"

		# noinspection PyUnusedLocal
		def on_open(qws):
			# todo if ws never opens then an error doesn't cause a thread restart - not sure why but should track down
			# possible logic - record successful open then if error while not yet open cause console to restart by setting some
			# global flag? Flag would be checked in main gui loop and cause a restart.  It is a one way comm from the threads so
			# should not be subject to a race
			# with open('/home/pi/Console/msglog{}'.format(self.name),'a') as f:
			#	f.write('----------OPEN\n')
			self.HB.Entry('Open')
			if self.restarting:
				logsupport.Logs.Log('{}: WS Stream {} opened (HA restart took: {} secs.)'.format(self.name, self.HAnum,
																								 time.time() - self.restartingtime))
			else:
				logsupport.Logs.Log("{}: WS stream {} opened".format(self.name, self.HAnum))
			# refresh state after the web socket stream is open
			self.GetAllCurrentState()
			self.haconnectstate = "Running"
			self.restarting = False

		self.haconnectstate = "Starting"
		websocket.setdefaulttimeout(30)
		try:
			# websocket.enableTrace(True)
			# noinspection PyProtectedMember
			self.ws = websocket.WebSocketApp(self.wsurl, on_message=on_message,
											 on_error=on_error,
											 on_close=on_close, on_open=on_open, header=self.api._headers)
			self.msgcount = 0
		except AttributeError as e:
			logsupport.Logs.Log(self.name + ": Problem starting WS handler - retrying: ", repr(e),
								severity=ConsoleWarning)
		try:
			self.haconnectstate = "Running"
			self.ws.run_forever(ping_timeout=999)
		except self.HAClose:
			logsupport.Logs.Log(self.name + " Event thread got close")
		sev = ConsoleWarning if self.ReportThisError() else logsupport.ConsoleInfo
		logsupport.Logs.Log(self.name + " Event Thread " + str(self.HAnum) + " exiting", severity=sev,
							tb=False)
		if self.haconnectstate not in ("Failed", "Closed"): self.haconnectstate = "Exited"

	def ReportThisError(self):
		return config.sysStore.ErrLogReconnects and not self.restarting

	def ParseDomainCommands(self, dom, services):
		title = '{} ParseSpecial:'.format(dom)
		entry = {}
		normal = True

		for c, info in services.items():
			try:
				t = info['target']
				if 'entity' in t and 'domain' in t['entity'] and t['entity']['domain'] == dom:
					targ = ''
					entry[c] = {'target': dom}
				elif 'entity' in t and t['entity'] == {}:
					targ = ''
					entry[c] = {'target': '*'}
				else:
					normal = False
					entry[c] = {'target': 'NONSTD'}
					targ = t
			except Exception as E:
				entry[c] = {'target': 'NONE'}
				targ = "        No Target"

			try:
				flds = []
				for fn, f in info['fields'].items():
					s = f['selector'] if 'selector' in f else {}
					keys = list(s.keys())
					if len(keys) == 0:
						entry[c][fn] = 'No selector'
					elif len(keys) > 1:
						flds.append("        Field: {} Selector: {}".format(fn, keys))
					else:
						entry[c][fn] = keys[0]
			except Exception as E:
				print("Pars excp: {} {} {} {}".format(dom, E, c, info))
				print('Info: {} {}'.format(s, keys))
			if not normal:
				with open('{}-nonentitycmds.txt'.format(self.name), 'w') as f:
					if title != '':
						print("{} {}".format(self.name, title), file=f)
						title = ''
					print("    Command: {}".format(c), file=f)
					if targ != '': print("    Target: {}".format(targ), file=f)
					for l in flds: print(l, file=f)
			else:
				self.SpecialCmds[dom] = entry

	# noinspection PyUnusedLocal
	def __init__(self, hubname, addr, user, password, version):
		self.SpecialCmds = {}
		self.restarting = False
		self.restartingtime = 0
		self.UnknownList = {}
		self.StatusCheckerThread = None
		self.DomainEntityReg = {}
		self.knownservices = []
		self.MonitoredAttributes = {}  # holds tuples with the name of attribute that is used in an alert
		self.HB = historybuffer.HistoryBuffer(40, hubname)
		if version not in (0, 1):
			logsupport.Logs.Log("Fatal error - no HA hub version {}".format(version), severity=ConsoleError)
			raise ValueError
		logsupport.Logs.Log(
			"{}: Creating structure for Home Assistant hub version {} at {}".format(hubname, version, addr))

		self.dyndomains = {}
		for domainimpl in os.listdir(os.getcwd() + '/hubs/ha/domains'):
			if '__' not in domainimpl:
				splitname = os.path.splitext(domainimpl)
				if splitname[1] == '.py':
					if splitname[0] != 'thermostat':
						self.dyndomains[splitname[0]] = importlib.import_module('hubs.ha.domains.' + splitname[0])
					else:
						if version == 0:
							logsupport.Logs.Log('Using old version of HA climate support - are you sure?',
												severity=ConsoleWarning)
							self.dyndomains['thermostat'] = importlib.import_module('hubs.ha.domains.__oldthermostat')
						else:
							self.dyndomains['thermostat'] = importlib.import_module('hubs.ha.domains.thermostat')

		for dom in hadomains:
			self.DomainEntityReg[dom] = {}

		self.addibledomains = {}  # {'media_player': MediaPlayer} todo resolve how to add things

		self.name = hubname
		# with open('/home/pi/Console/msglog{}'.format(self.name), 'w') as f:
		#	f.write('----------START Log\n')
		if addr.startswith('https'):
			prefix = 'https://'
			wsprefix = 'wss://'
		elif addr.startswith('http'):
			prefix = 'http://'
			wsprefix = 'ws://'
		else:
			prefix = 'http://'
			wsprefix = 'ws://'

		trimmedaddr = addr.replace(prefix, '', 1)

		if ':' in trimmedaddr:
			self.addr = trimmedaddr.split(':')[0]
			self.port = trimmedaddr.split(':')[1]
		else:
			self.addr = trimmedaddr
			self.port = '8123'
		self.url = prefix + self.addr + ':' + self.port
		self.wsurl = '{}{}:{}/api/websocket'.format(wsprefix, self.addr, self.port)
		self.config = None
		self.password = password
		self.HAnum = 0
		self.ws = None  # websocket client instance
		self.msgcount = 0
		self.watchstarttime = time.time()
		self.Entities = {}
		self.Domains = {}
		self.Indirectors = {}  # these hold nodes that the console config thinks exist but HA doesn't have yet - happens at startup of joint HA/Console node
		self.alertspeclist = {}  # if ever want auto alerts like ISY command vars they get put here
		self.AlertNodes = {}
		self.lasterror = None
		if password != '':
			self.api = ha.API(self.addr, prefix, password, port=int(self.port))
		else:
			self.api = ha.API(self.addr, prefix, port=int(self.port))
		for i in range(9 if config.sysStore.versionname not in ('none', 'development') else 1):
			hassok = False
			apistat = ha.validate_api(self.api)
			if apistat == ha.APIStatus.OK:
				if i > 2:  # this was probably a power fail restart so need to really wait while HA stabilizes
					logsupport.Logs.Log(
						'{}: Probable power fail restart so delay to allow HA stabilization'.format(self.name))
					time.sleep(120)
				hassok = True
				break
			elif apistat == ha.APIStatus.CANNOT_CONNECT:
				logsupport.Logs.Log('{}: Not yet responding (starting up?)({})'.format(self.name, i))
				time.sleep(10 * (i+1))
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
			raise HubInitError

		self.attrstore = valuestore.NewValueStore(
			haattraccess.HAattributes(hubname, self))  # don't create until access is ok
		entities = ha.get_states(self.api)
		for e in entities:
			if e.domain not in self.Domains:
				self.Domains[e.domain] = {}
			p2 = dict(e.as_dict(), **{'domain': e.domain, 'name': e.name, 'object_id': e.object_id})

			if e.domain in hadomains:
				N = hadomains[e.domain](self, p2)
				self.Entities[e.entity_id] = N
			else:
				AddIgnoredDomain(e.domain)
				N = hadomains[e.domain](self, p2)
				logsupport.Logs.Log(self.name + ': Uncatagorized HA domain type: ', e.domain, ' for entity: ',
									e.entity_id)
				debug.debugPrint('HASSgeneral', "Unhandled node type: ", e.object_id)

			self.Domains[e.domain][e.object_id] = N

		for n, T in self.DomainEntityReg['climate'].items():
			# This is special cased for Thermostats to connect the sensor entity with the thermostat to check for changes
			# If any other domain ever needs the same mechanism this should just be generalized to a "finish-up" call for
			# every entity
			try:
				try:
					tname = n.split('.')[1]
					tsensor = self.DomainEntityReg['sensor']['sensor.' + tname + '_thermostat_hvac_state']
					# noinspection PyProtectedMember
					T._connectsensors(tsensor)
				except Exception as E:
					logsupport.Logs.Log(
						'Exception from {} connecting sensor {} ({}) probably ISY Tstat'.format(self.name, n, E),
						severity=ConsoleDetail)
			except Exception as E:
				logsupport.Logs.Log('Exception looking at climate devices: {} ({})'.format(n, E),
									severity=ConsoleWarning)
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
			try:
				self.ParseDomainCommands(d['domain'], d['services'])
			except Exception as E:
				print('Parse Except: {}'.format(E))
			for s, c in d['services'].items():
				if s in self.knownservices[d['domain']]:
					logsupport.DevPrint(
						'Duplicate service noted for domain {}: service: {} existing: {} new: {}'.format(d['domain'], s,
																										 self.knownservices[
																											 d[
																												 'domain'][
																												 s]],
																										 c))
				self.knownservices[d['domain']][s] = c

		# print(self.SpecialCmds)
		# for d, cmds in self.SpecialCmds.items():
		#	print("Domain {}".format(d))
		#	for c,param in cmds.items():
		#		print("    {}({}): {}".format(c,param['target'],{x: param[x] for x in param if x != 'target'}))

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
			if e != {}:
				if isinstance(list(e.values())[0], self.dyndomains['ignore'].IgnoredDomain):
					logsupport.Logs.Log("    {}: {}  (Ignored)".format(d, len(e)))
				else:
					logsupport.Logs.Log("    {}: {}".format(d, len(e)))
			if d == 'unset':
				for i in e:
					logsupport.Logs.Log('  :{}'.format(i))

		self.initialstartup = True

		threadmanager.SetUpHelperThread(self.name, self.HAevents, prerestart=self.PreRestartHAEvents,
										poststart=self.PostStartHAEvents, postrestart=self.PostStartHAEvents,
										prestart=self.PreRestartHAEvents, checkok=self.HACheckThread,
										rpterr=self.ReportThisError)
		logsupport.Logs.Log("{}: Finished creating structure for hub".format(self.name))
