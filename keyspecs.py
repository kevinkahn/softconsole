import functools

import config
import eventlist
import isy
import supportscreens
import utilities
import debug
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from toucharea import ManualKeyDesc


def CreateKey(screen, screensection, keyname):
	if screensection.get('type', 'ONOFF', delkey=False) == 'RUNTHEN':
		screensection['type'] = 'RUNPROG'
	if screensection.get('type', 'ONOFF', delkey=False) == 'ONBLINKRUNTHEN':
		screensection['type'] = 'RUNPROG'
		screensection['FastPress'] = 1
		screensection['Blink'] = 7
		screensection['ProgramName'] = screensection.get('KeyRunThenName', '')


	keytype = screensection.get('type', 'ONOFF')
	logsupport.Logs.Log("-Key:" + keyname, severity=ConsoleDetail)
	if keytype in ('ONOFF', 'ON', 'OFF'):
		NewKey = OnOffKey(screen, screensection, keyname, keytype)
	elif keytype == 'SETVAR':
		NewKey = SetVarKey(screen, screensection, keyname)
	elif keytype == 'SETVARVALUE':
		NewKey = SetVarValueKey(screen, screensection, keyname)
	elif keytype == 'RUNPROG':
		NewKey = RunProgram(screen, screensection, keyname)
	else:  # unknown type
		NewKey = BlankKey(screen, screensection, keyname)
		logsupport.Logs.Log('Undefined key type ' + keytype + ' for: ' + keyname, severity=ConsoleWarning)
	return NewKey


def ErrorKey(presstype):
	# used to handle badly defined keys
	logsupport.Logs.Log('Ill-defined Key Pressed', severity=ConsoleWarning)


class BlankKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New Blank Key Desc ", keyname)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		self.Proc = ErrorKey
		self.State = False
		self.label = self.label.append('(NoOp)')

		utilities.register_example("BlankKey", self)


class SetVarValueKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVarValue Key Desc ", keyname)
		self.Value = None
		self.VarID = (0,0)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', VarType='undef', Var='')

		try:
			self.Proc = self.SetVarValue  # todo if not changeable?
			if self.VarType == 'State':
				self.VarID = (2, config.ISY.varsState[keyname])
			elif self.VarType == 'Int':
				self.VarID = (1, config.ISY.varsInt[keyname])
			elif self.VarType == 'Local':
				self.VarID = (3, config.ISY.varsLocal[keyname])
			else:
				logsupport.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', screen.name,
								severity=ConsoleWarning)
				self.VarID = (0, 0)
				self.Proc = ErrorKey
		except:
			logsupport.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + keyname, severity=ConsoleWarning)
			self.Proc = ErrorKey

		utilities.register_example("SetVarValueKey", self)

	def InitDisplay(self):
		debug.debugPrint("Screen", "SetVarValue Key.InitDisplay ", self.Screen.name, self.name)
		self.Value = isy.GetVar(self.VarID)
		super(SetVarValueKey, self).InitDisplay()

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super(SetVarValueKey, self).FinishKey(center, size, firstfont, shrink)
		self.Screen.VarsList[self.VarID] = self

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# extact current value from variable array
		self.SetKeyImages(self.label + [str(self.Value)])
		super(SetVarValueKey, self).PaintKey(ForceDisplay, DisplayState)

	def SetVarValue(self, presstype):
		# Call a screen repainter proc
		# call reinitdisplay on enclosing screen
		pass

	# todo create a screen to allow changing the value if parameter is maleable


class SetVarKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)

		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', VarType='undef', Var='', Value=0)
		try:
			self.Proc = self.SetVarKeyPressed
			if self.VarType == 'State':
				self.VarID = (2, config.ISY.varsState[self.Var])
			elif self.VarType == 'Int':
				self.VarID = (1, config.ISY.varsInt[self.Var])
			elif self.VarType == 'Local':
				self.VarID = (3, config.ISY.varsLocal[self.Var])
			else:
				logsupport.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', screen.name,
								severity=ConsoleWarning)
				self.Proc = ErrorKey
		except:
			logsupport.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + self.Var, severity=ConsoleWarning)
			self.Proc = ErrorKey

		utilities.register_example("SetVarKey", self)

        def SetVarKeyPressed(self, presstype):
		isy.SetVar(self.VarID, self.Value)

class NewSetVarKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)

		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', VarType='undef', Var='', Value=0)
		try:
			self.Proc = self.SetVarKeyPressed
			if self.VarType == 'State':
				self.VarID = (2, config.ISY.varsState[self.Var])
			elif self.VarType == 'Int':
				self.VarID = (1, config.ISY.varsInt[self.Var])
			elif self.VarType == 'Local':
				self.VarID = (3, config.ISY.varsLocal[self.Var])
			else:
				logsupport.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', screen.name,
								severity=ConsoleWarning)
				self.Proc = ErrorKey
		except:
			logsupport.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + self.Var, severity=ConsoleWarning)
			self.Proc = ErrorKey

		utilities.register_example("SetVarKey", self)

        def SetVarKeyPressed(self, presstype):
		isy.SetVar(self.VarID, self.Value)


