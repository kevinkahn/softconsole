import utilities
from debug import debugPrint
from toucharea import ManualKeyDesc
import eventlist
import functools
import config
import isy
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail


def CreateKey(screen, screensection, keyname):
	keytype = screensection.get('type', 'ONOFF')
	config.Logs.Log("-Key:" + keyname, severity=ConsoleDetail)
	if keytype in ('ONOFF', 'ON'):
		NewKey = OnOffKey(screen, screensection, keyname, keytype)
	elif keytype in ('ONBLINKRUNTHEN', 'RUNTHEN'):
		NewKey = RunThenKey(screen, screensection, keyname)
	elif keytype == 'SETVAR':
		NewKey = SetVarKey(screen, screensection, keyname)
	elif keytype == 'SETVARVALUE':
		NewKey = SetVarValueKey(screen, screensection, keyname)
	else:  # unknown type
		NewKey = BlankKey(screen, screensection, keyname)
		config.Logs.Log('Undefined key type ' + keytype + ' for: ' + keyname, severity=ConsoleWarning)
	return NewKey


def ErrorKey(presstype):
	# used to handle badly defined keys
	config.Logs.Log('Ill-defined Key Pressed', severity=ConsoleWarning)


class BlankKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debugPrint('Screen', "             New Blank Key Desc ", keyname)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		self.Proc = ErrorKey
		self.State = False
		self.label = self.label.append('(NoOp)')

		utilities.register_example("BlankKey", self)


class SetVarValueKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debugPrint('Screen', "             New SetVarValue Key Desc ", keyname)

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
				config.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', screen.name,
								severity=ConsoleWarning)
				self.VarID = (0, 0)
				self.Proc = ErrorKey
		except:
			config.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + keyname, severity=ConsoleWarning)
			self.Proc = ErrorKey

		utilities.register_example("SetVarValueKey", self)

	def InitDisplay(self):
		debugPrint("Screen", "SetVarValue Key.InitDisplay ", self.Screen.name, self.name)
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
		debugPrint('Screen', "             New SetVar Key Desc ", keyname)

		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', VarType='undef', Var='', Value=0)
		try:
			self.Proc = self.SetVar
			if self.VarType == 'State':
				self.VarID = (2, config.ISY.varsState[self.Var])
			elif self.VarType == 'Int':
				self.VarID = (1, config.ISY.varsInt[self.Var])
			elif self.VarType == 'Local':
				self.VarID = (3, config.ISY.varsLocal[self.Var])
			else:
				config.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', screen.name,
								severity=ConsoleWarning)
				self.Proc = ErrorKey
		except:
			config.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + self.Var, severity=ConsoleWarning)
			self.Proc = ErrorKey


		utilities.register_example("SetVarKey", self)

	def SetVar(self, presstype):
		isy.SetVar(self.VarID[0], self.VarID[1], self.Value)

	# todo  add visual call Feedback


class RunThenKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debugPrint('Screen', "             New RunThen Key Desc ", keyname)
		utilities.LocalizeParams(self, keysection, '--', KeyRunThenName='', FastPress=1, Blink=7)
		# todo check handle of deprecated keyword
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		self.State = False  # for appearance only
		try:
			self.ISYObj = config.ISY.ProgramsByName[self.KeyRunThenName]
		except:
			self.ISYObj = None
			debugPrint('Screen', "Unbound program key: ", self.name)
			config.Logs.Log("Missing Prog binding: " + self.name, severity=ConsoleWarning)
		self.Proc = self.OnBlinkRunThen  # todo should Proc be unified as 'action'?

		utilities.register_example("RunThenKey", self)

	def OnBlinkRunThen(self, presstype):
		# force double tap for programs for safety - too easy to accidentally single tap with touchscreen

		if not (self.FastPress and presstype <> config.FASTPRESS):
			self.ISYObj.runThen()
			if self.Blink <> 0:
				E = eventlist.ProcEventItem(id(self.Screen), 'keyblink', functools.partial(self.BlinkKey, self.Blink))
				# todo why dynamic, should move to a feedback call of some sort
				config.DS.Tasks.AddTask(E, .5)


class OnOffKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname, keytype):
		debugPrint('Screen', "             New ", keytype, " Key Desc ", keyname)
		utilities.LocalizeParams(self, keysection, '--', SceneProxy='', NodeName='')
		self.MonitorObj = None  # ISY Object monitored to reflect state in the key (generally a device within a Scene)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		if keyname == '*Action*': keyname = self.NodeName  # special case for alert screen action keys that always have same name
		if keyname in config.ISY.ScenesByName:
			self.ISYObj = config.ISY.ScenesByName[keyname]
			if self.SceneProxy <> '':
				# explicit proxy assigned
				if self.SceneProxy in config.ISY.NodesByAddr:
					# address given
					self.MonitorObj = config.ISY.NodesByAddr[self.SceneProxy]
					debugPrint('Screen', "Scene ", keyname, " explicit address proxying with ",
							   self.MonitorObj.name, '(', self.SceneProxy, ')')
				elif self.SceneProxy in config.ISY.NodesByName:
					self.MonitorObj = config.ISY.NodesByName[self.SceneProxy]
					debugPrint('Screen', "Scene ", keyname, " explicit name proxying with ",
							   self.MonitorObj.name, '(', self.MonitorObj.address, ')')
				else:
					config.Logs.Log('Bad explicit scene proxy:' + self.name, severity=ConsoleWarning)
			else:
				for i in self.ISYObj.members:
					device = i[1]
					if device.enabled and device.hasstatus:
						self.MonitorObj = device
						break
					else:
						config.Logs.Log('Skipping disabled/nonstatus device: ' + device.name, severity=ConsoleWarning)
				if self.MonitorObj is None:
					config.Logs.Log("No proxy for scene: " + keyname, severity=ConsoleError)
				debugPrint('Screen', "Scene ", keyname, " default proxying with ",
						   self.MonitorObj.name)
		elif keyname in config.ISY.NodesByName:
			self.ISYObj = config.ISY.NodesByName[keyname]
			self.MonitorObj = self.ISYObj
		else:
			debugPrint('Screen', "Screen", keyname, "unbound")
			config.Logs.Log('Key Binding missing: ' + self.name, severity=ConsoleWarning)

		if keytype == 'ONOFF':
			self.Proc = self.OnOff
		else:
			self.Proc = self.OnKey

		utilities.register_example("OnOffKey", self)

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super(OnOffKey, self).FinishKey(center, size, firstfont, shrink)
		self.Screen.NodeList[self.MonitorObj.address] = self  # register for events for this key

	def InitDisplay(self):
		debugPrint("Screen", "OnOffKey Key.InitDisplay ", self.Screen.name, self.name)
		state = isy.get_real_time_node_status(self.MonitorObj.address)
		self.State = not (state == 0)  # K is off (false) only if state is 0
		super(OnOffKey, self).InitDisplay()


	def OnOff(self, presstype):
		self.State = not self.State
		if self.ISYObj is not None:
			self.ISYObj.SendCommand(self.State, presstype)
		else:
			config.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,
							severity=ConsoleWarning)
		self.PaintKey()  # todo Feedback

	def OnKey(self, presstype):
		self.State = True
		if self.ISYObj is not None:
			self.ISYObj.SendCommand(True, presstype)
		else:
			config.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name, severity=ConsoleWarning)
		self.PaintKey()  # todo Feedback
