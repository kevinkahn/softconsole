import hw

consolestatus = 'started'

hubtypes = {}
Hubs = {}
defaulthub = None
defaulthubname = ""
defaultISYname = 'ISY'
hooks = None

WeathProvs = {}

starttime = 0
Running = True
Console_pid = 0
PRESS = 0
FASTPRESS = 1
ecode = 0 # exit code set for main loop

personalsystem = False
lastup = 0  # last time upstatus known
previousup = 0  # previous lifetime

monofont = "notomono"  # gets reset to "droidsansmono" if noto not present to support pre Stretch

# Global pointers
exdir = ''
homedir = ''

screen = None  # pygame screen to blit on etc
DS = None  # GlDaemobal Display Screen handles running the button presses and touch recognition
Alerts = []
configfile = ""  # issue with moving to console is using value on an exit/restart

versionname = ""
versionsha = ""
versiondnld = ""
versioncommit = ""

horizborder = 20  # todo move to __screen?
topborder = 20
botborder = 80
cmdvertspace = 10  # this is the space around the top/bot of  cmd button within the bot border

# Operational global navigation roots
SonosScreen = None  # todo hack to handle late appearing players
# _____________________________

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


