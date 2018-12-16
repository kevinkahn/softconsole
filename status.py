import paho.mqtt.client as mqtt
from datetime import datetime
import os
import time
import json
import sys
import collections

nodetable = {}
tm = time.time()

nodes = collections.OrderedDict()
noderecord = collections.namedtuple('noderecord', ['status', 'uptime', 'error', 'rpttime', 'FirstUnseenErrorTime',
												   'GlobalLogViewTime', 'registered', 'versionname', 'versionsha',
												   'versiondnld', 'versioncommit', 'boottime', 'osversion', 'hw'])

defaults = {k: v for (k, v) in zip(noderecord._fields, (
	'unknown', 0, -2, 0, 0, 0, 0, '*unknown*', '*unknown*', '*unknown*', '*unknown*', 0, '*unknown*', '*unknown*'))}


# emptynode = noderecord(**{k:None for k in noderecord._fields})


def paint():
	os.system('clear')
	print("{:^12s} {:^10s} E {:^25s}  {:^19s}".format('Node', 'Status', 'Uptime', 'Last Boot'))
	# for n, info in nodetable.items():
	for n, info in nodes.items():
		print("{:12.12s} ".format(n), end='')
		print("{:10.10s} ".format(info.status), end='')
		if info.status in ('dead', 'unknown'):
			print("{:29.29s}".format(' '), end='')
		else:
			print(' ' if info.error == -1 else '?' if info.error == -1 else '*', end='')
			print(" {:>25.25s}  ".format(interval_str(info.uptime)), end='')
		if info.boottime == 0:
			print("{:^19.19}".format('unknown'))
		else:
			print("{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(info.boottime)), end='')
		age = time.time() - info.rpttime if info.rpttime != 0 else 0
		if age > 45:  # todo use to determine likely powerfail case
			print(' (old)')
		else:
			print()


def baseinfo():
	os.system('clear')
	print("Info:")
	for n, info in nodes.items():
		offline = ' (offline)' if info.status in ('dead', 'unknown') else ''
		print("{:12.12s} ({})  {}".format(n, info.versionname, offline))
		print(' HW: {} OS: {}'.format(info.hw, info.osversion))
		print(' Console: {} Dnld: {}'.format(info.versioncommit, info.versiondnld))


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
			# print(topic)
			# print(msgdcd)
			nd = topic[-1]
			if nd not in nodes:
				nodes[nd] = noderecord(**defaults)
			nodes[nd] = nodes[nd]._replace(**msgdcd)

		elif topic[2] == 'status':
			nd = topic[1]
			if nd not in nodes:
				nodes[nd] = noderecord(**defaults)
			nodes[nd] = nodes[nd]._replace(**msgdcd)

	#print(nodes)
	except Exception as E:
		print("Exception: {}".format(repr(E)))
	if time.time() - tm > 1:
		if len(sys.argv) > 1:
			baseinfo()
		else:
			paint()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.loop_start()
client.connect('rpi-kck.pdxhome')
try:
	#time.sleep(1)
	print('Starting')
	try:
		if len(sys.argv) > 1:
			baseinfo()
		else:
			paint()
	except RuntimeError:
		print('Runtime error')
	while True:
		pass
except KeyboardInterrupt:
	print()
except Exception as E:
	print('Exc: {}'.format(repr(E)))
