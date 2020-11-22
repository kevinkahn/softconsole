import stats
import config
import time
import logsupport
from logsupport import ConsoleError
import psutil
import historybuffer
import exitutils
import threadmanager
import multiprocessing
import threading
import failsafe

'''
History Buffer
'''
HBEvents = historybuffer.HistoryBuffer(80, 'Events')

'''
Event Deferals
'''
Deferrals = []

'''
Statistics Stuff
'''
maincyc: stats.CntStat
nextstat = None
ckperf = 0
rptreal = 0.0
rptvirt = 0.0


def SetUpStats():
	global maincyc, nextstat
	config.sysstats = stats.StatReportGroup(name='System', title='System Statistics',
											reporttime=stats.LOCAL(0))  # EVERY(0,2))#
	stats.MaxStat(name='queuedepthmax', PartOf=config.sysstats, keeplaps=True, title='Maximum Queue Depth',
				  rpt=stats.timeddaily)
	stats.MaxStat(name='queuetimemax', PartOf=config.sysstats, keeplaps=True, title='Maximum Queued Time',
				  rpt=stats.timeddaily)
	stats.MaxStat(name='realmem', PartOf=config.sysstats, keeplaps=False, title='Real memory use', rpt=stats.daily)
	stats.MaxStat(name='virtmem', PartOf=config.sysstats, keeplaps=False, title='Virtual Memory Use',
				  rpt=stats.daily)
	stats.MinStat(name='realfree', PartOf=config.sysstats, keeplaps=False, title='Min Real Mem', rpt=stats.daily)
	stats.MinStat(name='swapfree', PartOf=config.sysstats, keeplaps=False, title='Min Free Swap', rpt=stats.daily)
	maincyc = stats.CntStat(name='maincyclecnt', PartOf=config.sysstats, title='Main Loop Cycle:', keeplaps=True,
							rpt=stats.daily)
	nextstat = stats.GetNextReportTime()


def CycleStats():
	global nextstat, ckperf, rptreal, rptvirt
	if maincyc.Op() == 4:
		config.sysstats.ResetGrp(exclude=maincyc)
		ckperf = 0  # get a initial mem reading next cycle
	if nextstat[0][0] < time.time():
		nextstat, rpt = stats.TimeToReport(nextstat)

		# rpt is list of lists of lines per report due
		def loglist(lst, tab=''):
			for i in lst:
				if isinstance(i, str):
					logsupport.Logs.Log(tab + i)
				else:
					loglist(i, tab=tab + '    ')

		for r in rpt: loglist(r)

	if time.time() - ckperf > 30:  # todo 900:
		ckperf = time.time()
		p = psutil.Process(config.sysStore.Console_pid)
		realmem = p.memory_info().rss / (2 ** 10)
		realfree = psutil.virtual_memory().available / (2 ** 20)
		virtmem = p.memory_info().vms / (2 ** 10)
		virtfree = psutil.swap_memory().free / (2 ** 20)

		config.sysstats.Op('realmem', val=realmem)
		config.sysstats.Op('virtmem', val=virtmem)
		config.sysstats.Op('realfree', val=realfree)
		config.sysstats.Op('swapfree', val=virtfree)
		if config.sysStore.versionname in ('development', 'homerelease'):
			newhigh = []
			if realmem > rptreal * 1.01:
				rptreal = realmem
				newhigh.append('real')
			if virtmem > rptvirt * 1.01:
				rptvirt = virtmem
				newhigh.append('virtual')
			why = '/'.join(newhigh)
			if why != '':
				logsupport.Logs.Log(
					'Memory({}) use Real: {:.2f}/{:.2f}  Virtual: {:.2f}/{:.2f}'.format(why, realmem,
																						realfree, virtmem, virtfree))


'''
Integrity Checks
'''
Failsafe = multiprocessing.Process(target=failsafe.MasterWatchDog, name='Failsafe')


def SetUpIntegrity():
	if config.sysStore.versionname in ('development',):
		TempThdList = threading.Thread(target=failsafe.TempThreadList, name='ThreadLister')
		TempThdList.daemon = True
		TempThdList.start()
	Injector = threading.Thread(target=failsafe.NoEventInjector, name='Injector')
	Injector.daemon = True
	Injector.start()
	Failsafe.daemon = True
	Failsafe.start()
	config.sysStore.SetVal('Watchdog_pid', Failsafe.pid)
	# if config.sysStore.versionname in ('development', 'homerelease'): topper.inittop()
	logsupport.Logs.Log(
		'Starting master watchdog {} for {}'.format(config.sysStore.Watchdog_pid, config.sysStore.Console_pid))


def CheckConsoleIntegrity():
	if not Failsafe.is_alive():
		logsupport.DevPrint('Watchdog died')
		logsupport.Logs.Log('Watchdog died - restarting console', severity=ConsoleError, hb=True)
		config.terminationreason = 'watchdog died'
		exitutils.Exit(exitutils.ERRORRESTART)
	failsafe.KeepAlive.set()
	if not threadmanager.Watcher.is_alive():
		logsupport.Logs.Log("Threadmanager Failure", severity=ConsoleError, tb=False)
		config.terminationreason = 'watcher died'
		exitutils.Exit(exitutils.ERRORRESTART)
