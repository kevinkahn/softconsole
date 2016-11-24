from config import Logs

Flags = {}
DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISY', 'Dispatch', 'EventList', 'Fonts']


def debugPrint(flag, *args):
	if flag in DbgFlags:
		if Flags[flag]:
			print flag, '-> ',
			for arg in args:
				print arg,
			print
			if Logs <> None:
				Logs.Log(*args, severity=-1, diskonly=True)
	else:
		print "DEBUG FLAG NAME ERROR", flag
