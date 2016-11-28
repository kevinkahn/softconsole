import utilities
from debug import debugPrint
from toucharea import ManualKeyDesc
import eventlist
import functools
import config
from logsupport import ConsoleWarning, ConsoleError


def CreateKey(screen, screensection, keyname):
	keytype = screensection.get('type', 'ONOFF')
	config.Logs.Log("-Key:" + keyname)
	if keytype == 'ONOFF':
		NewKey = OnOffKey(screen, screensection, keyname)
	elif keytype in ('ONBLINKRUNTHEN', 'RUNTHEN'):
		NewKey = RunThenKey(screen, screensection, keyname)
	elif keytype == 'SETVAR':
		NewKey = SetVarKey(screen, screensection, keyname)
	else:  # unknown type
		NewKey = None  # todo - this should be a "blank" key
		config.Logs.Log('Undefined key type ' + keytype + ' for: ' + keyname, severity=ConsoleWarning)
	return NewKey


class SetVarKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debugPrint('Screen', "             New SetVar Key Desc ", keyname)

		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', VarType='State', Var='', Value=0)
		try:
			if self.VarType == 'State':
				self.VarID = (2, config.ISY.varsState[self.Var])
			else:
				self.VarID = (1, config.ISY.varsInt[self.Var])
		except:
			# todo error fix
			config.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + self.Var)
		self.Proc = self.SetVar
		utilities.register_example("SetVarKey", self)

	# need to set the proc to call using id(screen) as gp

	def SetVar(self, presstype):
		config.ISY.SetVar(self.VarID[0], self.VarID[1], self.Value)

	# todo  call Feedback


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
			# todo Feedback
			if self.Blink <> 0:
				E = eventlist.ProcEventItem(id(self.Screen), 'keyblink', functools.partial(self.BlinkKey,
																						   self.Blink))  # todo why dynamic, should move to a feedback call of some sort
				config.DS.Tasks.AddTask(E, .5)


class OnOffKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debugPrint('Screen', "             New OnOff Key Desc ", keyname)
		utilities.LocalizeParams(self, keysection, '--', SceneProxy='')
		self.MonitorObj = None  # ISY Object monitored to reflect state in the key (generally a device within a Scene) todo?
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
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
		self.Proc = self.OnOff  # todo should Proc be unified as 'action'?

		utilities.register_example("OnOffKey", self)

	def OnOff(self, presstype):
		self.State = not self.State
		if self.ISYObj is not None:
			self.ISYObj.SendCommand(self.State, presstype)
		else:
			config.Logs.Log("Screen: " + self.name + " press unbound key: " + K.name,
							severity=ConsoleWarning)
		self.PaintKey()  # todo Feedback
