import paho.mqtt.client as mqtt
import json, time
from utilities import CheckPayload

NodeTally = {}
LocationTally = {}
LocLastFetch = {}
LocNames = {}
LocAve = {}
statdump = time.time() - 3700


def on_connect(client, userdata, flags, rc):
	print('Connected')
	client.subscribe('consoles/all/weather/#')


def on_message(client, userdata, msg):
	global statdump, NodeTally, LocationTally, LocLastFetch, LocNames
	try:
		topic = msg.topic.split('/')[4]
		payload = msg.payload.decode('ascii')
		p = json.loads(CheckPayload(payload, topic, 'watchweather'))
		loc = p['location']
		ft = p['fetchtime']
		fn = p['fetchingnode']
		if loc in LocationTally:
			LocationTally[loc] += 1
			gap = ft - LocLastFetch[loc]
			LocLastFetch[loc] = ft
		else:
			LocNames[loc] = topic
			LocationTally[loc] = 1
			LocLastFetch[loc] = ft
			gap = -1
		if fn in NodeTally:
			NodeTally[fn] += 1
		else:
			NodeTally[fn] = 1
		if time.time() - statdump > 3600:
			statdump = time.time()
			with open('tally', 'a') as f:
				f.write('----- Nodes --------\n')
				for n in NodeTally:
					f.write('{}: {}\n'.format(n, NodeTally[n]))
				f.write('----- Locations --------\n')
				for l in LocationTally:
					f.write('{}: {}    ({})\n'.format(LocNames[l], LocationTally[l], l))
			with open('watchw', 'a') as f:
				f.write('------\n')

		print(topic, fn, loc, p['fetchcount'], time.strftime('%H:%M:%S', time.localtime(ft)), gap)
		with open('watchw', 'a') as f:
			f.write('{}, {}, {}, {}, {}, {}\n'.format(topic, fn, gap, loc, ft, p['fetchcount']))
	except Exception as E:
		print('Exception in loop for {} E: {}'.format(topic, E))
		print(payload)


MQTTclient = mqtt.Client()
MQTTclient.on_connect = on_connect
MQTTclient.on_message = on_message

print('Starting')
MQTTclient.connect('mqtt')
print('Connecting')
with open('tally', 'w') as f:
	f.write('-------------\n')
with open('watchw', 'w') as f:
	f.write('-------------\n')
MQTTclient.loop_forever()
