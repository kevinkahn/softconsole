# noinspection PyProtectedMember
from configobj import Section

import config
import screen
import utilities
import debug
import keyspecs

class KeyScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debug.debugPrint('Screen', "New KeyScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)

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

		#for i in self.NodeList:
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

	def ISYEvent(self, hub='', node=0, value='', varinfo = ()):
		# Watched node reported change event is ("Node", addr, value, seq)
		if node != 0:
			# noinspection PyBroadException
			try:
				K = self.HubInterestList[hub][node]
			except:
				debug.debugPrint('Screen', 'Bad key to KS - race?', self.name, str(node))
				return  # treat as noop
			debug.debugPrint('Screen', 'KS ISYEvent ', K.name, str(value), str(K.State))
			K.State = not (int(value if value.isdigit() else 0) == 0)  # K is off (false) only if state is 0
		else:
			# noinspection PyBroadException
			try:
				# varinfo is (keyname, varname)
				K = self.Keys[varinfo[0]]
			except:
				debug.debugPrint('Screen', 'Bad var key', self.name, str(varinfo))
				return
		K.PaintKey()

config.screentypes["Keypad"] = KeyScreenDesc
