from dataclasses import dataclass

import utilities
import logsupport
from logsupport import ConsoleWarning
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


Tests = ('EQ', 'NE', 'GT', 'ISNONE')


def comparams(cspec):
	ctest = getvalid(cspec, 'Test', Tests)
	cvalue = cspec.get('Value', None)
	cdelay = utilities.get_timedelta(cspec.get('Delay', None))
	return ctest, cvalue, cdelay
