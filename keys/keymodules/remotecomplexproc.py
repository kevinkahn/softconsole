import config
import logsupport
import screen
from keys.keyspecs import KeyTypes
from keys.keyutils import internalprocs
from keys.keymodules.internalproc import InternalProcKey
from logsupport import ConsoleWarning


class RemoteComplexProcKey(InternalProcKey):
	def __init__(self, thisscreen, keysection, keyname):
		super().__init__(thisscreen, keysection, keyname)
		screen.AddUndefaultedParams(self, keysection, EventProcName='')
		self.Hub = config.MQTTBroker
		self.Seq = 0
		self.FinishProc = internalprocs[self.EventProcName]

	def FinishKey(self, center, size, firstfont=0, shrink=True):
		super().FinishKey(center, size, firstfont, shrink)
		self.thisscreen.AddToHubInterestList(self.Hub, self.name, self)

	def HandleNodeEvent(self, evnt):
		if int(evnt.seq) != self.Seq:
			logsupport.Logs.Log(
				'Remote response sequence error for {} expected {} got {}'.format(self.name, self.Seq, evnt),
				severity=ConsoleWarning, tb=True)
		self.FinishProc(evnt)


KeyTypes['REMOTECPLXPROC'] = RemoteComplexProcKey
