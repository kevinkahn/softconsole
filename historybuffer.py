import time
import shutil, os

Buffers = {}
HBdir = ''


def SetupHistoryBuffers(dirnm, maxlogs):
	global HBdir
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
	now = time.time()
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
				'{:1s}{:10s}:({:3d}) {}: {}\n'.format(initial[nextup], nextup, curfirst[nextup][0],
													  now - curfirst[nextup][1],
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
		for i in range(self.size):
			j = (i + curind) % self.size
			if cur[j].timeofentry != 0:
				yield (j, cur[j].timeofentry, cur[j].entry)


	def Dump(self, f):
		for i in range(self.size):
			j = (i + self.current) % self.size
			if self.buf[j].timeofentry != 0:
				f.write('(' + str(j) + ') ' + str(self.buf[j].timeofentry) + ': ' + repr(self.buf[j].entry) + '\n')
