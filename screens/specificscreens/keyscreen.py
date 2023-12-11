# noinspection PyProtectedMember
from configobj import Section

import debug
from keys import keyspecs
import logsupport
from screens import screen
import screens.__screens as screens
from utils import utilities, displayupdate
from logsupport import ConsoleWarning
from utils.utilfuncs import safeprint


# noinspection PyBroadException
class KeyScreenDesc(screen.BaseKeyScreenDesc):
	# noinspection PyBroadException
	def __init__(self, screensection, screenname, parentscreen=None):
		super().__init__(screensection, screenname, parentscreen=parentscreen)
		debug.debugPrint('Screen', "New KeyScreenDesc ", screenname)

		# Build the Key objects
		for keyname in screensection:
			if isinstance(screensection[keyname], Section):
				self.Keys[keyname] = keyspecs.CreateKey(self, screensection[keyname], keyname)

		self.LayoutKeys()

		debug.debugPrint('Screen', "Active Subscription List for ", self.name, " will be:")
		for h, l in self.HubInterestList.items():
			for i, j in l.items():
				m1 = "  Subscribe on hub {} node: {} {}".format(h, i, j.name)
				m2 = ""
				try:
					m2 = ":{} via {}".format(j.ControlObj.name, j.DisplayObj.name)
				except Exception:
					pass
				debug.debugPrint('Screen', m1 + m2)

		utilities.register_example("KeyScreenDesc", self)

	def InitDisplay(self, nav):
		debug.debugPrint("Screen", "Keyscreen InitDisplay: ", self.name)
		for K in self.Keys.values():
			K.InitDisplay()
		super().InitDisplay(nav)

	def NodeEvent(self, evnt):
		# Watched node reported change event is ("Node", addr, value, seq)
		debug.debugPrint('Screen', evnt)

		if evnt.node is None:  # all keys for this hub
			for _, K in self.HubInterestList[evnt.hub].items():
				logsupport.Logs.Log('Node event to keyscreen with no node {}'.format(evnt), severity=ConsoleWarning)
				debug.debugPrint('Screen', 'KS Wildcard ISYEvent ', K.name, evnt)
				K.UnknownState = True
				K.PaintKey()
				displayupdate.updatedisplay()
		elif evnt.node != 0:
			try:
				K = self.HubInterestList[evnt.hub][evnt.node]
			except Exception as E:
				debug.debugPrint(f'Screen {self.name} Node {evnt.node} ({E})  Bad key to KS - race? ')
				return  # treat as noop
			debug.debugPrint('Screen', 'KS ISYEvent ', K.name, evnt, str(K.State))
			if hasattr(K, 'HandleNodeEvent'):  # todo make all handle event key specifig
				K.HandleNodeEvent(evnt)
			else:
				logsupport.Logs.Log('Generic node event??? {} {}'.format(K.name, evnt),
									severity=ConsoleWarning)
				if not isinstance(evnt.value, int):
					logsupport.Logs.Log("Node event with non integer state: " + evnt,
										severity=ConsoleWarning)
					evnt.value = int(evnt.value)
				K.State = not (evnt.value == 0)  # K is off (false) only if state is 0
				K.UnknownState = True if evnt.value == -1 else False
				K.PaintKey()
				displayupdate.updatedisplay()
		else:
			logsupport.Logs.Log('varchange via Node event? {} {}'.format(self.name, evnt), severity=ConsoleWarning)

	def VarEvent(self, evnt):
		safeprint('Var event called {}'.format(evnt))
		try:
			K = self.Keys[evnt.varinfo[0]]
			K.PaintKey()
			displayupdate.updatedisplay()
		except Exception as E:
			debug.debugPrint('Screen', "Var change reported to screen that doesn't care", self.name,
							 str(evnt.varinfo), E)  # todo event reporting correlation to screens could use rework
			logsupport.Logs.Log(f"Var change reported to screen that doesn't care {self.name} {evnt} ({E})",
								severity=ConsoleWarning)


screens.screentypes["Keypad"] = KeyScreenDesc
