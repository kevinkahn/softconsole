import functools

import webcolors
from configobj import Section

import config
import isy
import keydesc
import screen
import utilities
import logsupport
from config import debugPrint, WAITNORMALBUTTON, WAITNORMALBUTTONFAST, WAITISYCHANGE, WAITEXIT

wc = webcolors.name_to_rgb


class KeyScreenDesc(screen.BaseKeyScreenDesc):
	def __init__(self, screensection, screenname):
		debugPrint('BuildScreen', "New KeyScreenDesc ", screenname)
		screen.BaseKeyScreenDesc.__init__(self, screensection, screenname)
		self.subscriptionlist = {}

		# Build the Key objects
		for keyname in screensection:
			if isinstance(screensection[keyname], Section):
				NewKey = keydesc.KeyDesc(screensection[keyname], keyname)
				self.keysbyord.append(NewKey)

		self.LayoutKeys()
		utilities.register_example("KeyScreenDesc", self)

	def __repr__(self):
		return screen.ScreenDesc.__repr__(self) + "\r\n     KeyScreenDesc:" + ":<" + str(self.keysbyord) + ">"

	def HandleScreen(self, newscr=True):

		def BlinkKey(scr, key, cycle):
			# thistime = finalstate if cycle % 2 <> 0 else not finalstate
			key.State = not key.State
			key.PaintKey()

		if newscr:
			# key screen change actually occurred
			self.PaintBase()
			self.subscriptionlist = {}
			debugPrint('Main', "Switching to screen: ", self.name)
			for K in self.keysbyord:
				if K.MonitorObj is not None:
					# skip program buttons
					self.subscriptionlist[K.MonitorObj.address] = K
			states = isy.get_real_time_status(self.subscriptionlist.keys())
			for K in self.keysbyord:
				if K.MonitorObj is not None:
					K.State = not (states[K.MonitorObj.address] == 0)  # K is off (false) only if state is 0

			debugPrint('Main', "Active Subscription List will be:")
			addressestoscanfor = ["Status"]
			for i in self.subscriptionlist:
				debugPrint('Main', "  Subscribe: ", i, self.subscriptionlist[i].name, " : ",
						   self.subscriptionlist[i].RealObj.name, ' via ', self.subscriptionlist[i].MonitorObj.name)
				addressestoscanfor.append(i)
			config.toDaemon.put(addressestoscanfor)
			self.PaintKeys()
		else:
			debugPrint('Main', "Skipping screen recreation: ", self.name)

		blinkproc = None
		blinktime = 0
		blinks = 0

		while 1:
			choice = config.DS.NewWaitPress(self, callbackint=blinktime, callbackproc=blinkproc, callbackcount=blinks)
			blinkproc = None
			blinktime = 0
			blinks = 0
			if (choice[0] == WAITNORMALBUTTON) or (choice[0] == WAITNORMALBUTTONFAST):
				# handle various keytype cases
				K = self.keysbyord[choice[1]]
				if K.type == "ONOFF":
					K.State = not K.State
					if K.RealObj is not None:
						K.RealObj.SendCommand(K.State, choice[0] <> WAITNORMALBUTTON)
					# config.Logs.Log("Sent command to " + K.RealObj.name)
					else:
						config.Logs.Log("Screen: " + self.name + " press unbound key: " + K.name, severity=logsupport.ConsoleWarning)
					K.PaintKey()
				elif K.type == "ONBLINKRUNTHEN":
					# force double tap for programs for safety - too easy to accidentally single tap with touchscreen
					if choice[0] == WAITNORMALBUTTONFAST:
						K.RealObj.runThen()
						blinkproc = functools.partial(BlinkKey, config.screen, K)
						blinktime = .5
						blinks = 8  # even number leaves final state of key same as initial state
						K.PaintKey()
					# leave K.State as is - key will return to off at end
				elif K.type == "ONOFFRUN":
					pass
			elif choice[0] == WAITEXIT:
				return choice[1]
			elif choice[0] == WAITISYCHANGE:
				K = self.subscriptionlist[choice[1][0]]
				ActState = int(choice[1][1]) <> 0

				if ActState <> K.State:
					K.State = ActState
					K.PaintKey()


config.screentypes["Keypad"] = KeyScreenDesc
