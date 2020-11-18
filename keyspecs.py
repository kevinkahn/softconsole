import shlex

import debug
import displayupdate
import hubs.hubs
import logsupport
import screen
import screens.__screens as screens
import supportscreens
import utilities
from controlevents import CEvent, PostEvent, ConsoleEvent
from logsupport import ConsoleWarning, ConsoleDetail
from stores import valuestore
from toucharea import ManualKeyDesc
from utilfuncs import *
from configobjects import GoToTargetList
import config
from enum import Enum, auto

# noinspection PyUnusedLocal
def KeyWithVarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl', 'Var changed for key ', storeitem.name, ' from ', old, ' to ', new)
	# noinspection PyArgumentList
	PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub='*VARSTORE*', varinfo=param))


internalprocs = {}

def _resolvekeyname(kn, DefHub):
	t = kn.split(':')
	if len(t) == 1:
		return t[0], DefHub
	elif len(t) == 2:
		try:
			return t[1], hubs.hubs.Hubs[t[0]]
		except KeyError:
			logsupport.Logs.Log("Bad qualified node name for key: " + kn, severity=ConsoleWarning)
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
	elif keytype == 'GOTO':
		NewKey = GoToKey(thisscreen, screensection, keyname)
	elif keytype == 'PROC':
		NewKey = InternalProcKey(thisscreen, screensection, keyname)
	elif keytype == 'REMOTEPROC':
		NewKey = RemoteProcKey(thisscreen, screensection, keyname)
	elif keytype == 'REMOTECPLXPROC':
		NewKey = RemoteComplexProcKey(thisscreen, screensection, keyname)
	else:  # unknown type
		NewKey = BlankKey(thisscreen, screensection, keyname)
		logsupport.Logs.Log('Undefined key type ' + keytype + ' for: ' + keyname, severity=ConsoleWarning)
	return NewKey


# noinspection PyUnusedLocal
def ErrorKey():
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
		super().InitDisplay()

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super(SetVarValueKey, self).FinishKey(center, size, firstfont, shrink)

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# extact current value from variable array
		self.SetKeyImages(self.label + [str(self.Value)])
		super(SetVarValueKey, self).PaintKey(ForceDisplay, DisplayState)

	def SetVarValue(self):
		# Call a screen repainter proc
		# call reinitdisplay on enclosing screen
		pass

# Future create a screen to allow changing the value if parameter is maleable

class ChooseType(Enum):
	intval = auto()
	rangeval = auto()
	enumval = auto()
	Noneval = auto()
	strval = auto()

