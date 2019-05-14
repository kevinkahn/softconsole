# noinspection PyProtectedMember
import functools

from configobj import Section

import config
import debug
import exitutils
import hw
import logsupport
import screens.__screens as screens
import toucharea
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail


class MyScreens(object):
	class scrlistitem(object):
		def __init__(self, scr):
			self.screen = scr
			self.prevkey = None
			self.nextkey = None

	def __init__(self, configfile):

		thisconfig = configfile
		self.ExtraDict = {}
		self.ExtraChain = []

		debug.debugPrint('Screen', "Process Configuration File")

		for screenitem in thisconfig:
			NewScreen = None
			if isinstance(thisconfig[screenitem], Section):
				thisScreen = thisconfig[screenitem]
				# its a screen
				tempscreentype = thisScreen.get("type", "unspec")
				debug.debugPrint('Screen', "Screen of type ", tempscreentype)

				if tempscreentype in screens.screentypes:
					try:
						NewScreen = screens.screentypes[tempscreentype](thisScreen, screenitem)
						logsupport.Logs.Log(tempscreentype + " screen " + screenitem, severity=ConsoleDetail)
					except ValueError:
						NewScreen = None
						logsupport.Logs.Log(tempscreentype + " screen not created due to error " + screenitem,
											severity=ConsoleWarning)
						del thisconfig[screenitem]
				else:
					logsupport.Logs.Log("Screentype error " + screenitem + " type " + tempscreentype,
										severity=ConsoleWarning)
					del thisconfig[screenitem]
					pass
			if NewScreen is not None:
				if NewScreen.name in config.sysStore.MainChain:
					# entry filled in later with prev and next key pointers
					screens.MainDict[NewScreen.name] = self.scrlistitem(NewScreen)
				elif NewScreen.name in config.sysStore.SecondaryChain:
					screens.SecondaryDict[NewScreen.name] = self.scrlistitem(NewScreen)
				else:
					self.ExtraDict[NewScreen.name] = self.scrlistitem(NewScreen)
					self.ExtraChain.append(NewScreen.name)

		# Validate screen lists and log them

		logsupport.Logs.Log("Main Screen List:")
		tmpchain = config.sysStore.MainChain[:]  # copy MainChain (not pointer to) because of possiblity of deletions
		for scr in tmpchain:
			if not scr in screens.MainDict:
				logsupport.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.sysStore.MainChain.remove(scr)
			else:
				logsupport.Logs.Log("---" + scr)
		logsupport.Logs.Log("Secondary Screen List:")
		tmpchain = config.sysStore.SecondaryChain[:]
		for scr in tmpchain:
			if not scr in screens.SecondaryDict:
				logsupport.Logs.Log("-- Undefined Screen:", scr, severity=ConsoleWarning)
				config.sysStore.SecondaryChain.remove(scr)
			else:
				logsupport.Logs.Log("---" + scr)

		# Make sure we have screens defined
		if not config.sysStore.MainChain:
			logsupport.Logs.Log("No screens defined for Main Chain", severity=ConsoleError)
			exitutils.errorexit(exitutils.ERRORDIE)

		# Create the navigation keys
		cbutwidth = (hw.screenwidth - 2 * screens.horizborder) / 2
		cvertcenter = hw.screenheight - screens.botborder / 2
		cbutheight = screens.botborder - screens.cmdvertspace * 2
		for i, kn in enumerate(config.sysStore.MainChain):
			prevk = screens.MainDict[config.sysStore.MainChain[i - 1]].screen
			nextk = screens.MainDict[config.sysStore.MainChain[(i + 1) % len(config.sysStore.MainChain)]].screen
			screens.MainDict[kn].prevkey = toucharea.ManualKeyDesc(screens.MainDict[kn].screen, 'Nav<' + prevk.name,
																   prevk.label,
																   prevk.CmdKeyCol, prevk.CmdCharCol,
																   prevk.CmdCharCol,
																   proc=functools.partial(screens.DS.NavPress, prevk),
																   center=(
																	   screens.horizborder + .5 * cbutwidth,
																	   cvertcenter),
																   size=(cbutwidth, cbutheight))
			screens.MainDict[kn].nextkey = toucharea.ManualKeyDesc(screens.MainDict[kn].screen, 'Nav>' + nextk.name,
																   nextk.label,
																   nextk.CmdKeyCol, nextk.CmdCharCol,
																   nextk.CmdCharCol,
																   proc=functools.partial(screens.DS.NavPress, nextk),
																   center=(
																	   screens.horizborder + 1.5 * cbutwidth,
																	   cvertcenter),
																   size=(cbutwidth, cbutheight))

		for i, kn in enumerate(config.sysStore.SecondaryChain):
			prevk = screens.SecondaryDict[config.sysStore.SecondaryChain[i - 1]].screen
			nextk = screens.SecondaryDict[
				config.sysStore.SecondaryChain[(i + 1) % len(config.sysStore.SecondaryChain)]].screen
			screens.SecondaryDict[kn].prevkey = toucharea.ManualKeyDesc(
				screens.SecondaryDict[kn].screen,
				'Nav<' + prevk.name,
				prevk.label,
				prevk.CmdKeyCol, prevk.CmdCharCol,
				prevk.CmdCharCol,
				proc=functools.partial(screens.DS.NavPress,
									   prevk),
				center=(
					screens.horizborder + .5 * cbutwidth, cvertcenter),
				size=(cbutwidth, cbutheight))
			screens.SecondaryDict[kn].nextkey = toucharea.ManualKeyDesc(
				screens.SecondaryDict[kn].screen,
				'Nav>' + nextk.name,
				nextk.label,
				nextk.CmdKeyCol, nextk.CmdCharCol,
				nextk.CmdCharCol,
				proc=functools.partial(screens.DS.NavPress,
									   nextk),
				center=(screens.horizborder + 1.5 * cbutwidth,
						cvertcenter),
				size=(cbutwidth, cbutheight))

		if config.sysStore.HomeScreenName in config.sysStore.MainChain:
			screens.HomeScreen = screens.MainDict[config.sysStore.HomeScreenName].screen
		else:
			logsupport.Logs.Log("Error in Home Screen Name", severity=ConsoleWarning)
			screens.HomeScreen = screens.MainDict[config.sysStore.MainChain[0]].screen
		logsupport.Logs.Log("Home Screen: " + screens.HomeScreen.name)

		if config.sysStore.SecondaryChain:
			screens.HomeScreen2 = screens.SecondaryDict[config.sysStore.SecondaryChain[0]].screen
			logsupport.Logs.Log("Secondary home screen: " + screens.HomeScreen2.name)
		else:
			screens.HomeScreen2 = screens.HomeScreen
			logsupport.Logs.Log("No secondary screen chain")  # just point secondary at main

		# noinspection PyBroadException
		try:
			for sn, st in zip(config.sysStore.DimIdleListNames, config.sysStore.DimIdleListTimes):
				for l, d in zip((config.sysStore.MainChain, config.sysStore.SecondaryChain,
								 self.ExtraChain),
								(screens.MainDict, screens.SecondaryDict, self.ExtraDict)):
					if sn in l:
						logsupport.Logs.Log('Cover Screen: ' + sn + '/' + st)
						screens.DimIdleList.append(d[sn].screen)
						screens.DimIdleTimes.append(int(st))
		except:
			logsupport.Logs.Log("Error specifying idle screens - check config", severity=ConsoleWarning)

		# handle deprecated DimHomeScreenCoverName
		cn = config.sysStore.DimHomeScreenCoverName
		if cn != "" and not screens.DimIdleList:
			if cn in config.sysStore.MainChain:
				screens.DimIdleList.append(screens.MainDict[cn].screen)
				screens.DimIdleTimes.append(1000000)
				logsupport.Logs.Log("DimHS(deprecated): " + cn, severity=ConsoleWarning)
				logsupport.Logs.Log('Replace with DimIdleListNames = [<list of screen names>]', severity=ConsoleWarning)
		if not screens.DimIdleList:
			screens.DimIdleList = [screens.HomeScreen]
			screens.DimIdleTimes = [1000000]
			logsupport.Logs.Log("No Dim Home Screen Cover Set")

		logsupport.Logs.Log("Defined but unused screens:")
		for nm, scr in self.ExtraDict.items():
			if (not isinstance(scr.screen, screens.screentypes["Alert"])) and (not scr.screen in screens.DimIdleList):
				logsupport.Logs.Log("---Unused: " + nm, severity=ConsoleWarning)
