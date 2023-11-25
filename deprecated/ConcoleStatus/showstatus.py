import paho.mqtt.client as mqtt
import json, time
import pprint

from stores.mqttsupport import MQitem
from utils.utilities import CheckPayload

pp = pprint.PrettyPrinter(indent=4)


class MQTTBroker():

	def __init__(self, name):
		self.MQTTCommFailed = False
		self.MQTTnum = 0

		# self.HB.Entry('Gave up control for: {}'.format(time.time() - loopend))

		def _parsesection(nm, sect, prefix=''):
			tp = sect.get('TopicType', 'string')
			if tp == 'group':
				thistopic = sect.get('Topic', nm[-1])
				rtn = {}
				for itemnm, val in sect.items():
					rtn[itemnm] = _parsesection(nm + [itemnm], val, prefix=prefix + '/' + thistopic)
				return rtn
			else:
				if tp == 'float':
					tpcvrt = float
				elif tp == 'int':
					tpcvrt = int
				else:
					tpcvrt = str
				thistopic = sect.get('Topic', nm[-1])
				jsonflds = sect.get('json', '')
				if jsonflds: jsonflds = jsonflds.split(':')
				tpc = (prefix + '/' + thistopic).lstrip('/')
				rtn = MQitem(nm, tpc, tpcvrt, int(sect.get('Expires', 99999999999999999)), jsonflds, self)
				if tpc in self.topicindex:
					self.topicindex[tpc].append(rtn)
				else:
					self.topicindex[tpc] = [rtn]
				return rtn

		self.vars = {}
		self.ids = {}
		self.topicindex = {}  # dict from full topics to MQitems


"""
	def Publish(self, topic, payload=None, node='Master', qos=1, retain=False, viasvr=False):
		if self.MQTTCommFailed: return
		self.sent.Op()
		fulltopic = 'consoles/' + node + '/' + topic
		if self.MQTTrunning:
			try:
				self.MQTTclient.publish(fulltopic, payload, qos=qos, retain=retain)
			except Exception as E:
				self.MQTTCommFailed = True
				logprint('MQTT Publish error ({})'.format(repr(E)))
		else:
			if viasvr:
				logprint("{}: Publish attempt with server not running ({})".format(self.name, repr(payload)))
			else:
				try:
					publish.single(fulltopic, payload, hostname=self.address, qos=qos, retain=retain, auth=self.auth)
				except Exception as E:
					self.MQTTCommFailed = True
					logprint("MQTT single publish error ({})".format(repr(E)), severity=ConsoleError,
										localonly=True)
	# noinspection PyUnusedLocal
	def PushToMQTT(self, storeitem, old, new, param, modifier):
		self.Publish('/'.join(storeitem.name), str(new))
"""


# ___________________________________________________________________________

def logprint(info):
	print(info)


def on_connect(client, userdata, flags, rc):
	# for i, _ in userdata.topicindex.items():
	#	client.subscribe(i)
	client.subscribe([('consoles/all/cmd', 1),
					  ('consoles/+/cmd', 1),
					  ('consoles/+/set', 1),
					  ('consoles/all/set', 1)])
	client.subscribe('consoles/all/nodes/#')
	client.subscribe('consoles/all/weather2/#')
	client.subscribe('consoles/+/status')
	client.subscribe('consoles/+/resp')


