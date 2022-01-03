import debug
import logsupport
from screens import screen
from keys.keyspecs import KeyTypes
from keys.keyutils import _SetUpProgram
from logsupport import ConsoleWarning
from stores import valuestore
from keyspecs.toucharea import ManualKeyDesc

class VarKey(ManualKeyDesc):

	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "              New Var Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, ValueSeq=[], ProgramName='', Parameter=[])
		if self.ValueSeq != [] and self.ProgramName != '':
			logsupport.Logs.Log('VarKey {} cannot specify both ValueSeq and ProgramName'.format(self.name),
								severity=ConsoleWarning)
			self.ProgramName = ''
		if self.ProgramName != '':
			self.Proc = self.VarKeyPressed
			self.Program, self.Parameter = _SetUpProgram(self.ProgramName, self.Parameter, thisscreen,
														 keyname)
		if self.ValueSeq:
			self.Proc = self.VarKeyPressed
			t = []
			for n in self.ValueSeq: t.append(int(n))
			self.ValueSeq = t
		self.oldval = '*******'  # forces a display compute first time through
		self.State = False
		self.waspressed = False

	#	def PaintKey(self, ForceDisplay=False, DisplayState=True):
	#		# create the images here dynamically then let lower methods do display, blink etc.
	#		val = valuestore.GetVal(self.Var)
	#		AdjustAppearance(self, val)
	#		#		if self.waspressed:  # todo verify that this is actually needed now Blink scheduling is done in super PaintKey
	#		#			self.ScheduleBlinkKey(self.Blink)
	#		#			self.waspressed = False
	#		super().PaintKey(ForceDisplay, val is not None)

	# noinspection PyUnusedLocal
	def VarKeyPressed(self):
		self.waspressed = True
		if self.ValueSeq:
			try:
				i = self.ValueSeq.index(int(valuestore.GetVal(self.Var)))
			except ValueError:
				i = len(self.ValueSeq) - 1
			valuestore.SetVal(self.Var, self.ValueSeq[(i + 1) % len(self.ValueSeq)])
		else:
			self.Program.RunProgram(param=self.Parameter)
		self.ScheduleBlinkKey(self.Blink)

KeyTypes['VARKEY'] = VarKey
