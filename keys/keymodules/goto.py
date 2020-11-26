import debug
import logsupport
from screens import screen
from configobjects import GoToTargetList
from guicore.switcher import SwitchScreen
from logsupport import ConsoleWarning
from keyspecs.toucharea import ManualKeyDesc
from keys.keyspecs import KeyTypes


class GoToKey(ManualKeyDesc):
	# Note: cannot do verify on a goto key - would make no sense of the verify pop back to previous screen
	# this is actually a Push Screen key in that it makes a stack entry
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New GoTo Key ", keyname)
		if 'Verify' in keysection:
			logsupport.Logs.Log('Verify not allowed for GoTo Key {} on {}'.format(keyname,thisscreen.name))
			del keysection['Verify']
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
			SwitchScreen(self.targetscreen, 'Bright', 'Direct go to' + self.targetscreen.name, push=True)


KeyTypes['GOTO'] = GoToKey
