import os
import sys
import time
from collections import OrderedDict, deque

import exitutils
import alerttasks
import config
import debug
import hw
import logsupport
import screens.__screens as screens
import threadmanager
from controlevents import *
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail, ReportStatus
import historybuffer
import maintscreen
import timers
import failsafe

LateTolerance = 2

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
		self.ScreensDict = {}  # all the sceens by name for setting navigation keys
		self.Chain = 0  # which screen chain is active 0: Main chain 1: Secondary Chain
		self.HBScreens = historybuffer.HistoryBuffer(20, 'Screens')
		self.HBEvents = historybuffer.HistoryBuffer(80, 'Events')

	def Dim(self):
		self.dim = 'Dim'
		hw.GoDim(int(config.sysStore.DimLevel))

	def Brighten(self):
		self.dim = 'Bright'
		hw.GoBright(int(config.sysStore.BrightLevel))

	@staticmethod
	def SetActivityTimer(timeinsecs, dbgmsg):
		pygame.time.set_timer(ACTIVITYTIMER, timeinsecs * 1000)
		debug.debugPrint('Dispatch', 'Set activity timer: ', timeinsecs, ' ', dbgmsg)

	def SwitchScreen(self, NS, newdim, newstate, reason, NavKeys=True):
		ASname = '*None*' if self.AS is None else self.AS.name
		self.HBScreens.Entry(
			NS.name + ' was ' + ASname + ' dim: ' + str(newdim) + ' state: ' + str(newstate) + ' reason: ' + str(
				reason))
		# config.sysStore.SetVal(['CurrentScreen'],NS.name) #todo temp
		config.sysStore.CurrentScreen = NS.name
		oldstate = self.state
		olddim = self.dim
		if NS == screens.HomeScreen:  # always force home state on move to actual home screen
			newstate = 'Home'
		if NS == self.AS:
			debug.debugPrint('Dispatch', 'Null SwitchScreen: ', reason)
			logsupport.Logs.Log('Null switchscreen: ' + reason, hb=True)
		if self.AS is not None and self.AS != NS:
			debug.debugPrint('Dispatch', "Switch from: ", self.AS.name, " to ", NS.name, "Nav=", NavKeys, ' State=',
					   oldstate + '/' + newstate + ':' + olddim + '/' + newdim, ' ', reason)
			self.AS.ExitScreen()
		OS = self.AS
		self.AS = NS
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

		if NavKeys:
			nav = OrderedDict(
				{'prevkey': self.ScreensDict[self.AS.name].prevkey, 'nextkey': self.ScreensDict[self.AS.name].nextkey})
		else:
			nav = {}

		self.state = newstate

		debug.debugPrint('Dispatch', "New watchlist(Main): " + str(self.AS.HubInterestList))

		if OS != self.AS:
			try:
				self.AS.InitDisplay(nav)
			except Exception as e:
				logsupport.Logs.Log('Screen display error: ', self.AS.name, ' ', repr(e), severity=ConsoleError)

	# noinspection PyUnusedLocal
	def NavPress(self, NS, press):
		debug.debugPrint('Dispatch', 'Navkey: ', NS.name, self.state + '/' + self.dim)
		self.SwitchScreen(NS, 'Bright', 'NonHome', 'Nav Press')

	def MainControlLoop(self, InitScreen):

		TimerName = 0

		config.sysStore.ErrorNotice = -1  # don't pester for errors during startup

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
					PostControl(ISYAlert, hub='DS-NodeChange', alert=a)
			elif a.type == 'VarChange':
				a.state = 'Init'
				# Note: VarChange alerts don't need setup because the store has an alert proc
				pass
			elif a.type == 'Init':
				a.Invoke()
			else:
				logsupport.Logs.Log("Internal error - unknown alert type: ", a.type, ' for ', a.name, severity=ConsoleError, tb=False)

		logsupport.Logs.livelog = False  # turn off logging to the screen

		with open(config.homedir + "/.ConsoleStart", "a") as f:
			f.write(str(time.time()) + '\n')
		if config.Running:  # allow for a very early restart request from things like autoversion
			self.SwitchScreen(InitScreen, 'Bright', 'Home', 'Startup')

		statusperiod = time.time()
		cyclehistory = deque((-1, -1, -1, -1, -1, -1, -1, -1, -1, -1))
		prevstatus = ''

		failsafe.Injector.start()
		failsafe.Failsafe.start()
		logsupport.Logs.Log('Starting master watchdog {} for {}'.format(failsafe.Failsafe.pid, config.Console_pid))

		while config.Running:  # Operational Control Loop
			failsafe.KeepAlive.set()
			nowtime = time.time()
			postwaittime = nowtime
			if statusperiod <= nowtime or prevstatus != config.consolestatus:
				ReportStatus(config.consolestatus)
				prevstatus = config.consolestatus
				statusperiod = nowtime + 60

			if not threadmanager.Watcher.is_alive():
				logsupport.Logs.Log("Threadmanager Failure", severity=ConsoleError,tb=False)
				exitutils.Exit(exitutils.ERRORRESTART)

			os.utime(config.homedir + "/.ConsoleStart", None)
			if debug.dbgStore.GetVal('StatesDump'):
				debug.dbgStore.SetVal('StatesDump',False)
				for h, hub in config.Hubs.items():
					print('States dump for hub: ',h)
					hub.StatesDump()

			nowtime2 = time.time()
			if self.Deferrals:  # an event was deferred mid screen touches - handle now
				event = self.Deferrals.pop(0)
				debug.debugPrint('EventList', 'Deferred Event Pop', event)
			elif debug.dbgStore.GetVal('QDump'):
				events = pygame.fastevent.get()
				if events:
					debug.debugPrint('QDump', 'Time: ', time.time())
					for e in events:
						self.Deferrals.append(e)
						debug.debugPrint('QDump', e, e.type)
					else:
						debug.debugPrint('QDump', "Empty queue")
						time.sleep(0.01)
				event = pygame.event.Event(NOEVENT, dict={'inject':time.time(),'defer':True})
			else:

				event = pygame.fastevent.wait()  # wait for the next event: touches, timeouts, ISY changes on note
				postwaittime = time.time()
				if hasattr(event, 'TargetTime'):
					if (postwaittime - nowtime2 > .5) and (postwaittime - event.TargetTime > LateTolerance):
						self.HBEvents.Entry("Main event waited {} at {} in loop started at {} for {}".format(postwaittime-nowtime2,postwaittime, nowtime,event))
				else:
					if (time.time() - nowtime2 > 4):
						self.HBEvents.Entry(
							"Main event waited (nonsched) {} at {} in loop started at {} for {}".format(time.time() - nowtime2,
																							 time.time(), nowtime,
																							 event))

			nowtime3 = time.time()
			cyclehistory.pop()
			cyclehistory.appendleft((nowtime%1000, nowtime2%1000, nowtime3%1000, event.type)) #todo del

			if event.type == NOEVENT:
				#print('Saw NOEVENT {} after injection'.format(time.time()-event.inject))
				self.HBEvents.Entry('Saw NOEVENT {} after injection at {}'.format(time.time()-event.inject, event.inject))
				pass # these appear to make sure loop is running
			elif event.type == pygame.MOUSEBUTTONDOWN:
				self.HBEvents.Entry('MouseDown' + str(event.pos))
				debug.debugPrint('Touch', 'MouseDown' + str(event.pos) + repr(event))
				# screen touch events; this includes touches to non-sensitive area of screen
				self.SetActivityTimer(self.AS.DimTO, 'Screen touch')
				# refresh non-dimming in all cases including non=sensitive areas
				# this refresh is redundant in some cases where the touch causes other activities

				if self.dim == 'Dim':
					# wake up the screen and if in a cover state go home
					config.consolestatus = 'active'
					if self.state == 'Cover':
						self.SwitchScreen(screens.HomeScreen, 'Bright', 'Home', 'Wake up from cover')
					else:
						self.Brighten()  # if any other screen just brighten
					continue  # wakeup touches are otherwise ignored

				# Screen was not Dim so the touch was meaningful
				pos = event.pos
				tapcount = 1
				pygame.time.delay(config.sysStore.MultiTapTime)
				while True:
					eventx = pygame.fastevent.poll()
					if eventx.type == pygame.MOUSEBUTTONDOWN:
						self.HBEvents.Entry('Follow MouseDown' + str(event.pos))
						debug.debugPrint('Touch', 'Follow MouseDown' + str(event.pos) + repr(event))
						tapcount += 1
						pygame.time.delay(config.sysStore.MultiTapTime)
					elif eventx.type == NOEVENT:
						break
					else:
						if eventx.type >= pygame.USEREVENT:  # it isn't a screen related event
							self.HBEvents.Entry('Defer' + repr(eventx))
							self.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out
						else:
							debug.debugPrint('Touch',
											 'Other event ' + pygame.event.event_name(eventx.type) + repr(eventx))
						# Future add handling for hold here with checking for MOUSE UP etc.
				if tapcount == 3:
					# Switch screen chains
					if screens.HomeScreen != screens.HomeScreen2:  # only do if there is a real secondary chain
						if self.Chain == 0:
							self.Chain = 1
							self.SwitchScreen(screens.HomeScreen2, 'Bright', 'NonHome', 'Chain switch to secondary')
						else:
							self.Chain = 0
							self.SwitchScreen(screens.HomeScreen, 'Bright', 'Home', 'Chain switch to main')
					continue

				elif tapcount > 3:
					# Go to maintenance
					timers.StartLongOp('maintenance') # todo a bit ugly - start long op here but end in gohome in maint screen
					self.SwitchScreen(maintscreen.MaintScreen, 'Bright', 'Maint', 'Tap to maintenance', NavKeys=False)
					continue

				if self.AS.Keys is not None:
					for K in self.AS.Keys.values():
						if K.touched(pos):
							if tapcount == 1:
								if K.Proc is not None: K.Proc(config.PRESS)
							else:
								if K.Proc is not None: K.Proc(config.FASTPRESS)

				for K in self.AS.NavKeys.values():
					if K.touched(pos):
						K.Proc(config.PRESS)  # same action whether single or double tap

			elif event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
				debug.debugPrint('Touch', 'Other mouse event ' + pygame.event.event_name(event.type) + repr(event))

			# ignore for now - handle more complex gestures here if ever needed

			elif event.type == ACTIVITYTIMER:
				debug.debugPrint('Dispatch', 'Activity timer fired State=', self.state, '/', self.dim)

				if self.dim == 'Bright':
					self.HBEvents.Entry('ActivityTimer(Bright) state: {}'.format(self.state))
					config.consolestatus = 'idle'
					self.Dim()
					self.SetActivityTimer(self.AS.PersistTO, 'Go dim and wait persist')
				else:
					self.HBEvents.Entry('ActivityTimer(non-Bright) state: {}'.format(self.state))
					if self.state == 'NonHome':
						self.SwitchScreen(screens.HomeScreen, 'Dim', 'Home', 'Dim nonhome to dim home')
					elif self.state == 'Home':
						self.SwitchScreen(screens.DimIdleList[0], 'Dim', 'Cover', 'Go to cover', NavKeys=False)
						# rotate covers - save even if only 1 cover
						screens.DimIdleList = screens.DimIdleList[1:] + [screens.DimIdleList[0]]
						screens.DimIdleTimes = screens.DimIdleTimes[1:] + [screens.DimIdleTimes[0]]
					elif self.state == 'Cover':
						if len(screens.DimIdleList) > 1:
							self.SwitchScreen(screens.DimIdleList[0], 'Dim', 'Cover', 'Go to next cover', NavKeys=False)
							screens.DimIdleList = screens.DimIdleList[1:] + [screens.DimIdleList[0]]
							screens.DimIdleTimes = screens.DimIdleTimes[1:] + [screens.DimIdleTimes[0]]
					else:  # Maint or Alert - todo?
						logsupport.Logs.Log('Activity timer fired while in state: {}'.format(self.state),severity=ConsoleWarning)
						debug.debugPrint('Dispatch', 'TO while in: ', self.state)


			elif event.type == GeneralRepaint:
				self.HBEvents.Entry('General Repaint' + repr(event))
				debug.debugPrint('Dispatch', 'General Repaint Event', event)
				self.AS.InitDisplay()

			elif event.type == HubNodeChange:
				self.HBEvents.Entry('Hub Change' + repr(event))
				debug.debugPrint('Dispatch', 'Hub Change Event', event)
				if hasattr(event, 'node'):
					self.AS.NodeEvent(hub=event.hub, node=event.node, value=event.value)
				elif hasattr(event, 'varinfo'):
					self.AS.NodeEvent(hub=event.hub, varinfo=event.varinfo)
				else:
					debug.debugPrint('Dispatch', 'Bad Node Change Event: ', event)
					logsupport.Logs.Log('Bad Node Change Event ', event, severity=ConsoleWarning)

			elif event.type in (ISYVar, ISYAlert):
				self.HBEvents.Entry('Var or Alert' + repr(event))
				evtype = 'variable' if event.type == ISYVar else 'node'
				debug.debugPrint('Dispatch', 'ISY ', evtype, ' change', event)
				alert = event.alert
				if alert.state in ('Armed', 'Init'):
					if alert.trigger.IsTrue():  # alert condition holds
						if alert.trigger.delay != 0:  # delay invocation
							alert.state = 'Delayed'
							debug.debugPrint('Dispatch', "Post with delay:", alert.name, alert.trigger.delay)
							TimerName += 1
							timers.OnceTimer(alert.trigger.delay, start=True, name='MainLoop'+str(TimerName),proc=alerttasks.HandleDeferredAlert,param=alert)
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
					self.SwitchScreen(screens.HomeScreen, 'Dim', 'Home', 'Cleared alert')
				elif ((alert.state == 'Delayed') or (alert.state == 'Deferred')) and not alert.trigger.IsTrue():
					# condition changed under a pending action (screen or proc) so just cancel and rearm
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
					debug.debugPrint('Dispatch', 'ISYVar/ISYAlert passing: ', alert.state, alert.trigger.IsTrue(), event,
							   alert)
				# Armed and false: irrelevant report
				# Active and true: extaneous report
				# Delayed or deferred and true: redundant report

			elif event.type == SchedEvent:
				self.HBEvents.Entry('Sched event {}'.format(repr(event)))
				#print('Sched event {}'.format(repr(event)))
				eventnow = time.time()
				diff = eventnow - event.TargetTime
				if abs(diff) > LateTolerance:
					#print('{}: Late timer: {}  {}'.format(time.time(),diff%1000 ,repr(event))) #todo change to late event log
					logsupport.Logs.Log('Timer late by {} seconds. Event: {}'.format(diff, repr(event)), severity=ConsoleWarning, hb=True, localonly=True)
					self.HBEvents.Entry('Event late by {} target: {} now: {}'.format(diff,event.TargetTime, eventnow))
					self.HBEvents.Entry('Cycle history: {}'.format(cyclehistory))
				event.proc(event)

			elif event.type == RunProc:
				self.HBEvents.Entry('Run procedure {}'.format(event.name))
				event.proc()

			else:
				logsupport.Logs.Log("Unknown main event {}".format(repr(event)), severity=ConsoleError, hb=True,
									tb=False)
			if time.time() - postwaittime > 2 and not timers.LongOpInProgress: # this loop took a long time
				logsupport.Logs.Log("Slow loop at {} took {} for {}".format(time.time(),time.time()-postwaittime,event),severity=ConsoleWarning, hb=True, localonly=True)

		logsupport.Logs.Log('Main Loop Exit: ', config.ecode)
		timers.ShutTimers()
		pygame.quit()
		sys.exit(config.ecode)

