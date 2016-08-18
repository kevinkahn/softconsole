# Global Defaults Settable in config.txt in Console
ISYaddr = ""
ISYuser = ""
_ISYpassword = ""
HomeScreenName = ""
HomeScreenTO = 60
DimLevel = 10
BrightLevel = 100
DimTO = 20
CmdKeyCol = "red"
CmdCharCol = "white"
MultiTapTime = 400
DimHomeScreenCoverName = ""
DimIdleListNames = []
DimIdleListTimes = []
CharColor = "white"
BackgroundColor = 'maroon'

MaxLogFiles = 5  # would be nice to get these in globalparams but right now there is an ordering issue since logging starts before global sucking
LogFontSize = 23

_MainChain = []  # defaults to order based on config file
_SecondaryChain = []  # if spec'd used for secondary screens else random order
_ExtraChain = []  # defaults to empty, unused screens

# Defaults for Keys
KeyColor = "aqua"
KeyColorOn = ""
KeyColorOff = ""
KeyCharColorOn = "white"
KeyCharColorOff = "black"
KeyOnOutlineColor = "white"
KeyOffOutlineColor = "black"
KeyOutlineOffset = 3
