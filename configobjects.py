from configobj import Section

import config
import debug
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
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

		debug.debugPrint('Screen', "Process Configuration File")

		for screenitem in thisconfig:
			NewScreen = None
			if isinstance(thisconfig[screenitem], Section):
				thisScreen = thisconfig[screenitem]
				# its a screen
				tempscreentype = thisScreen.get("type", "unspec")
				debug.debugPrint('Screen', "Screen of type ", tempscreentype)

				if tempscreentype in config.screentypes:
					logsupport.Logs.Log(tempscreentype + " screen " + screenitem, severity=ConsoleDetail)
					NewScreen = config.screentypes[tempscreentype](thisScreen, screenitem)

				else:
					logsupport.Logs.Log("Screentype error" + screenitem + " type " + tempscreentype, severity=ConsoleWarning)
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
		'''
		if not config.SecondaryDict:
			# Secondary Dict empty
			config.SecondaryDict = config.ExtraDict
			config.SecondaryChain = config.ExtraChain
			config.ExtraChain = []
			config.ExtraDict = {}
		'''

		# Validate screen lists and log them

		logsupport.Logs.Log("Main Screen List:")
		tmpchain = config.MainChain[:]  # copy MainChain (not pointer to) because of possiblity of deletions
		for scr in tmpchain:
			if not scr in config.MainDict:
				logsupport.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.MainChain.remove(scr)
			else:
				logsupport.Logs.Log("---" + scr)
		logsupport.Logs.Log("Secondary Screen List:")
		tmpchain = config.SecondaryChain[:]
		for scr in tmpchain:
			if not scr in config.SecondaryDict:
				logsupport.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.SecondaryChain.remove(scr)
			else:
				logsupport.Logs.Log("---" + scr)

		# Make sure we have screens defined
		if not config.MainChain:
			logsupport.Logs.Log("No screens defined for Main Chain", severity=ConsoleError)
			exitutils.errorexit(exitutils.ERRORDIE)

		# Create the navigation keys
		cbutwidth = (config.screenwidth - 2*config.horizborder)/2
		cvertcenter = config.screenheight - config.botborder/2
		cbutheight = config.botborder - config.cmdvertspace*2
		for i, kn in enumerate(config.MainChain):
			prevk = config.MainDict[config.MainChain[i - 1]].screen
			nextk = config.MainDict[config.MainChain[(i + 1)%len(config.MainChain)]].screen
			config.MainDict[kn].prevkey = toucharea.ManualKeyDesc(config.MainDict[kn].screen, prevk.name, prevk.label,
																  config.CmdKeyCol, config.CmdCharCol,
																  config.CmdCharCol,
																  proc=functools.partial(config.DS.NavPress, prevk),
																  center=(
																  config.horizborder + .5*cbutwidth, cvertcenter),
																  size=(cbutwidth, cbutheight))
			config.MainDict[kn].nextkey = toucharea.ManualKeyDesc(config.MainDict[kn].screen, nextk.name, nextk.label,
																  config.CmdKeyCol, config.CmdCharCol,
																  config.CmdCharCol,
																  proc=functools.partial(config.DS.NavPress, nextk),
																  center=(
																	  config.horizborder + 1.5*cbutwidth, cvertcenter),
																  size=(cbutwidth, cbutheight))

		for i, kn in enumerate(config.SecondaryChain):
			prevk = config.SecondaryDict[config.SecondaryChain[i - 1]].screen
			nextk = config.SecondaryDict[config.SecondaryChain[(i + 1)%len(config.SecondaryChain)]].screen
			config.SecondaryDict[kn].prevkey = toucharea.ManualKeyDesc(config.SecondaryDict[kn].screen, prevk.name,
																	   prevk.label,
																	   config.CmdKeyCol, config.CmdCharCol,
																	   config.CmdCharCol,
																	   proc=functools.partial(config.DS.NavPress,
																							  prevk),
																	   center=(
																	   config.horizborder + .5*cbutwidth, cvertcenter),
																	   size=(cbutwidth, cbutheight))
			config.SecondaryDict[kn].nextkey = toucharea.ManualKeyDesc(config.SecondaryDict[kn].screen, nextk.name,
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
			logsupport.Logs.Log("Error in Home Screen Name", severity=ConsoleWarning)
			config.HomeScreen = config.MainDict[config.MainChain[0]].screen
		logsupport.Logs.Log("Home Screen: " + config.HomeScreen.name)

		if config.SecondaryChain:
			config.HomeScreen2 = config.SecondaryDict[config.SecondaryChain[0]].screen
			logsupport.Logs.Log("Secondary home screen: " + config.HomeScreen2.name)
		else:
			config.HomeScreen2 = config.HomeScreen
			logsupport.Logs.Log("No secondary screen chain")  # just point secondary at main

		try:
			for sn, st in zip(config.DimIdleListNames, config.DimIdleListTimes):
				for l, d in zip((config.MainChain, config.SecondaryChain, config.ExtraChain),
								(config.MainDict, config.SecondaryDict, config.ExtraDict)):
					if sn in l:
						logsupport.Logs.Log('Cover Screen: ' + sn + '/' + st)
						config.DimIdleList.append(d[sn].screen)
						config.DimIdleTimes.append(int(st))
		except:
			logsupport.Logs.Log("Error specifying idle screens - check config", severity=ConsoleWarning)

		# handle deprecated DimHomeScreenCoverName
		if config.DimHomeScreenCoverName != "" and not config.DimIdleList:
			if config.DimHomeScreenCoverName in config.MainChain:
				config.DimIdleList.append(config.MainDict[config.DimHomeScreenCoverName].screen)
				config.DimIdleTimes.append(1000000)
				logsupport.Logs.Log("DimHS(deprecated): " + config.DimHomeScreenCoverName)
		if not config.DimIdleList:
			config.DimIdleList = [config.HomeScreen]
			config.DimIdleTimes = [1000000]
			logsupport.Logs.Log("No Dim Home Screen Cover Set")

		logsupport.Logs.Log("Not on screen list and not cover screen:")
		for nm, scr in config.ExtraDict.items():
			if (not isinstance(scr.screen, config.screentypes["Alert"])) and (not scr.screen in config.DimIdleList):
				logsupport.Logs.Log("---" + nm, severity=ConsoleWarning)
