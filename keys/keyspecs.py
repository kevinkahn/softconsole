import debug
import logsupport
import utilities
from controlevents import CEvent, PostEvent, ConsoleEvent
from keys.keyutils import ErrorKey

from logsupport import ConsoleWarning, ConsoleDetail
from keyspecs.toucharea import ManualKeyDesc
import os
import importlib

KeyTypes = {}

for keytype in os.listdir(os.getcwd() + '/keys/keymodules'):
	if '__' not in keytype:
		splitname = os.path.splitext(keytype)
		if splitname[1] == '.py':
			importlib.import_module('keys.keymodules.' + splitname[0])


# noinspection PyUnusedLocal
def KeyWithVarChanged(storeitem, old, new, param, modifier):
	debug.debugPrint('DaemonCtl', 'Var changed for key ', storeitem.name, ' from ', old, ' to ', new)
	# noinspection PyArgumentList
	PostEvent(ConsoleEvent(CEvent.HubNodeChange, hub='*VARSTORE*', varinfo=param))


def CreateKey(thisscreen, screensection, keyname):
	if screensection.get('type', 'ONOFF', delkey=False) == 'RUNTHEN':
		screensection['type'] = 'RUNPROG'
	if screensection.get('type', 'ONOFF', delkey=False) == 'ONBLINKRUNTHEN':
		screensection['type'] = 'RUNPROG'
		screensection['FastPress'] = 1
		screensection['Blink'] = 7
		screensection['ProgramName'] = screensection.get('KeyRunThenName', '')

	keytype = screensection.get('type', 'ONOFF')
	logsupport.Logs.Log("-Key:" + keyname, severity=ConsoleDetail)
	if keytype in KeyTypes:
		NewKey = KeyTypes[keytype](thisscreen, screensection, keyname)
	else:  # unknown type
		NewKey = BlankKey(thisscreen, screensection, keyname)
		logsupport.Logs.Log('Undefined key type ' + keytype + ' for: ' + keyname, severity=ConsoleWarning)
	return NewKey


class BlankKey(ManualKeyDesc):
	def __init__(self, thisscreen, keysection, keyname):
		debug.debugPrint('Screen', "             New Blank Key Desc ", keyname)
		ManualKeyDesc.__init__(self, thisscreen, keysection, keyname)
		self.Proc = ErrorKey
		self.State = False
		self.label = self.label.append('(NoOp)')
		utilities.register_example("BlankKey", self)

# Future create a screen to allow changing the value if parameter is maleable
