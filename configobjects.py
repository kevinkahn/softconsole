from configobj import Section

import config
from config import debugPrint
from logsupport import ConsoleWarning


class MyScreens(object):
	def __init__(self):

		thisconfig = config.ParsedConfigFile

		debugPrint('BuildScreen', "Process Configuration File")

		mainlist = {}
		secondlist = {}
		extralist = {}

		for screenitem in thisconfig:
			NewScreen = None
			if isinstance(thisconfig[screenitem], Section):
				thisScreen = thisconfig[screenitem]
				# its a screen
				tempscreentype = thisScreen.get("type", "unspec")
				debugPrint('BuildScreen', "Screen of type ", tempscreentype)

				if tempscreentype in config.screentypes:
					NewScreen = config.screentypes[tempscreentype](thisScreen, screenitem)
					config.Logs.Log(tempscreentype + " screen " + screenitem)
				else:
					config.Logs.Log("Screentype error" + screenitem + " type " + tempscreentype, severity=ConsoleWarning)
					pass
			if NewScreen is not None:
				# set the standard navigation keys and navigation linkages
				if NewScreen.name in config.MainChain:
					mainlist[NewScreen.name] = NewScreen
				elif NewScreen.name in config.SecondaryChain:
					secondlist[NewScreen.name] = NewScreen
				else:
					extralist[NewScreen.name] = NewScreen
					config.ExtraChain.append(NewScreen.name)

		if len(secondlist) == 0:
			secondlist = extralist
			config.SecondaryChain = config.ExtraChain
			config.ExtraChain = []
		config.Logs.Log("Main Screen List:")
		for scr in config.MainChain:
			if not scr in mainlist:
				config.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.MainChain.remove(scr)
		for scr in config.MainChain:
			if scr in mainlist:
				S = mainlist[scr]
				S.PrevScreen = mainlist[config.MainChain[config.MainChain.index(scr) - 1]]
				S.NextScreen = mainlist[config.MainChain[(config.MainChain.index(scr) + 1)%len(config.MainChain)]]
				config.Logs.Log("---" + scr)

		config.Logs.Log("Secondary Screen List:")
		for scr in config.SecondaryChain:
			if not scr in secondlist:
				config.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.SecondaryChain.remove(scr)
		for scr in config.SecondaryChain:
			if scr in secondlist:
				S = secondlist[scr]
				S.PrevScreen = secondlist[config.SecondaryChain[config.SecondaryChain.index(scr) - 1]]
				S.NextScreen = secondlist[
					config.SecondaryChain[(config.SecondaryChain.index(scr) + 1)%len(config.SecondaryChain)]]
				config.Logs.Log("---" + scr)

		config.Logs.Log("Not on a screen list (unavailable)", severity=ConsoleWarning)
		for scr in config.ExtraChain:
			config.Logs.Log("---" + scr, severity=ConsoleWarning)

		for S in mainlist.itervalues():
			S.FinishScreen()
		for S in secondlist.itervalues():
			S.FinishScreen()

		if config.HomeScreenName in config.MainChain:
			config.HomeScreen = mainlist[config.HomeScreenName]
		else:
			config.Logs.Log("Error in Home Screen Name", severity=ConsoleWarning)
			config.HomeScreen = mainlist[config.MainChain[0]]

		config.HomeScreen2 = secondlist[config.SecondaryChain[0]]

		config.Logs.Log("Home Screen: " + config.HomeScreen.name)
		for sn, st in zip(config.DimIdleListNames, config.DimIdleListTimes):
			for l, d in zip((config.MainChain, config.SecondaryChain, config.ExtraChain),
							(mainlist, secondlist, extralist)):
				if sn in l:
					config.Logs.Log('Dim Screen: ' + sn + '/' + st)
					config.DimIdleList.append(d[sn])
					config.DimIdleTimes.append(int(st)*1000)

		# handle deprecated DimHomeScreenCoverName
		if config.DimHomeScreenCoverName <> "" and len(config.DimIdleList) == 0:
			if config.DimHomeScreenCoverName in config.MainChain:
				config.DimIdleList.append(mainlist[config.DimHomeScreenCoverName])
				config.DimIdleTimes.append(1000)
				config.Logs.Log("DimHS(deprecated): " + config.DimHomeScreenCoverName)

		if len(config.DimIdleList) == 0:
			config.DimIdleList[0] = config.HomeScreen
			config.DimIdleTimes[0] = 1000
			config.Logs.Log("No Dim Home Screen Cover Set")

		config.Logs.Log("First Secondary Screen: " + config.HomeScreen2.name)
