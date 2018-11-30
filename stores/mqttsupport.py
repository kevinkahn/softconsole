import paho.mqtt.client as mqtt
import debug
import logsupport
import json
from logsupport import ConsoleWarning
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

		# noinspection PyUnusedLocal
		def on_connect(client, userdata, flags, rc):
			logm = "Connected" if self.loopexited else "Reconnected"
			logsupport.Logs.Log(logm + " to ", self.name, " result code: " + str(rc))
			for i, _ in userdata.topicindex.items():
				client.subscribe(i)
			self.loopexited = False

		#			for i, v in userdata.vars.items():
		#				client.subscribe(v.Topic)

		# noinspection PyUnusedLocal
		def on_disconnect(client, userdata, rc):
			logsupport.Logs.Log("Disconnected from ", self.name, " result code: " + str(rc))

		# noinspection PyUnusedLocal
		def on_message(client, userdata, msg):
			#print time.ctime() + " Received message " + str(msg.payload) + " on topic "  + msg.topic + " with QoS " + str(msg.qos)
			var = []
			for t, item in userdata.topicindex.items():
				if t == msg.topic:
					var.extend(item)

			# noinspection PySimplifyBooleanCheck
			if var == []:
				logsupport.Logs.Log('Unknown topic ',msg.topic, ' from broker ',self.name,severity=ConsoleWarning)
			else:
				for v in var:
					v.SetTime = time.time()
					if v.jsonflds == []:
						v.Value = v.Type(msg.payload)
					# debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ', v.Value)
					else:
						try:
							payload = '*bad json*'+msg.payload.decode('ascii') # for exception log below
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

		# noinspection PyUnusedLocal
		def on_log(client, userdata, level, buf):
			logsupport.Logs.Log("MQTT Log: ",str(level)," buf: ",str(buf),severity=ConsoleWarning)
			#print time.ctime() + " MQTT Log " + str(level) + '  ' + str(buf)

		def _parsesection(nm, sect, prefix=''):
			tp = sect.get('TopicType', 'string')
			if tp == 'group':
				thistopic = sect.get('Topic', nm[-1])
				rtn = {}
				for itemname, value in sect.items():
					rtn[itemname] = _parsesection(nm + [itemname], value, prefix=prefix + '/' + thistopic)
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
				if jsonflds != []: jsonflds = jsonflds.split(':')
				tpc = (prefix + '/' + thistopic).lstrip('/')
				rtn = MQitem(nm, tpc, tpcvrt, int(sect.get('Expires', 99999999999999999)), jsonflds, self)
				if tpc in self.topicindex:
					self.topicindex[tpc].append(rtn)
				else:
					self.topicindex[tpc] = [rtn]
				return rtn



		self.address = configsect.get('address',None)
		self.password = configsect.get('password',None)
		self.vars = {}
		self.ids = {}
		self.topicindex = {}  # dict from full topics to MQitems
		self.loopexited = True
		'''
		for itemname,value in configsect.items():
			if isinstance(value,Section):
				tp = value.get('TopicType', str)
				if tp == 'group':
					pass
				elif tp == 'float':
					tpcvrt = float
				elif tp == 'int':
					tpcvrt = int
				else:
					tpcvrt = str
				tpc = value.get('Topic',None)
				jsonflds = value.get('json', '').split(':')
				self.vars[itemname] = MQitem(itemname, tpc, tpcvrt,int(value.get('Expires',99999999999999999)),jsonflds,self)
				self.ids[tpc] = itemname
		'''
		for itemname, value in configsect.items():
			if isinstance(value, Section):
				self.vars[itemname] = _parsesection([itemname], value)

		self.MQTTclient = mqtt.Client(userdata=self)
		self.MQTTclient.on_connect = on_connect
		self.MQTTclient.on_message = on_message
		self.MQTTclient.on_disconnect = on_disconnect
		threadmanager.SetUpHelperThread(self.name,self.MQTTLoop)
		#self.MQTTclient.on_log = on_log
		#self.MQTTclient.connect(self.address)
		#self.MQTTclient.loop_start()

	def MQTTLoop(self):
		self.MQTTclient.connect(self.address)
		self.MQTTclient.loop_forever()
		self.MQTTclient.disconnect()
		logsupport.Logs.Log("MQTT handler thread ended for: "+self.name,severity=ConsoleWarning)
		self.loopexited = True

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
									severity=ConsoleError,
									tb=False)
			return None

	# noinspection PyUnusedLocal
	@staticmethod
	def SetValByID(lclid, val):
		logsupport.Logs.Log("Can't set MQTT subscribed var by id within console: ", str(lclid))







