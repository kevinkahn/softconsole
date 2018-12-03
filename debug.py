from __future__ import print_function

import logsupport
import mypprint
from logsupport import ConsoleDebug, ConsoleError, ConsoleWarning
from stores import valuestore
from alerttasks import DumpAlerts
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
			'QDump', 'LLTouch', 'Touch', 'ISYDump', 'ISYLoad', 'StoreTrack', 'StoresDump', 'StatesDump', 'AlertsTrace', 'AlertsCheck']
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
	dbgStore.AddAlert('AlertsCheck',AlertsCheck)
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


def DumpStore(f, store, name, indent):
	notdumped = True
	while notdumped:
		try:
			f.write('\n' + indent + name + ' -->\n')
			for i in store.items():
				f.write(indent + '  ' + str(i) + ' ' + str(store.GetVal(i)) + '\n')
				f.flush()
			notdumped = False
		except Exception as e:
			f.write(store.name + " changed - retry dump\n  (" + repr(e) + ")\n")
		if store.children is not None:
			for child, childstore in store.children.items():
				DumpStore(f, childstore, child, indent + '    ')


# noinspection PyUnusedLocal
def StoresDump(store, old, new, param, _):
	if not new: return
	with open('/home/pi/Console/StoresDump.txt', mode='w') as f:
		for store in valuestore.ValueStores.values():
			DumpStore(f, store, store.name, '')

	dbgStore.SetVal('StoresDump',False)


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
def AlertsCheck(store,old,new,param,_):
	if not new: return
	DumpAlerts()
	dbgStore.SetVal('AlertsCheck', False)

