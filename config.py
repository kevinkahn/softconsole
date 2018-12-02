import hw

screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module
screenparamuse = {}

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
hostname = ""
screentype = ""
portrait = True
lastup = 0  # last time upstatus known
previousup = 0  # previous lifetime

monofont = "notomono"  # gets reset to "droidsansmono" if noto not present to support pre Stretch

# Global pointers
exdir = ''
homedir = ''

screen = None  # pygame screen to blit on etc
backlight = None  # GPIO instance of pin 18
DS = None  # GlDaemobal Display Screen handles running the button presses and touch recognition
Alerts = []
ParsedConfigFile = None  # config.txt internal version
configfilebase = "/home/pi/Console/"  # default location of configfile, can be overridden by arg1.
configfile = ""
fonts = None

configfilelist = {}  # list of configfiles and their timestamps

versionname = ""
versionsha = ""
versiondnld = ""
versioncommit = ""

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
HomeScreen = None
HomeScreen2 = None
MaintScreen = None
DimHomeScreenCover = None
DimIdleList = []
DimIdleTimes = []
MainDict = {}  # map: name:screen
SecondaryDict = {}
ExtraDict = {}
ExtraChain = []
# _____________________________

# Global Defaults Settable in config.txt in Console
sysStore = None

sysvals = {
	'DimLevel': (int, 10, (hw.ResetScreenLevel, True)),
	'BrightLevel': (int, 100, (hw.ResetScreenLevel, False)),
	'MultiTapTime': (int, 400, None),
	'HomeScreenName': (str, '', None),
	'MaxLogFiles': (int, 5, None),
	'LogFontSize': (int, 14, None),
	'DimHomeScreenCoverName': (str, "", None),
	'MainChain': (list, [], None),
	'SecondaryChain': (list, [], None),
	'DimIdleListNames': (list, [], None),
	'DimIdleListTimes': (list, [], None)
}

# DimIdleListNames = []
# DimIdleListTimes = []


# _MainChain = []  # defaults to order based on config file
# _SecondaryChain = []  # if spec'd used for secondary screens else random order
# _ExtraChain = []  # defaults to empty, unused screens
