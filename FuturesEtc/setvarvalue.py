import debug
from screens import screen
from utils import utilities
from stores import valuestore
from keyspecs.toucharea import ManualKeyDesc
from keys.keyspecs import KeyTypes


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

	def PaintKey(self):
		# extact current value from variable array
		self.SetKeyImages(self.label + [str(self.Value)])
		super(SetVarValueKey, self).PaintKey()

	def SetVarValue(self):
		# Call a screen repainter proc
		# call reinitdisplay on enclosing screen
		pass


KeyTypes['SETVARVALUE'] = SetVarValueKey
