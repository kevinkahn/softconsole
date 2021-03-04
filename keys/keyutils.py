from enum import Enum, auto

import hubs.hubs
import logsupport
from logsupport import ConsoleWarning


def _resolvekeyname(kn, DefHub):
	t = kn.split(':')
	if len(t) == 1:
		return t[0], DefHub
	elif len(t) == 2:
		try:
			return t[1], hubs.hubs.Hubs[t[0]]
		except KeyError:
			logsupport.Logs.Log("Bad qualified node name for key: " + kn, severity=ConsoleWarning)
			return "*none*", DefHub
	else:
		logsupport.Logs.Log("Ill formed keyname: ", kn)
		return '*none*', DefHub


internalprocs = {}


def _SetUpProgram(ProgramName, Parameter, thisscreen, kn):
	pn, hub = _resolvekeyname(ProgramName, thisscreen.DefaultHubObj)
	Prog = hub.GetProgram(pn)
	if Prog is None:
		Prog = DummyProgram(kn, hub.name, ProgramName)
		logsupport.Logs.Log(
			"Missing Prog binding Key: {} on screen {} Hub: {} Program: {}".format(kn, thisscreen.name, hub.name,
																				   ProgramName),
			severity=ConsoleWarning)
	if Parameter == []:
		pdict = None
	else:
		pdict = {}
		if len(Parameter) == 1 and not ':' in Parameter[0]:
			pdict['Parameter'] = Parameter[0]
		else:
			for p in Parameter:
				t = p.split(':')
				pdict[t[0]] = t[1]
	return Prog, pdict


class ChooseType(Enum):
	intval = auto()
	rangeval = auto()
	enumval = auto()
	Noneval = auto()
	strval = auto()


class DummyProgram(object):
	def __init__(self, kn, hn, pn):
		self.keyname = kn
		self.hubname = hn
		self.programname = pn

	def RunProgram(self, param=None):
		logsupport.Logs.Log(
			"Pressed unbound program key: {} for hub: {} program: {} param: {}".format(self.keyname, self.hubname,
																					   self.programname, param))


def ErrorKey():
	# used to handle badly defined keys
	logsupport.Logs.Log('Ill-defined Key Pressed', severity=ConsoleWarning)
