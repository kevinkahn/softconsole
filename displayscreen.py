import os
import time
from collections import OrderedDict

import pygame
import exitutils
import alerttasks
import config
import debug
import hw
import logsupport
import threadmanager
from eventlist import AlertEventItem, ProcEventItem
from eventlist import EventList
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail


class DisplayScreen(object):
	def __init__(self):

		debug.debugPrint("Main", "Screensize: ", config.screenwidth, config.screenheight)
		logsupport.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))
		logsupport.Logs.Log(
			"Scaling ratio: " + "{0:.2f} W ".format(config.dispratioW) + "{0:.2f} H".format(config.dispratioH))

		self.dim = 'Bright'  # either Bright or Dim (or '' for don't change when a parameter
		self.state = 'Home'  # one of Home, NonHome, Maint, Cover, Alert

		# Central Task List
		self.Tasks = EventList()
		self.Deferrals = []
		self.WatchVarVals = {}  # most recent reported watched variable values

		# Events that drive the main control loop
		# self.ACTIVITYTIMER = pygame.event.Event(
		#	pygame.USEREVENT + 1)  # screen activity timing (Dimming, persistence etc)
		self.ACTIVITYTIMER = pygame.USEREVENT + 1
		self.HubNodeChange = pygame.USEREVENT + 2  # Node state change in a current screen watched node on the ISY
		self.ISYAlert = pygame.USEREVENT + 3  # Mpde state change in watched node for alerts
		self.ISYVar = pygame.USEREVENT + 4  # Var value change for a watched variable on ISY
		self.GeneralRepaint = pygame.USEREVENT + 5 # force a repaint of current screen
		# noinspection PyArgumentList
		self.NOEVENT = pygame.event.Event(pygame.NOEVENT)

		self.AS = None  # Active Screen
		self.ScreensDict = {}  # all the sceens by name for setting navigation keys
		self.Chain = 0  # which screen chain is active 0: Main chain 1: Secondary Chain

	def Dim(self):
		self.dim = 'Dim'
		hw.GoDim(int(config.sysStore.GetVal('DimLevel')))

	def Brighten(self):
		self.dim = 'Bright'
		hw.GoBright(int(config.sysStore.GetVal('BrightLevel')))

	def SetActivityTimer(self, timeinsecs, dbgmsg):
		pygame.time.set_timer(self.ACTIVITYTIMER, timeinsecs*1000)  #todo .type deleted
		debug.debugPrint('Dispatch', 'Set activity timer: ', timeinsecs, ' ', dbgmsg)

	def SwitchScreen(self, NS, newdim, newstate, reason, NavKeys=True):
		oldstate = self.state
		olddim = self.dim
		if NS == config.HomeScreen:  # always force home state on move to actual home screen
			newstate = 'Home'
		if NS == self.AS:
			debug.debugPrint('Dispatch', 'Null SwitchScreen: ', reason)
			logsupport.Logs.Log('Null switchscreen: ' + reason, severity=ConsoleWarning)
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
					self.SetActivityTimer(config.DimIdleTimes[0], reason + ' using cover time')
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
		# todo - just wait for timer to switch screen?

	# noinspection PyUnusedLocal
	def NavPress(self, NS, press):
		debug.debugPrint('Dispatch', 'Navkey: ', NS.name, self.state + '/' + self.dim)
		self.SwitchScreen(NS, 'Bright', 'NonHome', 'Nav Press')

	def MainControlLoop(self, InitScreen):

		threadmanager.StartThreads()

		self.ScreensDict = config.SecondaryDict.copy()
		self.ScreensDict.update(config.MainDict)

		for a in config.Alerts.AlertsList.values():
			a.state = 'Armed'
			logsupport.Logs.Log("Arming " + a.type + " alert " + a.name)
			logsupport.Logs.Log("->" + str(a), severity=ConsoleDetail)

			if a.type == 'Periodic':
				E = AlertEventItem(id(a), a.name, a)
				self.Tasks.AddTask(E, a.trigger.NextInterval())
			elif a.type == 'NodeChange':
				a.trigger.node.Hub.SetAlertWatch(a.trigger.node, a)
				if a.trigger.IsTrue():
					# noinspection PyArgumentList
					notice = pygame.event.Event(config.DS.ISYAlert, alert=a)
					pygame.fastevent.post(notice)
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

		while config.Running:  # Operational Control Loop

			if not threadmanager.Watcher.is_alive():
				logsupport.Logs.Log("Threadmanager Failure", severity=ConsoleError,tb=False)
				exitutils.Exit(exitutils.ERRORRESTART)

			os.utime(config.homedir + "/.ConsoleStart", None)
			if debug.dbgStore.GetVal('StatesDump'):
				debug.dbgStore.SetVal('StatesDump',False)
				for h, hub in config.Hubs.items():
					print('States dump for hub: ',h)
					hub.StatesDump()

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
				event = self.NOEVENT
			else:
				event = pygame.fastevent.wait()  # wait for the next event: touches, timeouts, ISY changes on note

			if event.type == pygame.MOUSEBUTTONDOWN:
				debug.debugPrint('Touch','MouseDown'+str(event.pos))
				# screen touch events; this includes touches to non-sensitive area of screen
				self.SetActivityTimer(self.AS.DimTO,
									  'Screen touch')  # refresh non-dimming in all cases including non=sensitive areas
				# this refresh is redundant in some cases where the touch causes other activities

				if self.dim == 'Dim':
					# wake up the screen and if in a cover state go home
					if self.state == 'Cover':
						self.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Wake up from cover')
					else:
						self.Brighten()  # if any other screen just brighten
					continue  # wakeup touches are otherwise ignored

				# Screen was not Dim so the touch was meaningful
				pos = event.pos
				tapcount = 1
				pygame.time.delay(config.sysStore.GetVal('MultiTapTime'))
				while True:
					eventx = pygame.fastevent.poll()
					if eventx.type == pygame.MOUSEBUTTONDOWN:
						debug.debugPrint('Touch','Follow MouseDown'+str(event.pos))
						tapcount += 1
						pygame.time.delay(config.sysStore.GetVal('MultiTapTime'))
					elif eventx.type == pygame.NOEVENT:
						break
					else:
						if eventx.type >= pygame.USEREVENT:  # it isn't a screen related event
							self.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out
						else:
							debug.debugPrint('Touch','Other event '+ pygame.event.event_name(eventx.type) + str(eventx.type))
						# Future add handling for hold here with checking for MOUSE UP etc.
				if tapcount == 3:
					# Switch screen chains
					if config.HomeScreen != config.HomeScreen2:  # only do if there is a real secondary chain
						if self.Chain == 0:
							self.Chain = 1
							self.SwitchScreen(config.HomeScreen2, 'Bright', 'NonHome', 'Chain switch to secondary')
						else:
							self.Chain = 0
							self.SwitchScreen(config.HomeScreen, 'Bright', 'Home', 'Chain switch to main')
					continue

				elif tapcount > 3:
					# Go to maintenance
					self.SwitchScreen(config.MaintScreen, 'Bright', 'Maint', 'Tap to maintenance', NavKeys=False)
					continue

				for K in self.AS.Keys.values():
					if K.touched(pos):
						if tapcount == 1:
							K.Proc(config.PRESS)
						else:
							K.Proc(config.FASTPRESS)

				for K in self.AS.NavKeys.values():
					if K.touched(pos):
						K.Proc(config.PRESS)  # same action whether single or double tap

			elif event.type == self.ACTIVITYTIMER:  # todo .type:
				debug.debugPrint('Dispatch', 'Activity timer fired State=', self.state, '/', self.dim)

				if self.dim == 'Bright':
					self.Dim()
					self.SetActivityTimer(self.AS.PersistTO, 'Go dim and wait persist')
				else:
					if self.state == 'NonHome':
						self.SwitchScreen(config.HomeScreen, 'Dim', 'Home', 'Dim nonhome to dim home')
					elif self.state == 'Home':
						self.SwitchScreen(config.DimIdleList[0], 'Dim', 'Cover', 'Go to cover', NavKeys=False)
						# TODO funny case where there are no idle screens and the nav keys don't get drawn on touch
						# rotate covers - save even if only 1 cover
						config.DimIdleList = config.DimIdleList[1:] + config.DimIdleList[:1]
						config.DimIdleTimes = config.DimIdleTimes[1:] + config.DimIdleTimes[:1]
					elif self.state == 'Cover':
						if len(config.DimIdleList) > 1:
							self.SwitchScreen(config.DimIdleList[0], 'Dim', 'Cover', 'Go to next cover', NavKeys=False)
							config.DimIdleList = config.DimIdleList[1:] + config.DimIdleList[:1]
							config.DimIdleTimes = config.DimIdleTimes[1:] + config.DimIdleTimes[:1]
					else:  # Maint or Alert - todo?
						debug.debugPrint('Dispatch', 'TO while in: ', self.state)

			elif event.type == self.GeneralRepaint:
				debug.debugPrint('Dispatch', 'General Repaint Event', event)
				self.AS.InitDisplay()

			elif event.type == self.HubNodeChange:
				debug.debugPrint('Dispatch', 'Hub Change Event', event)
				if hasattr(event, 'node'):
					self.AS.NodeEvent(hub=event.hub, node=event.node, value=event.value)
				elif hasattr(event, 'varinfo'):
					self.AS.NodeEvent(varinfo=event.varinfo)
				else:
					debug.debugPrint('Dispatch', 'Bad Node Change Event: ', event)
					logsupport.Logs.Log('Bad Node Change Event ', event, severity=ConsoleWarning)

			elif event.type in (self.ISYVar, self.ISYAlert):
				evtype = 'variable' if event.type == self.ISYVar else 'node'
				debug.debugPrint('Dispatch', 'ISY ', evtype, ' change', event)
				alert = event.alert
				if alert.state in ('Armed', 'Init'):
					if alert.trigger.IsTrue():  # alert condition holds
						if alert.trigger.delay != 0:  # delay invocation
							alert.state = 'Delayed'
							debug.debugPrint('Dispatch', "Post with delay:", alert.name, alert.trigger.delay)
							E = AlertEventItem(id(alert), 'delayed' + evtype, alert)
							self.Tasks.AddTask(E, alert.trigger.delay)
						else:  # invoke now
							alert.state = 'FiredNoDelay'
							debug.debugPrint('Dispatch', "Invoke: ", alert.name)
							alert.Invoke()  # either calls a proc or enters a screen and adjusts alert state appropriately
					else:
						if alert.state == 'Armed':
							# condition cleared after alert rearmed  - timing in the queue?
							logsupport.Logs.Log('Anomolous Trigger clearing while armed: ', repr(alert),
											severity=ConsoleWarning)
						else:
							alert.state = 'Armed'
							logsupport.Logs.Log('Initial var value for trigger is benign: ', repr(alert),
												severity=ConsoleDetail)
				elif alert.state == 'Active' and not alert.trigger.IsTrue():  # alert condition has cleared and screen is up
					debug.debugPrint('Dispatch', 'Active alert cleared', alert.name)
					alert.state = 'Armed'  # just rearm the alert
					self.SwitchScreen(config.HomeScreen, 'Dim', 'Home', 'Cleared alert')
				elif ((alert.state == 'Delayed') or (alert.state == 'Deferred')) and not alert.trigger.IsTrue():
					# condition changed under a pending action (screen or proc) so just cancel and rearm
					debug.debugPrint('Dispatch', 'Delayed event cleared before invoke', alert.name)
					alert.state = 'Armed'
					self.Tasks.RemoveAllGrp(id(alert))
					self.Tasks.RemoveAllGrp(id(alert.actiontarget))
					# todo - verify this is correct.  Issue is that the alert might have gotten here from a delay or from the
					# alert screen deferring.  The screen uses it's own id for this alert to might be either.  Probably should
					# distinguish based on if delay or defer but doing both should be same id(alert.actiontarget))  originally this was id-alert for some
				    # reason I changed it to id-actiontarget don't know why but it was done while adding HASS this screwed up clearing deferred alerts
					# so switched it back in hopes to remember why the change todo
				else:
					logsupport.Logs.Log("Anomolous change situation  State: ", alert.state, " Alert: ", repr(alert),
										" Trigger IsTue: ",
										alert.trigger.IsTrue(), severity=ConsoleWarning)
					debug.debugPrint('Dispatch', 'ISYVar/ISYAlert passing: ', alert.state, alert.trigger.IsTrue(), event,
							   alert)
				# Armed and false: irrelevant report
				# Active and true: extaneous report
				# Delayed or deferred and true: redundant report

			elif event.type == self.Tasks.TASKREADY.type:
				E = self.Tasks.PopTask()
				if E is None:
					debug.debugPrint('Dispatch', 'Empty Task Event fired')
					continue  # some deleted task cleared
				if isinstance(E, ProcEventItem):  # internal proc fired
					debug.debugPrint('Dispatch', 'Task ProcEvent fired: ', E)
					if callable(E.proc):
						E.proc()
				elif isinstance(E, AlertEventItem):
					debug.debugPrint('Dispatch', 'Task AlertEvent fired: ', E)
					logsupport.Logs.Log("Alert event fired" + str(E.alert), severity=ConsoleDetail)
					E.alert.state = 'Fired'
					if E.alert.trigger.IsTrue():
						E.alert.Invoke()  # defered or delayed or scheduled alert firing or any periodic
					else:
						if isinstance(E.alert.trigger, alerttasks.NodeChgtrigger):
							# why not cleared before getting here?
							logsupport.Logs.Log('Anomolous NodeChgTrigger firing as task: ',repr(E.alert),severity = ConsoleWarning)
						elif isinstance(E.alert.trigger, alerttasks.VarChangeTrigger):
							logsupport.Logs.Log('Anomolous VarChangeTrigger firing as task: ',repr(E.alert),severity=ConsoleWarning)
						E.alert.state = 'Armed'
					if isinstance(E.alert.trigger, alerttasks.Periodictrigger):
						self.Tasks.AddTask(E, E.alert.trigger.NextInterval())
				else:
					# unknown eevent?
					debug.debugPrint('Dispatch', 'TASKREADY found unknown event: ', E)

		logsupport.Logs.Log('Main Loop Exit: ', config.ecode)
		pygame.quit()
		# noinspection PyProtectedMember
		os._exit(config.ecode)

