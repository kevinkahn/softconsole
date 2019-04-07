# noinspection PyProtectedMember
import pygame
from configobj import Section

import debug
import keyspecs
import logsupport
import screen
import screens.__screens as screens
import utilities
from logsupport import ConsoleWarning


class KeyScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		debug.debugPrint('Screen', "New KeyScreenDesc ", screenname)

		# Build the Key objects
		for keyname in screensection:
			if isinstance(screensection[keyname], Section):
				self.Keys[keyname] = keyspecs.CreateKey(self, screensection[keyname], keyname)

		self.LayoutKeys()

		debug.debugPrint('Screen', "Active Subscription List for ", self.name, " will be:")
		for h, l in self.HubInterestList.items():
			for i, j in l.items():
				debug.debugPrint('Screen', "  Subscribe on hub " + h + " node: " + i + ' ' + j.name + ":" +
								 j.ControlObj.name + ' via ' + j.DisplayObj.name)

		# for i in self.NodeList:
		#	debug.debugPrint('Screen', "  Subscribe node: ", i, self.NodeList[i].name, " : ",
		#			   self.NodeList[i].ControlObj.name, ' via ', self.NodeList[i].DisplayObj.name)

		utilities.register_example("KeyScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     KeyScreenDesc:" + ":<" + str(self.Keys) + ">"

	def InitDisplay(self, nav):
		debug.debugPrint("Screen", "Keyscreen InitDisplay: ", self.name)
		for K in self.Keys.values():
			K.InitDisplay()
		super(KeyScreenDesc, self).InitDisplay(nav)
		pygame.display.update()

	def NodeEvent(self, hub='', node=0, value=0, varinfo=()):
		# Watched node reported change event is ("Node", addr, value, seq)
		De('HUB', hub, node, type(value), value)
		if isinstance(value, float):
			logsupport.Logs.Log("Node event with floating state: " + hub + ':' + str(node) + '->' + str(value),
								severity=ConsoleWarning)
			value = int(value)

		assert isinstance(value, int)
		if node is None:  # all keys for this hub
			for _, K in self.HubInterestList[hub].items():
				debug.debugPrint('Screen', 'KS Wildcard ISYEvent ', K.name, str(value), str(K.State))
				K.UnknownState = True
				K.PaintKey()
				pygame.display.update()
		elif node != 0:
			# noinspection PyBroadException
			try:
				K = self.HubInterestList[hub][node]
			except:
				debug.debugPrint('Screen', 'Bad key to KS - race?', self.name, str(node))
				return  # treat as noop
			debug.debugPrint('Screen', 'KS ISYEvent ', K.name, str(value), str(K.State))
			K.State = not (value == 0)  # K is off (false) only if state is 0
			K.UnknownState = True if value == -1 else False
			K.PaintKey()
			pygame.display.update()
		else:
			# noinspection PyBroadException
			try:
				# varinfo is (keyname, varname)
				K = self.Keys[varinfo[0]]
				K.PaintKey()
				pygame.display.update()
			except:
				debug.debugPrint('Screen', "Var change reported to screen that doesn't care", self.name,
								 str(varinfo))  # todo event reporting correlation to screens could use rework
				return


screens.screentypes["Keypad"] = KeyScreenDesc
