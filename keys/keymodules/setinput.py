import debug
import hubs.hubs
import logsupport
from screens import screen
from utils import utilities
from keys.keyspecs import KeyTypes
from keys.keyutils import ErrorKey
from logsupport import ConsoleWarning
from stores import valuestore
from keyspecs.toucharea import ManualKeyDesc


# key to provide HA style input values
class SetInputKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New SetVar Key Desc ", keyname)
		# todo suppress Verify
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, VarType='undef', Var='',
									Value='')  # value should be checked later
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

		utilities.register_example("SetVarKey", self)

	# noinspection PyUnusedLocal
	def SetInputKeyPressed(self):
		# valuestore.SetVal(self.VarName, self.Value)
		self.entity.SetValue(self.Value)
		self.ScheduleBlinkKey(self.Blink)


KeyTypes['SETINPUT'] = SetInputKey