def on_message(client, userdata, msg):
	msgtopic = msg.topic
	try:
		d = json.loads(CheckPayload(msg.payload.decode('ascii'), msgtopic, 'mqtt-consoles-set'))
		try:
			del d['stats']
		except:
			pass
		print("{}: \n\r {}".format(msgtopic, d))
		return
		# command to force get: mosquitto_pub -t consoles/all/cmd -m getstable;  mosquitto_pub -t consoles/all/cmd -m restart
		var = []
		for t, item in userdata.topicindex.items():
			if t == msgtopic:
				var.extend(item)

		topicsplit = msgtopic.split('/')
		if msgtopic in ('consoles/all/cmd', 'consoles/' + hw.hostname + '/cmd'):
			payld = msg.payload.decode('ascii').split('|')

			cmd = payld[0]
			fromnd = 'unknown' if len(payld) < 2 else payld[1]
			seq = 'unknown' if len(payld) < 3 else payld[2]
			cmdparam = None if len(payld) < 4 else payld[3]
			logprint(
				'{}: Remote command received on {} from {}-{}: {} {}'.format(self.name, msgtopic, fromnd, seq,
																			 cmd, cmdparam))

			return
		elif msgtopic in ('consoles/all/set', 'consoles/' + hw.hostname + '/set'):
			d = json.loads(CheckPayload(msg.payload.decode('ascii'), msgtopic, 'mqtt-consoles-set'))
			try:
				logprint('{}: set {} = {}'.format(self.name, d['name'], d['value']))
				valuestore.SetVal(d['name'], d['value'])
			except Exception as E:
				logprint('Bad set via MQTT: {} Exc: {}'.format(repr(d), E))
			return
		elif msgtopic.startswith('consoles/all/weather2'):
			# return  COMMENT TO TEST FETCHING WITHOUT CACHE FOOLING US
			provider = topicsplit[3]
			locname = topicsplit[4]
			if msg.payload is None or msg.payload.decode('ascii') == '':
				logsupport.Logs.Log(
					'MQTT Entry clear for {}'.format(msgtopic))  # ignore null entries
			else:
				wpayload = json.loads(CheckPayload(msg.payload.decode('ascii'), 'weathup', 'weathup'))
				MQTTWeatherUpdate(provider, locname, wpayload)
			return

		elif topicsplit[2] in ('nodes', 'status', 'resp'):
			# see if it is node specific message
			msgdcd = json.loads(CheckPayload(msg.payload.decode('ascii'), topicsplit, 'mqtt-nodespec',
											 emptyok=topicsplit[2] in ('status', 'nodes')))
			if topicsplit[2] == 'nodes':
				consolestatus.UpdateNodeStatus(topicsplit[-1], msgdcd)
				return
			elif topicsplit[2] == 'status':
				consolestatus.UpdateNodeStatus(topicsplit[1], msgdcd)
				return
			elif topicsplit[2] == 'resp':
				if self.name in config.AS.HubInterestList:
					if msgdcd['cmd'] in config.AS.HubInterestList[self.name]:
						usevalue = msgdcd['value'] if 'value' in msgdcd else ''
						respnode = msgdcd['respfrom'] if 'respfrom' in msgdcd else '*oldsys*'
						try:
							controlevents.PostEvent(
								controlevents.ConsoleEvent(controlevents.CEvent.HubNodeChange,
														   hub=self.name, stat=msgdcd['status'],
														   seq=msgdcd['seq'],
														   node=msgdcd['cmd'],
														   respfrom=respnode,
														   value=usevalue))
						except Exception as E:
							logprint(
								'Exception posting event from mqtt resp: ({}) Exception {}'.format(
									(self.name, msgdcd, respnode, userdata), E))
				return

		# noinspection PySimplifyBooleanCheck
		# not a command/status message
		if var == []:
			logprint(f"Unknown topic {msgtopic} from broker {self.name}")
		else:
			for v in var:
				v.SetTime = time.time()
				if not v.jsonflds:
					v.Value = v.Type(msg.payload)
				# debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ', v.Value)
				else:
					payload = '*bad json*' + msg.payload.decode('ascii')  # for exception log below
					try:
						payload = json.loads(CheckPayload(msg.payload.decode('ascii').replace('nan',
																							  'null'), v,
														  'mqtt-var'))  # work around bug in tasmota returning bad json
						for i in v.jsonflds:
							payload = payload[i]
						if payload is not None:
							v.Value = v.Type(payload)
						else:
							v.Value = None
					# debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ', v.Value)
					except Exception as e:
						logprint(f"Error handling json MQTT item: {v.name} {str(v.jsonflds)} {msg.payload.decode('ascii')} {e} {repr(payload)}")

	except Exception as E:
		logprint('MQTT Error: {} topic: {} msg: {}'.format(repr(E), msgtopic, msg.payload))


# noinspection PyUnusedLocal

MQTTclient = mqtt.Client()
MQTTclient.on_connect = on_connect
# MQTTclient.on_disconnect = on_disconnect
MQTTclient.on_message = on_message

MQTTclient.username_pw_set(None, None)

print('Starting')
MQTTclient.connect('mqtt')
print('Connecting')
with open('tally', 'w') as frpt:
	frpt.write('-------------\n')
with open('watchw', 'w') as frpt:
	frpt.write('-------------\n')
MQTTclient.loop_forever()

try:
	MQTTclient.connect('mqtt', keepalive=20)
except Exception as E:
	logprint('Exception connecting to MQTT - authentication or server down error ({})'.format(E))
	exit(99)
MQTTclient.loop_forever()
# self.MQTTclient.disconnect()
logprint("MQTT handler thread ended ")
