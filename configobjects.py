from configobj import Section

import config
from debug import debugPrint
from logsupport import ConsoleWarning, ConsoleError
import toucharea
import functools
import exitutils


class MyScreens(object):
	class scrlistitem(object):
		def __init__(self, scr):
			self.screen = scr
			self.prevkey = None
			self.nextkey = None

	def __init__(self):

		thisconfig = config.ParsedConfigFile

		debugPrint('Screen', "Process Configuration File")

		for screenitem in thisconfig:
			NewScreen = None
			if isinstance(thisconfig[screenitem], Section):
				thisScreen = thisconfig[screenitem]
				# its a screen
				tempscreentype = thisScreen.get("type", "unspec")
				debugPrint('Screen', "Screen of type ", tempscreentype)

				if tempscreentype in config.screentypes:
					config.Logs.Log(tempscreentype + " screen " + screenitem)
					NewScreen = config.screentypes[tempscreentype](thisScreen, screenitem)

				else:
					config.Logs.Log("Screentype error" + screenitem + " type " + tempscreentype, severity=ConsoleWarning)
					pass
			if NewScreen is not None:
				if NewScreen.name in config.MainChain:
					# entry filled in later with prev and next key pointers
					config.MainDict[NewScreen.name] = self.scrlistitem(NewScreen)
				elif NewScreen.name in config.SecondaryChain:
					config.SecondaryDict[NewScreen.name] = self.scrlistitem(NewScreen)
				else:
					config.ExtraDict[NewScreen.name] = self.scrlistitem(NewScreen)
					config.ExtraChain.append(NewScreen.name)

		if not config.SecondaryDict:
			# Secondary Dict empty
			config.SecondaryDict = config.ExtraDict
			config.SecondaryChain = config.ExtraChain
			config.ExtraChain = []
			config.ExtraDict = {}

		# Validate screen lists and log them

		config.Logs.Log("Main Screen List:")
		tmpchain = config.MainChain  # can't sequence loop over actual MainChain because of possiblity of deletions
		for scr in tmpchain:
			if not scr in config.MainDict:
				config.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.MainChain.remove(scr)
			else:
				config.Logs.Log("---" + scr)
		config.Logs.Log("Secondary Screen List:")
		tmpchain = config.SecondaryChain
		for scr in tmpchain:
			if not scr in config.SecondaryDict:
				config.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.SecondaryChain.remove(scr)
			else:
				config.Logs.Log("---" + scr)
		config.Logs.Log("Not on a screen list (unavailable via nav keys)")
		for scr in config.ExtraChain:
			config.Logs.Log("---" + scr, severity=ConsoleWarning)

		# Make sure we have screens defined
		if config.MainChain == []:
			config.Logs.Log("No screens defined for Main Chain", severity=ConsoleError)
			exitutils.errorexit("shut")

		# Create the navigation keys
		cbutwidth = (config.screenwidth - 2*config.horizborder)/2
		cvertcenter = config.screenheight - config.botborder/2
		cbutheight = config.botborder - config.cmdvertspace*2
		for i, kn in enumerate(config.MainChain):
			prevk = config.MainDict[config.MainChain[i - 1]].screen
			nextk = config.MainDict[config.MainChain[(i + 1)%len(config.MainChain)]].screen
			config.MainDict[kn].prevkey = toucharea.ManualKeyDesc(config.MainChain[i], prevk.name, prevk.label,
																  config.CmdKeyCol, config.CmdCharCol,
																  config.CmdCharCol,
																  proc=functools.partial(config.DS.NavPress, prevk),
																  center=(
																  config.horizborder + .5*cbutwidth, cvertcenter),
																  size=(cbutwidth, cbutheight))
			config.MainDict[kn].nextkey = toucharea.ManualKeyDesc(config.MainChain[i], nextk.name, nextk.label,
																  config.CmdKeyCol, config.CmdCharCol,
																  config.CmdCharCol,
																  proc=functools.partial(config.DS.NavPress, nextk),
																  center=(
																	  config.horizborder + 1.5*cbutwidth, cvertcenter),
																  size=(cbutwidth, cbutheight))

		for i, kn in enumerate(config.SecondaryChain):
			prevk = config.SecondaryDict[config.SecondaryChain[i - 1]].screen
			nextk = config.SecondaryDict[config.SecondaryChain[(i + 1)%len(config.SecondaryChain)]].screen
			config.SecondaryDict[kn].prevkey = toucharea.ManualKeyDesc(config.SecondaryChain[i], prevk.name,
																	   prevk.label,
																	   config.CmdKeyCol, config.CmdCharCol,
																	   config.CmdCharCol,
																	   proc=functools.partial(config.DS.NavPress,
																							  prevk),
																	   center=(
																	   config.horizborder + .5*cbutwidth, cvertcenter),
																	   size=(cbutwidth, cbutheight))
			config.SecondaryDict[kn].nextkey = toucharea.ManualKeyDesc(config.SecondaryChain[i], nextk.name,
																	   nextk.label,
																	   config.CmdKeyCol, config.CmdCharCol,
																	   config.CmdCharCol,
																	   proc=functools.partial(config.DS.NavPress,
																							  nextk),
																	   center=(config.horizborder + 1.5*cbutwidth,
																			   cvertcenter),
																	   size=(cbutwidth, cbutheight))


		if config.HomeScreenName in config.MainChain:
			config.HomeScreen = config.MainDict[config.HomeScreenName].screen
		else:
			config.Logs.Log("Error in Home Screen Name", severity=ConsoleWarning)
			config.HomeScreen = config.MainDict[config.MainChain[0]].screen

		if config.SecondaryChain <> []:
			config.HomeScreen2 = config.SecondaryDict[config.SecondaryChain[0]].screen
		else:
			config.HomeScreen2 = config.HomeScreen  # just point secondary at main
		config.Logs.Log("Home Screen: " + config.HomeScreen.name)
		for sn, st in zip(config.DimIdleListNames, config.DimIdleListTimes):
			for l, d in zip((config.MainChain, config.SecondaryChain, config.ExtraChain),
							(config.MainDict, config.SecondaryDict, config.ExtraDict)):
				if sn in l:
					config.Logs.Log('Dim Screen: ' + sn + '/' + st)
					config.DimIdleList.append(d[sn].screen)
					config.DimIdleTimes.append(int(st))

		# handle deprecated DimHomeScreenCoverName
		if config.DimHomeScreenCoverName <> "" and not config.DimIdleList:
			if config.DimHomeScreenCoverName in config.MainChain:
				config.DimIdleList.append(config.MainDict[config.DimHomeScreenCoverName].screen)
				config.DimIdleTimes.append(1000000)
				config.Logs.Log("DimHS(deprecated): " + config.DimHomeScreenCoverName)

		if not config.DimIdleList:
			config.DimIdleList = [config.HomeScreen]
			config.DimIdleTimes = [1000000]
			config.Logs.Log("No Dim Home Screen Cover Set")

		config.Logs.Log("First Secondary Screen: " + config.HomeScreen2.name)
