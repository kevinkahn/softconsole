import datetime
import time
from operator import itemgetter, lt, gt

# Performance info
# todo triggered callbacks for immediate anomoly reports?


statroot = None
ReportTimes = []  # time:group
gmtoffset = (time.timezone / 3600 - time.localtime().tm_isdst) % 24
lastreporttime = -1


def Get(start=None):  # test code
	at = lastreporttime if start is None else start
	testtime = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min).timestamp() + at
	n = GetNextReportTime(at=testtime)
	print(n)
	for i in n:
		print(time.strftime('%m-%d %H:%M:%S', time.localtime(i[0])), i[1].name)


def GetNextReportTime(at=None):
	global lastreporttime
	midnight = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min).timestamp()
	if at is None:
		daysec = time.time() - midnight
	else:
		daysec = at - midnight
	h = daysec // 3600
	m = (daysec - h * 3600) // 60
	reporttimesleft = list(filter(lambda x: x[0] > daysec, ReportTimes))
	if reporttimesleft != []:
		lastreporttime = reporttimesleft[0][0]
		return [(x[0] + midnight, x[1]) for x in filter(lambda x: x[0] == reporttimesleft[0][0], reporttimesleft)]
	else:
		t = midnight + 24 * 60 * 60 + ReportTimes[0][0]
		lastreporttime = ReportTimes[0][0]
		return [(x[0] + t, x[1]) for x in filter(lambda x: x[0] == ReportTimes[0][0], ReportTimes)]


def TimeToReport(reports):
	report = []
	for i in reports:
		report.append(i[1].Report()[1])
	return GetNextReportTime(), report


def GMT(hour, minutes=0):
	t = 24 - (hour + gmtoffset) % 24
	return t * 3600 + minutes * 60


def LOCAL(hour, minutes=0):
	return hour * 3600 + minutes * 60


def EVERY(hour, minutes=0):
	return tuple(range(0, 24 * 60 * 60, hour * 3600 + minutes * 60))


class StatGroup(object):
	def __init__(self, name='', title='', totals='', netreport=None, PartOf=None):
		global statroot
		self.totals = totals
		self.title = title
		self.name = name
		self.elements = {}
		self.netreport = netreport
		if PartOf is not None:
			PartOf.elements[name] = self
			self.PartOf = PartOf
		else:
			if name == 'statroot':
				statroot = self
				self.PartOf = self
			else:
				statroot.elements[name] = self
				self.PartOf = statroot

	def Op(self, name, **kwargs):
		self.elements[name].Op(**kwargs)

	def Reset(self, name, **kwargs):
		self.elements[name].Reset(**kwargs)

	def Exists(self, name):
		return name in self.elements

	def ResetGrp(self, exclude):
		skip = exclude if isinstance(exclude, tuple) else (exclude,)
		for e in self.elements.values():
			if e not in skip: e.Reset()

	def Values(self):  # return total of group values - may only be meaningful for uniform stats in group
		tot = [0, 0]
		for e in self.elements.values():
			tot[0] += e.Values()[0]
			tot[1] += e.Values()[1]
		return tot

	def Report(self):
		rpt = []
		tot = 0
		rtntot = 0
		for e in self.elements.values():
			logitems = e.Report()
			if logitems is not None:
				for l in logitems[1]: rpt.append(l)
				tot += logitems[0]

		if self.totals != '':
			rpt.append('{}: {}'.format(self.totals, tot))
			rtntot = tot
		return rtntot, [self.title, rpt]


StatGroup(name='statroot', title='')  # initialize tree


class StatSubGroup(StatGroup):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
# self.name = name


class StatReportGroup(StatGroup):
	def __init__(self, reporttime=None, **kwargs):
		super().__init__(**kwargs)
		global ReportTimes
		# reporttime = seconds after midnight, list of such
		if reporttime is not None:
			self.times = reporttime if isinstance(reporttime, tuple) else (reporttime,)
			for i in self.times:
				ReportTimes.append((i, self))
			ReportTimes = sorted(ReportTimes, key=itemgetter(0))

	def ResetTimes(self, reporttime=None):
		pass
	# go through ReportTImes to delete old items then do the append and sort


class Stat(object):
	def __init__(self, name, title=None, PartOf=None, netreport=None):
		self.title = title if title is not None else name
		self.name = name
		PartOf.elements[name] = self
		self.netreport = netreport

	def Op(self, val=999999):
		self.value = val
		return self.value

	def Report(self, all=True):
		pass
# print value


class CntStat(Stat):
	def __init__(self, keeplaps=False, inc=1, init=0, **kwargs):
		super(CntStat, self).__init__(**kwargs)
		self.keeplaps = keeplaps
		self.value = init
		self.lastrpt = 0
		self.inc = inc

	def Op(self, **kwargs):
		self.value += self.inc
		return self.value

	def Set(self, val, lastrpt):
		self.value = val
		self.lastrpt = lastrpt

	def Reset(self):
		self.value = 0
		self.lastrpt = 0

	def Values(self):
		return self.value - self.lastrpt, self.value

	def Report(self, clear=True):
		val = self.value
		if self.keeplaps:
			rtn = (('{}: {}'.format(self.title, self.value - self.lastrpt)),
				   '{} (since start): {}'.format(self.title, self.value))
			self.lastrpt = self.value
		else:
			rtn = (('{}: {}'.format(self.title, self.value),))
			self.value = 0
		return val, rtn


