import config
import supportscreens
import utilities
import debug
import logsupport
from logsupport import ConsoleWarning, ConsoleDetail
from toucharea import ManualKeyDesc
from stores import valuestore
from controlevents import *
import shlex
from utilfuncs import *
import screen

# noinspection PyUnusedLocal
def KeyWithVarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl','Var changed for key ',storeitem.name,' from ',old,' to ',new)
	# noinspection PyArgumentList
	PostEvent(ConsoleEvent(CEvent.HubNodeChange,hub='*VARSTORE*', varinfo=param))

def _resolvekeyname(kn,DefHub):
	t = kn.split(':')
	if len(t) == 1:
		return t[0], DefHub
	elif len(t) == 2:
		try:
			return t[1], config.Hubs[t[0]]
		except KeyError:
			logsupport.Logs.Log("Bad qualified node name for key: " + kn, severity = ConsoleWarning)
			return "*none*", DefHub
	else:
		logsupport.Logs.Log("Ill formed keyname: ", kn)
		return '*none*', DefHub


def CreateKey(thisscreen, screensection, keyname):
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
		NewKey = OnOffKey(thisscreen, screensection, keyname, keytype)
	elif keytype == 'VARKEY':
		NewKey = VarKey(thisscreen, screensection, keyname)
	elif keytype == 'SETVAR':
		NewKey = SetVarKey(thisscreen, screensection, keyname)
	elif keytype == 'SETVARVALUE':
		NewKey = SetVarValueKey(thisscreen, screensection, keyname)
	elif keytype == 'RUNPROG':
		NewKey = RunProgram(thisscreen, screensection, keyname)
	else:  # unknown type
		NewKey = BlankKey(thisscreen, screensection, keyname)
		logsupport.Logs.Log('Undefined key type ' + keytype + ' for: ' + keyname, severity=ConsoleWarning)
	return NewKey

# noinspection PyUnusedLocal
def ErrorKey(presstype):
	# used to handle badly defined keys
	logsupport.Logs.Log('Ill-defined Key Pressed', severity=ConsoleWarning)


class BlankKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New Blank Key Desc ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		self.Proc = ErrorKey
		self.State = False
		self.label = self.label.append('(NoOp)')

		utilities.register_example("BlankKey", self)


class SetVarValueKey(ManualKeyDesc):
	# This is a key that brings up a sub screen that allows buttons to change the value of the var explicitly
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVarValue Key Desc ", keyname)
		self.Value = None
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, Var='')
		self.Proc = self.SetVarValue

		utilities.register_example("SetVarValueKey", self)

	def InitDisplay(self):
		debug.debugPrint("Screen", "SetVarValue Key.InitDisplay ", self.Screen.name, self.name)
		self.Value = valuestore.GetVal(self.Var)
		super(SetVarValueKey, self).InitDisplay()

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super(SetVarValueKey, self).FinishKey(center, size, firstfont, shrink)

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# extact current value from variable array
		self.SetKeyImages(self.label + [str(self.Value)])
		super(SetVarValueKey, self).PaintKey(ForceDisplay, DisplayState)

	def SetVarValue(self, presstype):
		# Call a screen repainter proc
		# call reinitdisplay on enclosing screen
		pass

	# Future create a screen to allow changing the value if parameter is maleable


class VarKey(ManualKeyDesc):

	class DistOpt(object):
		def __init__(self,chooser,color,label):
			self.Chooser = chooser
			self.Color = color
			self.Label = label.split(';')

	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen',"              New Var Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, Var='', Appearance=[], ValueSeq=[])
		valuestore.AddAlert(self.Var, (KeyWithVarChanged,(keyname,self.Var)))
		if self.ValueSeq:
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
			oncolor = wc(self.KeyColorOn)
			offcolor = wc(self.KeyColorOff)
			lab = []
			for i in self.displayoptions:
				if i.Chooser[0] <= val <= i.Chooser[1]:
					lab = i.Label[:]

					oncolor = tint(i.Color)
					offcolor = wc(i.Color)
					break
			if not lab: lab = self.KeyLabelOn[:]
			lab2 = []
			for line in lab:
				lab2.append(line.replace('$', str(val)))
			self.BuildKey(oncolor, offcolor)
			self.SetKeyImages(lab2, lab2, 0, True)
			if self.Blink != 0: self.ScheduleBlinkKey(self.Blink)
		super(VarKey,self).PaintKey(ForceDisplay,DisplayState)

	# noinspection PyUnusedLocal
	def VarKeyPressed(self, presstype):
		try:
			i = self.ValueSeq.index(valuestore.GetVal(self.Var))
		except ValueError:
			i = len(self.ValueSeq) - 1
		valuestore.SetVal(self.Var, self.ValueSeq[(i+1)%len(self.ValueSeq)])



class SetVarKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, VarType='undef', Var='', Value=0)
		try:
			self.Proc = self.SetVarKeyPressed
			if self.VarType != 'undef': # deprecate

				# todo the default hub name stuff is wrong - not updated to store stuff
				if self.VarType == 'State':
					self.VarName = (config.defaulthub.name,'State',self.Var) # use default hub for each of these 2
				elif self.VarType == 'Int':
					self.VarName = (config.defaulthub.name, 'Int', self.Var)
				elif self.VarType == 'Local':
					self.VarName = ('LocalVars', self.Var)
				else:
					logsupport.Logs.Log('VarType not specified for key ', self.Var, ' on screen ', thisscreen.name,
										severity=ConsoleWarning)
					self.Proc = ErrorKey
				logsupport.Logs.Log('VarKey definition using depreacted VarKey ', self.VarType, ' change to ',
									valuestore.ExternalizeVarName(self.VarName), severity=ConsoleWarning)
			else:
				self.VarName = self.Var.split(':')
		except Exception as e:
			logsupport.Logs.Log('Var key error on screen: ' + thisscreen.name + ' Var: ' + self.Var,
								severity=ConsoleWarning)
			logsupport.Logs.Log('Excpt: ',str(e))
			self.Proc = ErrorKey

		utilities.register_example("SetVarKey", self)

	# noinspection PyUnusedLocal
	def SetVarKeyPressed(self, presstype):
		valuestore.SetVal(self.VarName,self.Value)
		self.ScheduleBlinkKey(self.Blink)

class DummyProgram(object):
	def __init__(self,kn, hn, pn):
		self.keyname = kn
		self.hubname = hn
		self.programname = pn

	def RunProgram(self):
		logsupport.Logs.Log("Pressed unbound program key: " + self.keyname + " for hub: " + self.hubname + " program: " + self.programname)

class RunProgram(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New RunProgram Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, ProgramName='')
		self.State = False
		pn, self.Hub = _resolvekeyname(self.ProgramName, thisscreen.DefaultHubObj)
		self.Program = self.Hub.GetProgram(pn)
		if self.Program is None:
			self.Program = DummyProgram(keyname,self.Hub.name,self.ProgramName)
			logsupport.Logs.Log("Missing Prog binding Key: " + keyname + " Hub: " + self.Hub.name + " Program: " + self.ProgramName, severity=ConsoleWarning)
		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.VerifyRunAndReturn,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
		self.Proc = self.RunKeyPressed

	# noinspection PyUnusedLocal
	def VerifyRunAndReturn(self, go, presstype):
		if go:
			self.Program.RunProgram()
			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)
			if self.Blink != 0:
				self.ScheduleBlinkKey(self.Blink)
		else:
			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)

	def RunKeyPressed(self, presstype):
		if self.FastPress and presstype != config.FASTPRESS:
			return
		if self.Verify:
			self.VerifyScreen.Invoke()
		else:
			self.Program.RunProgram()
			self.ScheduleBlinkKey(self.Blink)

class OnOffKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, kn, keytype):
		keyname, self.Hub = _resolvekeyname(kn, thisscreen.DefaultHubObj)
		self.ControlObj = None # object on which to make operation calls
		self.DisplayObj = None # object whose state is reflected in key

		debug.debugPrint('Screen', "             New ", keytype, " Key Desc ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, SceneProxy='', NodeName='')
		self.lastpresstype = 0

		if keyname == '*Action*': keyname = self.NodeName  # special case for alert screen action keys that always have same name todo - can nodename ever be explicitly set otherwise?
		self.ControlObj, self.DisplayObj = self.Hub.GetNode(keyname,self.SceneProxy)

		if self.ControlObj is None:
			debug.debugPrint('Screen', "Screen", keyname, "unbound")
			logsupport.Logs.Log('Key Binding missing: ' + self.name, severity=ConsoleWarning)

		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.VerifyPressAndReturn,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)

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
		if self.DisplayObj is not None:
			self.Screen.AddToHubInterestList(self.Hub,self.DisplayObj.address,self)

	def InitDisplay(self):
		debug.debugPrint("Screen", "OnOffKey Key.InitDisplay ", self.Screen.name, self.name)
		state = self.Hub.GetCurrentStatus(self.DisplayObj)
		if state is None:
			logsupport.Logs.Log("No state available for  key: " + self.name + ' on screen: ' + self.Screen.name, severity=ConsoleWarning)
			state = -1
			self.State = False
		else:
			self.State = not (state == 0)  # K is off (false) only if state is 0
		self.UnknownState = True if state == -1 else False
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

			if self.ControlObj is not None:
				self.ControlObj.SendOnOffCommand(self.State, presstype)
				self.ScheduleBlinkKey(self.Blink)
			else:
				logsupport.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)
				self.ScheduleBlinkKey(20)

	# noinspection PyUnusedLocal
	def VerifyPressAndReturn(self, go, presstype):
		if go:
			if self.KeyAction == "OnOff":
				self.State = not self.State
			elif self.KeyAction == "On":
				self.State = True
			elif self.KeyAction == "Off":
				self.State = False
			if self.ControlObj is not None:
				self.ControlObj.SendOnOffCommand(self.State, self.lastpresstype)
			else:
				logsupport.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)

			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)
			self.ScheduleBlinkKey(self.Blink)
		else:
			config.DS.SwitchScreen(self.Screen, 'Bright', config.DS.state, 'Verify Run ' + self.Screen.name)
