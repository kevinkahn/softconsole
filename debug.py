import config
import sys
from logsupport import ConsoleDebug

Flags = {}
DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISY', 'Dispatch', 'EventList', 'Fonts', 'DebugSpecial',
			'QDump']
DebugFlagKeys = {}
flagspercol = 3  # number of flags per maint screen
flagsperrow = 2

def debugPrint(flag, *args):
	global Flags, DbgFlags
	if flag in DbgFlags:
		if Flags[flag]:
			print >> sys.stderr, flag, '-> ',
			for arg in args:
				print >> sys.stderr, arg,
			print >> sys.stderr
			if config.Logs is not None:
				config.Logs.Log(flag, '-> ', *args, severity=ConsoleDebug, diskonly=True)
	else:
		print >> sys.stderr, "DEBUG FLAG NAME ERROR", flag


def InitFlags():
	global DbgFlags
	dbg = {}
	for flg in DbgFlags:
		dbg[flg] = config.ParsedConfigFile.get(flg, False)

	return dbg