class VarKey(ManualKeyDesc):
	class DistOpt(object):
		# todo add a state to display opt?
		def __init__(self, item, deflabel):
			desc = shlex.split(item)
			if ':' in desc[0]:
				self.ChooserType = ChooseType.rangeval
				rng = desc[0].split(':')
				self.Chooser = (int(rng[0]), int(rng[1]))
			elif '|' in desc[0]:
				self.ChooserType = ChooseType.enumval
				rng = desc[0].split('|')
				self.Chooser = (int(x) for x in rng)
			elif RepresentsInt(desc[0]):
				self.ChooserType = ChooseType.intval
				self.Chooser = int(desc[0])
			elif desc[0] == 'None':
				self.ChooserType = ChooseType.Noneval
				self.Chooser = None
			else:
				self.ChooserType = ChooseType.strval
				self.Chooser = desc[0]
			self.Color = desc[1]
			self.Label = deflabel if len(desc) < 3 else desc[2].split(';')

		def Matches(self, val):
			if self.ChooserType == ChooseType.Noneval:
				return val is None
			elif self.ChooserType == ChooseType.intval:
				return isinstance(val, int) and self.Chooser == val
			elif self.ChooserType == ChooseType.rangeval:
				return isinstance(val, int) and self.Chooser[0] <= val <= self.Chooser[1]
			elif self.ChooserType == ChooseType.strval:
				return self.Chooser == val
			elif self.ChooserType == ChooseType.enumval:
				return val in self.Chooser
			return False

	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "              New Var Key ", keyname)
		# todo suppress Verify
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, Var='', Appearance=[], ValueSeq=[], ProgramName='', Parameter='',
									DefaultAppearance='')
		if self.ValueSeq != [] and self.ProgramName != '':
			logsupport.Logs.Log('VarKey {} cannot specify both ValueSeq and ProgramName'.format(self.name),
								severity=ConsoleWarning)
			self.ProgramName = ''
		if self.ProgramName != '':
			self.Proc = self.VarKeyPressed
			self.Program, self.Parameter = _SetUpProgram(self.ProgramName, self.Parameter, thisscreen,
														 keyname)  # if none set this is dummy todo
		# valuestore.AddAlert(self.Var, (KeyWithVarChanged, (keyname, self.Var))) todo this doesn't work for HA vars why do we need the alert?
		if self.ValueSeq:
			self.Proc = self.VarKeyPressed
			t = []
			for n in self.ValueSeq: t.append(int(n))
			self.ValueSeq = t
		if self.DefaultAppearance == '':
			self.defoption = self.DistOpt('None {} {}'.format(self.KeyColorOn, self.KeyLabelOn[:]), '')
		else:
			self.defoption = self.DistOpt(self.DefaultAppearance, self.label)
		self.displayoptions = []
		self.oldval = '*******'  # forces a display compute first time through
		self.State = False
		for item in self.Appearance:
			self.displayoptions.append(self.DistOpt(item, self.label))

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# create the images here dynamically then let lower methods do display, blink etc.
		val = valuestore.GetVal(self.Var)
		if self.oldval != val:  # rebuild the key for a value change
			self.oldval = val
			# oncolor = wc(self.KeyColorOn)
			# offcolor = wc(self.KeyColorOff)
			# lab = []
			founddisp = False
			for i in self.displayoptions:
				if i.Matches(val):
					lab = i.Label[:]
					oncolor = tint(i.Color)
					offcolor = wc(i.Color)
					founddisp = True
					break
			if not founddisp:
				lab = self.defoption.Label[:]
				oncolor = tint(self.defoption.Color)
				offcolor = wc(self.defoption.Color)

			lab2 = []
			dval = '--' if val is None else str(
				val)  # todo could move to the DistOp class and have it return processed label
			for line in lab:
				lab2.append(line.replace('$', dval))
			self.BuildKey(oncolor, offcolor)
			self.SetKeyImages(lab2, lab2, 0, True)
			self.ScheduleBlinkKey(
				self.Blink)  # todo is this correct with clocked stuff?  Comes before PaintKey parent call
		super().PaintKey(ForceDisplay, val is not None)

	# noinspection PyUnusedLocal
	def VarKeyPressed(self):
		if self.ValueSeq != []:
			print('DoValSeq')  # todo del
			try:
				i = self.ValueSeq.index(valuestore.GetVal(self.Var))
			except ValueError:
				i = len(self.ValueSeq) - 1
			valuestore.SetVal(self.Var, self.ValueSeq[(i + 1) % len(self.ValueSeq)])
		else:
			self.Program.RunProgram(param=self.Parameter)


class SetVarKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)
		# todo suppress Verify
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, VarType='undef', Var='', Value=0)
		try:
			self.Proc = self.SetVarKeyPressed
			if self.VarType != 'undef':  # deprecate

				if self.VarType == 'State':
					self.VarName = (hubs.hubs.defaulthub.name, 'State', self.Var)  # use default hub for each of these 2
				elif self.VarType == 'Int':
					self.VarName = (hubs.hubs.defaulthub.name, 'Int', self.Var)
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
			logsupport.Logs.Log('Excpt: ', str(e))
			self.Proc = ErrorKey

		utilities.register_example("SetVarKey", self)

	# noinspection PyUnusedLocal
	def SetVarKeyPressed(self):
		valuestore.SetVal(self.VarName, self.Value)
		self.ScheduleBlinkKey(self.Blink)