class RunProgram(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New RunProgram Key ", keyname)
		utilities.LocalizeParams(self, keysection, '--', ProgramName='')
		ManualKeyDesc.__init__(self, screen, keysection, keyname)

		self.State = False
		try:
			self.ISYObj = config.ISY.ProgramsByName[self.ProgramName]
		except:
			self.ISYObj = config.DummyProgram
			debug.debugPrint('Screen', "Unbound program key: ", self.name)
			logsupport.Logs.Log("Missing Prog binding: " + self.name, severity=ConsoleWarning)
		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.VerifyRunAndReturn,
															screen, self.KeyColorOff, self.KeyCharColorOff,
															screen.BackgroundColor, self.KeyOffOutlineColor,
															screen.CharColor, self.State)
		self.Proc = self.RunKeyPressed

	def VerifyRunAndReturn(self, go, presstype):
		if go:
			self.ISYObj.runThen()
			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)
			if self.Blink != 0:
				E = eventlist.ProcEventItem(id(self.Screen), 'keyblink', functools.partial(self.BlinkKey, self.Blink))
				config.DS.Tasks.AddTask(E, .5)
		else:
			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)

	def RunKeyPressed(self, presstype):
		if self.FastPress and presstype != config.FASTPRESS:
			return
		if self.Verify:
			self.VerifyScreen.Invoke()
		else:
			self.ISYObj.runThen()
			self.BlinkKey(self.Blink)

class OnOffKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname, keytype):
		debug.debugPrint('Screen', "             New ", keytype, " Key Desc ", keyname)
		utilities.LocalizeParams(self, keysection, '--', SceneProxy='', NodeName='')
		ManualKeyDesc.__init__(self, screen, keysection, keyname)

		self.MonitorObj = None  # ISY Object monitored to reflect state in the key (generally a device within a Scene)
		if keyname == '*Action*': keyname = self.NodeName  # special case for alert screen action keys that always have same name
		if config.ISY.SceneExists(keyname):
			self.ISYObj = config.ISY.GetSceneByName(keyname)
			if self.SceneProxy != '':
				# explicit proxy assigned
				if self.SceneProxy in config.ISY.NodesByAddr:
					# address given
					self.MonitorObj = config.ISY.NodesByAddr[self.SceneProxy]
					debug.debugPrint('Screen', "Scene ", keyname, " explicit address proxying with ",
							   self.MonitorObj.name, '(', self.SceneProxy, ')')
				elif config.ISY.NodeExists(self.SceneProxy):
					self.MonitorObj = config.ISY.GetNodeByName(self.SceneProxy)
					debug.debugPrint('Screen', "Scene ", keyname, " explicit name proxying with ",
							   self.MonitorObj.name, '(', self.MonitorObj.address, ')')
				else:
					logsupport.Logs.Log('Bad explicit scene proxy:' + self.name, severity=ConsoleWarning)
			else:
				for i in self.ISYObj.members:
					device = i[1]
					if device.enabled and device.hasstatus:
						self.MonitorObj = device
						break
					else:
						logsupport.Logs.Log('Skipping disabled/nonstatus device: ' + device.name, severity=ConsoleWarning)
				if self.MonitorObj is None:
					logsupport.Logs.Log("No proxy for scene: " + keyname, severity=ConsoleError)
				debug.debugPrint('Screen', "Scene ", keyname, " default proxying with ",
						   self.MonitorObj.name)
		elif config.ISY.NodeExists(keyname):
			self.ISYObj = config.ISY.GetNodeByName(keyname)
			self.MonitorObj = self.ISYObj
		else:
			debug.debugPrint('Screen', "Screen", keyname, "unbound")
			logsupport.Logs.Log('Key Binding missing: ' + self.name, severity=ConsoleWarning)

		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.VerifyPressAndReturn,
															screen, self.KeyColorOff, self.KeyCharColorOff,
															screen.BackgroundColor, self.KeyOffOutlineColor,
															screen.CharColor, self.State)

		if keytype == 'ONOFF':
			self.KeyAction = 'OnOff'
		elif keytype == 'ON':
			self.KeyAction = 'On'
		else:
			self.KeyAction = 'Off'
		self.Proc = self.OnOffKeyPressed

		utilities.register_example("OnOffKey", self)

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super(OnOffKey, self).FinishKey(center, size, firstfont, shrink)
		if self.MonitorObj != None:
			self.Screen.NodeList[self.MonitorObj.address] = self  # register for events for this key

	def InitDisplay(self):
		debug.debugPrint("Screen", "OnOffKey Key.InitDisplay ", self.Screen.name, self.name)
		state = isy.get_real_time_obj_status(self.MonitorObj)
		self.State = not (state == 0)  # K is off (false) only if state is 0
		super(OnOffKey, self).InitDisplay()

	def OnOffKeyPressed(self, presstype):
		self.lastpresstype = presstype
		if self.Verify:
			self.VerifyScreen.Invoke()
		else:
			if self.KeyAction == "OnOff":
				self.State = not self.State
			elif self.KeyAction == "On":
				self.State = True
			elif self.KeyAction == "Off":
				self.State = False

			if self.ISYObj is not None:
				self.ISYObj.SendCommand(self.State, presstype)
				self.BlinkKey(self.Blink)
			else:
				logsupport.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)
				self.BlinkKey(20)

	def VerifyPressAndReturn(self, go, presstype):
		if go:
			if self.KeyAction == "OnOff":
				self.State = not self.State
			elif self.KeyAction == "On":
				self.State = True
			elif self.KeyAction == "Off":
				self.State = False
			if self.ISYObj is not None:
				self.ISYObj.SendCommand(self.State, self.lastpresstype)
			else:
				logsupport.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)

			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)
			self.BlinkKey(self.Blink)
		else:
			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)
