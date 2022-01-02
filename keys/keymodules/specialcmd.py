import debug
from screens import screen
import screens.supportscreens as supportscreens
from keys.keyutils import _resolvekeyname
from keys.keyspecs import KeyTypes
from keyspecs.toucharea import ManualKeyDesc


class SpecCmd(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SpecCmd Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, Command='', Parameter=[])
		self.target, self.hub = _resolvekeyname(keyname, thisscreen.DefaultHubObj)
		self.node = self.hub.GetNode(self.target)[0]

		self.param = {}
		if self.Parameter != []:
			for p in self.Parameter:
				t = p.split(':')
				self.param[t[0]] = t[1]
		self.State = False
		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.CmdKeyPressed,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
			self.Proc = self.VerifyScreen.Invoke
			self.ProcDblTap = self.VerifyScreen.Invoke
		else:
			self.Proc = self.CmdKeyPressed
			self.ProcDblTap = self.CmdKeyDblPressed

	def CmdKeyPressed(self):
		if self.FastPress: return
		self.node.SendSpecialCmd(self.Command, self.target, self.param)
		self.ScheduleBlinkKey(self.Blink)

	def CmdKeyDblPressed(self):
		if self.FastPress:
			if self.Verify:
				self.VerifyScreen.Invoke()
			else:
				self.node.SendSpecialCmd(self.Command, self.target, self.param)
				self.ScheduleBlinkKey(self.Blink)


KeyTypes['SPECCMD'] = SpecCmd
