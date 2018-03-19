import sys
import mypprint
from stores import valuestore, localvarsupport
import logsupport
from logsupport import ConsoleDebug, ConsoleError, ConsoleWarning

def debugPrintNull(flag, *args):
	return

def debugPrintEarly(flag,*args):
	#print "Early debug call", flag, args
	return

def debugPrintReal(flag, *args):
	global Flags, debugPrint

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

debugPrint = debugPrintEarly
DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISY', 'Dispatch', 'EventList', 'Fonts', 'DebugSpecial',
			'QDump', 'LLTouch', 'Touch', 'ISYDump', 'ISYLoad', 'StoreTrack', 'StoresDump']
DebugFlagKeys = {}
dbgStore = valuestore.NewValueStore(valuestore.ValueStore('Debug'))
dbgStore.SimpleInit(DbgFlags,False)
valuestore.SetVal(('Debug','LogLevel'),3)

def OptimizeDebug(store, old, new, param, modifier):
	global debugPrint
	flgCount = 0
	for f in dbgStore:
		if f.name[0] != 'LogLevel' and f.Value: flgCount += 1
	if flgCount > 0:
		debugPrint = debugPrintReal
	else:
		debugPrint = debugPrintNull

def LogDebugFlags():
	for flg in DbgFlags:
		fval = dbgStore.GetVal(flg)
		if fval:
			logsupport.Logs.Log('Debug flag ', flg, '=', fval, severity=ConsoleWarning)
			dbgStore.SetVal('LogLevel', 0) # if a debug flag is set force Logging unless explicitly overridden

def InitFlags(sect):
	global DbgFlags, debugPrint
	flgCount = 0
	for flg in DbgFlags:
		v = sect.get(flg, False)
		if flg != 'LogLevel' and v: flgCount +=1
		dbgStore.SetVal(flg, v)
		dbgStore.AddAlert(flg,OptimizeDebug)
	dbgStore.AddAlert('StoresDump',StoresDump)
	if flgCount > 0:
		debugPrint = debugPrintReal
	else:
		debugPrint = debugPrintNull


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

def StoresDump(store,old,new,param):
	if not new: return
	for store in valuestore.ValueStores.itervalues():
		for i in store.items():
			print store.name, i,store.GetVal(i)
	dbgStore.SetVal('StoresDump',False)
