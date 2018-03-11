import pygame
import config
import debug
import hw
import isy
from eventlist import EventItem, EventList
import time
from debug import debugPrint
from logsupport import ConsoleWarning, ConsoleError, ConsoleDetail
from collections import OrderedDict
from eventlist import AlertEventItem, ProcEventItem
import alerttasks
import isyeventmonitor
import os
import errno
import threadmanager

class DisplayScreen(object):
	def __init__(self):

		debug.debugPrint("Main", "Screensize: ", config.screenwidth, config.screenheight)
		config.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))
		config.Logs.Log(
			"Scaling ratio: " + "{0:.2f} W ".format(config.dispratioW) + "{0:.2f} H".format(config.dispratioH))

		self.dim = 'Bright'  # either Bright or Dim (or '' for don't change when a parameter
		self.state = 'Home'  # one of Home, NonHome, Maint, Cover, Alert

		# Central Task List
		self.Tasks = EventList()
		self.WatchNodes = {}  # Nodes that should be watched for changes (key is node address, value is [alerts]
		# todo if ever possible to delete alerts then need id per comment on vars
		self.WatchVars = {}  # Variables that should be watched for changes (key is (vartype,varid) value is [alerts]
		# todo if watches could be dynamic then delete needs to pass in the alert to id which to delete
		self.Deferrals = []
		self.WatchVarVals = {}  # most recent reported watched variable values

		# Events that drive the main control loop
		# self.ACTIVITYTIMER = pygame.event.Event(
		#	pygame.USEREVENT + 1)  # screen activity timing (Dimming, persistence etc)
		self.ACTIVITYTIMER = pygame.USEREVENT + 1
		self.ISYChange = pygame.USEREVENT + 2  # Node state change in a current screen watched node on the ISY
		self.ISYAlert = pygame.USEREVENT + 3  # Mpde state change in watched node for alerts
		self.ISYVar = pygame.USEREVENT + 4  # Var value change for a watched variable on ISY
		self.NOEVENT = pygame.event.Event(pygame.NOEVENT)

		self.AS = None  # Active Screen
		self.ScreensDict = {}  # all the sceens by name for setting navigation keys
		self.Chain = 0  # which screen chain is active 0: Main chain 1: Secondary Chain

	def Dim(self):
		self.dim = 'Dim'
		hw.GoDim(self.AS.DimLevel)

	def Brighten(self):
		self.dim = 'Bright'
		hw.GoBright(self.AS.BrightLevel)

	def SetActivityTimer(self, timeinsecs, dbgmsg):
		pygame.time.set_timer(self.ACTIVITYTIMER, timeinsecs*1000)  #todo .type deleted
		debugPrint('Dispatch', 'Set activity timer: ', timeinsecs, ' ', dbgmsg)

	def SwitchScreen(self, NS, newdim, newstate, reason, NavKeys=True):
		oldstate = self.state
		olddim = self.dim
		if NS == config.HomeScreen:  # always force home state on move to actual home screen
			newstate = 'Home'
		if NS == self.AS:
			debugPrint('Dispatch', 'Null SwitchScreen: ', reason)
			config.Logs.Log('Null switchscreen: ' + reason, severity=ConsoleWarning)
		if self.AS is not None and self.AS <> NS:
			debugPrint('Dispatch', "Switch from: ", self.AS.name, " to ", NS.name, "Nav=", NavKeys, ' State=',
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

		debugPrint('Dispatch', "New watchlist(Main): " + str(self.AS.NodeList) + str(self.WatchNodes))

		if OS != self.AS: self.AS.InitDisplay(nav)

	def NavPress(self, NS, press):
		debugPrint('Dispatch', 'Navkey: ', NS.name, self.state + '/' + self.dim)
		self.SwitchScreen(NS, 'Bright', 'NonHome', 'Nav Press')

	def ResetScreenState(self):
		pass
		# TODO this proc needs to reestablish knowm state (home, non dim, ...) and perhaps flush the event queue, and
		# then somehow get back into the normal flow.  Just doing a return may be sufficient for that.  Use is for
		# dealing with places where I'd like to capture the screen for a message that the local net is down so things are
		# unresponsive  Would a better approach be to define an urgent alert screen?  That runs afoul the need to just
		# wait a bit for the router to come back up

	def MainControlLoop(self, InitScreen):

		threadmanager.StartThreads()

		self.ScreensDict = config.SecondaryDict.copy()
		self.ScreensDict.update(config.MainDict)

		for a in config.Alerts.AlertsList.itervalues():
			a.state = 'Armed'
			config.Logs.Log("Arming " + a.type + " alert " + a.name)
			config.Logs.Log("->" + str(a), severity=ConsoleDetail)
			if a.type in ('StateVarChange', 'IntVarChange', 'LocalVarChange'):
				var = (a.trigger.vartype, a.trigger.varid)
				if var in self.WatchVars:
					self.WatchVars[var].append(a)
				else:
					self.WatchVars[var] = [a]
				self.WatchVarVals[var] = isy.GetVar(var)
				if a.trigger.IsTrue():
					notice = pygame.event.Event(self.ISYVar, alert=a)
					pygame.fastevent.post(notice)
			elif a.type == 'Periodic':
				E = AlertEventItem(id(a), a.name, a)
				self.Tasks.AddTask(E, a.trigger.interval)
			elif a.type == 'TOD':
				pass  # schedule next occurrence todo
			elif a.type == 'NodeChange':
				if a.trigger.nodeaddress in self.WatchNodes:
					self.WatchNodes[a.trigger.nodeaddress].append(a)
				else:
					self.WatchNodes[a.trigger.nodeaddress] = [a]
				if a.trigger.IsTrue():
					notice = pygame.event.Event(config.DS.ISYAlert, alert=a)
					pygame.fastevent.post(notice)
			elif a.type == 'Init':
				a.Invoke()

		while config.digestinginit and config.ISYaddr != '':
			config.Logs.Log("Waiting initial status dump")
			time.sleep(.2)
		with open(config.homedir + "/.ConsoleStart", "a") as f:
			f.write(str(time.time()) + '\n')
		if config.Running:  # allow for a very early restart request from things like autoversion
			self.SwitchScreen(InitScreen, 'Bright', 'Home', 'Startup')

		while config.Running:  # Operational Control Loop

			os.utime(config.homedir + "/.ConsoleStart", None)

			threadmanager.CheckThreads()

			if not config.QH.is_alive() and config.ISYaddr != '':
				config.Logs.Log('Queue handler died, last error:' + str(config.EventMonitor.lasterror), severity=ConsoleError)
				try:
					if config.EventMonitor.lasterror[0] == errno.ENETUNREACH:
						# likely home network down so wait a bit
						config.Logs.Log('Wait for likely router reboot or down',severity=ConsoleError)
						# todo overlay a screen delay message so locked up console is understood
						time.sleep(120)
				except:
					pass

				isyeventmonitor.CreateWSThread()

			if time.time() - config.lastheartbeat > 240 and config.ISYaddr != '':  # twice heartbeat interval
				config.Logs.Log('Lost ISY heartbeat', severity=ConsoleError, tb=False)
				isyeventmonitor.CreateWSThread()

			if self.Deferrals:  # an event was deferred mid screen touches - handle now
				event = self.Deferrals.pop(0)
				debugPrint('EventList', 'Deferred Event Pop', event)
			elif debug.Flags['QDump']:
				events = pygame.fastevent.get()
				if events:
					debugPrint('QDump', 'Time: ', time.time())
					for e in events:
						self.Deferrals.append(e)
						debugPrint('QDump', e, e.type)
					else:
						debugPrint('QDump', "Empty queue")
						time.sleep(0.01)
				event = self.NOEVENT
			else:
				event = pygame.fastevent.wait()  # wait for the next event: touches, timeouts, ISY changes on note

			if event.type == pygame.MOUSEBUTTONDOWN:
				debugPrint('Touch','MouseDown'+str(event.pos))
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
				pygame.time.delay(config.MultiTapTime)
				while True:
					eventx = pygame.fastevent.poll()
					if eventx.type == pygame.MOUSEBUTTONDOWN:
						debugPrint('Touch','Follow MouseDown'+str(event.pos))
						tapcount += 1
						pygame.time.delay(config.MultiTapTime)
					elif eventx.type == pygame.NOEVENT:
						break
					else:
						if eventx.type >= pygame.USEREVENT:  # it isn't a screen related event
							self.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out
						else:
							debugPrint('Touch','Other event '+ pygame.event.event_name(eventx.type) + str(eventx.type))
						# todo add handling for hold here with checking for MOUSE UP etc.
				if tapcount == 3:
					# Switch screen chains
					if config.HomeScreen <> config.HomeScreen2:  # only do if there is a real secondary chain
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

				for K in self.AS.Keys.itervalues():
					if K.touched(pos):
						if tapcount == 1:
							K.Proc(config.PRESS)
						else:
							K.Proc(config.FASTPRESS)

				for K in self.AS.NavKeys.itervalues():
					if K.touched(pos):
						K.Proc(config.PRESS)  # same action whether single or double tap

			elif event.type == self.ACTIVITYTIMER:  # todo .type:
				debugPrint('Dispatch', 'Activity timer fired State=', self.state, '/', self.dim)

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
						debugPrint('Dispatch', 'TO while in: ', self.state)

			elif event.type == self.ISYChange:
				debugPrint('Dispatch', 'ISY Change Event', event)
				if hasattr(event, 'node'):
					self.AS.ISYEvent(node=event.node, value=event.value)
				elif hasattr(event, 'vartype'):
					self.AS.ISYEvent(varid=(event.vartype, event.varid), value=event.value)
				else:
					debugPrint('Dispatch', 'Bad ISYChange Event: ', event)
					config.Logs.Log('Bad ISYChange Event ', event, severity=ConsoleWarning)

			elif event.type in (self.ISYVar, self.ISYAlert):
				evtype = 'variable' if event.type == self.ISYVar else 'node'
				debugPrint('Dispatch', 'ISY ', evtype, ' change', event)
				alert = event.alert
				if alert.state == 'Armed' and alert.trigger.IsTrue():  # alert condition holds
					if alert.trigger.delay <> 0:  # delay invocation
						alert.state = 'Delayed'
						debugPrint('Dispatch', "Post with delay:", alert.name, alert.trigger.delay)
						E = AlertEventItem(id(alert), 'delayed' + evtype, alert)
						self.Tasks.AddTask(E, alert.trigger.delay)
					else:  # invoke now
						debugPrint('Dispatch', "Invoke: ", alert.name)
						alert.Invoke()  # either calls a proc or enters a screen and adjusts alert state appropriately
				elif alert.state == 'Active' and not alert.trigger.IsTrue():  # alert condition has cleared and screen is up
					debugPrint('Dispatch', 'Active alert cleared', alert.name)
					alert.state = 'Armed'  # just rearm the alert
					self.SwitchScreen(config.HomeScreen, 'Dim', 'Home', 'Cleared alert')
				elif ((alert.state == 'Delayed') or (alert.state == 'Deferred')) and not alert.trigger.IsTrue():
					# condition changed under a pending action (screen or proc) so just cancel and rearm
					debugPrint('Dispatch', 'Delayed event cleared before invoke', alert.name)
					alert.state = 'Armed'
					self.Tasks.RemoveAllGrp(id(alert))
				else:
					debugPrint('Dispatch', 'ISYVar/ISYAlert passing: ', alert.state, alert.trigger.IsTrue(), event,
							   alert)
				# Armed and false: irrelevant report
				# Active and true: extaneous report
				# Delayed or deferred and true: redundant report

			elif event.type == self.Tasks.TASKREADY.type:
				E = self.Tasks.PopTask()
				if E is None:
					debugPrint('Dispatch', 'Empty Task Event fired')
					continue  # some deleted task cleared
				if isinstance(E, ProcEventItem):  # internal proc fired
					debugPrint('Dispatch', 'Task ProcEvent fired: ', E)
					if callable(E.proc):
						E.proc()
				elif isinstance(E, AlertEventItem):  # delayed alert screen
					debugPrint('Dispatch', 'Task AlertEvent fired: ', E)
					config.Logs.Log("Alert event fired" + str(E.alert), severity=ConsoleDetail)
					E.alert.Invoke()  # defered or delayed alert firing
					if isinstance(E.alert.trigger, alerttasks.Periodictrigger):
						self.Tasks.AddTask(E, E.alert.trigger.interval)
				else:
					# unknown eevent?
					debugPrint('Dispatch', 'TASKREADY found unknown event: ', E)

		config.Logs.Log('Main Loop Exit: ', config.ecode)
		pygame.quit()
		os._exit(config.ecode)

