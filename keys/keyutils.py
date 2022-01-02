from enum import Enum, auto

import shlex

import hubs.hubs
import logsupport
from logsupport import ConsoleWarning
from utils.utilfuncs import RepresentsInt, tint, wc, BoolTrueWord, BoolFalseWord


def _resolvekeyname(kn, DefHub):
	knbase = kn.split('/')[0]  # remove any yniqueness suffix
	t = knbase.split(':')
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
	boolval = auto()

class DispOpt(object):
	# todo add a state to display opt?
	def __init__(self, item, deflabel):
		desc = shlex.split(item)
		if ':' in desc[0]:
			self.ChooserType = ChooseType.rangeval
			rng = desc[0].split(':')
			self.Chooser = (int(rng[0]), int(rng[1]))
		elif '|' in desc[0]:
			self.ChooserType = ChooseType.enumval
			rng = desc[0].split('|')
			try:
				r = []
				for x in rng:
					r.append(int(x))
				# r = (int(x) for x in rng) this simpler version results in an uncaught ValueError
				self.Chooser = r
			except ValueError:
				self.Chooser = rng
		elif RepresentsInt(desc[0]):
			self.ChooserType = ChooseType.intval
			self.Chooser = int(desc[0])
		elif desc[0] == 'None':
			self.ChooserType = ChooseType.Noneval
			self.Chooser = None
		elif BoolTrueWord(desc[0]) or BoolFalseWord(desc[0]):
			self.ChooserType = ChooseType.boolval
			self.Chooser = BoolTrueWord(desc[0])
		else:
			self.ChooserType = ChooseType.strval
			self.Chooser = desc[0]
		self.Color = desc[1]
		self.Label = deflabel if len(desc) < 3 else desc[2].split(';')

	def Matches(self, val):
		if self.ChooserType == ChooseType.Noneval:
			return val is None
		elif self.ChooserType == ChooseType.intval:
			try:
				v2 = int(val)
			except ValueError:
				return False
			return self.Chooser == v2
		elif self.ChooserType == ChooseType.rangeval:
			try:
				v = float(val)
				return self.Chooser[0] <= v <= self.Chooser[1]
			except ValueError:
				return False
		elif self.ChooserType == ChooseType.boolval:
			return BoolTrueWord(val) == self.Chooser
		elif self.ChooserType == ChooseType.strval:
			return self.Chooser == val
		elif self.ChooserType == ChooseType.enumval:
			return val in self.Chooser
		return False


def AdjustAppearance(key, val):
	if key.oldval != val:  # rebuild the key for a value change
		key.oldval = val
		lab = key.defoption.Label[:]
		oncolor = tint(key.defoption.Color)
		offcolor = wc(key.defoption.Color)
		for i in key.displayoptions:
			if i.Matches(val):
				lab = i.Label[:]
				oncolor = tint(i.Color)
				offcolor = wc(i.Color)
				break
		lab2 = []
		dval = '--' if val is None else str(val)
		for line in lab:
			lab2.append(line.replace('$', dval))
		key.BuildKey(oncolor, offcolor)
		key.SetKeyImages(lab2, lab2, 0, True)


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
