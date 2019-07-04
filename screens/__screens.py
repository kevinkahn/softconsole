from hw import scaleH, scaleW
import hw
import collections

HomeScreen = None
HomeScreen2 = None
DimIdleList = []
DimIdleTimes = []
MainDict = {}  # map: name:screen
SecondaryDict = {}
ExtraDict = {}
ExtraChain = []
screenslist = collections.ChainMap(MainDict, SecondaryDict, ExtraDict)
DS = None  # Display Screen handles running the button presses and touch recognition

screenStore = None  # filled in by screen to avoid import circularity

screentypes = {}  # set by each module for screens of the type that module creates (see last line in any XxxScreen module


def ScaleScreensInfo():
	# Compute all values in base screen size case
	screenStore.SetVal('BotBorder', scaleH(screenStore.BotBorderWONav + screenStore.NavKeyHeight))
	screenStore.SetVal('NavKeyHeight', scaleH(screenStore.NavKeyHeight))
	screenStore.SetVal('TopBorder', scaleH(screenStore.TopBorder))
	screenStore.SetVal('HorizBorder', scaleW(screenStore.HorizBorder))
