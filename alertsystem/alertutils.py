from dataclasses import dataclass

import utilities
import utilfuncs
import logsupport
from logsupport import ConsoleWarning, ConsoleError
import exitutils

TriggerTypes = {}


@dataclass
class TriggerRecord:
	Parse: callable
	Arm: callable
	Trig: callable


def getvalid(spec, item, choices, default=None):
	i = spec.get(item, default)
	if i is not None:
		if i in choices:
			return i
		else:
			logsupport.Logs.Log('Choice error: ' + item + " not in " + str(choices), severity=logsupport.ConsoleWarning)
			exitutils.errorexit(exitutils.ERRORDIE)
	else:
		logsupport.Logs.Log('Missing required alert parameter: ' + item, severity=ConsoleWarning)
		exitutils.errorexit(exitutils.ERRORDIE)


import operator

Tests = ['EQ', 'NE', 'GT', 'LT', 'GE', 'LE']  # standard tests 2 operands
TestOps = {x: operator.__dict__[x.lower()] for x in Tests}
Tests.append('ISNONE')
TestOps['ISNONE'] = lambda arg1, arg2: arg1 is None


def comparams(cspec):
	ctest = getvalid(cspec, 'Test', Tests)
	cvalue = cspec.get('Value', None)
	cdelay = utilities.get_timedelta(cspec.get('Delay', None))
	return ctest, cvalue, cdelay


def TestCondition(arg1, arg2, test):
	if type(arg1) != type(arg2):
		arg1 = int(arg1) if utilfuncs.RepresentsInt(arg1) else arg1
		arg2 = int(arg2) if utilfuncs.RepresentsInt(arg2) else arg2
	try:
		return TestOps[test](arg1, arg2)
	except TypeError:
		return False
	except KeyError:
		logsupport.Logs.Log('Bad test in IsTrue', test, severity=ConsoleError)
		return False
