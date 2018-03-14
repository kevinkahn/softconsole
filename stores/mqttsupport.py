import paho.mqtt.client as mqtt
import config
import logsupport
from logsupport import ConsoleWarning
from configobj import Section
import time
import valuestore
import threading
import threadmanager

class MQitem(valuestore.StoreItem):
	def __init__(self, name, Topic, Type, Expires):
		self.Topic = Topic
		super(MQitem,self).__init__(name, None,Type,Expires)

class MQTTBroker(valuestore.ValueStore):

	def __init__(self, name, configsect):
		super(MQTTBroker,self).__init__(name,refreshinterval=0,itemtyp=MQitem)
		def on_connect(client, userdata, flags, rc):
			logsupport.Logs.Log("Connected to ", self.name, " result code: " + str(rc))
			for i, v in userdata.vars.iteritems():
				client.subscribe(v.Topic)

		def on_disconnect(client, userdata, rc):
			logsupport.Logs.Log("Disconnected from ", self.name, "result code: " + str(rc))

		def on_message(client, userdata, msg):
			#print time.ctime() + " Received message " + str(msg.payload) + " on topic "  + msg.topic + " with QoS " + str(msg.qos)
			var = None
			for v,d in self.vars.iteritems():
				if d.Topic == msg.topic:
					var = v
					break
			if var is None:
				logsupport.Logs.Log('Unknown topic ',msg.topic, ' from broker ',self.name,severity=ConsoleWarning)
			else:
				self.vars[var].SetTime = time.time()
				self.vars[var].Value = self.vars[var].Type(msg.payload)

		def on_log(client, userdata, level, buf):
			logsupport.Logs.Log("MQTT Log: ",str(level)," buf: ",str(buf),severity=ConsoleWarning)
			print time.ctime() + " MQTT Log " + str(level) + '  ' + str(buf)

		self.address = configsect.get('address',None)
		self.password = configsect.get('password',None)
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
				self.vars[i] = MQitem(i, tpc, tpcvrt,int(v.get('Expires',99999999999999999)))
				self.ids[tpc] = i
		self.MQTTclient = mqtt.Client(userdata=self)
		self.MQTTclient.on_connect = on_connect
		self.MQTTclient.on_message = on_message
		self.MQTTclient.on_disconnect = on_disconnect
		threadmanager.HelperThreads[self.name] = threadmanager.ThreadItem(self.name, self.StartThread, self.StartThread)
		#self.MQTTclient.on_log = on_log
		#self.MQTTclient.connect(self.address)
		#self.MQTTclient.loop_start()

	def MQTTLoop(self):
		self.MQTTclient.connect(self.address)
		self.MQTTclient.loop_forever()
		self.MQTTclient.disconnect()
		logsupport.Logs.Log("MQTT handler thread ended for: "+self.name,severity=ConsoleWarning)

	def StartThread(self):
		threadmanager.HelperThreads[self.name].Thread = threading.Thread(name=self.name, target= self.MQTTLoop)
		threadmanager.HelperThreads[self.name].Thread.setDaemon(True)
		threadmanager.HelperThreads[self.name].Thread.start()

	def GetValByID(self,id):
		self.GetVal(self.ids[id])

	def SetVal(self,name, val):
		logsupport.Logs.Log("Can't set MQTT subscribed var within console: ",name)

	def SetValByID(self,id, val):
		logsupport.Logs.Log("Can't set MQTT subscribed var by id within console: ", str(id))

	#todo add pub support?






