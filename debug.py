import config
from logsupport import ConsoleDebug

Flags = {}
DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISY', 'Dispatch', 'EventList', 'Fonts', 'Special']


def debugPrint(flag, *args):
	global Flags, DbgFlags
	if flag in DbgFlags:
		if Flags[flag]:
			print flag, '-> ',
			for arg in args:
				print arg,
			print
			if config.Logs is not None:
				config.Logs.Log(*args, severity=ConsoleDebug, diskonly=True)
	else:
		print "DEBUG FLAG NAME ERROR", flag


def InitFlags():
	global DbgFlags
	dbg = {}
	for flg in DbgFlags:
		dbg[flg] = config.ParsedConfigFile.get(flg, False)
	return dbg
