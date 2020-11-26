import collections
import json
import os
import sys
import time
from itertools import zip_longest
from datetime import datetime
import statusinput
from utils.utilities import CheckPayload

import paho.mqtt.client as mqtt

nodetable = {}
tm = time.time()

nodes = collections.OrderedDict()
noderecord = collections.namedtuple('noderecord', ['status', 'uptime', 'error', 'rpttime', 'FirstUnseenErrorTime',
												   'registered', 'versionname', 'versionsha',
												   'versiondnld', 'versioncommit', 'boottime', 'osversion', 'hw',
												   'DarkSkyfetchs', 'Weatherbitfetches', 'queuetimemax24',
												   'queuetimemax24time',
												   'queuedepthmax24', 'maincyclecnt', 'queuedepthmax24time',
												   'queuetimemaxtime', 'daystartloops', 'queuedepthmax', 'queuetimemax',
												   'DarkSkyfetches24', 'Weatherbitfetches24', 'queuedepthmaxtime'])

defaults = {k: v for (k, v) in zip_longest(noderecord._fields, (
	'unknown', 0, -2, 0, 0, 0, 0), fillvalue='unknown*')}


# emptynode = noderecord(**{k:None for k in noderecord._fields})


def paint():
	os.system('clear')
	print("Status (h for hardware, v for console version):")
	print("{:^12s} {:^10s} {:^4s} E {:^14s}  {:^19s}".format('Node', 'Status', 'QMax', 'Uptime', 'Last Boot'))
	# for n, info in nodetable.items():
	for n, info in nodes.items():
		print("{:12.12s} ".format(n), end='')
		if info.maincyclecnt == 'unknown*':
			stat = info.status
			qmax = '     '
		else:
			stat = '{} cyc'.format(info.maincyclecnt) if info.status == 'idle' else info.status
			qmax = '{:4.2f} '.format(info.queuetimemax24)

		print("{:10.10s} {}".format(stat, qmax), end='')
		if info.status in ('dead', 'unknown'):
			print("{:20.20s}".format(' '), end='')
		else:
			print(' ' if info.error == -1 else '?' if info.error == -1 else '*', end='')
			print(" {:>14.14s}  ".format(interval_str(info.uptime)), end='')
		if info.boottime == 0:
			print("{:^17.17}".format('unknown'))
		else:
			print("{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(info.boottime)), end='')
		age = time.time() - info.rpttime if info.rpttime != 0 else 0
		# print("{:%Y-%m-%d %H:%M:%S}".format(datetime.fromtimestamp(info.rpttime)), end='')
		if age > 180:  # seconds?  todo use to determine likely powerfail case
			print(' (old:{})'.format(age))
			print('Boottime: {}'.format(info.boottime))
		else:
			print()


def baseinfo():
	os.system('clear')
	print("Hardware (s for status, v for console version):")
	for n, info in nodes.items():
		offline = ' (offline)' if info.status in ('dead', 'unknown') else ''
		print("{:12.12s} {} {}".format(n, info.hw, offline))
		print('             {}'.format(info.osversion))


def swinfo():
	os.system('clear')
	print("Software (s for status, h for hardware info):")
	for n, info in nodes.items():
		offline = ' (offline)' if info.status in ('dead', 'unknown') else ''
		print("{:12.12s} ({}) of {} {}".format(n, info.versionname, info.versioncommit, offline))
		print('             Downloaded: {}'.format(info.versiondnld))

def interval_str(sec_elapsed):
	d = int(sec_elapsed / (60 * 60 * 24))
	h = int((sec_elapsed % (60 * 60 * 24)) / 3600)
	m = int((sec_elapsed % (60 * 60)) / 60)
	s = int(sec_elapsed % 60)
	return "{} dys {:>02d}:{:>02d}:{:>02d}".format(d, h, m, s)


# noinspection PyUnusedLocal
def on_connect(mqclient, ud, flags, rc):
	# client.subscribe('consoles/all/#')
	mqclient.subscribe('consoles/all/nodes/#')
	mqclient.subscribe('consoles/+/status')


# client.subscribe('consoles/rpi-dev7')

# noinspection PyUnusedLocal
def on_message(mqclient, ud, msg):
	global screen
	# print('message')
	# print(msg.topic+  repr(msg.payload) + str(msg.timestamp))
	try:
		topic = msg.topic.split('/')
		msgdcd = json.loads(CheckPayload(msg.payload.decode('ascii'), topic, 'statusmsg'))
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

	# print(nodes)
	except Exception as Ex:
		print("Exception: {}".format(repr(Ex)))
	if KB.kbhit():
		c = KB.getch()
		if c == 's':
			screen = 'status'
		elif c == 'h':
			screen = 'os'
		elif c == 'v':
			screen = 'system'

	if True:  # time.time() - tm > 1:
		tm = time.time()
		if screen == 'status':
			paint()
		elif screen == 'os':
			baseinfo()
		elif screen == 'system':
			swinfo()


# if len(sys.argv) > 1:
#	baseinfo()
# else:
#	paint()

KB = statusinput.KBHit()
screen = 'status'
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.loop_start()
# client.connect('rpi-kck.pdxhome')
client.connect('rpi-pgaw1.pgawhome')
try:
	# time.sleep(1)
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
