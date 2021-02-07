import debug
import logsupport
from screens import screen
import screens.supportscreens as supportscreens
from utils import utilities, displayupdate
from keys.keyspecs import KeyTypes
from keys.keyutils import _resolvekeyname
from logsupport import ConsoleWarning
from keyspecs.toucharea import ManualKeyDesc
import functools


class OnOffKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, kn, keytype='ONOFF'):
		keyname, self.Hub = _resolvekeyname(kn, thisscreen.DefaultHubObj)
		# self.ControlObj = None  # object on which to make operation calls
		self.DisplayObj = None  # object whose state is reflected in key

		debug.debugPrint('Screen', "             New ", keytype, " Key Desc ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, SceneProxy='', NodeName='')

		if keyname == '*Action*': keyname = self.NodeName  # special case for alert screen action keys that always have same name
		self.ControlObj, self.DisplayObj = self.Hub.GetNode(keyname, self.SceneProxy)

		if self.ControlObjUndefined():
			debug.debugPrint('Screen', "Screen", keyname, "unbound")
			logsupport.Logs.Log('Key Binding missing: ' + self.name,
								severity=ConsoleWarning)  # todo - should this handle the delayed key case of an indirector?
		if hasattr(self.ControlObj, 'SendOnPct'): self.AllowSlider = True

		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.KeyPressAction,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
			self.Proc = self.VerifyScreen.Invoke
		else:
			self.Proc = self.KeyPressAction
			self.ProcDblTap = self.KeyPressActionDbl

		if self.AllowSlider:
			self.SliderScreen = supportscreens.SliderScreen(self, self.KeyCharColorOn, self.KeyColor,
															self.ControlObj.GetBrightness,
															self.UpdateBrightness)  # todo add orientation override
			self.ProcLong = self.SliderScreen.Invoke
		else:
			self.ProcLong = self.IgnoreLong

		if keytype == 'ONOFF':
			self.KeyAction = 'OnOff'
		elif keytype == 'ON':
			self.KeyAction = 'On'
		else:
			self.KeyAction = 'Off'

		utilities.register_example("OnOffKey", self)

	def HandleNodeEvent(self, evnt):
		if not isinstance(evnt.value, int):
			logsupport.Logs.Log("Node event with non integer state: " + evnt,
								severity=ConsoleWarning)
			evnt.value = int(evnt.value)
		oldunknown = self.UnknownState
		self.State = not (evnt.value == 0)  # K is off (false) only if state is 0
		self.UnknownState = True if evnt.value == -1 else False
		if self.UnknownState:
			# add node to unknowns list for hub
			self.ControlObj.Hub.AddToUnknowns(self.ControlObj)
		elif oldunknown:
			self.ControlObj.Hub.DeleteFromUnknowns(self.ControlObj)
		self.PaintKey()
		displayupdate.updatedisplay()

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super(OnOffKey, self).FinishKey(center, size, firstfont, shrink)
		if self.DisplayObj is not None:
			self.Screen.AddToHubInterestList(self.Hub, self.DisplayObj.address, self)

	def InitDisplay(self):
		debug.debugPrint("Screen", "OnOffKey Key.InitDisplay ", self.Screen.name, self.name)
		state = self.Hub.GetCurrentStatus(self.DisplayObj)
		if state is None:
			logsupport.Logs.Log("No state available for  key: " + self.name + ' on screen: ' + self.Screen.name,
								severity=ConsoleWarning)
			state = -1
			self.State = False
		else:
			self.State = not (state == 0)  # K is off (false) only if state is 0
		self.UnknownState = True if state == -1 else False
		super().InitDisplay()

	def KeyPressAction(self):
		if self.KeyAction == "OnOff":
			self.State = not self.State
		elif self.KeyAction == "On":
			self.State = True  # todo fix to allow override by object
		elif self.KeyAction == "Off":
			self.State = False

		if not self.ControlObjUndefined():
			poststate = self.ControlObj.SendOnOffCommand(self.State)
			if poststate is not None: self.State = poststate
			self.ScheduleBlinkKey(self.Blink)
		else:
			logsupport.Logs.Log("Screen: " + self.Screen.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)
			self.ScheduleBlinkKey(20)

	def KeyPressActionDbl(self):
		if self.KeyAction == "OnOff":
			self.State = not self.State
		elif self.KeyAction == "On":
			self.State = True
		elif self.KeyAction == "Off":
			self.State = False

		if not self.ControlObjUndefined():
			self.ControlObj.SendOnOffFastCommand(self.State)  # todo this codifies fast press even for nonISY hubs?
			self.ScheduleBlinkKey(self.Blink)
		else:
			logsupport.Logs.Log("Screen: " + self.Screen.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)
			self.ScheduleBlinkKey(20)

	def IgnoreLong(self):
		logsupport.Logs.Log('Ignore long press for screen {}, key {}'.format(self.Screen.name, self.name))
		self.ScheduleBlinkKey(5)

	def ProcLong(self):
		self.State = True
		self.SliderScreen.Invoke()

	# invoke slider screen todo

	def UpdateBrightness(self, brtpct):  # todo if off need to turn on for HA then set brightness value
		# print('Update brt {}'.format(brtpct))
		self.ControlObj.SendOnPct(brtpct)


KeyTypes['ONOFF'] = functools.partial(OnOffKey, keytype='ONOFF')
KeyTypes['ON'] = functools.partial(OnOffKey, keytype='ON')
KeyTypes['OFF'] = functools.partial(OnOffKey, keytype='OFF')
