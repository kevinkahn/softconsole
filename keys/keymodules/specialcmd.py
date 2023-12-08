import debug
from screens import screen
import screens.supportscreens as supportscreens
from keys.keyutils import _resolvekeyname
from keys.keyspecs import KeyTypes
from keyspecs.toucharea import ManualKeyDesc
import hubs.hubs

class SpecCmd(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SpecCmd Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, Command='', Parameter=[], SliderCommand='', SliderParameter=[])

		self.Hub = None  # never monitor state messages for key in slider
		self.target, self.hub = _resolvekeyname(keyname, thisscreen.DefaultHubObj)
		self.node = self.hub.GetNode(self.target)[0]

		self.param = {}
		if self.Parameter:
			for p in self.Parameter:
				if ':' in p:
					t = p.split(':')
					self.param[t[0]] = t[1]
				else:
					self.param[p] = 'noval'
		self.sliderparam = {}
		if self.SliderParameter:
			for p in self.SliderParameter:
				if ':' in p:
					t = p.split(':')
					self.sliderparam[t[0]] = t[1]
				else:
					self.sliderparam[p] = 'noval'

		self.State = False
		self.ProcLong = self.IgnorePress
		if self.Command == '':
			self.CmdKeyPressed = self.IgnorePress
			self.CmdKeyDblPressed = self.IgnorePress

		if self.SliderCommand != '':
			screen.AddUndefaultedParams(self, keysection, SlideOrientation=0)
			self.SliderScreen = supportscreens.SliderScreen(self, self.KeyCharColorOn, self.KeyColor,
															self.GetSliderVal,
															self.SetSliderVal, orientation=self.SlideOrientation)
			self.ProcLong = self.SliderScreen.Invoke
			self.InputItem = self.Var.split(':')
			self.entity = hubs.hubs.Hubs[self.InputItem[0]].GetNode(self.InputItem[1])[0].attributes[self.InputItem[2]]

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


	def GetSliderVal(self):
		return self.entity

	def SetSliderVal(self, val, final=False):
		if final:
			temp = {list(self.sliderparam.keys())[0]: int(val)}
			self.node.SendSpecialCmd(self.SliderCommand, self.target, temp)
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

	def IgnorePress(self):
		return


KeyTypes['SPECCMD'] = SpecCmd
