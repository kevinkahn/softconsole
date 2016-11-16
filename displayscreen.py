import time

import pygame
import webcolors

import config
import hw
from eventlist import EventItem, EventList
import threading
from config import debugPrint
from logsupport import ConsoleWarning

wc = webcolors.name_to_rgb


class DisplayScreen(object):
	(activenonhome, dimnonhome, activehome, dimhome, covers) = range(5)
	states = ['ActiveNonHome', 'DimNonHome', 'ActiveHome', 'DimHone', 'Covers']

	def __init__(self):

		config.debugPrint("Main", "Screensize: ", config.screenwidth, config.screenheight)
		config.Logs.Log("Screensize: " + str(config.screenwidth) + " x " + str(config.screenheight))
		config.Logs.Log(
			"Scaling ratio: " + "{0:.2f}".format(config.dispratioW) + ':' + "{0:.2f}".format(config.dispratioH))

		self.State = self.activehome

		# Central Task List
		self.Tasks = EventList()
		self.StatusNodes = []  # Nodes that should be watched due to alerts
		self.Deferrals = []

		# Time Events
		self.ACTIVITYTIMER = pygame.event.Event(pygame.USEREVENT + 1)

		# ISY Change event
		self.ISYChange = pygame.USEREVENT + 2

		self.AS = None  # Active Screen
		self.EventSet = []

		self.ScreensDict = {}
		self.Chain = 0

	# event set entry is type(owner,id,proc)

	def Dim(self, level):
		hw.GoDim(level)

	def Brighten(self, level):
		hw.GoBright(level)

	def SetActivityTimer(self, timeinsecs, dbgmsg):
		pygame.time.set_timer(self.ACTIVITYTIMER.type, timeinsecs*1000)
		debugPrint('Dispatch', 'Set activity timer: ', timeinsecs, ' ', dbgmsg)

	def SwitchScreen(self, NS, NavKeys=True):
		oldState = self.State
		if NS == config.HomeScreen:
			if (self.State == self.activehome) or (self.State == self.activenonhome):
				self.State = self.activehome
			else:
				self.State = self.dimhome
		if self.AS is not None:
			debugPrint('Dispatch', "Switch from: ", self.AS.name, " to ", NS.name, "Nav=", NavKeys, ' State=',
					   self.states[oldState], '/', self.states[self.State])
			self.AS.ExitScreen()
		self.AS = NS
		if NavKeys:
			nav = [self.ScreensDict[self.AS.name].prevkey, self.ScreensDict[self.AS.name].nextkey]
		else:
			nav = []
		self.AS.EnterScreen()
		config.toDaemon.put(['Status'] + self.AS.NodeWatch + self.StatusNodes)
		debugPrint('Dispatch', "New watchlist(Main): " + str(self.AS.NodeWatch + self.StatusNodes))
		self.AS.InitDisplay(nav)

	def NavPress(self, NS, press):
		# for now don't care about press type
		debugPrint('Dispatch', 'Navkey: ', NS.name, self.State)
		if NS == config.HomeScreen:
			self.State = self.activehome
		else:
			self.State = self.activenonhome
		debugPrint('Dispatch', 'Nav new state:', self.State)
		self.SwitchScreen(NS)
		self.SetActivityTimer(self.AS.DimTO, 'NavPress')

	def MainControlLoop(self, InitScreen):
		# Build the screen loops for prev/next keys

		"""
		Pick a screen, call its enter
		wait for event (press, daemon notification, timer, event queue item)
		respond to the event (Press -> call screen.press(button, type)
		Queued event -. has a proc to call
		command button -> exit screen pick new one?

		"""

		def Qhandler():
			while True:

				debugPrint('Dispatch', "Q size at main loop ", config.fromDaemon.qsize())
				item = config.fromDaemon.get()
				debugPrint('Dispatch', time.time(), "ISY reports change: ", "Key: ", str(item))
				if item[0] == "Log":
					config.Logs.Log(item[1], severity=item[2])
				elif item[0] == "Node":
					print "QH: ", item
					notice = pygame.event.Event(self.ISYChange, {"Info": item})
					pygame.fastevent.post(notice)
				else:
					config.Logs.Log("Bad msg from watcher: " + str(item), Severity=ConsoleWarning)

		QH = threading.Thread(name='QH', target=Qhandler)
		QH.setDaemon(True)
		QH.start()
		self.ScreensDict = config.SecondaryDict.copy()
		self.ScreensDict.update(config.MainDict)

		self.SwitchScreen(InitScreen)
		self.Brighten(self.AS.BrightLevel)
		self.SetActivityTimer(self.AS.DimTO, 'Startup')

		while True:

			if self.Deferrals:  # an event was deferred
				event = self.Deferrals.pop(0)
				debugPrint('EventList', 'Deferred Event Pop', event)
			else:
				event = pygame.fastevent.wait()

			if event.type == pygame.MOUSEBUTTONDOWN:
				self.SetActivityTimer(self.AS.DimTO, 'Screen touch')

				if self.State == self.activenonhome or self.State == self.activehome:
					pass
				# then fall through to handle the clicks; note that this lets the dim happen a little less than DimTO after last click for multiclick

				elif self.State == self.dimnonhome:
					self.State = self.activenonhome
					self.Brighten(self.AS.BrightLevel)
					continue  # ignore the tap that wakes the screen up

				elif self.State == self.dimhome:
					self.State = self.activehome
					self.Brighten(self.AS.BrightLevel)
					continue  # ignore the tap that wakes the screen up

				elif self.State == self.covers:
					self.State = self.activehome
					self.SwitchScreen(config.HomeScreen)
					self.Brighten(self.AS.BrightLevel)
					continue  # ignore the tap that wakes the screen up

				else:
					pass  # FatalError
				# error

				# Handle the touch as meaningful
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
						self.State = self.activenonhome
						self.SwitchScreen(config.HomeScreen2)
					else:
						self.Chain = 0
						self.State = self.activehome
						self.SwitchScreen(config.HomeScreen)
					continue

				elif tapcount > 3:
					# Go to maintenance
					self.SwitchScreen(config.MaintScreen, NavKeys=False)
					self.State = self.activenonhome
					continue

				for K in self.AS.Keys:
					if K.touched(pos):
						if tapcount == 1:
							K.Proc(config.PRESS)
						else:
							K.Proc(config.FASTPRESS)

				for K in self.AS.NavKeys:
					if K.touched(pos):
						K.Proc(config.PRESS)  # same action whether single or double tap

			elif event.type == self.ACTIVITYTIMER.type:
				oldState = self.State

				if self.State == self.activenonhome:
					# There is a non-home screen up time to dim it
					self.Dim(self.AS.DimLevel)  # set dim level based on AS
					self.State = self.dimnonhome
					self.SetActivityTimer(self.AS.PersistTO, "Dim nonhome and wait persist")
				elif self.State == self.dimnonhome:
					# There is a non=home screen up that is dim time to go home
					self.State = self.dimhome
					self.SetActivityTimer(self.AS.PersistTO, "Direct to dim home to persist")
					self.SwitchScreen(config.HomeScreen)
				elif self.State == self.activehome:
					# The Home screen is up and no dim - time to dim it
					self.Dim(self.AS.DimLevel)
					self.State = self.dimhome
					self.SetActivityTimer(self.AS.PersistTO, "Dim home and wait persist")
				elif self.State == self.dimhome:
					# The Home screen is up and dim - time to go to a cover screen
					self.State = self.covers
					self.SetActivityTimer(config.DimIdleTimes[0], "First cover persist")
					self.SwitchScreen(config.DimIdleList[0], NavKeys=False)
					config.DimIdleList = config.DimIdleList[1:] + config.DimIdleList[:1]
					config.DimIdleTimes = config.DimIdleTimes[1:] + config.DimIdleTimes[:1]
				elif self.State == self.covers:
					# Cover screen is up - move to the next one
					self.SetActivityTimer(config.DimIdleTimes[0], "Later cover persist")
					self.SwitchScreen(config.DimIdleList[0], NavKeys=False)
					config.DimIdleList = config.DimIdleList[1:] + config.DimIdleList[:1]
					config.DimIdleTimes = config.DimIdleTimes[1:] + config.DimIdleTimes[:1]

				else:
					# State value error - fatal error
					pass
				debugPrint('Dispatch', 'Activity timer fired State=', self.states[oldState], '/',
						   self.states[self.State])

			elif event.type == self.ISYChange:
				debugPrint('Dispatch', 'ISY Change Event', event)
				self.AS.ISYEvent(event.__dict__['Info'])


			elif event.type == self.Tasks.TASKREADY.type:
				E = self.Tasks.PopTask()
				if E is not None:
					debugPrint('Dispatch', 'Task Event fired: ', E.screen.name, E.id, E.name)
					E.proc()  # config.DS.Tasks,E.screen,E.id,E.name,E.delay) # todo deal with hidden
				else:
					debugPrint('Dispatch', 'Empty Task Event fired')
