import threadmanager
import config
import time
from stores import valuestore
import os
import logsupport

FileWatchInfo = None  # entry modtime: 0.0, params: str


def SetUpForFile(a):
	global FileWatchInfo
	entry = {'modtime': 0.0, 'invoke': a.actiontarget, 'param': a.param,
			 'store': valuestore.NewValueStore(valuestore.ValueStore(a.name))}
	if FileWatchInfo is None:
		FileWatchInfo = {a.trigger.filename: entry}
		threadmanager.SetUpHelperThread('fileWatch', FileWatcher)
	else:
		FileWatchInfo[a.trigger.filename] = entry
	valuestore.NewValueStore(valuestore.ValueStore(a.name))
	print('Registering: {}'.format(a))


def FileWatcher():
	global FileWatchInfo
	while not config.Running:
		time.sleep(1)
	for f, info in FileWatchInfo.items():
		FileWatchInfo[f]['modtime'] = os.path.getmtime(f)
		ParseFile(info['store'], f, info['param'])
		print(f, info)
	while True:
		time.sleep(1)
		for f, info in FileWatchInfo.items():
			t = os.path.getmtime(f)
			if t != info['modtime']:
				print('times: {} {}'.format(t, info['modtime']))
				info['modtime'] = t
				ParseFile(info['store'], f, info['param'])


def ParseFile(store, fn, param):
	print('Parse {} {}'.format(fn, param))
	with open(fn) as f:
		tmp = f.readlines()
	if param == 'SingleParse':
		store.SetVal('file', tmp)
	elif param == 'Settings':
		for l in tmp:
			t = l.strip()
			if t != '':
				try:
					t = l.split('=', 1)
					store.SetVal(t[0].strip(), t[1].strip())
				except:
					logsupport.Logs.Log('Malformed settings ({}) for watched file {}'.format(t, fn),
										severity=logsupport.ConsoleWarning)
# IF Invoke a screen PostEvent(ConsoleEvent(CEvent.SchedEvent, **self.kwargs)) with proc = Invoke
# what does hitting ok on alert screen mean? vs defer should change the istrue to false and then set it back to true here?
