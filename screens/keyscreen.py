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
		for i in self.NodeList:
			debug.debugPrint('Screen', "  Subscribe node: ", i, self.NodeList[i].name, " : ",
					   self.NodeList[i].ISYObj.name, ' via ', self.NodeList[i].MonitorObj.name)
		for i in self.VarsList:
			debug.debugPrint('Screen', "  Subscribe var: ", i, self.VarsList[i].name)


		utilities.register_example("KeyScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     KeyScreenDesc:" + ":<" + str(self.Keys) + ">"


	def InitDisplay(self, nav):
		debug.debugPrint("Screen", "Keyscreen InitDisplay: ", self.name)
		for K in self.Keys.itervalues():
			K.InitDisplay()
		super(KeyScreenDesc, self).InitDisplay(nav)

	def ISYEvent(self, node=0, value=0, varinfo = ()):
		# Watched node reported change event is ("Node", addr, value, seq)
		if node <> 0:
			try:
				K = self.NodeList[node]
			except:
				debug.debugPrint('Screen', 'Bad key to KS - race?', self.name, str(node))
				return  # treat as noop
			debug.debugPrint('Screen', 'KS ISYEvent ', K.name, str(value), str(K.State))
			K.State = not (int(value if value.isdigit() else 0) == 0)  # K is off (false) only if state is 0
		else:
			try:
				# varinfo is (keyname, varname)
				K = self.Keys[varinfo[0]]
			except:
				debug.debugPrint('Screen', 'Bad var key', self.name, str(varinfo))
				return
		K.PaintKey()

config.screentypes["Keypad"] = KeyScreenDesc
