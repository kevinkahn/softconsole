import shlex

import debug
import keys.keymodules.runprogram
import logsupport
from screens import screen
from keys.keyspecs import KeyTypes
from keys.keyutils import _SetUpProgram, ChooseType
from logsupport import ConsoleWarning
from stores import valuestore
from keyspecs.toucharea import ManualKeyDesc
from utils.utilfuncs import RepresentsInt, tint, wc


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
		if self.ValueSeq:
			print('DoValSeq')  # todo del
			try:
				i = self.ValueSeq.index(valuestore.GetVal(self.Var))
			except ValueError:
				i = len(self.ValueSeq) - 1
			valuestore.SetVal(self.Var, self.ValueSeq[(i + 1) % len(self.ValueSeq)])
		else:
			keys.keymodules.runprogram.RunProgram(param=self.Parameter)


KeyTypes['VARKEY'] = VarKey
