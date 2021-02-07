import time

from utils import hw
import os

hooks = None

Running = False
Exiting = False
terminationreason = 'unknown'

PRESS = 0
FASTPRESS = 1
ecode = 0  # exit code set for main loop

# Operational global navigation roots
SonosScreen = None  # todo hack to handle late appearing players
AS = None  # Current Active Screen

# Avoids import loops
mqttavailable = False
MQTTBroker = None

sysstats = None

# Global Defaults Settable in config.txt in Console
sysStore = None

sysvals = {
	# name: (type, value, (AddAlertproc, param) or None, write to log)
	'DimLevel': (int, 10, (hw.ResetScreenLevel, True), True),
	'BrightLevel': (int, 100, (hw.ResetScreenLevel, False), True),
	'MultiTapTime': (int, 400, None, True),
	'HomeScreenName': (str, '', None, True),
	'MaxLogFiles': (int, 5, None, True),
	'LogFontSize': (int, 14, None, True),
	'DimHomeScreenCoverName': (str, "", None, False),
	'MainChain': (list, [], None, False),
	'SecondaryChain': (list, [], None, False),
	'DimIdleListNames': (list, [], None, True),
	'DimIdleListTimes': (list, [], None, True),
	'CurrentScreen': (str, '*None*', None, False),
	'ErrorNotice': (int, -1, None, False),
	'NetErrorIndicator': (bool, False, None, False),
	'LogStartTime': (int, 0, None, False),
	'FirstUnseenErrorTime': (int, 0, None, False),
	'ErrLogReconnects': (bool, True, None, True),
	'LongTapTime': (int, 1000, None, False)  # time in msec
}

# Non user sysfile entries
#  ConsoleStartTime
#  Console_pid
#  Watchdog_pid
#  AsyncLogger_pid
#  Topper_pid
#  PersonalSystem
#  ExecDir
#  HomeDir
#  versionname
#  versionsha
#  versiondnld
#  versioncommit
#  consolestatus
#  configfile
#  configdir
#  hostname

def ptf(pstr):
	if sysStore.versionname in ('homerelease', 'development'):
		with open('/home/pi/Console/weathtrace', 'a') as f:
			print('{}:{}'.format(time.strftime('%H:%M:%S', time.localtime(time.time())), pstr), file=f, flush=True)

lastfetch = 0


def ptf2(pstr):
	global lastfetch
	flag = '***' if time.time() - lastfetch < 150 else '   '
	lastfetch = time.time()

	if sysStore.versionname in ('homerelease', 'development'):
		with open('/home/pi/Console/weathhist', 'a') as f:
			print('{}{}:{}'.format(flag, time.strftime('%H:%M:%S', time.localtime(time.time())), pstr), file=f,
				  flush=True)


# noinspection PyBroadException
try:
	os.replace('/home/pi/Console/weathtrace', '/home/pi/Console/weathtrace.prev')
except:
	pass
# noinspection PyBroadException
try:
	os.replace('/home/pi/Console/weathhist', '/home/pi/Console/weathhist.prev')
except:
	pass
