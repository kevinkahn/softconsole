import time
import shutil, os

Buffers = {}
HBdir = ''
BaseTime = 0


def SetupHistoryBuffers(dirnm, maxlogs):
	global HBdir, BaseTime
	r = [k for k in os.listdir('.') if '.HistoryBuffer' in k]
	if ".HistoryBuffer." + str(maxlogs) in r:
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
	BaseTime = time.time()


def DumpAll1(idline, entrytime):
	with open(HBdir + entrytime, 'w') as f:
		f.write(entrytime + ': ' + idline + '\n')
		for nm, HB in Buffers.items():
			f.write('-----------' + nm + '-----------\n')
			HB.Dump(f)
			f.write('\n')


def DumpAll(idline, entrytime):
	t = {}
	curfirst = {}
	curtime = {}
	initial = {}
	more = True
	for nm, HB in Buffers.items():
		t[nm] = HB.content()
		try:
			curfirst[nm] = next(t[nm])
			curtime[nm] = curfirst[nm][1]
		except StopIteration:
			del curfirst[nm]
			del curtime[nm]
		initial[nm] = '*'
	with open(HBdir + entrytime, 'w') as f:
		prevtime = 0
		f.write(entrytime + ': ' + idline + '\n')
		while more:
			nextup = min(curtime, key=curtime.get)
			if curtime[nextup] > prevtime:
				prevtime = curtime[nextup]
			else:
				f.write('seq error:' + str(prevtime) + ' ' + str(curtime[nextup]) + '\n')
				prevtime = 0
			f.write(
				'{:1s}{:10s}:({:3d}) {}: {}\n'.format(initial[nextup], nextup, curfirst[nextup][0], curfirst[nextup][1],
													  curfirst[nextup][2]))
			# f.write(nextup + ': (' + str(curfirst[nextup][0]) + ') ' + str(curfirst[nextup][1]) + ': ' + repr(curfirst[nextup][2]) + '\n')
			initial[nextup] = ' '
			try:
				curfirst[nextup] = next(t[nextup])
				curtime[nextup] = curfirst[nextup][1]
			except StopIteration:
				del curfirst[nextup]
				del curtime[nextup]
			if curfirst == {}: more = False





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

	def content(self):
		# freeze for dump and reset empty
		cur = self.buf
		curind = self.current
		self.buf = []
		for i in range(self.size):
			self.buf.append(EntryItem())
		self.current = 0
		for i in range(self.size):
			j = (i + curind) % self.size
			if cur[j].timeofentry != 0:
				yield (j, cur[j].timeofentry - BaseTime, cur[j].entry)


	def Dump(self, f):
		for i in range(self.size):
			j = (i + self.current) % self.size
			if self.buf[j].timeofentry != 0:
				f.write('(' + str(j) + ') ' + str(self.buf[j].timeofentry) + ': ' + repr(self.buf[j].entry) + '\n')
