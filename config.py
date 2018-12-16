import hw

consolestatus = 'started'

hubtypes = {}
Hubs = {}
defaulthub = None  # move at least the name to sysStore todo other stuff should go to a __hubs.py file?
defaulthubname = ""
hooks = None

starttime = 0
Running = True
Console_pid = 0
PRESS = 0
FASTPRESS = 1
ecode = 0 # exit code set for main loop

personalsystem = False
lastup = 0  # last time upstatus known
previousup = 0  # previous lifetime

# Global pointers
exdir = ''
homedir = ''

screen = None  # pygame screen to blit on etc
DS = None  # GlDaemobal Display Screen handles running the button presses and touch recognition
configfile = ""  # issue with moving to console is using value on an exit/restart

versionname = ""
versionsha = ""
versiondnld = ""
versioncommit = ""

# Operational global navigation roots
SonosScreen = None  # todo hack to handle late appearing players

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
	'LogStartTime': (int, 0, None, False),
	'FirstUnseenErrorTime': (int, 0, None, False),
	'GlobalLogViewTime': (int, 0, None, False)
}


