from __future__ import print_function

import logsupport
import mypprint
from logsupport import ConsoleDebug, ConsoleError, ConsoleWarning
from stores import valuestore
import traceback


# noinspection PyUnusedLocal
def debugPrintNull(flag, *args):
	return

# noinspection PyUnusedLocal
def debugPrintEarly(flag,*args):
	#print "Early debug call", flag, args
	return

def debugPrintReal(flag, *args):
	global debugPrint
	tb = False
	flg = dbgStore.GetVal(flag)

	if flg is not None:
		if flg:
			# noinspection PyBroadException
			try:
				print(flag, '-> ', end='')
				for arg in args:
					print(arg, end='')
				print()
				if tb:
					for line in traceback.format_stack():
						print(line.strip())
				if logsupport.Logs is not None:
					logsupport.Logs.Log(flag, '-> ', *args, severity=ConsoleDebug, diskonly=True)
			except:
				logsupport.Logs.Log("Internal debug print error: ", flag, ' ', repr(args), severity=ConsoleError)
	else:
		print("DEBUG FLAG NAME ERROR", flag)

debugPrint = debugPrintEarly
DbgFlags = ['Main', 'DaemonCtl', 'DaemonStream', 'Screen', 'ISYdbg', 'ISYchg', 'HASSgeneral', 'HASSchg', 'Dispatch', 'EventList', 'Fonts', 'DebugSpecial',
			'QDump', 'LLTouch', 'Touch', 'ISYDump', 'ISYLoad', 'StoreTrack', 'StoresDump', 'StatesDump']
DebugFlagKeys = {}
dbgStore = valuestore.NewValueStore(valuestore.ValueStore('Debug'))
dbgStore.SimpleInit(DbgFlags,False)
valuestore.SetVal(('Debug','LogLevel'),3)

# noinspection PyUnusedLocal
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
			f.write(item)

# noinspection PyUnusedLocal
def StoresDump(store,old,new,param,_):
	if not new: return
	for store in valuestore.ValueStores.values():
		for i in store.items():
			print (store.name + str(i)+str(store.GetVal(i)))
	dbgStore.SetVal('StoresDump',False)
