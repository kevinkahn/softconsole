from requests import get
import homeassistant.remote as ha
import json
import pprint
import threading
import websocket
from sseclient import SSEClient

url = 'http://rpi-dev7.pgawhome:8123/api/states'


class HAnode(object):
	def __init__(self, HA, eid, domain, oid, name, state, lupd, lchg):
		self.HA = HA
		self.state = state
		self.entity_id = eid
		self.domain = domain
		self.object_id = oid
		self.name = name
		self.last_updated = lupd
		self.last_changed = lchg
		self.attributes = {}
		self.HA.Entities[eid] = self

	def __str__(self):
		return self.name+'::'+self.state

class Group(HAnode):
	def __init__(self, elist, attrs, *args):
		super(Group,self).__init__(*args)
		self.members = elist
		self.attributes = attrs
		self.HA.Groups[self.entity_id] = self

class Light(HAnode):
	def __init__(self, attrs, *args):
		super(Light,self).__init__(*args)
		self.attributes = attrs
		self.HA.Lights[self.entity_id] = self

class Switch(HAnode):
	def __init__(self, attrs, *args):
		super(Switch,self).__init__(*args)
		self.attributes = attrs
		self.HA.Switches[self.entity_id] = self

class Sensor(HAnode): # this needs to become a store item
	def __init__(self, attrs, *args):
		super(Sensor,self).__init__(*args)
		self.attributes = attrs
		self.HA.Sensors[self.entity_id] = self

class ZWave(HAnode):
	def __init__(self, attrs, *args):
		super(ZWave,self).__init__(*args)
		self.attributes = attrs
		self.HA.ZWaves[self.entity_id] = self

class HA(object):

	def GetNode(self, name, proxy):
		# return (Control Obj, Monitor Obj)
		'''
		if name is scene return member, if name is light or switch return for both
		:param name:
		:param proxy:
		:return:
		'''
		pass # name should be the entity_id, proxy is same?

	def GetCurrentStatus(self, MonitorNode):
		pass

	def NodeExists(self, name):
		pass

	def HAevents(self):

		def on_message(qws, message):
			mdecode = json.loads(message)
			if mdecode['type'] == 'auth_ok':
				print('WS AuthOK')
				return
			if mdecode['type'] != 'event':
				print('Nonevent: ',mdecode)
				return
			m = mdecode['event']
			del mdecode['event']
			#print(mdecode)  == {'id': 1, 'type': 'event'}
			d = m['data']
			if d['entity_id'] in self.ZWaves:
				return
			if d['entity_id'] in self.Sensors:
				print('Set var: ',d['entity_id'],' to ',d['new_state']['state'])
			else:
				print('Entity: ',m['data']['entity_id'])
				print('New: ',d['new_state'])
				print('Old: ',d['old_state'])
			del d['entity_id']
			del d['new_state']
			del d['old_state']
			print("Rest: ", m)

		def on_error(qws, error):
			print("ERR", error)

		def on_close(qws, code, reason):
			print("CLOSE", reason)

		def on_open(qws):
			print('Open')
			ws.send(json.dumps(
				{'id': 1, 'type': 'subscribe_events'}))

		websocket.setdefaulttimeout(30)
		wsurl = 'ws://localhost:8123/api/websocket'

		while True:
			try:
				ws = websocket.WebSocketApp(wsurl, on_message=on_message,
											on_error=on_error,
											on_close=on_close, on_open=on_open)
				break
			except AttributeError as e:
				print("Problem starting WS handler - retrying: ", repr(e))
				print(e)
			ws.send(json.dumps({'id': 1, 'type': 'subscribe_events','event_type':'state_changed'}))
		# ws.send(json.dumps(
		#       	{'id': 1, 'type': 'subscribe_events'}))
		ws.run_forever()
		print("Exit!")


	def __init__(self, url):
		self.api = ha.API('rpi-dev7.pgawhome')
		if ha.validate_api(self.api).value != 'ok':
			print("Bad Validate")
		self.config = ha.get_config(self.api)
		self.Entities = {}
		self.Domains = {}
		self.Groups = {}
		self.Lights = {}
		self.Switches = {}
		self.Sensors = {}
		self.ZWaves = {}
		self.Others = {}


		entities = ha.get_states(self.api)
		for e in entities:
			params = (self, e.entity_id, e.domain, e.object_id, e.name, e.state, e.last_updated, e.last_changed)
			attrs = dict(e.attributes)
			if e.domain not in self.Domains:
				self.Domains[e.domain] = {}
			if e.domain == 'group':
				a = attrs['entity_id']
				del attrs['entity_id']
				N = Group(a,attrs,*params)
			elif e.domain == 'light':
				N = Light(attrs,*params)
			elif e.domain == 'switch':
				N = Switch(attrs,*params)
			elif e.domain == 'sensor':
				N = Sensor(attrs,*params)
			elif e.domain == 'zwave':
				N = ZWave(attrs,*params)
			else:
				N = HAnode(*params)
				self.Others[e.entity_id] = N


			self.Domains[e.domain][e.object_id] = N
			print(e)

		T = threading.Thread(name='HA', target=self.HAevents)
		T.setDaemon(True)
		T.start()

		self.services = ha.get_services(self.api)


X = HA(url)

while True:
	pass


