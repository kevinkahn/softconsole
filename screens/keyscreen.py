import functools

import webcolors
from configobj import Section

import config
import isy
import keydesc
import screen
import utilities
import logsupport
from config import debugPrint
from eventlist import EventItem

wc = webcolors.name_to_rgb


class KeyScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('Screen', "New KeyScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		self.subscriptionlist = {}
		self.NodeWatch = []

		# Build the Key objects
		for keyname in screensection:
			if isinstance(screensection[keyname], Section):
				config.Logs.Log("-Key:" + keyname)
				NewKey = keydesc.KeyDesc(screensection[keyname], keyname)
				if NewKey.type == 'ONOFF':
					NewKey.Proc = functools.partial(self.OnOff, NewKey)
				elif NewKey.type == 'ONBLINKRUNTHEN':
					NewKey.Proc = functools.partial(self.OnBlinkRunThen, NewKey)
				else:  # unknown type
					config.Logs.Log('Undefined key type for: ' + keyname, severity=logsupport.ConsoleWarning)
				self.Keys.append(NewKey)

		self.LayoutKeys()
		utilities.register_example("KeyScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     KeyScreenDesc:" + ":<" + str(self.Keys) + ">"

	def BlinkKey(self, K, cycle):
		if cycle > 0:
			if cycle%2 == 0:
				K.PaintKey(ForceDisplay=True, DisplayState=True)  # force on
			else:
				K.PaintKey(ForceDisplay=True, DisplayState=False)  # force off
			E = EventItem(self, 1, 'keyblink', .5, functools.partial(self.BlinkKey, K, cycle - 1))
			config.DS.Tasks.AddTask(E)
		else:
			K.PaintKey()  # make sure to leave it in real state

	def OnOff(self, K, presstype):
		K.State = not K.State
		if K.ISYObj is not None:
			K.ISYObj.SendCommand(K.State, presstype)
		else:
			config.Logs.Log("Screen: " + self.name + " press unbound key: " + K.name,
							severity=logsupport.ConsoleWarning)
		K.PaintKey()

	def OnBlinkRunThen(self, K, presstype):
		# force double tap for programs for safety - too easy to accidentally single tap with touchscreen
		print "Blinker"
		if presstype == config.FASTPRESS:
			K.ISYObj.runThen()
			E = EventItem(self, 1, 'keyblink', .5, functools.partial(self.BlinkKey, K, 7))
			config.DS.Tasks.AddTask(E)

	def EnterScreen(self):
		self.subscriptionlist = {}
		debugPrint('Main', "Enter to screen: ", self.name)

		for K in self.Keys:
			if K.MonitorObj is not None:
				# skip program buttons
				self.subscriptionlist[K.MonitorObj.address] = K

		debugPrint('Main', "Active Subscription List will be:")
		self.NodeWatch = []
		for i in self.subscriptionlist:
			debugPrint('Main', "  Subscribe: ", i, self.subscriptionlist[i].name, " : ",
					   self.subscriptionlist[i].ISYObj.name, ' via ', self.subscriptionlist[i].MonitorObj.name)
			self.NodeWatch.append(i)

	def InitDisplay(self, nav):

		states = isy.get_real_time_status(self.subscriptionlist.keys())
		for K in self.Keys:
			if K.MonitorObj is not None:
				K.State = not (states[K.MonitorObj.address] == 0)  # K is off (false) only if state is 0
		super(KeyScreenDesc, self).InitDisplay(nav)

	def ISYEvent(self, event):
		# Watched node reported change event is ("Node", addr, value, seq)
		K = self.subscriptionlist[event[1]]
		print 'KS ISYEvent ', K.name, event, K.State
		K.State = not (int(event[2] if event[2].isdigit() else 0) == 0)  # K is off (false) only if state is 0
		print 'KS after ', K.State
		K.PaintKey()






config.screentypes["Keypad"] = KeyScreenDesc