def _SetUpProgram(ProgramName, Parameter, thisscreen, kn):
	pn, hub = _resolvekeyname(ProgramName, thisscreen.DefaultHubObj)
	Prog = hub.GetProgram(pn)
	if Prog is None:
		Prog = DummyProgram(kn, hub.name, ProgramName)
		logsupport.Logs.Log(
			"Missing Prog binding Key: {} on screen {} Hub: {} Program: {}".format(kn, thisscreen.name, hub.name,
																				   ProgramName),
			severity=ConsoleWarning)
	if Parameter == '':
		Parameter = None
	elif ':' in Parameter:  # todo allow multiple params
		t = Parameter.split(':')
		Parameter = {t[0]: t[1]}
	else:
		Parameter = {'Parameter': Parameter}
	return Prog, Parameter

class DummyProgram(object):
	def __init__(self, kn, hn, pn):
		self.keyname = kn
		self.hubname = hn
		self.programname = pn

	def RunProgram(self, param=None):
		logsupport.Logs.Log(
			"Pressed unbound program key: " + self.keyname + " for hub: " + self.hubname + " program: " + self.programname)

class RunProgram(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New RunProgram Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, ProgramName='',
									Parameter='')  # todo Parameter is only string for now should it be more?
		# if ':' in self.Parameter:
		#	t = self.Parameter.split(':')
		#	self.Parameter = {t[0]:t[1]}
		# else:
		#	self.Parameter = {'Parameter':self.Parameter}
		self.State = False
		# pn, self.Hub = _resolvekeyname(self.ProgramName, thisscreen.DefaultHubObj)
		# self.Program = self.Hub.GetProgram(pn)
		# if self.Program is None:
		#	self.Program = DummyProgram(keyname, self.Hub.name, self.ProgramName)
		#	logsupport.Logs.Log(
		#		"Missing Prog binding Key: {} on screen {} Hub: {} Program: {}".format(keyname, thisscreen.name, self.Hub.name, self.ProgramName),
		#		severity=ConsoleWarning) todo does self.Hub get used anywhere?
		self.Program, self.Parameter = _SetUpProgram(self.ProgramName, self.Parameter, thisscreen, keyname)
		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.RunKeyPressed,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
			self.Proc = self.VerifyScreen.Invoke
			self.ProcDblTap = self.VerifyScreen.Invoke
		else:
			self.Proc = self.RunKeyPressed
			self.ProcDblTap = self.RunKeyDblPressed

	def RunKeyPressed(self):
		if self.FastPress: return
		self.Program.RunProgram(param=self.Parameter)
		self.ScheduleBlinkKey(self.Blink)

	def RunKeyDblPressed(self):
		if self.FastPress:
			if self.Verify:
				self.VerifyScreen.Invoke()
			else:
				self.Program.RunProgram()
				self.ScheduleBlinkKey(self.Blink)


class GoToKey(ManualKeyDesc):
	# Note: cannot do verify on a goto key - would make no sense of the verify pop back to previous screen
	# this is actually a Push Screen key in that it makes a stack entry
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New GoTo Key ", keyname)
		# todo remove any Verify from the keysection
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, ScreenName='**unspecified**')
		self.targetscreen = None
		GoToTargetList[self] = self.ScreenName

		self.Proc = self.GoToKeyPressed

	def GoToKeyPressed(self):
		if self.targetscreen is None:
			logsupport.Logs.Log('Unbound GOTO key {} pressed'.format(self.name), severity=ConsoleWarning)
			self.ScheduleBlinkKey(20)
		else:
			screens.DS.SwitchScreen(self.targetscreen, 'Bright', 'Direct go to' + self.targetscreen.name, push=True)


class OnOffKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, kn, keytype):
		keyname, self.Hub = _resolvekeyname(kn, thisscreen.DefaultHubObj)
		#self.ControlObj = None  # object on which to make operation calls
		self.DisplayObj = None  # object whose state is reflected in key

		debug.debugPrint('Screen', "             New ", keytype, " Key Desc ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, SceneProxy='', NodeName='')

		if keyname == '*Action*': keyname = self.NodeName  # special case for alert screen action keys that always have same name todo - can nodename ever be explicitly set otherwise?
		self.ControlObj, self.DisplayObj = self.Hub.GetNode(keyname, self.SceneProxy)

		if self.ControlObjUndefined():
			debug.debugPrint('Screen', "Screen", keyname, "unbound")
			logsupport.Logs.Log('Key Binding missing: ' + self.name, severity=ConsoleWarning)  #todo - should this handle the delayed key case of an indirector?

		if self.Verify:
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.KeyPressAction,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
			self.Proc = self.VerifyScreen.Invoke  # todo make this a goto key; make verify screen always do a pop and get rid of the switch screens below
		else:
			self.Proc = self.KeyPressAction
			self.ProcDblTap = self.KeyPressActionDbl  # todo need testing/completion

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
			self.State = True
		elif self.KeyAction == "Off":
			self.State = False

		if not self.ControlObjUndefined():
			self.ControlObj.SendOnOffCommand(self.State)
			self.ScheduleBlinkKey(self.Blink)
		else:
			logsupport.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,  # todo fix screen name
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
			logsupport.Logs.Log("Screen: " + self.name + " press unbound key: " + self.name,
								severity=ConsoleWarning)
			self.ScheduleBlinkKey(20)


class InternalProcKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		super().__init__(thisscreen, keysection, keyname)
		self.thisscreen = thisscreen
		screen.AddUndefaultedParams(self, keysection, ProcName='')
		self.Proc = internalprocs[self.ProcName]
		if self.Verify:  # todo make verified a single global proc??
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.Proc,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
			self.Proc = self.VerifyScreen.Invoke
		else:
			self.ProcDblTap = None


	def InitDisplay(self):
		debug.debugPrint("Screen", "InternalProcKey.InitDisplay ", self.Screen.name, self.name)
		self.State = True
		super().InitDisplay()

	def Pressed(self, tapcount):
		if not self.UnknownState: super().Pressed(tapcount)

class RemoteProcKey(InternalProcKey):
	def __init__(self, thisscreen, keysection, keyname):
		super().__init__(thisscreen, keysection, keyname)
		self.Hub = config.MQTTBroker
		self.Seq = 0
		self.ExpectedNumResponses = 1

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super().FinishKey(center, size, firstfont, shrink)
		self.thisscreen.AddToHubInterestList(self.Hub, self.name, self)

	def HandleNodeEvent(self, evnt):
		if int(evnt.seq) != self.Seq:
			logsupport.Logs.Log(
				'Remote response sequence error for {} expected {} got {}'.format(self.name, self.Seq, evnt),
				severity=ConsoleWarning, tb=True)
			return
		self.ExpectedNumResponses -= 1
		if self.ExpectedNumResponses == 0:
			if evnt.stat == 'ok':
				self.ScheduleBlinkKey(5)
			else:
				self.FlashNo(5)
		else:
			pass

class RemoteComplexProcKey(InternalProcKey):
	def __init__(self, thisscreen, keysection, keyname):
		super().__init__(thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, EventProcName='')
		self.Hub = config.MQTTBroker
		self.Seq = 0
		self.FinishProc = internalprocs[self.EventProcName]

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super().FinishKey(center, size, firstfont, shrink)
		self.thisscreen.AddToHubInterestList(self.Hub, self.name, self)

	def HandleNodeEvent(self, evnt):
		if int(evnt.seq) != self.Seq:
			logsupport.Logs.Log(
				'Remote response sequence error for {} expected {} got {}'.format(self.name, self.Seq, evnt),
				severity=ConsoleWarning, tb=True)
		self.FinishProc(evnt)
