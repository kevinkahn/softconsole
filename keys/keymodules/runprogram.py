import debug
import screen
import supportscreens
from keys.keyutils import _SetUpProgram
from keys.keyspecs import KeyTypes
from keyspecs.toucharea import ManualKeyDesc


class RunProgram(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New RunProgram Key ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, ProgramName='', Parameter='')
		self.State = False
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


KeyTypes['RUNPROG'] = RunProgram
