import debug
import hubs.hubs
import logsupport
import screen
import utilities
from keys.keyspecs import KeyTypes
from keys.keyutils import ErrorKey
from logsupport import ConsoleWarning
from stores import valuestore
from keyspecs.toucharea import ManualKeyDesc


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


KeyTypes['SETVAR'] = SetVarKey
