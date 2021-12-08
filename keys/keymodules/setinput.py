import debug
import logsupport
from screens import screen
from keys.keyspecs import KeyTypes
from keys.keyutils import DispOpt, AdjustAppearance
from logsupport import ConsoleWarning
from keyspecs.toucharea import ManualKeyDesc
from keys.keyutils import ErrorKey
from utils import utilities
import hubs.hubs


# key to provide HA style input values
class SetInputKey(ManualKeyDesc):

	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)
		# todo suppress Verify
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, VarType='undef', Var='', Appearance=[], DefaultAppearance='',
									Value='')  # value should be checked later
		if self.DefaultAppearance == '':
			self.defoption = DispOpt('None {} {}'.format(self.KeyColorOn, self.name), '')
		else:
			self.defoption = DispOpt(self.DefaultAppearance, self.label)
		self.displayoptions = []
		self.oldval = '*******'  # forces a display compute first time through
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
			self.displayoptions.append(DispOpt(item, self.label))

		utilities.register_example("SetInputKey", self)

	# noinspection PyUnusedLocal
	def SetInputKeyPressed(self):
		self.entity.SetValue(self.Value)  # Value is actually the type of input operation set in the config entry
		self.ScheduleBlinkKey(self.Blink)

	def PaintKey(self, ForceDisplay=False, DisplayState=True):
		# create the images here dynamically then let lower methods do display, blink etc.
		val = self.entity.state  # valuestore.GetVal(self.Var)
		AdjustAppearance(self, val)
		super().PaintKey(ForceDisplay, val is not None)


KeyTypes['SETINPUT'] = SetInputKey
