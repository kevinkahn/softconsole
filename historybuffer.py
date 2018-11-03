import time
import shutil, os

Buffers = {}
HBdir = ''


def SetupHistoryBuffers(dirnm, maxlogs):
	global HBdir
	r = [k for k in os.listdir('.') if '.HistoryBufferr' in k]
	if ".HistoryBuffer" + str(maxlogs) in r:
		shutil.rmtree(".HistoryBuffer." + str(maxlogs))
	for i in range(maxlogs - 1, 0, -1):
		if ".HistoryBuffer." + str(i) in r:
			os.rename('.HistoryBuffer.' + str(i), ".HistoryBuffer." + str(i + 1))
	try:
		os.rename('.HistoryBuffer', '.HistoryBuffer.1')
	except:
		pass
	os.mkdir('.HistoryBuffer')
	HBdir = dirnm + '/.HistoryBuffer/'


def DumpAll(idline, entrytime):
	with open(HBdir + entrytime, 'w') as f:
		f.write(entrytime + ': ' + idline + '\n')
		for nm, HB in Buffers.items():
			f.write('-----------' + nm + '-----------\n')
			HB.Dump(f)


class EntryItem(object):
	def __init__(self):
		self.timeofentry = 0
		self.entry = ""


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
		self.current = (self.current + 1) % self.size

	def Dump(self, f):
		for i in range(self.size):
			j = (i + self.current) % self.size
			f.write('(' + str(j) + ') ' + str(self.buf[j].timeofentry) + ': ' + repr(self.buf[j].entry) + '\n')
