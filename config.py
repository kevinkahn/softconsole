import pygame

WAITNORMALBUTTON = 1
WAITEXIT = 2
WAITISYCHANGE = 4
WAITEXTRACONTROLBUTTON = 5
WAITDBLTAP = 7
WAITQUADTAP = 8
WAITMAINTTAP = 9
WAITNORMALBUTTONFAST = 10


toDaemon = None
fromDaemon = None
watchlist =[]
starttime = 0

# Debug flags
isytreewalkdbgprt = False
dbgscreenbuild = False
dbgMain = False
dbgdaemon = False

def debugprint(flag,*args):
    if flag:
        for arg in args:
            print arg,
        print


ErrorItems = []

ConnISY = None

screen = None
backlight = None

ParsedConfigFile = None
screenwidth = 320
screenheight = 480
horizborder = 20
topborder = 20
botborder = 80
cmdvertspace = 10 # this is the space around the top/bot of  cmd button within the bot border

# Global Defaults
ISYaddr = ""
ISYuser = ""
ISYpassword = ""

currentscreen = None
#previousscreen = None
HomeScreenName = ""
HomeScreen = None
DimLevel = 10
BrightLevel = 100
HomeScreenTO = 60 
DimTO = 20
CmdKeyCol = "red"
CmdCharCol = "white"
multitaptime = 200

# General Screen Defaults
BColor = "maroon"

# Key Screen Defaults


# Key Defaults
Kcolor = "aqua"
KOnColor = "white"
KOffColor = "black"
Ktype = "ONOFF" # ONOFF ONBLINKRUNTHEN
Krunthen = ""

# Clock Screen Defaults
CharCol = "white"
CharSize = 35


