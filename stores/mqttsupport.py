import json
import time

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
# noinspection PyProtectedMember
from configobj import Section
from .genericweatherstore import MQTTWeatherUpdate

import config
import historybuffer
import logsupport
from utils import threadmanager, hw
from logsupport import ConsoleWarning, ConsoleError
from stores import valuestore
import consolestatus
import issuecommands
import controlevents
import stats
from utils.utilities import CheckPayload

class MQitem(valuestore.StoreItem):
	def __init__(self, name, Topic, Type, Expires, jsonflds, Store):
		self.Topic = Topic
		self.jsonflds = jsonflds
		self.Expires = Expires
		super(MQitem, self).__init__(name, None, store=Store, vt=Type)


class MQTTBroker(valuestore.ValueStore):

	def __init__(self, name, configsect):
		super().__init__(name, itemtyp=MQitem)
		self.MQTTCommFailed = False
		self.MQTTnum = 0
		self.fetcher = None
		self.HB = historybuffer.HistoryBuffer(40, name)
		self.mqttstats = stats.StatReportGroup(name='mqtt-{}'.format(self.name),
											   title='{} Broker Statistics'.format(self.name),
											   reporttime=stats.LOCAL(0))
		self.discon = stats.CntStat(name='Disconnects', keeplaps=True, PartOf=self.mqttstats, rpt=stats.daily)
		self.rcvd = stats.CntStat(name='Received', keeplaps=True, PartOf=self.mqttstats, rpt=stats.daily)
		self.sent = stats.CntStat(name='Sent', keeplaps=True, PartOf=self.mqttstats, rpt=stats.daily)

		# noinspection PyUnusedLocal
		def on_connect(client, userdata, flags, rc):
			logm = "Connected" if self.loopexited else "Reconnected"
			sckt = self.MQTTclient.socket()
			svraddr = sckt.getpeername()
			logsupport.Logs.Log(
				"{}: {} stream {} to {}({}) with result code {}".format(self.name, logm, self.MQTTnum, self.address,
																		svraddr[0], rc))
			for i, _ in userdata.topicindex.items():
				client.subscribe(i)
			if logsupport.primaryBroker == self:
				client.subscribe([('consoles/all/cmd', 1),
								  ('consoles/' + hw.hostname + '/cmd', 1),
								  ('consoles/' + hw.hostname + '/set', 1),
								  ('consoles/all/set', 1)])
				client.subscribe('consoles/all/nodes/#')
				client.subscribe('consoles/all/weather2/#')
				client.subscribe('consoles/+/status')
				client.subscribe('consoles/+/resp')
			self.loopexited = False

		# noinspection PyUnusedLocal
		def on_disconnect(client, userdata, rc):

			logsupport.Logs.Log("{}: Disconnected stream {} with result code {}".format(self.name, self.MQTTnum, rc))
			self.discon.Op()

		# noinspection PyUnusedLocal


		# noinspection PyUnusedLocal
		def on_message(client, userdata, msg):
			msgtopic = msg.topic
			try:
				self.rcvd.Op()
				# command to force get: mosquitto_pub -t consoles/all/cmd -m getstable;  mosquitto_pub -t consoles/all/cmd -m restart
				loopstart = time.time()
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
					logsupport.Logs.Log(
						'{}: Remote command received on {} from {}-{}: {} {}'.format(self.name, msgtopic, fromnd, seq,
																					 cmd, cmdparam))
					issuecommands.IssueCommand(self.name, cmd, seq, fromnd, param=cmdparam)
					# if fromnd != 'unknown':
					#	self.Publish('resp', '{}|ok|{}'.format(cmd, seq), fromnd)
					return
				elif msgtopic in ('consoles/all/set', 'consoles/' + hw.hostname + '/set'):
					d = json.loads(CheckPayload(msg.payload.decode('ascii'), msgtopic, 'mqtt-consoles-set'))
					try:
						logsupport.Logs.Log('{}: set {} = {}'.format(self.name, d['name'], d['value']))
						valuestore.SetVal(d['name'], d['value'])
					except Exception as E:
						logsupport.Logs.Log('Bad set via MQTT: {} Exc: {}'.format(repr(d), E), severity=ConsoleWarning)
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
									logsupport.Logs.Log(
										'Exception posting event from mqtt resp: ({}) Exception {}'.format(
											(self.name, msgdcd, respnode, userdata), E), severity=ConsoleError)
						return

				# noinspection PySimplifyBooleanCheck
				# not a command/status message
				if var == []:
					logsupport.Logs.Log('Unknown topic ', msgtopic, ' from broker ', self.name,
										severity=ConsoleWarning)
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
								logsupport.Logs.Log('Error handling json MQTT item: ', v.name, str(v.jsonflds),
													msg.payload.decode('ascii'), str(e), repr(payload),
													severity=ConsoleWarning)
				loopend = time.time()
				self.HB.Entry('Processing time: {} Done: {}'.format(loopend - loopstart, repr(msg)))
				time.sleep(.1)  # force thread to give up processor to allow response to time events
			except Exception as E:
				logsupport.Logs.Log('MQTT Error: {} topic: {} msg: {}'.format(repr(E), msgtopic, msg.payload))

		# self.HB.Entry('Gave up control for: {}'.format(time.time() - loopend))

		# noinspection PyUnusedLocal
		def on_log(client, userdata, level, buf):
			logsupport.Logs.Log("MQTT Log: ", str(level), " buf: ", str(buf), severity=ConsoleWarning)

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

		self.address = configsect.get('address', 'mqtt')
		self.username = configsect.get('username', None)
		self.password = configsect.get('password', None)
		if self.username is not None:
			self.auth = {"username": self.username, "password": self.password}
		else:
			self.auth = None
		self.reportstatus = configsect.get('ReportStatus', False)
		self.vars = {}
		self.ids = {}
		self.topicindex = {}  # dict from full topics to MQitems
		self.loopexited = True
		self.MQTTnum = 0

		for itemname, value in configsect.items():
			if isinstance(value, Section):
				self.vars[itemname] = _parsesection([itemname], value)

		self.MQTTclient = mqtt.Client(userdata=self)
		self.MQTTclient.username_pw_set(self.username, self.password)
		self.MQTTclient.on_connect = on_connect
		self.MQTTclient.on_message = on_message
		self.MQTTclient.on_disconnect = on_disconnect
		if self.reportstatus or logsupport.primaryBroker is None:
			topic = 'consoles/' + hw.hostname + '/status'
			self.MQTTclient.will_set(topic, json.dumps({'status': 'dead'}), retain=True)
			logsupport.primaryBroker = self
			self.MQTTrunning = False
			# register the console
			self.Publish(node='all/nodes', topic=hw.hostname,
						 payload=json.dumps(
							 {'registered': time.time(),
							  'versionname': config.sysStore.versionname,
							  'versionsha': config.sysStore.versionsha,
							  'versiondnld': config.sysStore.versiondnld,
							  'versioncommit': config.sysStore.versioncommit,
							  'boottime': hw.boottime,
							  'osversion': hw.osversion,
							  'hw': hw.hwinfo}),
						 retain=True, qos=1)
		threadmanager.SetUpHelperThread(self.name, self.MQTTLoop)
		config.mqttavailable = True
		config.MQTTBroker = self

	def MQTTLoop(self):
		try:
			self.MQTTclient.connect(self.address, keepalive=20)
		except Exception as E:
			self.MQTTCommFailed = True
			logsupport.Logs.Log('Exception connecting to MQTT - authentication or server down error ({})'.format(E),
								severity=ConsoleError)
			threadmanager.DeleteHelperThread(self.name)
			return
		self.MQTTrunning = True
		self.MQTTnum += 1
		self.MQTTclient.loop_forever()
		# self.MQTTclient.disconnect()
		logsupport.Logs.Log("MQTT handler thread ended for: " + self.name, severity=ConsoleWarning)
		self.loopexited = True
		self.MQTTrunning = False

	def GetValByID(self, lclid):
		self.GetVal(self.ids[lclid])

	def SetVal(self, name, val, modifier=None):
		logsupport.Logs.Log("Can't set MQTT subscribed var within console: ", name)

	def GetVal(self, name, failok=False):
		n2 = ''
		# noinspection PyBroadException
		try:
			n2 = self._normalizename(name)
			item, _ = self._accessitem(n2)
			if item.Expires + item.SetTime < time.time():
				# value is stale
				return None
			else:
				return item.Value
		except Exception as e:
			if not failok:
				logsupport.Logs.Log("Error accessing ", self.name, ":", str(name), str(n2), repr(e),
									severity=ConsoleError, tb=False)
			return None

	# noinspection PyUnusedLocal
	@staticmethod
	def SetValByID(lclid, val):
		logsupport.Logs.Log("Can't set MQTT subscribed var by id within console: ", str(lclid))

	def CommandResponse(self, success, cmd, seq, fromnd, value):
		resp = {'status': success, 'seq': seq, 'cmd': cmd, 'respfrom': hw.hostname}
		if value is not None:
			resp['value'] = value
		payld = json.dumps(resp)
		self.Publish('resp', payld, node=fromnd)

	def Publish(self, topic, payload=None, node=hw.hostname, qos=1, retain=False, viasvr=False):
		if self.MQTTCommFailed: return
		self.sent.Op()
		fulltopic = 'consoles/' + node + '/' + topic
		if self.MQTTrunning:
			try:
				self.MQTTclient.publish(fulltopic, payload, qos=qos, retain=retain)
			except Exception as E:
				self.MQTTCommFailed = True
				logsupport.Logs.Log('MQTT Publish error ({})'.format(repr(E)), severity=ConsoleError, localonly=True)
		else:
			if viasvr:
				logsupport.Logs.Log("{}: Publish attempt with server not running ({})".format(self.name, repr(payload)),
									severity=ConsoleWarning, localonly=True)  # don't push error to net if net is down
			else:
				try:
					publish.single(fulltopic, payload, hostname=self.address, qos=qos, retain=retain, auth=self.auth)
				except Exception as E:
					self.MQTTCommFailed = True
					logsupport.Logs.Log("MQTT single publish error ({})".format(repr(E)), severity=ConsoleError,
										localonly=True)
	# noinspection PyUnusedLocal
	def PushToMQTT(self, storeitem, old, new, param, modifier):
		self.Publish('/'.join(storeitem.name), str(new))
