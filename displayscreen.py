import time

import pygame
import webcolors

import config
import hw
from eventlist import EventItem, EventList
import threading
from config import debugPrint
from logsupport import ConsoleWarning, ConsoleError
from collections import OrderedDict
from eventlist import AlertEventItem, ProcEventItem, ScreenEventItem

wc = webcolors.name_to_rgb


class DisplayScreen(object):
	def __init__(self):

		config.debugPrint("Main", "Screensize: ", config.screenwidth, config.screenheight)
		config.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))
		config.Logs.Log(
			"Scaling ratio: " + "{0:.2f}".format(config.dispratioW) + ':' + "{0:.2f}".format(config.dispratioH))

		self.dim = 'Bright'  # either Bright or Dim (or '' for don't change when a parameter
		self.state = 'Home'  # one of Home, NonHome, Maint, Cover, Alert

		# Central Task List
		self.Tasks = EventList()
		self.WatchNodes = []  # Nodes that should be watched due to alerts
		self.WatchVars = []  # Variables that should be watched for changes (entry is (vartype,varid)
		self.Deferrals = []
		self.WatchVarVals = {}  # most revent reported watched variable values todo - should initialize?

		# Events that drive the main control loop
		self.ACTIVITYTIMER = pygame.event.Event(
			pygame.USEREVENT + 1)  # screen activity timing (Dimming, persistence etc)
		self.ISYChange = pygame.USEREVENT + 2  # Node state change in a current screen watched node on the ISY
		self.ISYAlert = pygame.USEREVENT + 3  # Mpde state change in watched node for alerts
		self.ISYVar = pygame.USEREVENT + 4  # Var value change for a watched variable on ISY

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
		pygame.time.set_timer(self.ACTIVITYTIMER.type, timeinsecs*1000)
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
		self.AS.EnterScreen()
		config.toDaemon.put(['Status'] + self.AS.NodeWatch + self.WatchNodes)
		debugPrint('Dispatch', "New watchlist(Main): " + str(self.AS.NodeWatch) + str(self.WatchNodes))
		self.AS.InitDisplay(nav)

	def NavPress(self, NS, press):
		debugPrint('Dispatch', 'Navkey: ', NS.name, self.state + '/' + self.dim)
		self.SwitchScreen(NS, 'Bright', 'NonHome', 'Nav Press')

	def MainControlLoop(self, InitScreen):

		def Qhandler():
			# integrate the daemon reports into the pygame event stream
			while True:

				debugPrint('DaemonCtl', "Q size at main loop ", config.fromDaemon.qsize())
				item = config.fromDaemon.get()

				if item[0] == "Log":
					config.Logs.Log(item[1], severity=item[2])
				elif item[0] == "Node":

					if item[1] in self.WatchNodes:
						debugPrint('DaemonCtl', 'ISY reports change(alert):', str(item))
						notice = pygame.event.Event(self.ISYAlert, node=item[1], value=item[2])
					else:
						debugPrint('DaemonCtl', time.time(), "ISY reports change: ", "Key: ", str(item))
						notice = pygame.event.Event(self.ISYChange, node=item[1], value=item[2])
					pygame.fastevent.post(notice)
				elif item[0] == "VarChg":
					notice = pygame.event.Event(self.ISYVar, vartype=item[1], varid=item[2], value=item[3], eid=item[4])
					self.WatchVarVals[(item[1], item[2])] = item[3]
					if item[1] == 1:
						debugPrint('DaemonCtl', 'Int variable value change: ', config.ISY.varsIntInv[item[2]], ' <- ',
								   item[3])
					elif item[1] == 2:
						debugPrint('DaemonCtl', 'State variable value change: ', config.ISY.varsStateInv[item[2]],
								   ' <- ', item[3])
					else:
						config.Logs.Log('Bad var message from daemon' + str(item[1]), severity=ConsoleError)
					pygame.fastevent.post(notice)
				else:
					config.Logs.Log("Bad msg from watcher: " + str(item), Severity=ConsoleWarning)

		QH = threading.Thread(name='QH', target=Qhandler)
		QH.setDaemon(True)
		QH.start()
		self.ScreensDict = config.SecondaryDict.copy()
		self.ScreensDict.update(config.MainDict)

		for vid, a in config.Alerts.AlertsList.items():
			if a.type in ('StateVarChange', 'IntVarChange'):
				self.WatchVars.append((a.trigger.vartype, a.trigger.varid, vid))
				self.WatchVarVals[(a.trigger.vartype, a.trigger.varid)] = None
			elif a.type == 'Periodic':
				pass  # todo schedule task
			elif a.type == 'TOD':
				pass  # schedule next occurrence
			elif a.type == 'NodeChange':
				self.WatchNodes.append(a.trigger.nodeaddress)
			a.State = 'Armed'

		config.toDaemon.put(['Vars'] + self.WatchVars)

		self.SwitchScreen(InitScreen, 'Bright', 'Home', 'Startup')

		while True:  # Operational Control Loop

			if self.Deferrals:  # an event was deferred mid screen touches - handle now
				event = self.Deferrals.pop(0)
				debugPrint('EventList', 'Deferred Event Pop', event)
			else:
				event = pygame.fastevent.wait()  # wait for the next event: touches, timeouts, ISY changes on note

			if event.type == pygame.MOUSEBUTTONDOWN:
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
				pos = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
				tapcount = 1
				pygame.time.delay(config.MultiTapTime)
				while True:
					eventx = pygame.fastevent.poll()
					if eventx.type == pygame.MOUSEBUTTONDOWN:
						tapcount += 1
						pygame.time.delay(config.MultiTapTime)
					elif eventx.type == pygame.NOEVENT:
						break
					else:
						if eventx.type >= pygame.USEREVENT:  # it isn't a screen related event
							self.Deferrals.append(eventx)  # defer the event until after the clicks are sorted out
						# todo add handling for hold here with checking for MOUSE UP etc.
				if tapcount == 3:
					# Switch screen chains
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

			elif event.type == self.ACTIVITYTIMER.type:
				debugPrint('Dispatch', 'Activity timer fired State=', self.state, '/', self.dim)

				if self.dim == 'Bright':
					self.Dim()
					self.SetActivityTimer(self.AS.PersistTO, 'Go dim and wait persist')
				else:
					if self.state == 'NonHome':
						self.SwitchScreen(config.HomeScreen, 'Dim', 'Home', 'Dim nonhome to dim home')
					elif self.state == 'Home' or self.state == 'Cover':
						self.SwitchScreen(config.DimIdleList[0], 'Dim', 'Cover', 'Go to cover', NavKeys=False)
						# rotate covers
						config.DimIdleList = config.DimIdleList[1:] + config.DimIdleList[:1]
						config.DimIdleTimes = config.DimIdleTimes[1:] + config.DimIdleTimes[:1]
					else:  # Maint or Alert - todo?
						debugPrint('Dispatch', 'TO while in: ', self.state)

			elif event.type == self.ISYChange:
				debugPrint('Dispatch', 'ISY Change Event', event)
				self.AS.ISYEvent(event.node, event.value)

			elif event.type == self.ISYAlert:
				debugPrint('Dispatch', 'ISY Node Alert', event)
			# todo finish handle delay etc evaluate the alert condition delay, execute, or stop

			elif event.type == self.ISYVar:
				debugPrint('Dispatch', 'ISY variable change', event)
				alert = config.Alerts.AlertsList[event.eid]
				if alert.State == 'Armed' and alert.trigger.IsTrue():
					if alert.trigger.delay <> 0:
						alert.State = 'Delayed'
						debugPrint('Dispatch', "Post with delay:", alert.name, alert.trigger.delay)
						E = AlertEventItem(0, 'delayedvar', alert.trigger.delay, alert)
						config.DS.Tasks.AddTask(E)
					else:
						alert.Invoke()
				elif alert.State == 'Active' and not alert.trigger.IsTrue():
					alert.State = 'Armed'
					self.SwitchScreen(config.HomeScreen, 'Dim', 'Home', 'Cleared alert')
				# condition changed under an active screen call exit and rearm
				elif ((alert.State == 'Delayed') or (alert.State == 'Deferred')) and not alert.trigger.IsTrue():
					# condition changed under a pending action (screen or proc) so just cancel and rearm
					pass  # remove task todo
				else:
					debugPrint('Dispatch', 'ISYVar passing: ', alert.State, alert.trigger.IsTrue(), event, alert)
					pass
				# Armed and false: irrelevant report
				# Active and true: extaneous report
				# Delayed or deferred and true: redundant report
				# todo finish

			elif event.type == self.Tasks.TASKREADY.type:
				E = self.Tasks.PopTask()
				if E is not None:
					if isinstance(E, ProcEventItem):
						debugPrint('Dispatch', 'Task ProcEvent fired with proc: ', E)
						if callable(E.proc):
							E.proc()
					elif isinstance(E, AlertEventItem):
						debugPrint('Dispatch', 'Task AlertEvent fired with screen: ', E)
						E.alert.State = 'Active'
						E.alert.Invoke()
				else:
					debugPrint('Dispatch', 'Empty Task Event fired')
