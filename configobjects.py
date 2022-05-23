# noinspection PyProtectedMember

import configobj
from configobj import Section
import config
import debug
from utils import exitutils
import logsupport
import screens.__screens as screens
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail

GoToTargetList = {}

class MyScreens(object):

	def __init__(self, configfile):

		thisconfig = configfile

		debug.debugPrint('Screen', "Process Configuration File")

		for screenitem in thisconfig:
			NewScreen = None
			if isinstance(thisconfig[screenitem], Section):
				thisScreen = thisconfig[screenitem]
				# it's a screen
				tempscreentype = thisScreen.get("type", "unspec")
				clockedscreen = thisScreen.get("Clocked", 0)
				debug.debugPrint('Screen', "Screen of type ", tempscreentype)

				if tempscreentype in screens.screentypes:
					try:
						NewScreen = screens.screentypes[tempscreentype](thisScreen, screenitem)
						if clockedscreen != 0: NewScreen.SetScreenClock(clockedscreen)
						logsupport.Logs.Log(tempscreentype + " screen " + screenitem, severity=ConsoleDetail)
					except Exception as E:
						NewScreen = None
						logsupport.Logs.Log(
							'{} screen {} not created due to error ({})'.format(tempscreentype, screenitem, E),
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
					screens.MainDict[NewScreen.name] = NewScreen
				elif NewScreen.name in config.sysStore.SecondaryChain:
					screens.SecondaryDict[NewScreen.name] = NewScreen
				else:
					screens.ExtraDict[NewScreen.name] = NewScreen
					screens.ExtraChain.append(NewScreen.name)

		if config.sysStore.versionname == 'development':
			allscreens = {**screens.MainDict, **screens.SecondaryDict, **screens.ExtraDict}
			thisscreenpartial = None
			scrnnum = 0
			perscreen = 0
			for sn, s in allscreens.items():
				if perscreen == 0:
					if thisscreenpartial is not None:
						config.sysStore.MainChain.append('TestScreen-{}'.format(scrnnum))
						screens.MainDict['TestScreen-{}'.format(scrnnum)] = screens.screentypes['Keypad'](
							thisscreenpartial, 'TestScreen-{}'.format(scrnnum))
					scrnnum += 1
					perscreen = 6
					thisscreenpartial = configobj.ConfigObj(
						{'ScreenTitle': 'TestScreen-{}'.format(scrnnum), 'label': ['TestScreen-{}'.format(scrnnum)]})
				thisscreenpartial[sn] = {'type': 'GOTO', 'ScreenName': sn, 'label': sn}
				perscreen -= 1
			if perscreen != 6:  # get the leftovers
				config.sysStore.MainChain.append('TestScreen-{}'.format(scrnnum))
				screens.MainDict['TestScreen-{}'.format(scrnnum)] = screens.screentypes['Keypad'](thisscreenpartial,
																								  'TestScreen-{}'.format(
																									  scrnnum))

		# Validate screen lists and log them

		logsupport.Logs.Log("Main Screen List:", severity=ConsoleDetail)
		tmpchain = config.sysStore.MainChain[:]  # copy MainChain (not pointer to) because of possiblity of deletions
		for scr in tmpchain:
			if not scr in screens.MainDict:
				logsupport.Logs.Log("--- Undefined Main List Screen:", scr, severity=ConsoleWarning)
				config.sysStore.MainChain.remove(scr)
			else:
				logsupport.Logs.Log("---" + scr, severity=ConsoleDetail)
		logsupport.Logs.Log("Secondary Screen List:", severity=ConsoleDetail)
		tmpchain = config.sysStore.SecondaryChain[:]
		for scr in tmpchain:
			if not scr in screens.SecondaryDict:
				logsupport.Logs.Log("--- Undefined Secondary List Screen:", scr, severity=ConsoleWarning)
				config.sysStore.SecondaryChain.remove(scr)
			else:
				logsupport.Logs.Log("---" + scr, severity=ConsoleDetail)

		# Make sure we have screens defined
		if not config.sysStore.MainChain:
			logsupport.Logs.Log("No screens defined for Main Chain", severity=ConsoleError)
			exitutils.errorexit(exitutils.ERRORDIE)

		# Create the navigation keys
		for i, kn in enumerate(config.sysStore.MainChain):
			prevk = screens.MainDict[config.sysStore.MainChain[i - 1]]
			nextk = screens.MainDict[config.sysStore.MainChain[(i + 1) % len(config.sysStore.MainChain)]]
			screens.MainDict[kn].CreateNavKeys(prevk, nextk)

		for i, kn in enumerate(config.sysStore.SecondaryChain):
			prevk = screens.SecondaryDict[config.sysStore.SecondaryChain[i - 1]]
			nextk = screens.SecondaryDict[
				config.sysStore.SecondaryChain[(i + 1) % len(config.sysStore.SecondaryChain)]]
			screens.SecondaryDict[kn].CreateNavKeys(prevk, nextk)

		if config.sysStore.HomeScreenName in config.sysStore.MainChain:
			screens.HomeScreen = screens.MainDict[config.sysStore.HomeScreenName]
		else:
			logsupport.Logs.Log("Error in Home Screen Name", severity=ConsoleWarning)
			screens.HomeScreen = screens.MainDict[config.sysStore.MainChain[0]]
		logsupport.Logs.Log("Home Screen: " + screens.HomeScreen.name)

		if config.sysStore.SecondaryChain:
			screens.HomeScreen2 = screens.SecondaryDict[config.sysStore.SecondaryChain[0]]
			logsupport.Logs.Log("Secondary home screen: " + screens.HomeScreen2.name)
		else:
			screens.HomeScreen2 = screens.HomeScreen
			logsupport.Logs.Log("No secondary screen chain")  # just point secondary at main

		# noinspection PyBroadException
		idlescreens = []
		try:
			for sn, st in zip(config.sysStore.DimIdleListNames, config.sysStore.DimIdleListTimes):
				screens.DimIdleList.append(screens.screenslist[sn])
				screens.DimIdleTimes.append(int(st))
				idlescreens.append("{}/{}".format(sn, st))
			logsupport.Logs.Log('Idle Screens: ' + ', '.join(idlescreens))
		except Exception as E:
			logsupport.Logs.Log("Error specifying idle screens - check config({})".format(repr(E)),
								severity=ConsoleWarning)

		# handle deprecated DimHomeScreenCoverName
		cn = config.sysStore.DimHomeScreenCoverName
		if cn != "" and not screens.DimIdleList:
			if cn in config.sysStore.MainChain:
				screens.DimIdleList.append(screens.MainDict[cn])
				screens.DimIdleTimes.append(1000000)
				logsupport.Logs.Log("DimHS(deprecated): " + cn, severity=ConsoleWarning)
				logsupport.Logs.Log('Replace with DimIdleListNames = [<list of screen names>]', severity=ConsoleWarning)
		if not screens.DimIdleList:
			screens.DimIdleList = [screens.HomeScreen]
			screens.DimIdleTimes = [1000000]
			logsupport.Logs.Log("No Dim Home Screen Cover Set")

		for k, s in GoToTargetList.items():
			try:
				k.targetscreen = screens.screenslist[s]
				if s in screens.ExtraDict: del screens.ExtraDict[s]
			except KeyError:
				logsupport.Logs.Log("GoTo Key target {} doesn't exist".format(s))

		logsupport.Logs.Log("Defined but unused screens:")
		for nm, scr in screens.ExtraDict.items():
			if (not isinstance(scr, screens.screentypes["Alert"])) and (
			not scr in screens.DimIdleList):  # todo also add targets of gotos
				logsupport.Logs.Log("---Unused: " + nm, severity=ConsoleWarning)
