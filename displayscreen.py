import hubs.hubs
import hw
import multiprocessing
import threading
import time
import psutil
import stats
from stats import LOCAL, EVERY

import pygame
import screen
import alerttasks
import config
import debug
import exitutils
import failsafe
import historybuffer
import logsupport
import maintscreen
import screens.__screens as screens
import threadmanager
import timers
from controlevents import CEvent, PostEvent, ConsoleEvent, GetEvent, GetEventNoWait
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from consolestatus import ReportStatus
import consolestatus
import controlevents
import traceback


# import objgraph


class DisplayScreen(object):
	def __init__(self):
		debug.debugPrint("Main", "Screensize: ", hw.screenwidth, hw.screenheight)
		logsupport.Logs.Log("Screensize: " + str(hw.screenwidth) + " x " + str(hw.screenheight))
		logsupport.Logs.Log(
			"Scaling ratio: " + "{0:.2f} W ".format(hw.dispratioW) + "{0:.2f} H".format(hw.dispratioH))

		self.dim = 'Bright'  # either Bright or Dim (or '' for don't change when a parameter
		self.state = 'Home'  # one of Home, NonHome, Maint, Cover, Alert

		self.Deferrals = []
		self.WatchVarVals = {}  # most recent reported watched variable values

		self.AS = None  # Active Screen
		self.Chain = 0  # which screen chain is active 0: Main chain 1: Secondary Chain
		self.HBScreens = historybuffer.HistoryBuffer(20, 'Screens')
		self.HBEvents = historybuffer.HistoryBuffer(80, 'Events')
		self.ActivityTimer = timers.ResettableTimer(name='ActivityTimer', start=True)
		self.activityseq = 0
		self.ScreenStack = []

	def Dim(self):
		self.dim = 'Dim'
		hw.GoDim(int(config.sysStore.DimLevel))

	def Brighten(self):
		self.dim = 'Bright'
		hw.GoBright(int(config.sysStore.BrightLevel))

	def SetActivityTimer(self, timeinsecs, dbgmsg):
		self.activityseq += 1
		self.ActivityTimer.set(ConsoleEvent(CEvent.ACTIVITYTIMER, seq=self.activityseq, msg=dbgmsg), timeinsecs)
		debug.debugPrint('Dispatch', 'Set activity timer: ', timeinsecs, ' ', dbgmsg)

	def SwitchScreen(self, NS, newdim, reason, *, newstate=None, AsCover=False, push=False, clear=False):
		if newstate is None: newstate = self.state  # no state change
		if NS == screens.HomeScreen: self.Chain = 0  # force to Main chain in case coming from secondary
		oldname = 'None' if self.AS is None else self.AS.name
		self.HBScreens.Entry(
			'SwitchScreen old: {} new: {} chain: {} reason: {}'.format(oldname, NS.name, self.Chain, reason))
		if NS == self.AS:
			debug.debugPrint('Dispatch', 'Null SwitchScreen: ', reason)
			logsupport.Logs.Log(
				'Null switchscreen for {}: {}'.format(NS.name, reason))
			if config.sysStore.versionname in ('development', 'homerelease'):
				logsupport.Logs.Log('Null switch stack:', severity=ConsoleWarning, hb=True)
				for L in traceback.format_stack():
					logsupport.Logs.Log(L.strip())
		if NS == screen.BACKTOKEN:
			if self.ScreenStack:
				NS = self.ScreenStack.pop()
			else:
				logsupport.Logs.Log('Screen BACK with empty stack', severity=ConsoleWarning, tb=True)
				NS = screens.HomeScreen
		elif NS == screen.HOMETOKEN:  # todo add PoppedOver for the stack items
			if self.ScreenStack:
				if len(self.ScreenStack) == 1:  # Home and Back would be the same so go to chain home
					NS = screens.HomeScreen
					self.ScreenStack[0].PopOver()
					self.ScreenStack = []
				else:
					NS = self.ScreenStack[0]
					for S in self.ScreenStack[1:]:
						S.PopOver()
					self.ScreenStack = []
			else:
				NS = screens.HomeScreen
				logsupport.Logs.Log('HOME from non stacked screen {}'.format(self.AS.name), severity=ConsoleWarning)
		elif NS == screen.SELFTOKEN:
			NS = self.AS
		else:
			if clear:
				for S in self.ScreenStack:
					S.PopOver()
				self.ScreenStack = []
			if push:
				self.ScreenStack.append(self.AS)

		NavKeys = NS.DefaultNavKeysShowing if not AsCover else False
		ASname = '*None*' if self.AS is None else self.AS.name
		self.HBScreens.Entry(
			NS.name + ' was ' + ASname + ' dim: ' + str(newdim) + ' state: ' + str(newstate) + ' reason: ' + str(
				reason))
		config.sysStore.CurrentScreen = NS.name
		oldstate = self.state
		olddim = self.dim
		if NS == screens.HomeScreen:  # always force home state on move to actual home screen
			newstate = 'Home'

		if self.AS is not None and self.AS != NS:
			debug.debugPrint('Dispatch', "Switch from: ", self.AS.name, " to ", NS.name, "Nav=", NavKeys, ' State=',
							 oldstate + '/' + newstate + ':' + olddim + '/' + newdim, ' ', reason)
			self.AS.Active = False
			self.AS.ExitScreen(
				push)  # todo should we call exit even on same screen recall? add via push and add PoppedOver
		OS = self.AS
		self.AS = NS
		self.AS.Active = True
		if newdim == 'Dim':
			self.Dim()
			if olddim == 'Dim':
				if newstate == 'Cover':
					# special case persist
					self.SetActivityTimer(screens.DimIdleTimes[0], reason + ' using cover time')
				else:
					self.SetActivityTimer(self.AS.PersistTO, reason)
			else:
				self.SetActivityTimer(self.AS.DimTO, reason)

		elif newdim == 'Bright':
			self.Brighten()
			self.SetActivityTimer(self.AS.DimTO, reason)
		else:
			pass  # leave dim as it

		self.AS.NavKeysShowing = NavKeys
		if NavKeys:
			if self.ScreenStack:
				nav = {'homekey': self.AS.homekey, 'backkey': self.AS.backkey}
			else:
				nav = {'prevkey': self.AS.prevkey, 'nextkey': self.AS.nextkey}
		else:
			nav = {}

		self.state = newstate

		debug.debugPrint('Dispatch', "New watchlist(Main): " + str(self.AS.HubInterestList))

		# if OS == self.AS:
		#	print('Double dispatch: {}'.format(self.AS.name))
		try:
			self.AS.InitDisplay(nav)
		except Exception as e:
			logsupport.Logs.Log('Screen display error: ', self.AS.name, ' ', repr(e), severity=ConsoleError)
			traceback.print_exc()
		# todo should this be just logged and return to home?


	def MainControlLoop(self, InitScreen):

		TimerName = 0


		threadmanager.StartThreads()
		config.sysStore.LogStartTime = time.time()  # MQTT will start tracking other console errors now
		# so we can start broadcasting our errors
		logsupport.LocalOnly = False

		self.ScreensDict = screens.SecondaryDict.copy()
		self.ScreensDict.update(screens.MainDict)

		for a in alerttasks.AlertItems.AlertsList.values():
			a.state = 'Armed'
			logsupport.Logs.Log("Arming " + a.type + " alert " + a.name)
			logsupport.Logs.Log("->" + str(a), severity=ConsoleDetail)

			if a.type == 'Periodic':
				alerttasks.SchedulePeriodicEvent(a)
			elif a.type == 'NodeChange':
				a.trigger.node.Hub.SetAlertWatch(a.trigger.node, a)
				if a.trigger.IsTrue():
					# noinspection PyArgumentList
					PostEvent(ConsoleEvent(CEvent.ISYAlert, hub='DS-NodeChange', alert=a))
			elif a.type == 'VarChange':
				a.state = 'Init'
				# Note: VarChange alerts don't need setup because the store has an alert proc
				pass
			elif a.type == 'Init':
				a.Invoke()
			else:
				logsupport.Logs.Log("Internal error - unknown alert type: ", a.type, ' for ', a.name,
									severity=ConsoleError, tb=False)

		logsupport.Logs.livelog = False  # turn off logging to the screen
		config.sysStore.ErrorNotice = -1  # don't pester for errors during startup
		time.sleep(1)  # give support services a chance to start (particularly MQTT)
		ReportStatus('mainloop starting')
		config.Running = True

		with open("{}/.ConsoleStart".format(config.sysStore.HomeDir), "a") as f:
			f.write(str(time.time()) + '\n')
		if config.Running:  # allow for a very early restart request from things like autoversion
			self.SwitchScreen(InitScreen, 'Bright', 'Startup', newstate='Home')

		statusperiod = time.time()
		prevstatus = ''

		if config.sysStore.versionname in ('development'):
			TempThdList = threading.Thread(target=failsafe.TempThreadList, name='ThreadLister')
			TempThdList.daemon = True
			TempThdList.start()

		Injector = threading.Thread(target=failsafe.NoEventInjector, name='Injector')
		Injector.daemon = True
		Injector.start()
		Failsafe = multiprocessing.Process(target=failsafe.MasterWatchDog,name='Failsafe')
		Failsafe.daemon = True
		Failsafe.start()
		config.sysStore.SetVal('Watchdog_pid', Failsafe.pid)
		#if config.sysStore.versionname in ('development', 'homerelease'): topper.inittop()

		logsupport.Logs.Log('Starting master watchdog {} for {}'.format(config.sysStore.Watchdog_pid, config.sysStore.Console_pid))

		event = None

		pcslist = ''
		for pcs in ('Console', 'Watchdog', 'AsyncLogger', 'Topper'):
			try:
				if config.sysStore.GetVal(pcs + '_pid') != 0:
					pcslist = pcslist + '{}: {} '.format(pcs, config.sysStore.GetVal(pcs + '_pid'))
			except:
				pass
		logsupport.Logs.Log('Console Up: {}'.format(pcslist))

		perfdump = time.time()
		ckperf = 0
		stackdepth = 0
		rptreal = 0.0
		rptvirt = 0.0
		peakstats = {}

		config.sysstats = stats.StatReportGroup(name='System', title='System Statistics',
												reporttime=LOCAL(0))  # EVERY(0,2))#
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

		try:
			while config.Running:  # Operational Control Loop
				if maincyc.Op() == 4:
					config.sysstats.ResetGrp(exclude=maincyc)
					ckperf = 0  # get a initial mem reading next cycle
				if nextstat[0][0] < time.time():
					nextstat, rpt = stats.TimeToReport(nextstat)

					# rpt is list of lists of lines per report due
					def loglist(l, tab=''):
						for i in l:
							if isinstance(i, str):
								logsupport.Logs.Log(tab + i)
							else:
								loglist(i, tab=tab + '    ')

					for r in rpt: loglist(r)

				self.HBEvents.Entry('Start event loop iteration')

				StackCheck = traceback.format_stack()
				if stackdepth == 0:
					stackdepth = len(StackCheck)
				if len(StackCheck) != stackdepth and config.sysStore.versionname in ('development', 'homerelease'):
					logsupport.Logs.Log('Stack growth error', severity=ConsoleWarning, hb=True)
					for L in StackCheck:
						logsupport.Logs.Log(L.strip())

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
																									realfree,
																									virtmem, virtfree))

				if not Failsafe.is_alive():
					logsupport.DevPrint('Watchdog died')
					logsupport.Logs.Log('Watchdog died - restarting console', severity=ConsoleError, hb=True)
					config.terminationreason = 'watchdog died'
					exitutils.Exit(exitutils.ERRORRESTART)
				failsafe.KeepAlive.set()

				nowtime = time.time()
				if statusperiod <= nowtime or prevstatus != config.sysStore.consolestatus:
					ReportStatus(config.sysStore.consolestatus)
					prevstatus = config.sysStore.consolestatus
					statusperiod = nowtime + 60

				if not threadmanager.Watcher.is_alive():
					logsupport.Logs.Log("Threadmanager Failure", severity=ConsoleError, tb=False)
					config.terminationreason = 'watcher died'
					exitutils.Exit(exitutils.ERRORRESTART)

				logsupport.LoggerQueue.put(
					(logsupport.Command.Touch, "{}/.ConsoleStart".format(config.sysStore.HomeDir)))

				if debug.dbgStore.GetVal('StatesDump'):
					debug.dbgStore.SetVal('StatesDump', False)
					for h, hub in hubs.hubs.Hubs.items():
						print('States dump for hub: ', h)
						hub.StatesDump()
					debug.dbgStore.SetVal('StatesDump', False)

				if self.Deferrals:  # an event was deferred mid screen touches - handle now
					event = self.Deferrals.pop(0)
					self.HBEvents.Entry('Got deferred event: {}   {}'.format(time.time(), repr(event)))
					debug.debugPrint('EventList', 'Deferred Event Pop', event)
				elif debug.dbgStore.GetVal('QDump'):
					# todo QDump with new event mechanism
					'''if events:
						debug.debugPrint('QDump', 'Time: ', time.time())
						for e in events:
							self.Deferrals.append(e)
							debug.debugPrint('QDump', e, e.type)
						else:
							debug.debugPrint('QDump', "Empty queue")
							time.sleep(0.01)
					event = pygame.event.Event(NOEVENT, dict={'inject':time.time(),'defer':True}) #eventfix
					'''
					pass
				else:
					needvalidevent = True
					while needvalidevent:
						event = GetEvent()
						self.HBEvents.Entry('Got event: {}  {}'.format(time.time(),repr(event)))
						if event.type == CEvent.ACTIVITYTIMER:
							if event.seq == self.activityseq:
								needvalidevent = False
							else:
								if config.sysStore.versionname == 'development':
									logsupport.Logs.Log('Outdated activity {} {}'.format(event.seq, self.activityseq))
									self.HBEvents.Entry('outdated activity {} {}'.format(event.seq, self.activityseq))
									logsupport.DevPrint('outdated activity {} {}'.format(event.seq, self.activityseq))
						else:
							needvalidevent = False
				self.HBEvents.Entry('Process at {}  {}'.format(time.time(), repr(event)))

				postwaittime = time.time()

				if event.type == CEvent.FailSafePing:
					self.HBEvents.Entry(
						'Saw NOEVENT {} after injection at {}'.format(time.time() - event.inject, event.inject))
					pass  # these appear to make sure loop is running
				elif event.type == CEvent.MouseDown:  # pygame.MOUSEBUTTONDOWN:
					self.HBEvents.Entry('MouseDown' + str(event.pos))
					debug.debugPrint('Touch', 'MouseDown' + str(event.pos) + repr(event))
					# screen touch events; this includes touches to non-sensitive area of screen
					self.SetActivityTimer(self.AS.DimTO, 'Screen touch')
					# refresh non-dimming in all cases including non=sensitive areas
					# this refresh is redundant in some cases where the touch causes other activities

					if self.dim == 'Dim':
						# wake up the screen and if in a cover state go home
						config.sysStore.consolestatus = 'active'
						if self.state == 'Cover':
							self.SwitchScreen(screens.HomeScreen, 'Bright', 'Wake up from cover', newstate='Home')
						else:
							self.Brighten()  # if any other screen just brighten
						continue  # wakeup touches are otherwise ignored

					# Screen was not Dim so the touch was meaningful
					pos = event.pos
					tapcount = 1
					pygame.time.delay(config.sysStore.MultiTapTime)
					while True:
						eventx = GetEventNoWait()
						if eventx is None:
							break
						elif eventx.type == CEvent.MouseDown:
							self.HBEvents.Entry('Follow MouseDown: {}'.format(repr(eventx)))
							debug.debugPrint('Touch', 'Follow MouseDown' + str(event.pos) + repr(event))
							tapcount += 1
							pygame.time.delay(config.sysStore.MultiTapTime)  # todo make general time call?
						else:
							if eventx.type in (CEvent.MouseUp, CEvent.MouseMotion):
								debug.debugPrint('Touch', 'Other event: {}'.format(repr(eventx)))
								self.HBEvents.Entry('Mouse Other: {}'.format(repr(eventx)))
							else:
								self.HBEvents.Entry('Defer' + repr(eventx))
								self.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out
						# Future add handling for hold here with checking for MOUSE UP etc.
					if tapcount == 3:
						if self.state == 'Maint':
							# ignore triple taps if in maintenance mode
							logsupport.Logs.Log('Secondary chain taps ignored - in Maint mode')
							continue
						# Switch screen chains
						if screens.HomeScreen != screens.HomeScreen2:  # only do if there is a real secondary chain
							if self.Chain == 0:
								self.Chain = 1
								self.SwitchScreen(screens.HomeScreen2, 'Bright', 'Chain switch to secondary',
												  newstate='NonHome')
							else:
								self.Chain = 0
								self.SwitchScreen(screens.HomeScreen, 'Bright', 'Chain switch to main', newstate='Home')
						continue

					elif tapcount > 3 and tapcount < 8:
						if self.state == 'Maint':
							# ignore if already in Maint
							logsupport.Logs.Log('Maintenance taps ignored - already in Maint mode')
							continue
						# Go to maintenance
						logsupport.Logs.Log('Entering Console Maintenance')
						#self.SwitchScreen(maintscreen.MaintScreen, 'Bright', 'Tap to maintenance', newstate='Maint')
						screen.PushToScreen(maintscreen.MaintScreen, newstate='Maint', msg='Push to Maint')
						continue
					elif tapcount >= 8:
						logsupport.Logs.Log('Runaway {} taps - likely hardware issue'.format(tapcount),
											severity=ConsoleWarning, hb=True)
						continue

					if self.AS.Keys is not None:
						for K in self.AS.Keys.values():
							if K.touched(pos):
								K.Pressed(tapcount)

					for K in self.AS.NavKeys.values():
						if K.touched(pos):
							K.Proc()  # todo make a goto key

				elif event.type in (CEvent.MouseUp, CEvent.MouseMotion):
					debug.debugPrint('Touch', 'Other mouse event {}'.format(event))

				# ignore for now - handle more complex gestures here if ever needed

				elif event.type == CEvent.ACTIVITYTIMER:  # ACTIVITYTIMER:
					debug.debugPrint('Dispatch', 'Activity timer fired State=', self.state, '/', self.dim)

					if self.dim == 'Bright':
						self.HBEvents.Entry('ActivityTimer(Bright) state: {}'.format(self.state))
						config.sysStore.consolestatus = 'idle'
						self.Dim()
						self.SetActivityTimer(self.AS.PersistTO, 'Go dim and wait persist')
					else:
						self.HBEvents.Entry('ActivityTimer(non-Bright) state: {}'.format(self.state))
						if self.state == 'NonHome':
							self.SwitchScreen(screens.HomeScreen, 'Dim', 'Dim nonhome to dim home', newstate='Home',
											  clear=True)
						elif self.state == 'Home':
							self.SwitchScreen(screens.DimIdleList[0], 'Dim', 'Go to cover', newstate='Cover',
											  AsCover=True,
											  clear=True)
							# rotate covers - save even if only 1 cover
							screens.DimIdleList = screens.DimIdleList[1:] + [screens.DimIdleList[0]]
							screens.DimIdleTimes = screens.DimIdleTimes[1:] + [screens.DimIdleTimes[0]]
						elif self.state == 'Cover':
							if len(screens.DimIdleList) > 1:
								self.SwitchScreen(screens.DimIdleList[0], 'Dim', 'Go to next cover', newstate='Cover',
												  AsCover=True, clear=True)
								screens.DimIdleList = screens.DimIdleList[1:] + [screens.DimIdleList[0]]
								screens.DimIdleTimes = screens.DimIdleTimes[1:] + [screens.DimIdleTimes[0]]
						elif self.state == 'Maint':
							# No activity on Maint screens so go home
							self.SwitchScreen(screens.HomeScreen, 'Dim', 'Dim maint to dim home', newstate='Home',
											  clear=True)
						else:  # Maint or Alert - just ignore the activity action
							# logsupport.Logs.Log('Activity timer fired while in state: {}'.format(self.state),severity=ConsoleWarning)
							logsupport.Logs.Log('Activity timeout in unknown state: {}'.format(self.state),
												severity=ConsoleWarning, hb=True)

				elif event.type == CEvent.GeneralRepaint:
					self.HBEvents.Entry('General Repaint: {}'.format(repr(event)))
					debug.debugPrint('Dispatch', 'General Repaint Event', event)
					self.AS.ReInitDisplay()

				elif event.type == CEvent.HubNodeChange:
					self.HBEvents.Entry('Hub Change: {}'.format(repr(event)))
					debug.debugPrint('Dispatch', 'Hub Change Event', event)
					if hasattr(event, 'node'):
						if hasattr(event, 'varinfo'):
							print('Event with both var and node {}'.format(event))
							logsupport.Logs.Log('Event with both var and node {}'.format(event),
												severity=ConsoleWarning)
						self.AS.NodeEvent(event)
					elif hasattr(event, 'varinfo'):
						self.AS.VarEvent(event)
					else:
						debug.debugPrint('Dispatch', 'Bad Node Change Event: ', event)
						logsupport.Logs.Log('Node Change Event missing node and varinfo: {} '.format(event),
											severity=ConsoleWarning)

				elif event.type in (CEvent.ISYVar, CEvent.ISYAlert):
					self.HBEvents.Entry('Var or Alert' + repr(event))
					evtype = 'variable' if event.type == CEvent.ISYVar else 'node'
					debug.debugPrint('Dispatch', 'ISY ', evtype, ' change', event)
					alert = event.alert
					if alert.state in ('Armed', 'Init'):
						if alert.trigger.IsTrue():  # alert condition holds
							if alert.trigger.delay != 0:  # delay invocation
								alert.state = 'Delayed'
								debug.debugPrint('Dispatch', "Post with delay:", alert.name, alert.trigger.delay)
								TimerName += 1
								alert.timer = timers.OnceTimer(alert.trigger.delay, start=True,
															   name='MainLoop' + str(TimerName),
															   proc=alerttasks.HandleDeferredAlert, param=alert)
							else:  # invoke now
								alert.state = 'FiredNoDelay'
								debug.debugPrint('Dispatch', "Invoke: ", alert.name)
								alert.Invoke()  # either calls a proc or enters a screen and adjusts alert state appropriately
						else:
							if alert.state == 'Armed':
								# condition cleared after alert rearmed  - timing in the queue?
								logsupport.Logs.Log('Anomolous Trigger clearing while armed: ', repr(alert),
													severity=ConsoleDetail, hb=True)
							else:
								alert.state = 'Armed'
								logsupport.Logs.Log('Initial var value for trigger is benign: ', repr(alert),
													severity=ConsoleDetail)
					elif alert.state == 'Active' and not alert.trigger.IsTrue():  # alert condition has cleared and screen is up
						debug.debugPrint('Dispatch', 'Active alert cleared', alert.name)
						alert.state = 'Armed'  # just rearm the alert
						self.SwitchScreen(screens.HomeScreen, 'Dim', 'Cleared alert', newstate='Home')
					elif ((alert.state == 'Delayed') or (alert.state == 'Deferred')) and not alert.trigger.IsTrue():
						# condition changed under a pending action (screen or proc) so just cancel and rearm
						if alert.timer is not None:
							alert.timer.cancel()
							alert.timer = None
						else:
							logsupport.DevPrint('Clear with no timer?? {}'.format(repr(alert)))
						debug.debugPrint('Dispatch', 'Delayed event cleared before invoke', alert.name)
						alert.state = 'Armed'
					# todo - verify this is correct.  Issue is that the alert might have gotten here from a delay or from the
					# alert screen deferring.  The screen uses it's own id for this alert to might be either.  Probably should
					# distinguish based on if delay or defer but doing both should be same id(alert.actiontarget))  originally this was id-alert for some
					# reason I changed it to id-actiontarget don't know why but it was done while adding HASS this screwed up clearing deferred alerts
					# so switched it back in hopes to remember why the change todo
					else:
						logsupport.Logs.Log("Anomolous change situation  State: ", alert.state, " Alert: ", repr(alert),
											" Trigger IsTue: ",
											alert.trigger.IsTrue(), severity=ConsoleWarning, hb=True)
						debug.debugPrint('Dispatch', 'ISYVar/ISYAlert passing: ', alert.state, alert.trigger.IsTrue(),
										 event,
										 alert)
				# Armed and false: irrelevant report
				# Active and true: extaneous report
				# Delayed or deferred and true: redundant report

				elif event.type == CEvent.SchedEvent:
					if hasattr(event, 'eventvalid') and not event.eventvalid():
						self.HBEvents.Entry('Ignore event that is no longer valid: {}'.format(repr(event)))
						continue
					self.HBEvents.Entry('Sched event {}'.format(repr(event)))
					eventnow = time.time()
					diff = eventnow - event.TargetTime
					if abs(diff) > controlevents.latencynotification:
						# todo 5 tap can cause this - really would like to check if event for active screen first
						self.HBEvents.Entry(
							'Event late by {} target: {} now: {}'.format(diff, event.TargetTime, eventnow))
						logsupport.Logs.Log('Timer late by {} seconds. Event: {}'.format(diff, repr(event)),
											hb=True, homeonly=True)
					event.proc(event)

				elif event.type == CEvent.RunProc:
					if hasattr(event, 'params'):
						self.HBEvents.Entry('Run procedure {} with params {}'.format(event.name, event.params))
						event.proc(event.params)
					else:
						self.HBEvents.Entry('Run procedure {}'.format(event.name))
						event.proc()

				else:
					logsupport.Logs.Log("Unknown main event {}".format(repr(event)), severity=ConsoleError, hb=True,
										tb=False)
				if time.time() - postwaittime > controlevents.latencynotification and not timers.LongOpInProgress:
					# this loop took a long time
					if not config.Exiting:
						logsupport.Logs.Log(
							"Slow loop at {} took {} for {}".format(time.time(), time.time() - postwaittime, event),
							hb=True, homeonly=True)
				self.HBEvents.Entry('End Event Loop took: {}'.format(time.time() - postwaittime))
		except Exception as E:
			logsupport.Logs.Log('Main display loop had exception: {}'.format(repr(E)))
			tbinfo = traceback.format_exc().splitlines()
			for l in tbinfo:
				logsupport.Logs.Log(l)
			config.ecode = exitutils.ERRORRESTART

		logsupport.Logs.Log('Main GUI loop exiting')


