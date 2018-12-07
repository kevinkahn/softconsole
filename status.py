import paho.mqtt.client as mqtt
from datetime import datetime
import os
import time
import json

nodetable = {}
tm = time.time()


def paint():
	os.system('clear')
	print("{:^12s} {:^10s} E {:^25s}  {:^19s}".format('Node', 'Status', 'Uptime', 'Last Boot'))
	for n, info in nodetable.items():
		print("{:12.12s} ".format(n), end='')
		print("{:10.10s} ".format(info['status']), end='')
		if info['status'] == 'dead':
			print("{:29.29s}".format(' '), end='')
		else:
			print(info['error'], end='')
			if 'uptime' in info:
				print(" {:>25.25s}  ".format(interval_str(info['uptime'])), end='')
		if info['boottime'] == 0:
			print("{:^19.19}".format('unknown'))
		else:
			print("{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(info['boottime'])))


def interval_str(sec_elapsed):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	return "{} days {:>02d}hrs {:>02d}mn {:>02d}sec".format(d, h, m, s)


def on_connect(client, ud, flags, rc):
	# client.subscribe('consoles/all/#')
	client.subscribe('consoles/all/nodes/#')
	client.subscribe('consoles/+/status')


# client.subscribe('consoles/rpi-dev7')

def on_message(client, ud, msg):
	# print('message')
	# print(msg.topic+  repr(msg.payload) + str(msg.timestamp))
	try:
		topic = msg.topic.split('/')
		msgdcd = json.loads(msg.payload.decode('ascii'))
		if topic[2] == 'nodes':
			nd = topic[-1]
			if nd not in nodetable: nodetable[nd] = {'status': 'unknown', 'boottime': 0, 'uptime': 0, 'error': '-'}
			if 'boottime' in msgdcd: nodetable[nd]['boottime'] = msgdcd['boottime']
		elif topic[2] == 'status':
			nd = topic[1]
			if nd not in nodetable: nodetable[nd] = {'status': 'unknown', 'boottime': 0, 'uptime': 0, 'error': '-'}
			nodetable[nd]['status'] = msgdcd['status']
			nodetable[nd]['uptime'] = msgdcd['uptime']
			if 'error' in msgdcd:
				nodetable[nd]['error'] = (' ', '*')[msgdcd['error'] != -1]
	except Exception as E:
		print("Exception: {}".format(repr(E)))
	if time.time() - tm > 2:
		paint()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.loop_start()
client.connect('rpi-kck.pdxhome')
try:
	time.sleep(1)
	try:
		paint()
	except Exception as E:
		print(repr(E))
	while True:
		pass
except KeyboardInterrupt:
	print()
