import debug
import hubs.hubs
import logsupport
from screens import screen
from utils import utilities
from keys.keyspecs import KeyTypes
from keys.keyutils import ErrorKey
from logsupport import ConsoleWarning
from keyspecs.toucharea import ManualKeyDesc
from keys.keyutils import ChooseType
from utils.utilfuncs import RepresentsInt, tint, wc
import shlex


# key to provide HA style input values
class SetInputKey(ManualKeyDesc):
	class DispOpt(object):
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
				try:
					r = []
					for x in rng:
						r.append(int(x))
					# r = (int(x) for x in rng) this simpler version results in an uncaught ValueError
					self.Chooser = r
				except ValueError:
					self.Chooser = rng
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
				try:
					v = float(val)
					return self.Chooser[0] <= v <= self.Chooser[1]
				except ValueError:
					return False
			elif self.ChooserType == ChooseType.strval:
				return self.Chooser == val
			elif self.ChooserType == ChooseType.enumval:
				return val in self.Chooser
			return False

	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)
		# todo suppress Verify
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, VarType='undef', Var='', Appearance=[], DefaultAppearance='',
									Value='')  # value should be checked later
		if self.DefaultAppearance == '':
			self.defoption = self.DispOpt('None {} {}'.format(self.KeyColorOn, self.name), '')
		else:
			self.defoption = self.DispOpt(self.DefaultAppearance, self.label)
		self.displayoptions = []
		self.oldval = '*******'  # forces a display compute first time through
		self.waspressed = False
		# determine type of input from store
		try:
			self.Proc = self.SetInputKeyPressed
			self.InputItem = self.Var.split(':')
			self.entity = hubs.hubs.Hubs[self.InputItem[0]].GetNode(self.InputItem[1])[0]

		except Exception as e:
			logsupport.Logs.Log('Input key error on screen: ' + thisscreen.name + ' Var: ' + self.Var,
								severity=ConsoleWarning)
			logsupport.Logs.Log('Excpt: ', str(e))
			self.Proc = ErrorKey

		if self.label == ['']:
			self.label = [self.entity.name]

		for item in self.Appearance:
			self.displayoptions.append(self.DispOpt(item, self.label))

		utilities.register_example("SetVarKey", self)

	# noinspection PyUnusedLocal
	def SetInputKeyPressed(self):
		# valuestore.SetVal(self.VarName, self.Value)
		self.waspressed = True
		self.entity.SetValue(self.Value)
		self.ScheduleBlinkKey(self.Blink)

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# create the images here dynamically then let lower methods do display, blink etc.
		val = self.entity.state  # valuestore.GetVal(self.Var)
		if self.oldval != val:  # rebuild the key for a value change
			self.oldval = val
			lab = self.defoption.Label[:]
			oncolor = tint(self.defoption.Color)
			offcolor = wc(self.defoption.Color)
			for i in self.displayoptions:
				if i.Matches(val):
					lab = i.Label[:]
					oncolor = tint(i.Color)
					offcolor = wc(i.Color)
					break
			lab2 = []
			dval = '--' if val is None else str(val)
			for line in lab:
				lab2.append(line.replace('$', dval))
			self.BuildKey(oncolor, offcolor)
			self.SetKeyImages(lab2, lab2, 0, True)
		if self.waspressed:
			self.ScheduleBlinkKey(self.Blink)
			self.waspressed = False
		super().PaintKey(ForceDisplay, val is not None)


KeyTypes['SETINPUT'] = SetInputKey
