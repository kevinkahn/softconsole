from enum import Enum, auto
import shlex
import hubs.hubs
import logsupport
from logsupport import ConsoleWarning
from utils.utilfuncs import RepresentsInt, BoolTrueWord, BoolFalseWord
from collections import namedtuple

BrightnessPossible = []

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
	stateval = auto()


CodeKeyDesc = namedtuple('CodeKeyDesc', 'Display Var statebased')

def ParseConfigToDispOpt(item, deflabel):
	try:
		parseditem = shlex.shlex(item, posix=True, punctuation_chars='()')
		desc = list(parseditem)
		while ',' in desc: desc.remove(',')
		if desc[1] == ':':
			desc.pop(1)
			ChooserType = ChooseType.rangeval
			Chooser = (int(desc.pop(0)), int(desc.pop(0)))
		elif desc[1] == '|':
			ChooserType = ChooseType.enumval
			r = []
			while desc[1] == '|':
				r.append(desc.pop(0))
				desc.pop(0)  # remove the |
			try:
				r2 = []
				for x in r:
					r.append(int(x))
				Chooser = r2
			except ValueError:
				Chooser = r
		elif RepresentsInt(desc[0]):
			ChooserType = ChooseType.intval
			Chooser = int(desc.pop(0))
		elif desc[0] == 'None':
			ChooserType = ChooseType.Noneval
			Chooser = None
			desc.pop(0)
		elif desc[0] in (
				"state*on", "state*off"):  # this should be stateon and stateoff then set 2 options for an on/off button
			# stateon Red onlabel -- this overlaps boolean but if state is 0 or non-zero then different test? maybe make this
			# setup match state*on/state*off but then in match do check for val matches  on state or not
			# stateoff Red|dull offlabel or just an off color
			ChooserType = ChooseType.stateval
			Chooser = desc.pop(0)
		elif BoolTrueWord(desc[0]) or BoolFalseWord(desc[0]):
			ChooserType = ChooseType.boolval
			Chooser = BoolTrueWord(desc.pop(0))
		else:
			ChooserType = ChooseType.strval
			Chooser = desc.pop(0)
		if desc[0] != '(':
			Color = [desc.pop(0)]
		else:
			Color = []
			desc.pop(0)
			while desc[0] != ')':
				Color.append(desc.pop(0))
			desc.pop(0)
		Label = deflabel if len(desc) == 0 else desc[0].split(';')
		return DispOpt(choosertype=ChooserType, chooser=Chooser, color=Color, deflabel=Label)
	except Exception as E:
		logsupport.Logs.Log('Error parsing Appearance spec {}, exception {}'.format(item, E), severity=ConsoleWarning)
		raise


class DispOpt(object):
	# typedesc colorset label  colorset is either a single color (default char and outline) or a triple (key, char, outline)
	def __init__(self, item='', deflabel='', choosertype=None, chooser=None, color=()):
		'''if item != '':
			print('Old Display Opt')
			parseditem = shlex.shlex(item, posix=True, punctuation_chars='()')
			desc = list(parseditem)
			while ',' in desc: desc.remove(',')
			if desc[1] == ':':
				desc.pop(1)
				self.ChooserType = ChooseType.rangeval
				self.Chooser = (int(desc.pop(0)), int(desc.pop(0)))
			elif desc[1] == '|':
				self.ChooserType = ChooseType.enumval
				r = []
				while desc[1] == '|':
					r.append(desc.pop(0))
					desc.pop(0)  # remove the |
				try:
					r2 = []
					for x in r:
						r.append(int(x))
					self.Chooser = r2
				except ValueError:
					self.Chooser = r
			elif RepresentsInt(desc[0]):
				self.ChooserType = ChooseType.intval
				self.Chooser = int(desc.pop(0))
			elif desc[0] == 'None':
				self.ChooserType = ChooseType.Noneval
				self.Chooser = None
				desc.pop(0)
			elif desc[0] in (
			"state*on", "state*off"):  # this should be stateon and stateoff then set 2 options for an on/off button
				# stateon Red onlabel -- this overlaps boolean but if state is 0 or non-zero then different test? maybe make this
				# setup match state*on/state*off but then in match do check for val matches  on state or not
				# stateoff Red|dull offlabel or just an off color
				self.ChooserType = ChooseType.stateval
				self.Chooser = desc.pop(0)
			elif BoolTrueWord(desc[0]) or BoolFalseWord(desc[0]):
				self.ChooserType = ChooseType.boolval
				self.Chooser = BoolTrueWord(desc.pop(0))
			else:
				self.ChooserType = ChooseType.strval
				self.Chooser = desc.pop(0)
			if desc[0] != '(':
				self.Color = [desc.pop(0)]
			else:
				self.Color = []
				desc.pop(0)
				while desc[0] != ')':
					self.Color.append(desc.pop(0))
				desc.pop(0)
			self.Label = deflabel if len(desc) == 0 else desc[0].split(';')
		else:
		'''
		self.ChooserType = choosertype
		self.Chooser = chooser
		self.Color = color
		self.Label = deflabel

	# print('Opt: {} {} {}'.format(self, deflabel, desc))

	def __str__(self):
		return "DispOpt({} {} {} {})".format(self.ChooserType, self.Chooser, self.Color, self.Label)

	def Matches(self, val):
		if self.ChooserType == ChooseType.Noneval:
			return val is None
		elif self.ChooserType == ChooseType.intval:
			try:
				v2 = int(val)
			except (ValueError, TypeError):
				return False
			return self.Chooser == v2
		elif self.ChooserType == ChooseType.rangeval:
			try:
				v = float(val)
				return self.Chooser[0] <= v <= self.Chooser[1]
			except (ValueError, TypeError):
				return False
		elif self.ChooserType == ChooseType.boolval:
			return BoolTrueWord(val) == self.Chooser
		elif self.ChooserType == ChooseType.strval:
			return self.Chooser == val
		elif self.ChooserType == ChooseType.enumval:
			return val in self.Chooser
		elif self.ChooserType == ChooseType.stateval:
			if self.Chooser == 'state*on':
				return BoolTrueWord(val)
			elif self.Chooser == 'state*off':
				return BoolFalseWord(val)
		return False


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
