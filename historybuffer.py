from __future__ import annotations
import os
import shutil
import time
import gc
import threading
from typing import Optional
from utils.utilfuncs import safeprint


def DummyAsyncFileWrite(fn, writestr, access='a'):
	safeprint('Called  HB file write before init {} {} {}'.format(fn, writestr, access))


AsyncFileWrite = DummyAsyncFileWrite  # set from log support to avoid circular imports
DevPrint = None

# import topper

WatchGC = False  # set True to see garbage collection info
Buffers = {}
HBdir = ''
GCBuf: Optional[HistoryBuffer] = None
bufdumpseq = 0
HBNet = None


def SetupHistoryBuffers(dirnm, maxlogs):
	global HBdir, GCBuf
	r = [k for k in os.listdir('.') if '.HistoryBuffer' in k]
	if ".HistoryBuffer." + str(maxlogs) in r:
		shutil.rmtree(".HistoryBuffer." + str(maxlogs))
	for i in range(maxlogs - 1, 0, -1):
		if ".HistoryBuffer." + str(i) in r:
			os.rename('.HistoryBuffer.' + str(i), ".HistoryBuffer." + str(i + 1))
	# noinspection PyBroadException
	try:
		os.rename('.HistoryBuffer', '.HistoryBuffer.1')
	except:
		pass
	os.mkdir('.HistoryBuffer')
	HBdir = dirnm + '/.HistoryBuffer/'
	if WatchGC:
		gc.callbacks.append(NoteGCs)
		GCBuf = HistoryBuffer(50, 'GC')


def NoteGCs(phase, info):
	if GCBuf is not None:
		GCBuf.Entry('GC Call' + phase + repr(info))


def DumpAll(idline, entrytime):
	global bufdumpseq
	if HBdir == '':  # logs not yet set up
		safeprint(time.strftime('%m-%d-%y %H:%M:%S') + ' Suppressing History Buffer Dump for {}'.format(idline))
		return
	fn = HBdir + str(bufdumpseq) + '-' + entrytime
	try:
		#topper.mvtops(str(bufdumpseq) + '-' + entrytime)
		bufdumpseq += 1
		t = {}
		curfirst = {}
		curtime = {}
		initial = {}
		now = time.time()
		more = True
		for nm, HB in Buffers.items():
			t[nm] = HB.content()
			try:
				curfirst[nm] = next(t[nm])
				curtime[nm] = curfirst[nm][1]
			except StopIteration:
				if nm in curfirst: del curfirst[nm]
				if nm in curtime:  del curtime[nm]
			initial[nm] = '*'
		if curfirst == {} or curtime == {}:
			more = False

		prevtime = 0
		AsyncFileWrite(fn, '{} ({}): '.format(entrytime, now) + idline + '\n', 'w')
		while more:
			nextup = min(curtime, key=curtime.get)
			if curtime[nextup] > prevtime:
				prevtime = curtime[nextup]
			else:
				AsyncFileWrite(fn, 'seq error:' + str(prevtime) + ' ' + str(curtime[nextup]) + '\n')
				prevtime = 0
			if now - curfirst[nextup][1] < 300:  # limit history dump to 5 minutes worth
				AsyncFileWrite(fn,
							   '{:1s}{:10s}:({:3d}) {:.5f}: [{}] {}\n'.format(initial[nextup], nextup,
																			  curfirst[nextup][0],
																			  now - curfirst[nextup][1],
																			  curfirst[nextup][3],
																			  curfirst[nextup][2]))
				initial[nextup] = ' '
			try:
				curfirst[nextup] = next(t[nextup])
				curtime[nextup] = curfirst[nextup][1]
			except StopIteration:
				del curfirst[nextup]
				del curtime[nextup]
			if curfirst == {} or curtime == {}: more = False
	except Exception as E:
		AsyncFileWrite(fn, 'Error dumping buffer for: ' + entrytime + ': ' + idline + '\n')
		AsyncFileWrite(fn, 'Exception was: ' + repr(E) + '\n')


class EntryItem(object):
	def __init__(self):
		self.timeofentry = 0
		self.entry = ""
		self.thread = ""


class HistoryBuffer(object):
	def __init__(self, size, name):
		self.buf = []
		for i in range(size):
			self.buf.append(EntryItem())
		self.current = 0
		self.size = size
		self.name = name
		Buffers[name] = self

	def Entry(self, entry):
		self.buf[self.current].entry = entry
		self.buf[self.current].timeofentry = time.time()
		self.buf[self.current].thread = threading.current_thread().name
		self.current = (self.current + 1) % self.size

	def content(self):
		# freeze for dump and reset empty
		# this is subject to races from other threads doing entry reports
		# sequence must be create new buf offline, replace current buf with it so always one or other valid list
		# then change current back to 0
		# at worst this loses a few events that record between grabbing current and replacing with new one
		tempbuf = []
		for i in range(self.size):
			tempbuf.append(EntryItem())
		cur = self.buf
		curind = self.current
		self.buf = tempbuf
		self.current = 0
		#DevPrint('Enter HB content for: {} index {}'.format(self.name, curind))
		for i in range(self.size):
			j = (i + curind) % self.size
			if cur[j].timeofentry != 0:
				# DevPrint('Item from {}: {}/{}/{}/{}'.format(self.name, i, j, cur[j].timeofentry, cur[j].entry))
				yield j, cur[j].timeofentry, cur[j].entry, cur[j].thread
	#DevPrint('Content exit: {}/{}'.format(self.name, j))
