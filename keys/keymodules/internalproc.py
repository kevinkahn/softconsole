import debug
import screen
import supportscreens
from keys.keyspecs import KeyTypes
from keys.keyutils import internalprocs
from toucharea import ManualKeyDesc
import config
import logsupport
from logsupport import ConsoleWarning


class InternalProcKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		super().__init__(thisscreen, keysection, keyname)
		self.thisscreen = thisscreen
		screen.AddUndefaultedParams(self, keysection, ProcName='')
		self.Proc = internalprocs[self.ProcName]
		if self.Verify:  # todo make verified a single global proc??
			self.VerifyScreen = supportscreens.VerifyScreen(self, self.GoMsg, self.NoGoMsg, self.Proc,
															thisscreen, self.KeyColorOff,
															thisscreen.BackgroundColor, thisscreen.CharColor,
															self.State, thisscreen.HubInterestList)
			self.Proc = self.VerifyScreen.Invoke
		else:
			self.ProcDblTap = None

	def InitDisplay(self):
		debug.debugPrint("Screen", "InternalProcKey.InitDisplay ", self.Screen.name, self.name)
		self.State = True
		super().InitDisplay()

	def Pressed(self, tapcount):
		if not self.UnknownState: super().Pressed(tapcount)


class RemoteProcKey(InternalProcKey):
	def __init__(self, thisscreen, keysection, keyname):
		super().__init__(thisscreen, keysection, keyname)
		self.Hub = config.MQTTBroker
		self.Seq = 0
		self.ExpectedNumResponses = 1

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super().FinishKey(center, size, firstfont, shrink)
		self.thisscreen.AddToHubInterestList(self.Hub, self.name, self)

	def HandleNodeEvent(self, evnt):
		if int(evnt.seq) != self.Seq:
			logsupport.Logs.Log(
				'Remote response sequence error for {} expected {} got {}'.format(self.name, self.Seq, evnt),
				severity=ConsoleWarning, tb=True)
			return
		self.ExpectedNumResponses -= 1
		if self.ExpectedNumResponses == 0:
			if evnt.stat == 'ok':
				self.ScheduleBlinkKey(5)
			else:
				self.FlashNo(5)
		else:
			pass


KeyTypes['PROC'] = InternalProcKey
KeyTypes['REMOTEPROC'] = RemoteProcKey
