from configobj import Section

import config
import isy
import screen
import utilities
from debug import debugPrint
import keyspecs

class KeyScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "New KeyScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		self.subscriptionlist = {}
		self.NodeWatch = []

		# Build the Key objects
		for keyname in screensection:
			if isinstance(screensection[keyname], Section):
				self.Keys[keyname] = keyspecs.CreateKey(self, screensection[keyname], keyname)

		self.LayoutKeys()
		utilities.register_example("KeyScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     KeyScreenDesc:" + ":<" + str(self.Keys) + ">"

	def EnterScreen(self):
		self.subscriptionlist = {}
		debugPrint('Screen', "Enter to screen: ", self.name)

		for K in self.Keys.itervalues():
			if isinstance(K, keyspecs.OnOffKey):
				# skip program buttons # todo how to make sure we don't forget this for new key types? keys should register their own needs (vars as well)
				# KEY should have an indicator of what node if any should go to subscriptionlist
				# with the change to capture duplicate state everywhere may want a general repaint list for a screen?
				self.subscriptionlist[K.MonitorObj.address] = K

		debugPrint('Main', "Active Subscription List will be:")
		self.NodeWatch = []
		for i in self.subscriptionlist:
			debugPrint('Screen', "  Subscribe: ", i, self.subscriptionlist[i].name, " : ",
					   self.subscriptionlist[i].ISYObj.name, ' via ', self.subscriptionlist[i].MonitorObj.name)
			self.NodeWatch.append(i)

	def InitDisplay(self, nav):

		states = isy.get_real_time_status(self.subscriptionlist.keys())
		for K in self.Keys.itervalues():
			if isinstance(K, keyspecs.OnOffKey):
				K.State = not (states[K.MonitorObj.address] == 0)  # K is off (false) only if state is 0
		super(KeyScreenDesc, self).InitDisplay(nav)

	def ISYEvent(self, node, value):
		# Watched node reported change event is ("Node", addr, value, seq) todo tied to above comment
		K = self.subscriptionlist[node]
		debugPrint('Screen', 'KS ISYEvent ', K.name, str(value), str(K.State))
		K.State = not (int(value if value.isdigit() else 0) == 0)  # K is off (false) only if state is 0
		K.PaintKey()

config.screentypes["Keypad"] = KeyScreenDesc
