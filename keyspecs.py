import functools
import pygame
import config
import eventlist
import isy
import supportscreens
import utilities
import debug
import logsupport
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from toucharea import ManualKeyDesc
from stores import valuestore
import shlex

def KeyWithVarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl','Var changed for key ',storeitem.name,' from ',old,' to ',new)
	notice = pygame.event.Event(config.DS.ISYChange, varinfo=param)
	pygame.fastevent.post(notice)
	pass


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
	elif keytype == 'VARKEY':
		NewKey = VarKey(screen, screensection, keyname)
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
	# This is a key that brings up a sub screen that allows buttons to change the value of the var explicitly
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVarValue Key Desc ", keyname)
		self.Value = None
		self.VarID = (0,0)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', Var='')
		self.VarName = self.Var.split(':')
		self.Proc = self.SetVarValue

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


class VarKey(ManualKeyDesc):

	class DistOpt(object):
		def __init__(self,chooser,color,label):
			self.Chooser = chooser
			self.Color = color
			self.Label = label.split(';')

	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen',"              New Var Key ", keyname)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', Var='', Appearance=[], ValueSeq=[])
		valuestore.AddAlert(self.Var, (KeyWithVarChanged,(keyname,self.Var)))
		if self.ValueSeq != []:
			self.Proc = self.VarKeyPressed
			t = []
			for n in self.ValueSeq: t.append(int(n))
			self.ValueSeq = t
		self.displayoptions = []
		self.oldval = None
		self.State = False
		for item in self.Appearance:
			desc = shlex.split(item)
			rng = desc[0].split(':')
			chooser = (int(rng[0]),int(rng[0])) if len(rng) == 1 else (int(rng[0]),int(rng[1]))
			clr = desc[1]
			lab = self.label if len(desc) < 3 else desc[2]
			self.displayoptions.append(self.DistOpt(chooser,clr,lab))

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# create the images here dynamically then let lower methods do display, blink etc.
		val = valuestore.GetVal(self.Var)
		if self.oldval != val:
			self.oldval = val
			oncolor = utilities.wc(self.KeyColorOn)
			offcolor = utilities.wc(self.KeyColorOff)
			lab = []
			for i in self.displayoptions:
				if val >= i.Chooser[0] and val <= i.Chooser[1]:
					lab = i.Label[:]

					oncolor = utilities.tint(i.Color)
					offcolor = utilities.wc(i.Color)
					break
			if lab == []: lab = self.KeyLabelOn[:]
			lab2 = []
			for line in lab:
				lab2.append(line.replace('$', str(val)))
			self.BuildKey(oncolor, offcolor)
			self.SetKeyImages(lab2, lab2, 0, True)
			if self.Blink != 0: self.ScheduleBlinkKey(self.Blink)
		super(VarKey,self).PaintKey(ForceDisplay,DisplayState)

	def VarKeyPressed(self, presstype):
		try:
			i = self.ValueSeq.index(valuestore.GetVal(self.Var))
		except ValueError:
			i = len(self.ValueSeq) - 1
		valuestore.SetVal(self.Var, self.ValueSeq[(i+1)%len(self.ValueSeq)])



class SetVarKey(ManualKeyDesc):
	def __init__(self, screen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)
		ManualKeyDesc.__init__(self, screen, keysection, keyname)
		utilities.LocalizeParams(self, keysection, '--', VarType='undef', Var='', Value=0)
		try:
			self.Proc = self.SetVarKeyPressed
			if self.VarType != 'undef': # todo del later

				if self.VarType == 'State':
					self.VarName = ('ISY','State',self.Var)
				elif self.VarType == 'Int':
					self.VarName = ('ISY', 'Int', self.Var)
				elif self.VarType == 'Local':
					self.VarName = ('LocalVars', self.Var)
				else:
					logsupport.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', screen.name,
								severity=ConsoleWarning)
					self.Proc = ErrorKey
				logsupport.Logs.Log('VarKey definition using depreacted VarKey ', self.VarType, ' change to ',
									valuestore.ExternalizeVarName(self.VarName), severity=ConsoleWarning)
			else:
				self.VarName = self.Var.split(':')
		except Exception as e:
			logsupport.Logs.Log('Var key error on screen: ' + screen.name + ' Var: ' + self.Var, severity=ConsoleWarning)
			self.Proc = ErrorKey

		utilities.register_example("SetVarKey", self)

	def SetVarKeyPressed(self, presstype):
		valuestore.SetVal(self.VarName,self.Value)
		self.BlinkKey(self.Blink)

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