class LimitStat(Stat):
	def __init__(self, max=True, keeplaps=False, **kwargs):
		super().__init__(**kwargs)
		self.keeplaps = keeplaps
		self.maxvalue = 0
		self.maxtime = 0
		self.overallmaxvalue = 0
		self.overallmaxtime = 0
		self.operator = gt if max else lt

	def Op(self, val=None):
		if val is None:
			raise ValueError
		if self.operator(val, self.maxvalue):
			self.maxvalue = val
			self.maxtime = time.time()
		if self.operator(val, self.overallmaxvalue):
			self.overallmaxvalue = val
			self.overallmaxtime = time.time()
		return self.maxvalue

	def Set(self, max, overallmax):  # debug function
		self.maxvalue = max
		self.maxtime = time.time()
		self.overallmaxvalue = overallmax
		self.overallmaxtime = time.time() + 100

	def Reset(self):
		self.maxvalue = 0
		self.maxtime = time.time()
		self.overallmaxvalue = 0
		self.overallmaxtime = time.time()

	def Values(self):
		return self.maxvalue, self.overallmaxvalue, self.maxtime, self.overallmaxtime

	def Report(self, clear=True):
		max = self.maxvalue
		rtn = ('{}: {} at {}'.format(self.title, self.maxvalue,
									 datetime.datetime.fromtimestamp(self.maxtime).strftime('%H:%M:%S')),)
		if self.keeplaps:
			rtn = rtn + ('{} (since start): {} at {}'.format(self.title, self.overallmaxvalue,
															 datetime.datetime.fromtimestamp(
																 self.overallmaxtime).strftime('%Y-%m-%d %H:%M:%S')),)
		if clear:
			self.maxvalue = 0
			self.maxtime = time.time()
		return max, rtn


class MaxStat(LimitStat):
	def __init__(self, **kwargs):
		super().__init__(max=True, **kwargs)


class MinStat(LimitStat):
	def __init__(self, **kwargs):
		super().__init__(max=False, **kwargs)


def _NetRpr(st):
	tempd = {}
	if st.netreport is None:
		pass
	elif isinstance(st.netreport, str):
		tempd[st.netreport] = st.Values()[0]
	else:
		for i in range(len(st.netreport)): tempd[st.netreport[i]] = st.Values()[i]
	return tempd


def GetReportables(root=statroot, rptnm=''):
	temp = {}
	tempdict = {}
	t = _NetRpr(root)
	if t != {}: tempdict['*Totals*'] = t
	for nm, st in root.elements.items():
		if not isinstance(st, StatGroup):

			# Label with group if group level stats (totals)
			label = '{}.{}'.format(rptnm, st.name) if isinstance(st, StatGroup) else rptnm
			if st.netreport is None:
				pass
			elif isinstance(st.netreport, str):
				# temp.update({'{}.{}'.format(label,st.netreport): st.Values()[0]})
				tempdict[st.netreport] = st.Values()[0]
			else:
				# temp.update({'{}.{}'.format(label,st.netreport[i]): st.Values()[i] for i in range(len(st.netreport))})
				for i in range(len(st.netreport)): tempdict[st.netreport[i]] = st.Values()[i]
		if isinstance(st, StatGroup):
			# temp.update(GetReportables(st,'{}.{}'.format(rptnm,st.name))[0])
			t = GetReportables(st, '{}.{}'.format(rptnm, st.name))[1]
			if t != {}: tempdict[st.name] = t
	return temp, tempdict


'''
#Testing code

sysstats = StatReportGroup(name='System', title='System Statistics', totals=False, reporttime=(LOCAL(0), LOCAL(1), LOCAL(1,30)))
qd = MaxStat(name='queuedepthmax', PartOf=sysstats, netreport='maxqd',keeplaps=True, title='Maximum Queue Depth')
qt = MaxStat(name='queuetimemax', PartOf=sysstats, netreport=('qtm','qta'),keeplaps=True, title='Maximum Queued Time')
c1 = CntStat(name='maincyclecnt', PartOf=sysstats, title='Main Loop Cycle:', keeplaps=True)
qd.Set(55, 66)
qt.Set(43, 21)


wb = StatReportGroup(name='Weather', title='Weatherbit Statistics', reporttime= (LOCAL(1), LOCAL(1,30), GMT(0), LOCAL(3)))
bl = StatSubGroup(name='ByLocation', PartOf=wb, title='Fetches by Location', totals='Total Fetches')
bn = StatSubGroup(name='ByNode', PartOf=wb, title='Fetches by Node', totals='Total Fetches')
lf = StatSubGroup(name='Local', PartOf=wb, title='Actual Local Fetches', totals='Total Local Fetches',
								  netreport=('Weatherbitfetches24','Weatherbitfetches'))
l1 = CntStat(name='loc1',keeplaps=True,PartOf=lf, netreport=('t1','t2'))
l2 = CntStat(name='loc2',keeplaps=True,PartOf=lf)
l1.Set(25,12)
l2.Set(55,10)

GetReportables()

'''
