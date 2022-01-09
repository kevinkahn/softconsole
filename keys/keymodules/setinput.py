import debug
import logsupport
from screens import screen
from keys.keyspecs import KeyTypes
from keys.keyutils import DispOpt
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
		screen.AddUndefaultedParams(self, keysection, VarType='undef',
									Value='')  # value should be checked later
		self.oldval = '*******'  # forces a display compute first time through
		# determine type of input from store
		try:
			self.statebasedkey = True
			self.Proc = self.SetInputKeyPressed
			self.InputItem = self.Var.split(':')
			self.entity = hubs.hubs.Hubs[self.InputItem[0]].GetNode(self.InputItem[1])[0]

		except Exception as e:
			logsupport.Logs.Log(
				'Input key error on screen {} key {} var {}'.format(thisscreen.name, self.name, self.Var),
				severity=ConsoleWarning)
			logsupport.Logs.Log('Excpt: ', str(e))
			self.Proc = ErrorKey

		if self.label == ['']:
			self.label = [self.entity.name]

		# for item in self.Appearance:
		#	self.displayoptions.append(DispOpt(item, self.label))

		utilities.register_example("SetInputKey", self)

	# noinspection PyUnusedLocal
	def SetInputKeyPressed(self):
		self.entity.SetValue(self.Value)  # Value is actually the type of input operation set in the config entry
		self.ScheduleBlinkKey(self.Blink)


KeyTypes['SETINPUT'] = SetInputKey
