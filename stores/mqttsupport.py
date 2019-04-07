import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

import hw
import logsupport
import config
import json
from controlevents import CEvent, PostEvent, ConsoleEvent
import exitutils
import maintscreen
import subprocess
import historybuffer
import functools
import threading

from logsupport import ConsoleWarning, ConsoleError, ConsoleInfo, ReportStatus
# noinspection PyProtectedMember
from configobj import Section
import time
from stores import valuestore
import threadmanager


class MQitem(valuestore.StoreItem):
	def __init__(self, name, Topic, Type, Expires, jsonflds, Store):
		self.Topic = Topic
		self.jsonflds = jsonflds
		self.Expires = Expires
		super(MQitem, self).__init__(name, None, store=Store, vt=Type)

class MQTTBroker(valuestore.ValueStore):

	def __init__(self, name, configsect):
		super(MQTTBroker, self).__init__(name, itemtyp=MQitem)
		MQTTnum = 0
		self.fetcher = None
		self.HB = historybuffer.HistoryBuffer(40, name)

		# noinspection PyUnusedLocal
		def on_connect(client, userdata, flags, rc):
			logm = "Connected" if self.loopexited else "Reconnected"
			logsupport.Logs.Log("{}: {} stream {} with result code {}".format(self.name, logm, self.MQTTnum, rc))
			for i, _ in userdata.topicindex.items():
				client.subscribe(i)
			if logsupport.primaryBroker == self:
				client.subscribe([('consoles/all/errors', 1),
								  ('consoles/all/cmd', 1),
								  ('consoles/' + hw.hostname + '/cmd', 1),
								  ('consoles/' + hw.hostname + '/set', 1),
								  ('consoles/all/set', 1)])
			self.loopexited = False

		#			for i, v in userdata.vars.items():
		#				client.subscribe(v.Topic)

		# noinspection PyUnusedLocal
		def on_disconnect(client, userdata, rc):
			logsupport.Logs.Log("{}: Disconnected stream {} with result code {}".format(self.name, self.MQTTnum, rc))

		# noinspection PyUnusedLocal
		def DoRestart():
			while self.fetcher is not None and self.fetcher.is_alive():
				logsupport.Logs.Log('Delaying restart until fetch completes')
				ReportStatus('wait restart')
				time.sleep(30)
			ReportStatus('rmt restart')
			exitutils.Exit_Screen_Message('Remote restart requested', 'Remote Restart')
			exitutils.Exit(exitutils.REMOTERESTART)

		def GetStable():
			self.fetcher = threading.Thread(name='FetchStableRemote', target=maintscreen.fetch_stable, daemon=True)
			self.fetcher.start()

		# maintscreen.fetch_stable()  # todo should do in separate thread

		def GetBeta():
			self.fetcher = threading.Thread(name='FetchBetaRemote', target=maintscreen.fetch_beta, daemon=True)
			self.fetcher.start()

		#maintscreen.fetch_beta()

		def UseStable():
			subprocess.Popen('sudo rm /home/pi/usebeta', shell=True)  # should move all these to some common place todo

		def UseBeta():
			subprocess.Popen('sudo touch /home/pi/usebeta', shell=True)

		def DumpHB():
			entrytime = time.strftime('%m-%d-%y %H:%M:%S')
			historybuffer.DumpAll('Command Dump', entrytime)

		def EchoStat():
			ReportStatus('running stat')

		def LogItem(sev):
			logsupport.Logs.Log('Remotely forced test message ({})'.format(sev), severity=sev, tb=False, hb=False)

		def on_message(client, userdata, msg):
			#print time.ctime() + " Received message " + str(msg.payload) + " on topic "  + msg.topic + " with QoS " + str(msg.qos)
			loopstart = time.time()
			var = []
			for t, item in userdata.topicindex.items():
				if t == msg.topic:
					var.extend(item)

			if msg.topic in ('consoles/all/cmd', 'consoles/' + hw.hostname + '/cmd'):
				cmd = msg.payload.decode('ascii')
				logsupport.Logs.Log('{}: Remote command received on {}: {}'.format(self.name, msg.topic, cmd))
				cmdcalls = {'restart': DoRestart,
							'getstable': GetStable,
							'getbeta': GetBeta,
							'usestable': UseStable,
							'usebeta': UseBeta,
							'hbdump': DumpHB,
							'status': EchoStat,
							'issueerror': functools.partial(LogItem, ConsoleError),
							'issuewarning': functools.partial(LogItem, ConsoleWarning),
							'issueinfo': functools.partial(LogItem, ConsoleInfo)}
				if cmd.lower() in cmdcalls:
					try:
						PostEvent(ConsoleEvent(CEvent.RunProc,name=cmd, proc=cmdcalls[cmd.lower()]))
					except Exception as E:
						logsupport.Logs.Log('Exc: {}'.format(repr(E)))
				else:
					logsupport.Logs.Log('{}: Unknown remote command request: {}'.format(self.name, cmd),
										severity=ConsoleWarning)
				return
			elif msg.topic == 'consoles/all/errors':
				d = json.loads(msg.payload.decode('ascii'))
				if d['node'] != hw.hostname:
					logsupport.Logs.LogRemote(d['node'], d['entry'], severity=d['sev'],
											  etime=d['etime'] if 'etime' in d else 0)
				return
			elif msg.topic in ('consoles/all/set', 'consoles/' + hw.hostname + '/set'):
				d = json.loads(msg.payload.decode('ascii'))
				try:
					logsupport.Logs.Log('{}: set {} = {}'.format(self.name, d['name'], d['value']))
					store = valuestore.SetVal(d['name'], d['value'])
				except Exception as E:
					logsupport.Logs.Log('Bad set via MQTT: {} Exc: {}'.format(repr(d), E), severity=ConsoleWarning)
				return

			# noinspection PySimplifyBooleanCheck
			if var == []:
				logsupport.Logs.Log('Unknown topic ',msg.topic, ' from broker ',self.name,severity=ConsoleWarning)
			else:
				for v in var:
					v.SetTime = time.time()
					if not v.jsonflds:
						v.Value = v.Type(msg.payload)
					# debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ', v.Value)
					else:
						payload = '*bad json*' + msg.payload.decode('ascii')  # for exception log below
						try:
							payload = json.loads(msg.payload.decode('ascii').replace('nan','null')) # work around bug in tasmota returning bad json
							for i in v.jsonflds:
								payload = payload[i]
							if payload is not None:
								v.Value = v.Type(payload)
							else:
								v.Value = None
						#debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ', v.Value)
						except Exception as e:
							logsupport.Logs.Log('Error handling json MQTT item: ', v.name, str(v.jsonflds),
												msg.payload.decode('ascii'), str(e), repr(payload), severity=ConsoleWarning)
			loopend = time.time()
			self.HB.Entry('Processing time: {} Done: {}'.format(loopend - loopstart, repr(msg)))  # todo try to force other thread to run
			time.sleep(.1)  # force thread to give up processor to allow response to time events
			self.HB.Entry('Gave up control for: {}'.format(time.time() - loopend))

		# noinspection PyUnusedLocal
		def on_log(client, userdata, level, buf):
			logsupport.Logs.Log("MQTT Log: ",str(level)," buf: ",str(buf),severity=ConsoleWarning)
			#print time.ctime() + " MQTT Log " + str(level) + '  ' + str(buf)

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
				jsonflds = sect.get('json', [])
				if jsonflds: jsonflds = jsonflds.split(':')
				tpc = (prefix + '/' + thistopic).lstrip('/')
				rtn = MQitem(nm, tpc, tpcvrt, int(sect.get('Expires', 99999999999999999)), jsonflds, self)
				if tpc in self.topicindex:
					self.topicindex[tpc].append(rtn)
				else:
					self.topicindex[tpc] = [rtn]
				return rtn



		self.address = configsect.get('address',None)
		self.password = configsect.get('password',None)
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
							  'versionname': config.versionname,
							  'versionsha': config.versionsha,
							  'versiondnld': config.versiondnld,
							  'versioncommit': config.versioncommit,
							  'boottime': hw.bootime,
							  'osversion': hw.osversion,
							  'hw': hw.hwinfo}),
						 retain=True, qos=1)
		threadmanager.SetUpHelperThread(self.name,self.MQTTLoop)


	def MQTTLoop(self):
		self.MQTTclient.connect(self.address, keepalive=20)
		self.MQTTrunning = True
		self.MQTTnum += 1
		self.MQTTclient.loop_forever()
		# self.MQTTclient.disconnect()
		logsupport.Logs.Log("MQTT handler thread ended for: "+self.name,severity=ConsoleWarning)
		self.loopexited = True
		self.MQTTrunning = False

	def GetValByID(self, lclid):
		self.GetVal(self.ids[lclid])

	def SetVal(self,name, val, modifier = None):
		logsupport.Logs.Log("Can't set MQTT subscribed var within console: ",name)

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

	def Publish(self, topic, payload=None, node=hw.hostname, qos=1, retain=False, viasvr=False):
		fulltopic = 'consoles/' + node + '/' + topic
		if self.MQTTrunning:
			self.MQTTclient.publish(fulltopic, payload, qos=qos, retain=retain)
		else:
			if viasvr:
				logsupport.Logs.Log("{}: Publish attempt with server not running ({})".format(self.name, repr(payload)),
									severity=ConsoleWarning)  # todo wrong = happens under lock
			else:
				publish.single(fulltopic, payload, hostname=self.address, qos=qos, retain=retain)

	def PushToMQTT(self, storeitem, old, new, param, modifier):
		self.Publish('/'.join(storeitem.name), str(new))
