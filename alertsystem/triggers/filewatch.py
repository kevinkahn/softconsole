import os

import alertsystem.alertutils as alertutils
import alertsystem.alerttasks as alerttasks
import logsupport
from utils import utilities, threadmanager
import config
from stores import valuestore
import time
from controlevents import CEvent, PostEvent, ConsoleEvent

triggername = 'FileWatch'


class FileWatchTrigger(object):
	def __init__(self, filename):
		self.filename = filename
		self.trigstate = False

	def IsTrue(self):
		return self.trigstate

	def ClearTrigger(self):
		self.trigstate = False

	def SetTrigger(self):
		self.trigstate = True

	def __repr__(self):
		return 'Filename = {}'.format(self.filename)


def Parse(nm, spec, action, actionname, param):
	# parse the filename
	tmp = spec.get('File', None)
	if tmp is None:
		logsupport.Logs.Log("Alert: {} Must supply file name".format(nm), severity=logsupport.ConsoleWarning)
		return None
	trig = FileWatchTrigger(utilities.inputfileparam(tmp, config.sysStore.configdir, 'news.txt'))
	if param not in ('SingleItem', 'Settings'):
		logsupport.Logs.Log("Alert: {} Paramter must be Settings or SingleItem".format(nm),
							severity=logsupport.ConsoleWarning)
		param = 'SingleItem'
	return alerttasks.Alert(nm, triggername, trig, action, actionname, param)


FileWatchInfo = {}  # entry modtime: 0.0, params: str


def SetUpForFile(a):
	global FileWatchInfo
	entry = {'modtime': 0.0, 'invoke': a.actiontarget, 'param': a.param, 'alert': a,
			 'store': valuestore.NewValueStore(valuestore.ValueStore(a.name))}
	if FileWatchInfo == {}:
		FileWatchInfo = {a.trigger.filename: entry}
		threadmanager.SetUpHelperThread('fileWatch', FileWatcher)
	else:
		FileWatchInfo[a.trigger.filename] = entry
	valuestore.NewValueStore(valuestore.ValueStore(a.name))


def FileWatcher():
	global FileWatchInfo
	while not config.Running:
		time.sleep(1)
	BadFiles = []
	for f, info in FileWatchInfo.items():
		try:
			FileWatchInfo[f]['modtime'] = os.path.getmtime(f)
			ParseFile(info['store'], f, info['param'])
		except Exception as E:
			logsupport.Logs.Log("Error accessing watched file {} ({})".format(f, E), severity=logsupport.ConsoleWarning)
			BadFiles.append(f)
	while True:
		time.sleep(1)
		for f, info in FileWatchInfo.items():
			try:
				t = os.path.getmtime(f)
			except Exception as E:
				if not f in BadFiles:
					logsupport.Logs.Log("Watched file {} became inaccessible ({})".format(f, E),
										severity=logsupport.ConsoleWarning)
					BadFiles.append(f)
				continue
			if f in BadFiles:
				BadFiles.remove(f)
			if t != info['modtime']:
				info['alert'].trigger.SetTrigger()
				info['modtime'] = t
				ParseFile(info['store'], f, info['param'])
				if info['invoke'] is not None:
					PostEvent(ConsoleEvent(CEvent.RunProc, proc=info['alert'].Invoke, name='FileWatch' + f))


# IF Invoke a screen PostEvent(ConsoleEvent(CEvent.SchedEvent, **self.kwargs)) with proc = Invoke
# what does hitting ok on alert screen mean? vs defer should change the istrue to false and then set it back to true here?

def ParseFile(store, fn, param):
	with open(fn) as f:
		tmp = f.readlines()
	if param == 'SingleItem':
		store.SetVal('file', tmp)
	elif param == 'Settings':
		for l in tmp:
			t = l.strip()
			if t != '':
				try:
					t = l.split('=', 1)
					store.SetVal(t[0].strip(), t[1].strip())
				except Exception as E:
					logsupport.Logs.Log('Malformed settings ({}) for watched file {} ({})'.format(t, fn, E),
										severity=logsupport.ConsoleWarning)


alertutils.TriggerTypes[triggername] = alertutils.TriggerRecord(Parse, SetUpForFile, FileWatchTrigger)
