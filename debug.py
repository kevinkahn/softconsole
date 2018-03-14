import config
import sys
import mypprint
from stores import valuestore, localvarsupport
import logsupport
from logsupport import ConsoleDebug, ConsoleError, ConsoleWarning

DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISY', 'Dispatch', 'EventList', 'Fonts', 'DebugSpecial',
			'QDump', 'LLTouch', 'Touch', 'ISYDump', 'ISYLoad']
DebugFlagKeys = {}
dbgStore = valuestore.NewValueStore(valuestore.ValueStore('Debug'))
dbgStore.SimpleInit(DbgFlags,bool,False)
valuestore.SetVal(('Debug','LogLevel'),3)

def LogDebugFlags():
	for flg in DbgFlags:
		fval = dbgStore.GetVal(flg)
		if fval:
			logsupport.Logs.Log('Debug flag ', flg, '=', fval, severity=ConsoleWarning)
			dbgStore.SetVal('LogLevel', 0) # if a debug flag is set force Logging unless explicitly overridden

def debugPrint(flag, *args):
	global Flags, DbgFlags
	flg = dbgStore.GetVal(flag)

	if flg is not None:
		if flg:
			try:
				print >> sys.stderr, flag, '-> ',
				for arg in args:
					print >> sys.stderr, arg,
				print >> sys.stderr
				if logsupport.Logs is not None:
					logsupport.Logs.Log(flag, '-> ', *args, severity=ConsoleDebug, diskonly=True)
			except:
				logsupport.Logs.Log("Internal debug print error: ", flag, ' ', repr(args), severity=ConsoleError)
	else:
		print >> sys.stderr, "DEBUG FLAG NAME ERROR", flag

def InitFlags():
	global DbgFlags
	for flg in DbgFlags:
		dbgStore.SetVal(flg,config.ParsedConfigFile.get(flg, False))

def ISYDump(fn, item, pretty = True,new=False):
	fm = 'w' if new else 'a'
	with open('/home/pi/Console/'+fn,mode=fm) as f:
		if pretty:
			if not new:
				f.write('\n--------------------------------------------------------\n')
			mypprint.pprint(item,stream=f,indent=3,width=50)
		else:
			if not new:
				f.write('\n')
			f.write(item.encode('UTF-8'))
