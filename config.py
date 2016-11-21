screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module
alertprocs = {}  # set by modules from alerts directory
alertscreens = {}
alertscreentype = None

starttime = 0
Console_pid = 0
Daemon_pid = 0
Ending = False
PRESS = 1
FASTPRESS = 2

""" Daemon related stuff"""
toDaemon = None
fromDaemon = None
watchlist = []  # todo can this be moved to somewhere else - it isn't shared at all
varlist = []
watchstarttime = 0
DaemonProcess = None
seq = 0
streamid = ""

# Debug flags
Flags = {}
DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISY', 'Dispatch', 'EventList', 'Fonts']
dbgscreenbuild = False
dbgMain = False
dbgdaemon = False


def debugPrint(flag, *args):
	if flag in DbgFlags:
		if Flags[flag]:
			print flag, '-> ',
			for arg in args:
				print arg,
			print
			if Logs <> None:
				Logs.Log(*args, severity=-1, diskonly=True)
	else:
		print "DEBUG FLAG NAME ERROR", flag


# Global pointers
exdir = ''
ISYrequestsession = None  # handle for requests to ISY via the request interface
ISY = None  # Root of structure representing the ISY - filled in from ISY
screen = None  # pygame screen to blit on etc
backlight = None  # GPIO instance of pin 18
DS = None  # GlDaemobal Display Screen handles running the button presses and touch recognition
Alerts = []
ParsedConfigFile = None  # config.txt internal version
configfile = "/home/pi/Console/config.txt"  # default location of configfile, can be overridden by arg1
ISYprefix = ''  # holds the url prefix for rest interface
fonts = None
Logs = None

configfilelist = {}  # list of configfiles and their timestamps

TermShortener = {}
versionname = ""
versionsha = ""
lastalertcheck = 0

# Screen Display Info
screenwidth = 0
screenheight = 0

dispratioW = 1
dispratioH = 1
baseheight = 480  # program design height
basewidth = 320  # program design width

horizborder = 20
topborder = 20
botborder = 80
cmdvertspace = 10  # this is the space around the top/bot of  cmd button within the bot border

# Operational global navigation roots
CurrentScreen = None
HomeScreen = None
HomeScreen2 = None
MaintScreen = None
DimHomeScreenCover = None
DimIdleList = []
DimIdleTimes = []
MainDict = {}  # map: name:screen
SecondaryDict = {}
ExtraDict = {}
