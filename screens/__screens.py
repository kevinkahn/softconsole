from hw import scaleH, scaleW

HomeScreen = None
HomeScreen2 = None
DimIdleList = []
DimIdleTimes = []
MainDict = {}  # map: name:screen
SecondaryDict = {}
DS = None  # Display Screen handles running the button presses and touch recognition

horizborder = 20
topborder = 20
botborder = 80
cmdvertspace = 10  # this is the space around the top/bot of  cmd button within the bot border
screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module


def initScreensInfo():
	global horizborder, topborder, botborder, cmdvertspace
	horizborder = scaleW(horizborder)
	topborder = scaleH(topborder)
	botborder = scaleH(botborder)
	cmdvertspace = scaleH(cmdvertspace)
