import logsupport
import pygame

screentypes = {} # set by each module for screens of the type that module creates (see last line in any XxxScreen module

starttime = 0

WAITNORMALBUTTON = 1
WAITEXIT = 2
WAITISYCHANGE = 4
WAITEXTRACONTROLBUTTON = 5
WAITDBLTAP = 7
WAITQUADTAP = 8
#WAITMAINTTAP = 9
WAITNORMALBUTTONFAST = 10

""" Daemon related stuff"""
toDaemon = None
fromDaemon = None
watchlist =[]
watchstarttime = 0
DaemonProcess = None
seq = 0
streamid = ""

# Debug flags
isytreewalkdbgprt = False
dbgscreenbuild = True
dbgMain = True
dbgdaemon = False

def debugprint(flag,*args):
    if flag:
        for arg in args:
            print arg,
        print

Logs = None

# Global pointers
ConnISY = None  # Root of structure representing the ISY from PyISY
screen = None # pygame screen
backlight = None # GPIO instance of pin 18
DS = None # Global Display Screen (only on such object - is there a better python way than isntantiating just one?
ParsedConfigFile = None # config.txt internal version

# Screen Display Info
screenwidth = 0
screenheight = 0
dispratio = 1
baseheight = 480
basewidth  = 320
horizborder = 20
topborder = 20
botborder = 80
cmdvertspace = 10 # this is the space around the top/bot of  cmd button within the bot border

# Global Defaults Settable in config.txt in Console
ISYaddr = ""        # from config globals
ISYuser = ""        # from config globals
ISYpassword = ""    # from config globals
HomeScreenName = "" # from config globals
HomeScreenTO = 60   # from config globals
DimLevel = 10
BrightLevel = 100
DimTO = 20
CmdKeyCol = "red"
CmdCharCol = "white"
MultiTapTime = 300
DimHomeScreenCoverName = ""
DefaultCharColor = "white"
DefaultBkgndColor = 'maroon'

# Names of screens in screen chains - set from config.txt and used to embed object references in screen objects
MainChain = []      # defaults to order based on config file
SecondaryChain = [] # if spec'd used for secondary screens else random order
ExtraChain = []     # defaults to empty, unused screens

# Operational golbal navigation roots
CurrentScreen       = None
HomeScreen          = None
HomeScreen2         = None
MaintScreen         = None
DimHomeScreenCover  = None

# Normal key Defaults across all screens
DefaultKeyColor = "aqua"
DefaultKeyOnOutlineColor = "white"
DefaultKeyOffOutlineColor = "black"
