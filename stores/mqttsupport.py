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
		super(MQitem,self).__init__(name, None, store = Store, vt = Type,Expires = Expires)

class MQTTBroker(valuestore.ValueStore):

	def __init__(self, name, configsect):
		super(MQTTBroker,self).__init__(name,refreshinterval=0,itemtyp=MQitem)

		# noinspection PyUnusedLocal
		def on_connect(client, userdata, flags, rc):
			logsupport.Logs.Log("Connected to ", self.name, " result code: " + str(rc))
			for i, v in userdata.vars.items():
				client.subscribe(v.Topic)

		# noinspection PyUnusedLocal
		def on_disconnect(client, userdata, rc):
			logsupport.Logs.Log("Disconnected from ", self.name, "result code: " + str(rc))

		# noinspection PyUnusedLocal
		def on_message(client, userdata, msg):
			#print time.ctime() + " Received message " + str(msg.payload) + " on topic "  + msg.topic + " with QoS " + str(msg.qos)
			var = []
			for v,d in self.vars.items():
				if d.Topic == msg.topic:
					var.append(v)
			# noinspection PySimplifyBooleanCheck
			if var == []:
				logsupport.Logs.Log('Unknown topic ',msg.topic, ' from broker ',self.name,severity=ConsoleWarning)
			else:
				for v in var:
					self.vars[v].SetTime = time.time()
					if self.vars[v].jsonflds == []:
						self.vars[v].Value = self.vars[v].Type(msg.payload)
						debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ',
										 self.vars[v].Value)
					else:
						try:
							payload = json.loads(msg.payload.decode('ascii'))
							for i in self.vars[v].jsonflds:
								payload = payload[i]
							self.vars[v].Value = self.vars[v].Type(payload)
							debug.debugPrint('StoreTrack', "Store(mqtt): ", self.name, ':', v, ' Value: ',
											 self.vars[v].Value)
						except Exception as e:
							logsupport.Logs.Log('Error handling json MQTT item: ',str(self.vars[v].jsonflds),
												msg.payload.decode('ascii'),str(e), severity=ConsoleWarning)

		# noinspection PyUnusedLocal
		def on_log(client, userdata, level, buf):
			logsupport.Logs.Log("MQTT Log: ",str(level)," buf: ",str(buf),severity=ConsoleWarning)
			#print time.ctime() + " MQTT Log " + str(level) + '  ' + str(buf)

		self.address = configsect.get('address',None)
		self.password = configsect.get('password',None)
		self.vars = {}
		self.ids = {}
		for itemname,value in configsect.items():
			if isinstance(value,Section):
				tp = value.get('TopicType', str)
				if tp == 'float':
					tpcvrt = float
				elif tp == 'int':
					tpcvrt = int
				else:
					tpcvrt = str
				tpc = value.get('Topic',None)
				jsonflds = value.get('json', '').split(':')
				self.vars[itemname] = MQitem(itemname, tpc, tpcvrt,int(value.get('Expires',99999999999999999)),jsonflds,self)
				self.ids[tpc] = itemname
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

	def GetValByID(self, lclid):
		self.GetVal(self.ids[lclid])

	def SetVal(self,name, val, modifier = None):
		logsupport.Logs.Log("Can't set MQTT subscribed var within console: ",name)

	# noinspection PyUnusedLocal
	@staticmethod
	def SetValByID(lclid, val):
		logsupport.Logs.Log("Can't set MQTT subscribed var by id within console: ", str(lclid))







