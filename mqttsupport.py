import paho.mqtt.client as mqtt
import config
from logsupport import ConsoleWarning
from configobj import Section
from collections import namedtuple
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

		self.address = configsect.get('address',None)
		self.password = configsect.get('password',None)
		self.name = name
		self.vars = {}
		for i,v in configsect.iteritems():
			if isinstance(v,Section):
				tp = v.get('TopicType', str)
				if tp == 'float':
					tpcvrt = float
				elif tp == 'int':
					tpcvrt = int
				else:
					tpcvrt = str
				self.vars[i] = MQitem(v.get('Topic',None),tpcvrt,int(v.get('Expires',99999999999999999))) # todo pub?
		self.MQTTclient = mqtt.Client(userdata=self)
		self.MQTTclient.on_connect = on_connect
		self.MQTTclient.on_message = on_message
		self.MQTTclient.on_disconnect = on_disconnect
		self.MQTTclient.connect(self.address)
		self.MQTTclient.loop_start()




