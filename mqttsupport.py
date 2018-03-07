import paho.mqtt.client as mqtt
import config
from logsupport import ConsoleWarning
from configobj import Section
import time


class MQitem(object):
	def __init__(self,Topic, Type, Expires):
		self.Topic = Topic
		self.Type  = Type
		self.RcvTime = 0
		self.Expires = Expires
		self.Value = None


class MQTTBroker(object):

	def __init__(self, name, configsect):
		def on_connect(client, userdata, flags, rc):
			config.Logs.Log("Connected to ", self.name, " result code: " + str(rc))
			for i, v in userdata.vars.iteritems():
				client.subscribe(v.Topic)

		def on_disconnect(client, userdata, rc):
			config.Logs.Log("Disconnected from ", self.name, "result code: " + str(rc))

		def on_message(client, userdata, msg):
			print time.ctime() + " Received message " + str(msg.payload) + " on topic "  + msg.topic + " with QoS " + str(msg.qos)
			var = None
			for v,d in self.vars.iteritems():
				if d.Topic == msg.topic:
					var = v
					break
			if var is None:
				config.Logs.Log('Unknown topic ',msg.topic, ' from broker ',self.name,severity=ConsoleWarning)
			else:
				self.vars[var].RcvTime = time.time()
				self.vars[var].Value = self.vars[var].Type(msg.payload)

		def on_log(client, userdata, level, buf):
			config.Logs.Log("MQTT Log: ",str(level)," buf: ",str(buf),severity=ConsoleWarning)
			print time.ctime() + " MQTT Log " + str(level) + '  ' + str(buf)

		self.address = configsect.get('address',None)
		self.password = configsect.get('password',None)
		self.name = name
		self.vars = {}
		self.ids = {}
		for i,v in configsect.iteritems():
			if isinstance(v,Section):
				tp = v.get('TopicType', str)
				if tp == 'float':
					tpcvrt = float
				elif tp == 'int':
					tpcvrt = int
				else:
					tpcvrt = str
				tpc = v.get('Topic',None)
				self.vars[i] = MQitem(tpc, tpcvrt,int(v.get('Expires',99999999999999999))) # todo pub?
				self.ids[tpc] = i
		self.MQTTclient = mqtt.Client(userdata=self)
		self.MQTTclient.on_connect = on_connect
		self.MQTTclient.on_message = on_message
		self.MQTTclient.on_disconnect = on_disconnect
		#self.MQTTclient.on_log = on_log
		self.MQTTclient.connect(self.address)
		self.MQTTclient.loop_start()

	def GetVal(self,name): # make name a sequence
		try:
			t = self.vars[name]
			if t.Expires + t.RcvTime < time.time():
				# value is stale
				return None
			else:
				return t.Value
		except:
			config.Logs.Log("(MQTT) Error accessing ",self.name, ":",name,severity=ConsoleWarning)

	def GetValByID(self,id):
		self.GetVal(self.ids[id])

	def SetVal(self,name, val):
		config.Logs.Log("Can't set MQTT subscribed var within console: ",name)

	def SetValById(self,id, val):
		config.Logs.Log("Can't set MQTT subscribed var by id within console: ", str(id))

	#todo add pub support?






