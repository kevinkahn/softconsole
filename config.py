screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module

starttime = 0

WAITNORMALBUTTON = 1
WAITEXIT = 2
WAITISYCHANGE = 4
WAITEXTRACONTROLBUTTON = 5
# WAITDBLTAP = 7
WAITQUADTAP = 8
# WAITMAINTTAP = 9
WAITNORMALBUTTONFAST = 10

""" Daemon related stuff"""
toDaemon = None
fromDaemon = None
watchlist = ["init"]
watchstarttime = 0
DaemonProcess = None
seq = 0
streamid = ""

# Debug flags
Flags = {}
DbgFlags = ['Main', 'Daemon', 'BuildScreen', 'ISY']
ISYdebug = False
dbgscreenbuild = False
dbgMain = False
dbgdaemon = True


def debugPrint(flag, *args):
	if flag in DbgFlags:
		if Flags[flag]:
			for arg in args:
				print arg,
			print
	else:
		print "DEBUG FLAG NAME ERROR", flag


# Global pointers
ISYrequestsession = None  # handle for requests to ISY via the request interface
ISY = None  # Root of structure representing the ISY - filled in from ISY
screen = None  # pygame screen to blit on etc
backlight = None  # GPIO instance of pin 18
DS = None  # Global Display Screen handles running the button presses and touch recognition
ParsedConfigFile = None  # config.txt internal version
configfile = "/home/pi/Console/config.txt"  # default location of configfile, can be overridden by arg1
ISYprefix = ''  # holds the url prefix for rest interface
fonts = None
Logs = None

# Screen Display Info
screenwidth = 0
screenheight = 0

dispratioW = 1
dispratioH = 1
baseheight = 480  # program design height
basewidth = 320  # program design width
# todo should any of these be settable in global params?
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
