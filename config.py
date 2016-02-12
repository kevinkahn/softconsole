screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module

starttime = 0

WAITNORMALBUTTON = 1
WAITEXIT = 2
WAITISYCHANGE = 4
WAITEXTRACONTROLBUTTON = 5
WAITDBLTAP = 7
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
ISYdebug = False
dbgscreenbuild = False
dbgMain = False
dbgdaemon = False


def debugprint(flag, *args):
    if flag:
        for arg in args:
            print arg,
        print


Logs = None

# Global pointers
ISYrequestsession = None
ISY = None  # Root of structure representing the ISY - filled in from ISY
screen = None  # pygame screen
backlight = None  # GPIO instance of pin 18
DS = None  # Global Display Screen (only one such object
ParsedConfigFile = None  # config.txt internal version

# Screen Display Info
screenwidth = 0
screenheight = 0
dispratio = 1
baseheight = 480  # program design height
basewidth = 320  # program design width
horizborder = 20
topborder = 20
botborder = 80
cmdvertspace = 10  # this is the space around the top/bot of  cmd button within the bot border

ISYprefix = ''
"""
# Names of screens in screen chains - set from config.txt and used to embed object references in screen objects
MainChain       = []  # defaults to order based on config file
SecondaryChain  = []  # if spec'd used for secondary screens else random order
ExtraChain      = []  # defaults to empty, unused screens
"""
# Operational global navigation roots
CurrentScreen = None
HomeScreen = None
HomeScreen2 = None
MaintScreen = None
DimHomeScreenCover = None
